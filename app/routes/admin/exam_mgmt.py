from datetime import datetime

from flask import g, jsonify, request

from app.models import ClassInfo, ExamTask, Score, Student, Subject, db
from app.services.audit_service import append_score_update_audit_log
from app.services.progress_service import calc_exam_task_progress

from . import admin_bp


@admin_bp.route("/exam_tasks", methods=["GET"])
def get_exam_tasks():
    entry_year = request.args.get("entry_year", type=int)
    subject_id = request.args.get("subject_id", type=int)
    academic_year = request.args.get("academic_year", type=int)
    paged = request.args.get("paged", default=0, type=int) == 1
    page = request.args.get("page", default=1, type=int) or 1
    page_size = request.args.get("page_size", type=int)
    if page_size is None:
        page_size = request.args.get("limit", default=20, type=int) or 20
    page = max(page, 1)
    page_size = min(max(page_size, 1), 100)

    query = ExamTask.query
    if entry_year:
        query = query.filter_by(entry_year=entry_year)
    if subject_id:
        query = query.filter_by(subject_id=subject_id)
    if academic_year:
        query = query.filter_by(academic_year=academic_year)

    query = query.order_by(ExamTask.create_time.desc())
    if paged:
        pagination = query.paginate(page=page, per_page=page_size, error_out=False)
        tasks = pagination.items
        total = pagination.total
    else:
        tasks = query.all()

    result = []
    for t in tasks:
        progress = calc_exam_task_progress(t)
        result.append(
            {
                "id": t.id,
                "name": t.name,
                "entry_year": t.entry_year,
                "grade_name": t.grade_name,
                "subject_id": t.subject_id,
                "subject_name": t.subject.name if t.subject else "-",
                "full_score": t.full_score,
                "is_active": t.is_active,
                "academic_year": t.academic_year,
                "assigned_class_count": progress["assigned_class_count"],
                "completed_class_count": progress["completed_class_count"],
                "pending_class_count": progress["pending_class_count"],
                "completion_rate": progress["completion_rate"],
                "progress_text": progress["progress_text"],
                "is_fully_completed": progress["is_fully_completed"],
            }
        )
    if paged:
        return jsonify(
            {
                "items": result,
                "total": total,
                "page": page,
                "page_size": page_size,
            }
        )
    return jsonify(result)


@admin_bp.route("/exam_tasks", methods=["POST"])
def add_exam_task():
    data = request.get_json()
    academic_year = data.get("academic_year", datetime.now().year)

    exists = ExamTask.query.filter_by(
        academic_year=academic_year,
        entry_year=data["entry_year"],
        subject_id=data["subject_id"],
        name=data["name"],
    ).first()

    if exists:
        return jsonify({"msg": "该学年的此考试任务已存在"}), 400

    new_task = ExamTask(
        name=data["name"],
        entry_year=data["entry_year"],
        subject_id=data["subject_id"],
        academic_year=academic_year,
        full_score=data.get("full_score", 100),
        is_active=data.get("is_active", True),
    )
    db.session.add(new_task)
    db.session.commit()
    return jsonify({"msg": "发布成功"})


@admin_bp.route("/exam_tasks/<int:id>", methods=["PUT"])
def update_exam_task(id):
    task = ExamTask.query.get(id)
    if not task:
        return jsonify({"msg": "任务不存在"}), 404

    data = request.get_json()
    if "full_score" in data:
        task.full_score = data["full_score"]
    if "is_active" in data:
        task.is_active = data["is_active"]
    if "name" in data:
        task.name = data["name"]

    db.session.commit()
    return jsonify({"msg": "更新成功"})


@admin_bp.route("/exam_tasks/<int:id>", methods=["DELETE"])
def delete_exam_task(id):
    task = ExamTask.query.get(id)
    if not task:
        return jsonify({"msg": "任务不存在"}), 404

    try:
        Score.query.filter_by(exam_task_id=id).delete()
        db.session.delete(task)
        db.session.commit()
        return jsonify({"msg": "删除成功，相关成绩记录已同步清理"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"msg": f"删除失败: {str(e)}"}), 500


@admin_bp.route("/score_entry/exams", methods=["GET"])
def get_class_active_exams():
    class_id = request.args.get("class_id", type=int)
    if not class_id:
        return jsonify([])

    cls = ClassInfo.query.get(class_id)
    if not cls:
        return jsonify([])

    tasks = (
        db.session.query(ExamTask, Subject.name.label("subject_name"))
        .join(Subject, ExamTask.subject_id == Subject.id)
        .filter(ExamTask.entry_year == cls.entry_year, ExamTask.is_active == True)
        .order_by(ExamTask.create_time.desc())
        .all()
    )

    return jsonify(
        [
            {
                "id": t.ExamTask.id,
                "name": t.ExamTask.name,
                "subject_name": t.subject_name,
                "full_score": t.ExamTask.full_score,
                "display_name": f"[{t.subject_name}] {t.ExamTask.name}",
            }
            for t in tasks
        ]
    )


@admin_bp.route("/score_entry/student_list", methods=["GET"])
def get_admin_score_list():
    class_id = request.args.get("class_id")
    exam_task_id = request.args.get("exam_task_id")

    if not exam_task_id or not class_id:
        return jsonify([])

    students = (
        Student.query.filter_by(class_id=class_id, status="在读")
        .order_by(Student.student_id.asc())
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
            display_val = "缺考" if score_record.remark == "缺考" else score_record.score

        result.append(
            {"student_id": s.id, "student_no": s.student_id, "name": s.name, "score": display_val}
        )

    return jsonify(result)


@admin_bp.route("/score_entry/save", methods=["POST"])
def save_admin_scores():
    data = request.get_json(silent=True) or {}
    exam_task_id = data.get("exam_task_id")
    scores_data = data.get("scores")

    if not exam_task_id:
        return jsonify({"msg": "缺少考试任务ID"}), 400

    if not isinstance(scores_data, list):
        return jsonify({"msg": "成绩数据格式错误"}), 400

    task = ExamTask.query.get(exam_task_id)
    if not task:
        return jsonify({"msg": "考试任务不存在"}), 404

    if not task.is_active:
        return jsonify({"msg": "该考试已锁定，无法修改"}), 403

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

    students = Student.query.filter(Student.id.in_(set(student_ids))).all()
    student_map = {stu.id: stu for stu in students}
    if len(student_map) != len(set(student_ids)):
        return jsonify({"msg": "提交数据中包含不存在的学生"}), 400

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
        raw_val = item["score"]
        final_score = 0.0
        final_remark = ""

        if raw_val is None or str(raw_val).strip() == "":
            missing_count += 1
            continue

        if str(raw_val).strip() == "缺考":
            final_score = 0.0
            final_remark = "缺考"
        else:
            try:
                final_score = float(raw_val)
            except (ValueError, TypeError):
                invalid_count += 1
                continue

            if final_score < 0 or final_score > task.full_score:
                invalid_count += 1
                continue

        existing_score = Score.query.filter_by(
            student_id=item["student_id"], exam_task_id=exam_task_id
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
                    source="admin_score_entry_save",
                    class_id=student_obj.class_id,
                    class_name=student_obj.current_class_rel.full_name
                    if student_obj.current_class_rel
                    else "",
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

    return jsonify(
        {
            "msg": f"成绩保存成功（新增 {added_count}，更新 {updated_count}）",
            "missing_count": missing_count,
            "invalid_count": invalid_count,
            "added_count": added_count,
            "updated_count": updated_count,
        }
    )
