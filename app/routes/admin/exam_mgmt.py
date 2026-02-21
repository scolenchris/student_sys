from datetime import datetime

from flask import jsonify, request

from app.models import ClassInfo, ExamTask, Score, Student, Subject, db

from . import admin_bp


@admin_bp.route("/exam_tasks", methods=["GET"])
def get_exam_tasks():
    entry_year = request.args.get("entry_year", type=int)
    subject_id = request.args.get("subject_id", type=int)
    academic_year = request.args.get("academic_year", type=int)

    query = ExamTask.query
    if entry_year:
        query = query.filter_by(entry_year=entry_year)
    if subject_id:
        query = query.filter_by(subject_id=subject_id)
    if academic_year:
        query = query.filter_by(academic_year=academic_year)

    tasks = query.order_by(ExamTask.create_time.desc()).all()

    return jsonify(
        [
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
            }
            for t in tasks
        ]
    )


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

    students = Student.query.filter_by(class_id=class_id, status="在读").all()

    result = []
    for s in students:
        score_record = Score.query.filter_by(
            student_id=s.id, exam_task_id=exam_task_id
        ).first()

        display_val = None
        if score_record:
            display_val = "缺考" if score_record.remark == "缺考" else score_record.score

        result.append(
            {"student_id": s.id, "student_no": s.student_id, "name": s.name, "score": display_val}
        )

    return jsonify(result)


@admin_bp.route("/score_entry/save", methods=["POST"])
def save_admin_scores():
    data = request.get_json()
    exam_task_id = data.get("exam_task_id")
    scores_data = data.get("scores")

    task = ExamTask.query.get(exam_task_id)
    if not task:
        return jsonify({"msg": "考试任务不存在"}), 404

    if not task.is_active:
        return jsonify({"msg": "该考试已锁定，无法修改"}), 403

    for item in scores_data:
        raw_val = item["score"]
        final_score = 0.0
        final_remark = ""

        if raw_val is None or str(raw_val).strip() == "":
            continue

        if str(raw_val).strip() == "缺考":
            final_score = 0.0
            final_remark = "缺考"
        else:
            try:
                final_score = float(raw_val)
            except ValueError:
                continue

        existing_score = Score.query.filter_by(
            student_id=item["student_id"], exam_task_id=exam_task_id
        ).first()

        if existing_score:
            existing_score.score = final_score
            existing_score.remark = final_remark
        else:
            new_score = Score(
                student_id=item["student_id"],
                subject_id=task.subject_id,
                exam_task_id=exam_task_id,
                score=final_score,
                term=task.name,
                remark=final_remark,
            )
            db.session.add(new_score)

    db.session.commit()
    return jsonify({"msg": "成绩保存成功"})

