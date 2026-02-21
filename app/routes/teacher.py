from flask import Blueprint, request, jsonify, send_file, g
import pandas as pd
import io
from urllib.parse import quote
from sqlalchemy import distinct, func, or_

from app.auth_utils import require_auth
from app.models import (
    db,
    Teacher,
    CourseAssignment,
    ClassInfo,
    Subject,
    Student,
    Score,
    ExamTask,
)
from app.services.audit_service import append_score_update_audit_log
from app.services.progress_service import build_class_name, calc_class_record_progress

teacher_bp = Blueprint("teacher", __name__)


@teacher_bp.before_request
def _teacher_auth_guard():
    return require_auth(required_roles={"teacher"})


def _get_current_teacher():
    user = getattr(g, "current_user", None)
    if not user:
        return None, (jsonify({"msg": "未登录或登录已过期，请重新登录"}), 401)

    teacher = Teacher.query.filter_by(user_id=user.id).first()
    if not teacher:
        return None, (jsonify({"msg": "教师档案不存在，请联系管理员"}), 403)

    return teacher, None


def _get_teacher_allowed_class_ids_for_task(teacher_id, task):
    rows = (
        db.session.query(CourseAssignment.class_id)
        .join(ClassInfo, CourseAssignment.class_id == ClassInfo.id)
        .filter(
            CourseAssignment.teacher_id == teacher_id,
            CourseAssignment.subject_id == task.subject_id,
            CourseAssignment.academic_year == task.academic_year,
            ClassInfo.entry_year == task.entry_year,
        )
        .all()
    )
    return {row.class_id for row in rows}


def _teacher_can_operate_task_class(teacher_id, class_id, task):
    if not class_id or not task:
        return False

    cls = ClassInfo.query.get(class_id)
    if not cls:
        return False

    if cls.entry_year != task.entry_year:
        return False

    assignment = CourseAssignment.query.filter_by(
        teacher_id=teacher_id,
        class_id=class_id,
        subject_id=task.subject_id,
        academic_year=task.academic_year,
    ).first()
    return bool(assignment)


def _count_abnormal_scores(exam_task_id, student_ids, pass_line):
    if not student_ids:
        return 0

    abnormal_count = (
        db.session.query(func.count(distinct(Score.student_id)))
        .filter(Score.exam_task_id == exam_task_id, Score.student_id.in_(student_ids))
        .filter(
            or_(
                Score.remark == "缺考",
                Score.score < pass_line,
            )
        )
        .scalar()
        or 0
    )
    return abnormal_count


# --- 1. 获取当前老师的任教课程 ---
@teacher_bp.route("/my_courses", methods=["GET"])
@teacher_bp.route("/my_courses/<int:user_id>", methods=["GET"])
def get_my_courses(user_id=None):
    current_user = g.current_user
    if user_id is not None and user_id != current_user.id:
        return jsonify({"msg": "无权查看其他教师的任课数据"}), 403

    teacher, err = _get_current_teacher()
    if err:
        return err

    assignments = (
        db.session.query(
            CourseAssignment.id,
            CourseAssignment.academic_year,
            ClassInfo.id.label("class_id"),
            ClassInfo.entry_year,
            ClassInfo.class_num,
            Subject.id.label("subject_id"),
            Subject.name.label("subject_name"),
        )
        .join(ClassInfo, CourseAssignment.class_id == ClassInfo.id)
        .join(Subject, CourseAssignment.subject_id == Subject.id)
        .filter(CourseAssignment.teacher_id == teacher.id)
        .all()
    )

    valid_courses = []

    for a in assignments:
        has_active_exam = (
            db.session.query(ExamTask.id)
            .filter_by(
                entry_year=a.entry_year,
                subject_id=a.subject_id,
                academic_year=a.academic_year,
                is_active=True,
            )
            .first()
        )

        if has_active_exam:
            valid_courses.append(
                {
                    "assignment_id": a.id,
                    "class_id": a.class_id,
                    "grade_class": f"{a.entry_year}级({a.class_num})班",
                    "subject_name": a.subject_name,
                    "subject_id": a.subject_id,
                }
            )

    return jsonify(valid_courses)


# --- 1.1 教师首页待办提醒 ---
@teacher_bp.route("/dashboard_todos", methods=["GET"])
def get_dashboard_todos():
    teacher, err = _get_current_teacher()
    if err:
        return err

    assignments = (
        db.session.query(
            CourseAssignment.class_id,
            CourseAssignment.subject_id,
            CourseAssignment.academic_year,
            ClassInfo.entry_year,
            ClassInfo.class_num,
            Subject.name.label("subject_name"),
        )
        .join(ClassInfo, CourseAssignment.class_id == ClassInfo.id)
        .join(Subject, CourseAssignment.subject_id == Subject.id)
        .filter(CourseAssignment.teacher_id == teacher.id)
        .all()
    )

    pending_items = []
    abnormal_items = []

    for assignment in assignments:
        tasks = (
            ExamTask.query.filter_by(
                entry_year=assignment.entry_year,
                subject_id=assignment.subject_id,
                academic_year=assignment.academic_year,
                is_active=True,
            )
            .order_by(ExamTask.create_time.desc())
            .all()
        )

        if not tasks:
            continue

        class_name = build_class_name(assignment.entry_year, assignment.class_num)

        for task in tasks:
            class_progress = calc_class_record_progress(task.id, assignment.class_id)

            if class_progress["recorded_count"] < class_progress["total_students"]:
                pending_items.append(
                    {
                        "task_id": task.id,
                        "task_name": task.name,
                        "subject_name": assignment.subject_name,
                        "class_id": assignment.class_id,
                        "class_name": class_name,
                        "recorded_count": class_progress["recorded_count"],
                        "total_students": class_progress["total_students"],
                        "msg": (
                            f"您有 [{task.name} - {assignment.subject_name}] 的成绩尚未录入，"
                            f"当前进度 {class_progress['recorded_count']}/{class_progress['total_students']}。"
                        ),
                    }
                )

            pass_line = task.full_score * 0.6
            abnormal_count = _count_abnormal_scores(
                task.id,
                class_progress["student_ids"],
                pass_line,
            )

            if abnormal_count > 0:
                abnormal_items.append(
                    {
                        "task_id": task.id,
                        "task_name": task.name,
                        "subject_name": assignment.subject_name,
                        "class_id": assignment.class_id,
                        "class_name": class_name,
                        "abnormal_count": abnormal_count,
                        "pass_line": round(pass_line, 1),
                        "msg": (
                            f"您带的 {class_name} 在 [{task.name} - {assignment.subject_name}]"
                            f" 有 {abnormal_count} 名学生成绩异常（低于及格线或者误登记缺考）。"
                        ),
                    }
                )

    return jsonify(
        {
            "pending_items": pending_items,
            "abnormal_items": abnormal_items,
            "total_todos": len(pending_items) + len(abnormal_items),
        }
    )


# --- 2. 获取打分列表（学生名单 + 现有分数） ---
@teacher_bp.route("/score_list", methods=["GET"])
def get_score_list():
    class_id = request.args.get("class_id", type=int)
    exam_task_id = request.args.get("exam_task_id", type=int)

    if not class_id or not exam_task_id:
        return jsonify({"msg": "参数缺失"}), 400

    teacher, err = _get_current_teacher()
    if err:
        return err

    task = ExamTask.query.get(exam_task_id)
    if not task:
        return jsonify({"msg": "考试任务不存在"}), 404

    if not _teacher_can_operate_task_class(teacher.id, class_id, task):
        return jsonify({"msg": "无权访问该班级的考试成绩"}), 403

    students = (
        Student.query.filter_by(class_id=class_id, status="在读")
        .order_by(Student.student_id)
        .all()
    )

    student_ids = [s.id for s in students]
    score_map = {}
    if student_ids:
        scores = Score.query.filter(
            Score.exam_task_id == exam_task_id,
            Score.student_id.in_(student_ids),
        ).all()
        score_map = {score.student_id: score for score in scores}

    result = []
    for s in students:
        score_record = score_map.get(s.id)

        display_val = None
        if score_record:
            if score_record.remark == "缺考":
                display_val = "缺考"
            else:
                display_val = score_record.score

        result.append(
            {
                "student_id": s.id,
                "student_no": s.student_id,
                "name": s.name,
                "score": display_val,
            }
        )

    return jsonify(result)


# --- 3. 保存成绩 ---
@teacher_bp.route("/save_scores", methods=["POST"])
def save_scores():
    data = request.get_json(silent=True) or {}
    exam_task_id = data.get("exam_task_id")
    scores_data = data.get("scores")

    if not exam_task_id:
        return jsonify({"msg": "缺少考试任务ID"}), 400

    if not isinstance(scores_data, list):
        return jsonify({"msg": "成绩数据格式错误"}), 400

    teacher, err = _get_current_teacher()
    if err:
        return err

    task = ExamTask.query.get(exam_task_id)
    if not task:
        return jsonify({"msg": "考试任务不存在"}), 404

    if not task.is_active:
        return jsonify({"msg": "该考试录入通道已关闭，无法保存"}), 403

    allowed_class_ids = _get_teacher_allowed_class_ids_for_task(teacher.id, task)
    if not allowed_class_ids:
        return jsonify({"msg": "当前教师没有该考试对应的任课权限"}), 403

    student_ids = []
    for item in scores_data:
        if not isinstance(item, dict):
            return jsonify({"msg": "成绩数据格式错误"}), 400

        student_id = item.get("student_id")
        if not isinstance(student_id, int):
            return jsonify({"msg": "存在非法学生ID"}), 400
        student_ids.append(student_id)

    if not student_ids:
        return jsonify({"msg": "未提交可保存的成绩数据"}), 400

    unique_student_ids = set(student_ids)
    students = Student.query.filter(Student.id.in_(unique_student_ids)).all()
    if len(students) != len(unique_student_ids):
        return jsonify({"msg": "提交数据中包含不存在的学生"}), 400

    student_map = {s.id: s for s in students}

    for s in students:
        if s.class_id not in allowed_class_ids:
            return jsonify({"msg": "包含无权操作的学生成绩"}), 403

    missing_count = 0
    invalid_count = 0
    updated_count = 0
    added_count = 0
    actor_user = g.current_user
    client_ip = request.headers.get("X-Forwarded-For", request.remote_addr or "")
    if "," in client_ip:
        client_ip = client_ip.split(",")[0].strip()

    for item in scores_data:
        student_obj = student_map[item["student_id"]]
        raw_val = item.get("score")

        final_score = 0.0
        final_remark = ""

        if raw_val is None:
            missing_count += 1
            continue

        val_str = str(raw_val).strip()
        if val_str == "":
            missing_count += 1
            continue

        if val_str == "缺考":
            final_score = 0.0
            final_remark = "缺考"
        else:
            try:
                final_score = float(val_str)
                final_remark = ""
            except (ValueError, TypeError):
                invalid_count += 1
                continue

            if final_score < 0 or final_score > task.full_score:
                invalid_count += 1
                continue

        existing_score = Score.query.filter_by(
            student_id=student_obj.id,
            exam_task_id=exam_task_id,
        ).first()

        if existing_score:
            old_score = existing_score.score
            old_remark = existing_score.remark

            existing_score.score = final_score
            existing_score.remark = final_remark
            existing_score.class_id_snapshot = student_obj.class_id

            if old_score != final_score or old_remark != final_remark:
                append_score_update_audit_log(
                    actor_user=actor_user,
                    student_obj=student_obj,
                    task_obj=task,
                    old_score=old_score,
                    old_remark=old_remark,
                    new_score=final_score,
                    new_remark=final_remark,
                    source="teacher_save_scores",
                    class_id=student_obj.class_id,
                    class_name=(
                        student_obj.current_class_rel.full_name
                        if student_obj.current_class_rel
                        else ""
                    ),
                    client_ip=client_ip,
                )
                updated_count += 1
        else:
            new_score = Score(
                student_id=student_obj.id,
                subject_id=task.subject_id,
                exam_task_id=exam_task_id,
                score=final_score,
                term=task.name,
                remark=final_remark,
                class_id_snapshot=student_obj.class_id,
            )
            db.session.add(new_score)
            added_count += 1

    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({"msg": f"数据库写入失败: {str(e)}"}), 500

    if missing_count > 0 or invalid_count > 0:
        msg = (
            f"已保存（新增 {added_count}，更新 {updated_count}）。"
            f" 仍有 {missing_count} 项未填写"
        )
        if invalid_count > 0:
            msg += f"，{invalid_count} 项格式不合法已跳过"
        msg += "。"
        return jsonify(
            {
                "msg": msg,
                "missing_count": missing_count,
                "invalid_count": invalid_count,
                "added_count": added_count,
                "updated_count": updated_count,
            }
        )

    return jsonify(
        {
            "msg": f"成绩保存成功（新增 {added_count}，更新 {updated_count}）",
            "missing_count": 0,
            "invalid_count": 0,
            "added_count": added_count,
            "updated_count": updated_count,
        }
    )


# --- 获取某班级某科目可用的考试任务 ---
@teacher_bp.route("/available_exams", methods=["GET"])
def get_available_exams():
    class_id = request.args.get("class_id", type=int)
    subject_id = request.args.get("subject_id", type=int)

    if not class_id or not subject_id:
        return jsonify([])

    teacher, err = _get_current_teacher()
    if err:
        return err

    cls = ClassInfo.query.get(class_id)
    if not cls:
        return jsonify([])

    assignments = CourseAssignment.query.filter_by(
        teacher_id=teacher.id,
        class_id=class_id,
        subject_id=subject_id,
    ).all()

    if not assignments:
        return jsonify([])

    academic_years = {a.academic_year for a in assignments}
    if not academic_years:
        return jsonify([])

    tasks = (
        ExamTask.query.filter(
            ExamTask.entry_year == cls.entry_year,
            ExamTask.subject_id == subject_id,
            ExamTask.is_active.is_(True),
            ExamTask.academic_year.in_(academic_years),
        )
        .order_by(ExamTask.create_time.desc())
        .all()
    )

    return jsonify(
        [
            {
                "id": t.id,
                "name": t.name,
                "full_score": t.full_score,
                "is_active": t.is_active,
            }
            for t in tasks
        ]
    )


# --- 5. 导出成绩单/录入模板 (XLSX格式) ---
@teacher_bp.route("/export_scores", methods=["GET"])
def export_scores():
    exam_task_id = request.args.get("exam_task_id", type=int)
    class_id = request.args.get("class_id", type=int)

    if not exam_task_id or not class_id:
        return jsonify({"msg": "参数缺失"}), 400

    teacher, err = _get_current_teacher()
    if err:
        return err

    task = ExamTask.query.get(exam_task_id)
    cls = ClassInfo.query.get(class_id)
    if not task or not cls:
        return jsonify({"msg": "任务或班级不存在"}), 404

    if not _teacher_can_operate_task_class(teacher.id, class_id, task):
        return jsonify({"msg": "无权导出该班级的成绩模板"}), 403

    subject_name = task.subject.name
    short_year = str(cls.entry_year)[-2:]
    formatted_class_name = f"{short_year}级({cls.class_num})班"

    students = (
        Student.query.filter_by(class_id=class_id, status="在读")
        .order_by(Student.student_id)
        .all()
    )

    scores = Score.query.filter_by(exam_task_id=exam_task_id).all()
    score_map = {}
    for s in scores:
        if s.remark == "缺考":
            score_map[s.student_id] = "缺考"
        else:
            score_map[s.student_id] = s.score

    data_list = []
    for s in students:
        row = {
            "学号": s.student_id,
            "姓名": s.name,
            "班级名称": formatted_class_name,
            "状态": s.status,
            subject_name: score_map.get(s.id, ""),
        }
        data_list.append(row)

    df = pd.DataFrame(data_list)

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="成绩录入")

    output.seek(0)

    filename = f"{formatted_class_name}-{subject_name}-{task.name}.xlsx"
    filename = quote(filename)

    return send_file(
        output,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name=filename,
        max_age=0,
    )


# --- 6. Excel 批量导入成绩 (含详细错误处理与严格校验) ---
@teacher_bp.route("/import_scores", methods=["POST"])
def import_scores():
    if "file" not in request.files:
        return jsonify({"msg": "没有上传文件"}), 400

    file = request.files["file"]
    exam_task_id = request.form.get("exam_task_id", type=int)
    class_id = request.form.get("class_id", type=int)

    if not exam_task_id or not class_id:
        return jsonify({"msg": "缺少任务ID或班级ID"}), 400

    teacher, err = _get_current_teacher()
    if err:
        return err

    task = ExamTask.query.get(exam_task_id)
    cls = ClassInfo.query.get(class_id)
    if not task or not cls:
        return jsonify({"msg": "考试任务或班级不存在"}), 404

    if not _teacher_can_operate_task_class(teacher.id, class_id, task):
        return jsonify({"msg": "无权导入该班级的成绩数据"}), 403

    if not task.is_active:
        return jsonify({"msg": "该考试已锁定，禁止导入"}), 403

    subject_name = task.subject.name

    short_year = str(cls.entry_year)[-2:]
    expected_class_name = f"{short_year}级({cls.class_num})班"

    try:
        df = pd.read_excel(file)
        df.fillna("", inplace=True)
    except Exception as e:
        return jsonify({"msg": f"Excel读取失败: {str(e)}"}), 400

    required_cols = ["学号", "姓名", "班级名称", subject_name]
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        return (
            jsonify({"msg": f"Excel格式错误，缺少必要列: {','.join(missing_cols)}"}),
            400,
        )

    logs = {"success": 0, "updated": 0, "errors": []}
    actor_user = g.current_user
    client_ip = request.headers.get("X-Forwarded-For", request.remote_addr or "")
    if "," in client_ip:
        client_ip = client_ip.split(",")[0].strip()

    all_subjects = Subject.query.all()
    all_subject_names = set(s.name for s in all_subjects)

    extra_subjects = [
        col for col in df.columns if col in all_subject_names and col != subject_name
    ]

    if extra_subjects:
        logs["errors"].append(
            {
                "row": "全局警报",
                "name": "-",
                "msg": f"检测到多余的科目数据列: [{', '.join(extra_subjects)}]。为了安全起见，只读取 [{subject_name}]，其余科目数据已被忽略。",
            }
        )

    db_students = Student.query.filter_by(class_id=class_id, status="在读").all()
    db_student_map = {s.student_id: s for s in db_students}

    processed_student_ids = set()

    for index, row in df.iterrows():
        excel_row_num = index + 2

        s_id = str(row["学号"]).strip()
        s_name = str(row["姓名"]).strip()
        row_class_name = str(row["班级名称"]).strip()
        raw_score = row[subject_name]

        if not s_id:
            continue

        if row_class_name != expected_class_name:
            logs["errors"].append(
                {
                    "row": excel_row_num,
                    "name": s_name,
                    "msg": f"班级不匹配: Excel中为 [{row_class_name}]，应为 [{expected_class_name}]",
                }
            )
            continue

        if s_id not in db_student_map:
            other_student = Student.query.filter_by(student_id=s_id).first()
            if other_student:
                current_cls = other_student.current_class_rel
                c_name = current_cls.full_name if current_cls else "未知"
                logs["errors"].append(
                    {
                        "row": excel_row_num,
                        "name": s_name,
                        "msg": f"非本班学生 (该生属于 {c_name})，已忽略",
                    }
                )
            else:
                logs["errors"].append(
                    {
                        "row": excel_row_num,
                        "name": s_name,
                        "msg": "系统中不存在该学号，已忽略",
                    }
                )
            continue

        student_obj = db_student_map[s_id]

        if student_obj.name != s_name:
            logs["errors"].append(
                {
                    "row": excel_row_num,
                    "name": s_name,
                    "msg": f"姓名与学号不匹配，系统记录为: {student_obj.name}",
                }
            )
            continue

        score_val = 0.0
        remark_val = ""
        if raw_score == "" or pd.isna(raw_score):
            continue

        str_val = str(raw_score).strip()

        if str_val == "缺考":
            score_val = 0.0
            remark_val = "缺考"
        else:
            try:
                score_val = float(raw_score)
                if score_val < 0 or score_val > task.full_score:
                    logs["errors"].append(
                        {
                            "row": excel_row_num,
                            "name": s_name,
                            "msg": f"分数 {score_val} 超出范围 (0-{task.full_score})",
                        }
                    )
                    continue
            except (ValueError, TypeError):
                logs["errors"].append(
                    {
                        "row": excel_row_num,
                        "name": s_name,
                        "msg": f"分数格式错误: {raw_score}",
                    }
                )
                continue

        processed_student_ids.add(s_id)

        existing_score = Score.query.filter_by(
            student_id=student_obj.id,
            exam_task_id=exam_task_id,
        ).first()

        if existing_score:
            if existing_score.score != score_val or existing_score.remark != remark_val:
                old_score = existing_score.score
                old_remark = existing_score.remark
                existing_score.score = score_val
                existing_score.remark = remark_val
                existing_score.class_id_snapshot = student_obj.class_id
                append_score_update_audit_log(
                    actor_user=actor_user,
                    student_obj=student_obj,
                    task_obj=task,
                    old_score=old_score,
                    old_remark=old_remark,
                    new_score=score_val,
                    new_remark=remark_val,
                    source="teacher_import_scores",
                    class_id=student_obj.class_id,
                    class_name=expected_class_name,
                    client_ip=client_ip,
                )
                logs["updated"] += 1
        else:
            new_score = Score(
                student_id=student_obj.id,
                subject_id=task.subject_id,
                exam_task_id=task.id,
                score=score_val,
                term=task.name,
                remark=remark_val,
                class_id_snapshot=student_obj.class_id,
            )
            db.session.add(new_score)
            logs["success"] += 1

    all_db_ids = set(db_student_map.keys())
    missing_ids = all_db_ids - processed_student_ids

    if missing_ids:
        missing_names = [db_student_map[mid].name for mid in missing_ids]
        show_names = ",".join(missing_names[:5])
        if len(missing_names) > 5:
            show_names += f" 等{len(missing_names)}人"

        logs["errors"].append(
            {
                "row": "-",
                "name": "-",
                "msg": f"提示: 本班还有 {len(missing_names)} 人未包含在Excel中 ({show_names})，未更新其成绩",
            }
        )

    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({"msg": f"数据库写入失败: {str(e)}"}), 500

    msg = f"处理完成。成功录入: {logs['success']}，更新: {logs['updated']}。"
    if logs["errors"]:
        msg += f" 发现 {len(logs['errors'])} 个问题/提示，请务必查看详情。"

    return jsonify({"msg": msg, "logs": logs})
