from flask import Flask, request
from flask_cors import CORS
from config import Config
from .models import db
from sqlalchemy.exc import OperationalError
from sqlalchemy import text
from flask import jsonify
import os
import sys
from .license_guard import LicenseError, validate_license


def _ensure_unique_score_records():
    """
    兼容已有 SQLite 库：
    1) 归档同一学生同一考试的旧重复成绩，保留 id 最大的一条。
    2) 创建唯一索引，防止后续再次写入重复成绩。
    """
    archive_table_sql = """
        CREATE TABLE IF NOT EXISTS score_duplicate_archives (
            original_score_id INTEGER PRIMARY KEY,
            archived_at TEXT NOT NULL,
            student_id INTEGER,
            subject_id INTEGER,
            score REAL,
            remark TEXT,
            exam_task_id INTEGER,
            class_id_snapshot INTEGER,
            term TEXT,
            create_time TEXT,
            update_time TEXT,
            kept_score_id INTEGER,
            archive_reason TEXT NOT NULL
        );
    """
    duplicate_groups_sql = """
        SELECT COUNT(*)
        FROM (
            SELECT student_id, exam_task_id
            FROM scores
            WHERE student_id IS NOT NULL AND exam_task_id IS NOT NULL
            GROUP BY student_id, exam_task_id
            HAVING COUNT(*) > 1
        ) duplicate_groups;
    """
    duplicate_rows_sql = """
        SELECT COUNT(*)
        FROM scores s
        JOIN (
            SELECT student_id, exam_task_id, MAX(id) AS keep_id
            FROM scores
            WHERE student_id IS NOT NULL AND exam_task_id IS NOT NULL
            GROUP BY student_id, exam_task_id
            HAVING COUNT(*) > 1
        ) keep_rows
            ON s.student_id = keep_rows.student_id
            AND s.exam_task_id = keep_rows.exam_task_id
        WHERE s.id <> keep_rows.keep_id;
    """
    archive_duplicates_sql = """
        INSERT OR IGNORE INTO score_duplicate_archives (
            original_score_id,
            archived_at,
            student_id,
            subject_id,
            score,
            remark,
            exam_task_id,
            class_id_snapshot,
            term,
            create_time,
            update_time,
            kept_score_id,
            archive_reason
        )
        SELECT
            s.id,
            datetime('now', 'localtime'),
            s.student_id,
            s.subject_id,
            s.score,
            s.remark,
            s.exam_task_id,
            s.class_id_snapshot,
            s.term,
            s.create_time,
            s.update_time,
            keep_rows.keep_id,
            '同一学生同一考试存在重复成绩，建立唯一约束前自动归档旧记录'
        FROM scores s
        JOIN (
            SELECT student_id, exam_task_id, MAX(id) AS keep_id
            FROM scores
            WHERE student_id IS NOT NULL AND exam_task_id IS NOT NULL
            GROUP BY student_id, exam_task_id
            HAVING COUNT(*) > 1
        ) keep_rows
            ON s.student_id = keep_rows.student_id
            AND s.exam_task_id = keep_rows.exam_task_id
        WHERE s.id <> keep_rows.keep_id;
    """
    delete_duplicates_sql = """
        DELETE FROM scores
        WHERE id IN (
            SELECT s.id
            FROM scores s
            JOIN (
                SELECT student_id, exam_task_id, MAX(id) AS keep_id
                FROM scores
                WHERE student_id IS NOT NULL AND exam_task_id IS NOT NULL
                GROUP BY student_id, exam_task_id
                HAVING COUNT(*) > 1
            ) keep_rows
                ON s.student_id = keep_rows.student_id
                AND s.exam_task_id = keep_rows.exam_task_id
            WHERE s.id <> keep_rows.keep_id
        );
    """
    unique_index_sql = """
        CREATE UNIQUE INDEX IF NOT EXISTS uq_scores_student_exam_task
        ON scores(student_id, exam_task_id)
        WHERE student_id IS NOT NULL AND exam_task_id IS NOT NULL;
    """

    db.session.execute(text(archive_table_sql))
    duplicate_groups = db.session.execute(text(duplicate_groups_sql)).scalar() or 0
    duplicate_rows = db.session.execute(text(duplicate_rows_sql)).scalar() or 0

    if duplicate_rows:
        db.session.execute(text(archive_duplicates_sql))
        db.session.execute(text(delete_duplicates_sql))
        print(
            ">> [SQLite] 成绩重复记录已清理: "
            f"{duplicate_groups} 组，归档并删除 {duplicate_rows} 条旧记录。"
        )

    db.session.execute(text(unique_index_sql))


def _ensure_unique_class_records():
    """
    兼容已有 SQLite 库：
    1) 合并同一入学届同一班号的重复班级，保留 id 最小的一条。
    2) 将学生、成绩班级快照、任课/班主任分配和审计快照引用迁到保留班级。
    3) 创建唯一索引，防止后续再次出现重复班级。
    """
    duplicate_groups_sql = """
        SELECT COUNT(*)
        FROM (
            SELECT entry_year, class_num
            FROM classes
            GROUP BY entry_year, class_num
            HAVING COUNT(*) > 1
        ) duplicate_groups;
    """
    duplicate_rows_sql = """
        SELECT COUNT(*) FROM class_duplicate_merge_map;
    """
    drop_merge_map_sql = """
        DROP TABLE IF EXISTS class_duplicate_merge_map;
    """
    create_merge_map_sql = """
        CREATE TEMP TABLE class_duplicate_merge_map AS
        SELECT c.id AS duplicate_id, keep_rows.keep_id
        FROM classes c
        JOIN (
            SELECT entry_year, class_num, MIN(id) AS keep_id
            FROM classes
            GROUP BY entry_year, class_num
            HAVING COUNT(*) > 1
        ) keep_rows
            ON c.entry_year = keep_rows.entry_year
            AND c.class_num = keep_rows.class_num
        WHERE c.id <> keep_rows.keep_id;
    """
    class_archive_table_sql = """
        CREATE TABLE IF NOT EXISTS class_duplicate_archives (
            original_class_id INTEGER PRIMARY KEY,
            archived_at TEXT NOT NULL,
            entry_year INTEGER NOT NULL,
            class_num INTEGER NOT NULL,
            kept_class_id INTEGER NOT NULL,
            moved_student_count INTEGER NOT NULL DEFAULT 0,
            moved_score_snapshot_count INTEGER NOT NULL DEFAULT 0,
            moved_course_assignment_count INTEGER NOT NULL DEFAULT 0,
            moved_head_teacher_assignment_count INTEGER NOT NULL DEFAULT 0,
            moved_audit_log_count INTEGER NOT NULL DEFAULT 0,
            archive_reason TEXT NOT NULL
        );
    """
    course_archive_table_sql = """
        CREATE TABLE IF NOT EXISTS course_assignment_duplicate_archives (
            original_assignment_id INTEGER PRIMARY KEY,
            archived_at TEXT NOT NULL,
            teacher_id INTEGER,
            class_id INTEGER,
            kept_class_id INTEGER,
            subject_id INTEGER,
            academic_year INTEGER,
            kept_assignment_id INTEGER,
            archive_reason TEXT NOT NULL
        );
    """
    head_teacher_archive_table_sql = """
        CREATE TABLE IF NOT EXISTS head_teacher_duplicate_archives (
            original_assignment_id INTEGER PRIMARY KEY,
            archived_at TEXT NOT NULL,
            teacher_id INTEGER,
            class_id INTEGER,
            kept_class_id INTEGER,
            academic_year INTEGER,
            kept_assignment_id INTEGER,
            archive_reason TEXT NOT NULL
        );
    """
    archive_classes_sql = """
        INSERT OR IGNORE INTO class_duplicate_archives (
            original_class_id,
            archived_at,
            entry_year,
            class_num,
            kept_class_id,
            moved_student_count,
            moved_score_snapshot_count,
            moved_course_assignment_count,
            moved_head_teacher_assignment_count,
            moved_audit_log_count,
            archive_reason
        )
        SELECT
            c.id,
            datetime('now', 'localtime'),
            c.entry_year,
            c.class_num,
            class_map.keep_id,
            (SELECT COUNT(*) FROM students WHERE class_id = c.id),
            (SELECT COUNT(*) FROM scores WHERE class_id_snapshot = c.id),
            (SELECT COUNT(*) FROM course_assignments WHERE class_id = c.id),
            (SELECT COUNT(*) FROM assign_head_teacher WHERE class_id = c.id),
            (SELECT COUNT(*) FROM audit_logs WHERE class_id_snapshot = c.id),
            '同一入学届同一班号存在重复班级，建立唯一约束前自动合并'
        FROM classes c
        JOIN class_duplicate_merge_map class_map ON c.id = class_map.duplicate_id;
    """
    archive_course_conflicts_sql = """
        INSERT OR IGNORE INTO course_assignment_duplicate_archives (
            original_assignment_id,
            archived_at,
            teacher_id,
            class_id,
            kept_class_id,
            subject_id,
            academic_year,
            kept_assignment_id,
            archive_reason
        )
        WITH class_map AS (
            SELECT duplicate_id, keep_id FROM class_duplicate_merge_map
        ),
        normalized AS (
            SELECT
                ca.id,
                ca.teacher_id,
                ca.class_id,
                COALESCE(class_map.keep_id, ca.class_id) AS normalized_class_id,
                ca.subject_id,
                ca.academic_year,
                FIRST_VALUE(ca.id) OVER (
                    PARTITION BY
                        COALESCE(class_map.keep_id, ca.class_id),
                        ca.subject_id,
                        ca.academic_year
                    ORDER BY
                        CASE WHEN class_map.keep_id IS NULL THEN 0 ELSE 1 END,
                        ca.id DESC
                ) AS kept_assignment_id,
                ROW_NUMBER() OVER (
                    PARTITION BY
                        COALESCE(class_map.keep_id, ca.class_id),
                        ca.subject_id,
                        ca.academic_year
                    ORDER BY
                        CASE WHEN class_map.keep_id IS NULL THEN 0 ELSE 1 END,
                        ca.id DESC
                ) AS row_no
            FROM course_assignments ca
            LEFT JOIN class_map ON ca.class_id = class_map.duplicate_id
            WHERE
                class_map.keep_id IS NOT NULL
                OR EXISTS (
                    SELECT 1 FROM class_map keep_map WHERE keep_map.keep_id = ca.class_id
                )
        )
        SELECT
            id,
            datetime('now', 'localtime'),
            teacher_id,
            class_id,
            normalized_class_id,
            subject_id,
            academic_year,
            kept_assignment_id,
            '重复班级合并后同一班级同一学年同一科目任课分配冲突，自动归档冲突记录'
        FROM normalized
        WHERE row_no > 1;
    """
    delete_course_conflicts_sql = """
        WITH class_map AS (
            SELECT duplicate_id, keep_id FROM class_duplicate_merge_map
        ),
        normalized AS (
            SELECT
                ca.id,
                ROW_NUMBER() OVER (
                    PARTITION BY
                        COALESCE(class_map.keep_id, ca.class_id),
                        ca.subject_id,
                        ca.academic_year
                    ORDER BY
                        CASE WHEN class_map.keep_id IS NULL THEN 0 ELSE 1 END,
                        ca.id DESC
                ) AS row_no
            FROM course_assignments ca
            LEFT JOIN class_map ON ca.class_id = class_map.duplicate_id
            WHERE
                class_map.keep_id IS NOT NULL
                OR EXISTS (
                    SELECT 1 FROM class_map keep_map WHERE keep_map.keep_id = ca.class_id
                )
        )
        DELETE FROM course_assignments
        WHERE id IN (
            SELECT id FROM normalized WHERE row_no > 1
        );
    """
    archive_head_teacher_conflicts_sql = """
        INSERT OR IGNORE INTO head_teacher_duplicate_archives (
            original_assignment_id,
            archived_at,
            teacher_id,
            class_id,
            kept_class_id,
            academic_year,
            kept_assignment_id,
            archive_reason
        )
        WITH class_map AS (
            SELECT duplicate_id, keep_id FROM class_duplicate_merge_map
        ),
        normalized AS (
            SELECT
                ht.id,
                ht.teacher_id,
                ht.class_id,
                COALESCE(class_map.keep_id, ht.class_id) AS normalized_class_id,
                ht.academic_year,
                FIRST_VALUE(ht.id) OVER (
                    PARTITION BY
                        COALESCE(class_map.keep_id, ht.class_id),
                        ht.academic_year
                    ORDER BY
                        CASE WHEN class_map.keep_id IS NULL THEN 0 ELSE 1 END,
                        ht.id DESC
                ) AS kept_assignment_id,
                ROW_NUMBER() OVER (
                    PARTITION BY
                        COALESCE(class_map.keep_id, ht.class_id),
                        ht.academic_year
                    ORDER BY
                        CASE WHEN class_map.keep_id IS NULL THEN 0 ELSE 1 END,
                        ht.id DESC
                ) AS row_no
            FROM assign_head_teacher ht
            LEFT JOIN class_map ON ht.class_id = class_map.duplicate_id
            WHERE
                class_map.keep_id IS NOT NULL
                OR EXISTS (
                    SELECT 1 FROM class_map keep_map WHERE keep_map.keep_id = ht.class_id
                )
        )
        SELECT
            id,
            datetime('now', 'localtime'),
            teacher_id,
            class_id,
            normalized_class_id,
            academic_year,
            kept_assignment_id,
            '重复班级合并后同一班级同一学年班主任分配冲突，自动归档冲突记录'
        FROM normalized
        WHERE row_no > 1;
    """
    delete_head_teacher_conflicts_sql = """
        WITH class_map AS (
            SELECT duplicate_id, keep_id FROM class_duplicate_merge_map
        ),
        normalized AS (
            SELECT
                ht.id,
                ROW_NUMBER() OVER (
                    PARTITION BY
                        COALESCE(class_map.keep_id, ht.class_id),
                        ht.academic_year
                    ORDER BY
                        CASE WHEN class_map.keep_id IS NULL THEN 0 ELSE 1 END,
                        ht.id DESC
                ) AS row_no
            FROM assign_head_teacher ht
            LEFT JOIN class_map ON ht.class_id = class_map.duplicate_id
            WHERE
                class_map.keep_id IS NOT NULL
                OR EXISTS (
                    SELECT 1 FROM class_map keep_map WHERE keep_map.keep_id = ht.class_id
                )
        )
        DELETE FROM assign_head_teacher
        WHERE id IN (
            SELECT id FROM normalized WHERE row_no > 1
        );
    """
    update_reference_sql = [
        """
        UPDATE students
        SET class_id = (
            SELECT keep_id
            FROM class_duplicate_merge_map
            WHERE duplicate_id = students.class_id
        )
        WHERE class_id IN (SELECT duplicate_id FROM class_duplicate_merge_map);
        """,
        """
        UPDATE scores
        SET class_id_snapshot = (
            SELECT keep_id
            FROM class_duplicate_merge_map
            WHERE duplicate_id = scores.class_id_snapshot
        )
        WHERE class_id_snapshot IN (SELECT duplicate_id FROM class_duplicate_merge_map);
        """,
        """
        UPDATE audit_logs
        SET class_id_snapshot = (
            SELECT keep_id
            FROM class_duplicate_merge_map
            WHERE duplicate_id = audit_logs.class_id_snapshot
        )
        WHERE class_id_snapshot IN (SELECT duplicate_id FROM class_duplicate_merge_map);
        """,
        """
        UPDATE course_assignments
        SET class_id = (
            SELECT keep_id
            FROM class_duplicate_merge_map
            WHERE duplicate_id = course_assignments.class_id
        )
        WHERE class_id IN (SELECT duplicate_id FROM class_duplicate_merge_map);
        """,
        """
        UPDATE assign_head_teacher
        SET class_id = (
            SELECT keep_id
            FROM class_duplicate_merge_map
            WHERE duplicate_id = assign_head_teacher.class_id
        )
        WHERE class_id IN (SELECT duplicate_id FROM class_duplicate_merge_map);
        """,
    ]
    delete_duplicate_classes_sql = """
        DELETE FROM classes
        WHERE id IN (SELECT duplicate_id FROM class_duplicate_merge_map);
    """
    unique_index_sql = """
        CREATE UNIQUE INDEX IF NOT EXISTS uq_classes_entry_year_class_num
        ON classes(entry_year, class_num);
    """

    db.session.execute(text(class_archive_table_sql))
    db.session.execute(text(course_archive_table_sql))
    db.session.execute(text(head_teacher_archive_table_sql))
    db.session.execute(text(drop_merge_map_sql))
    db.session.execute(text(create_merge_map_sql))

    duplicate_groups = db.session.execute(text(duplicate_groups_sql)).scalar() or 0
    duplicate_rows = db.session.execute(text(duplicate_rows_sql)).scalar() or 0

    if duplicate_rows:
        db.session.execute(text(archive_classes_sql))
        db.session.execute(text(archive_course_conflicts_sql))
        db.session.execute(text(archive_head_teacher_conflicts_sql))
        db.session.execute(text(delete_course_conflicts_sql))
        db.session.execute(text(delete_head_teacher_conflicts_sql))

        for sql in update_reference_sql:
            db.session.execute(text(sql))

        db.session.execute(text(delete_duplicate_classes_sql))
        print(
            ">> [SQLite] 班级重复记录已合并: "
            f"{duplicate_groups} 组，归档并删除 {duplicate_rows} 条重复班级。"
        )

    db.session.execute(text(unique_index_sql))


def _optimize_sqlite_runtime(app):
    """
    对 SQLite 做运行时优化。
    1) 设置并发友好的 PRAGMA
    2) 为高频查询补齐索引（兼容已有库，无需迁移）
    """
    if db.engine.url.drivername != "sqlite":
        return

    allowed_journal_modes = {"DELETE", "TRUNCATE", "PERSIST", "MEMORY", "WAL", "OFF"}
    allowed_synchronous = {"OFF", "NORMAL", "FULL", "EXTRA"}

    journal_mode = str(app.config.get("SQLITE_JOURNAL_MODE", "DELETE")).strip().upper()
    synchronous = str(app.config.get("SQLITE_SYNCHRONOUS", "FULL")).strip().upper()

    if journal_mode not in allowed_journal_modes:
        print(f">> [SQLite] 无效 SQLITE_JOURNAL_MODE={journal_mode}，回退 DELETE")
        journal_mode = "DELETE"

    if synchronous not in allowed_synchronous:
        print(f">> [SQLite] 无效 SQLITE_SYNCHRONOUS={synchronous}，回退 FULL")
        synchronous = "FULL"

    pragma_sql = [
        f"PRAGMA journal_mode={journal_mode};",
        f"PRAGMA synchronous={synchronous};",
        "PRAGMA temp_store=MEMORY;",
        "PRAGMA foreign_keys=ON;",
    ]

    index_sql = [
        "CREATE INDEX IF NOT EXISTS idx_students_class_status ON students(class_id, status);",
        "CREATE INDEX IF NOT EXISTS idx_students_class_student_id ON students(class_id, student_id);",
        "CREATE INDEX IF NOT EXISTS idx_scores_exam_student ON scores(exam_task_id, student_id);",
        "CREATE INDEX IF NOT EXISTS idx_scores_student_exam ON scores(student_id, exam_task_id);",
        "CREATE INDEX IF NOT EXISTS idx_scores_exam_class_snapshot ON scores(exam_task_id, class_id_snapshot);",
        "CREATE INDEX IF NOT EXISTS idx_course_teacher_subject_year_class ON course_assignments(teacher_id, subject_id, academic_year, class_id);",
        "CREATE INDEX IF NOT EXISTS idx_course_class_subject_year ON course_assignments(class_id, subject_id, academic_year);",
        "CREATE INDEX IF NOT EXISTS idx_exam_task_filter_active ON exam_tasks(entry_year, subject_id, academic_year, is_active, create_time);",
    ]

    try:
        for sql in pragma_sql:
            db.session.execute(text(sql))

        _ensure_unique_class_records()
        _ensure_unique_score_records()

        for sql in index_sql:
            db.session.execute(text(sql))

        db.session.commit()
        print(f">> [SQLite] PRAGMA 已应用: journal_mode={journal_mode}, synchronous={synchronous}")
    except Exception as e:
        db.session.rollback()
        print(f">> [SQLite] 性能优化项应用失败: {e}")


def create_app(config_class=Config):
    license_info = validate_license()
    print(
        ">> [授权] 校验通过: "
        f"{license_info['customer']}，有效期 {license_info['valid_from']} 至 {license_info['valid_until']}"
    )

    # 优先使用当前目录或 exe 目录的 dist，兼容源码运行和打包运行。
    cwd_dist = os.path.join(os.getcwd(), "dist")
    exe_dist = os.path.join(os.path.dirname(sys.executable), "dist")
    dev_dist = "./dist"

    if os.path.exists(cwd_dist):
        dist_path = cwd_dist
        mode_msg = "生产模式 (在当前目录下找到 dist)"
    elif os.path.exists(exe_dist):
        dist_path = exe_dist
        mode_msg = "生产模式 (在exe目录下找到 dist)"
    else:
        dist_path = dev_dist
        mode_msg = "开发模式 (未找到本地dist，尝试使用源码路径)"

    # 启动时输出路径判定，便于排查静态资源问题。
    print("=" * 60)
    print(f"路径判定结果: {mode_msg}")
    print(f"最终使用的前端路径: {dist_path}")
    print(f"路径有效性校验: {os.path.exists(dist_path)}")
    print("=" * 60)

    app = Flask(__name__, static_folder=dist_path, static_url_path="")
    app.config.from_object(config_class)

    # 初始化插件
    CORS(app)
    db.init_app(app)

    @app.errorhandler(413)
    def request_entity_too_large(error):
        return jsonify(msg="上传文件过大，请限制在 16MB 以内"), 413

    @app.errorhandler(OperationalError)
    def handle_db_error(e):
        print(f"数据库错误: {str(e)}")

        if "database is locked" in str(e):
            return jsonify({"msg": "当前提交人数过多，系统繁忙，请稍后重试！"}), 500

        return jsonify({"msg": "数据库操作异常"}), 500

    @app.before_request
    def enforce_license():
        try:
            validate_license()
        except LicenseError as e:
            msg = str(e) or "授权校验失败"
            if request.path.startswith("/api/"):
                return jsonify({"msg": msg}), 403
            return msg, 403

    # 注册蓝图
    from .routes.auth import auth_bp
    from .routes.admin import admin_bp
    from .routes.teacher import teacher_bp

    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(admin_bp, url_prefix="/api/admin")
    app.register_blueprint(teacher_bp, url_prefix="/api/teacher")

    @app.route("/")
    def index():
        if not os.path.exists(app.static_folder):
            return (
                "前端构建文件(dist)未找到，请先执行 npm run build 并将 dist 文件夹拷贝到后端根目录。",
                404,
            )
        return app.send_static_file("index.html")

    @app.errorhandler(404)
    def not_found(e):
        # API 路由保持标准 404；前端路由交给 SPA 入口处理。
        if request.path.startswith("/api/"):
            return jsonify(msg="接口不存在"), 404

        if os.path.exists(os.path.join(app.static_folder, "index.html")):
            return app.send_static_file("index.html")

        return "404 Not Found", 404

    # 创建表并在首次启动时补齐科目基础数据。
    with app.app_context():
        db.create_all()
        _optimize_sqlite_runtime(app)

        from .models import Subject

        target_order = [
            "语文",
            "数学",
            "英语",
            "英语听说",
            "物理",
            "化学",
            "道德与法治",
            "历史",
            "生物",
            "地理",
            "体育与健康",
            "信息科技",
            "美术",
            "音乐",
        ]

        if Subject.query.count() == 0:
            for name in target_order:
                db.session.add(Subject(name=name))
            db.session.commit()
            print(">> [SQLite] 科目表初始化完成。")

        db.session.commit()

    return app
