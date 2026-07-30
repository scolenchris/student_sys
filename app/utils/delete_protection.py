import json

from sqlalchemy import func

from app.models import ClassInfo, ImportBatch, Score, Student, db


def get_client_ip(request_obj):
    client_ip = request_obj.headers.get("X-Forwarded-For", request_obj.remote_addr or "")
    if "," in client_ip:
        client_ip = client_ip.split(",", 1)[0].strip()
    return client_ip


def format_class_name(class_obj):
    if not class_obj:
        return "未分配"
    short_year = str(class_obj.entry_year)[-2:]
    class_num = str(class_obj.class_num).zfill(2)
    return f"{short_year}级({class_num})班"


def _json_loads(raw, default):
    try:
        return json.loads(raw or "")
    except (TypeError, ValueError):
        return default


def _score_items_contain_student(items, student_pk):
    return any(item.get("student_id") == student_pk for item in items or [])


def _score_items_contain_exam_task(items, exam_task_id):
    return any(item.get("exam_task_id") == exam_task_id for item in items or [])


def _collect_related_import_batches(predicate):
    related_ids = []
    batches = ImportBatch.query.order_by(ImportBatch.id.desc()).all()
    for batch in batches:
        snapshot = _json_loads(batch.snapshot_json, {})
        if predicate(batch, snapshot):
            related_ids.append(batch.id)
    return related_ids


def count_student_related_import_batches(student):
    def is_related(batch, snapshot):
        if batch.import_type == "student":
            if student.student_id in snapshot.get("created_student_ids", []):
                return True
            return any(
                item.get("student_id") == student.student_id
                for item in snapshot.get("before_students", [])
            )

        if batch.import_type == "score":
            return _score_items_contain_student(
                snapshot.get("before_scores", []), student.id
            ) or _score_items_contain_student(
                snapshot.get("created_scores", []), student.id
            )

        return False

    return _collect_related_import_batches(is_related)


def count_exam_task_related_import_batches(exam_task_id):
    def is_related(batch, snapshot):
        if batch.import_type != "score":
            return False
        return _score_items_contain_exam_task(
            snapshot.get("before_scores", []), exam_task_id
        ) or _score_items_contain_exam_task(
            snapshot.get("created_scores", []), exam_task_id
        )

    return _collect_related_import_batches(is_related)


def build_student_delete_impact(student):
    class_name = format_class_name(student.current_class_rel)
    score_count = Score.query.filter_by(student_id=student.id).count()
    exam_task_count = (
        db.session.query(func.count(func.distinct(Score.exam_task_id)))
        .filter(Score.student_id == student.id, Score.exam_task_id.isnot(None))
        .scalar()
        or 0
    )
    related_batch_ids = count_student_related_import_batches(student)

    return {
        "student": {
            "id": student.id,
            "student_id": student.student_id,
            "name": student.name,
            "status": student.status,
            "class_name": class_name,
        },
        "score_count": score_count,
        "exam_task_count": exam_task_count,
        "related_import_batch_count": len(related_batch_ids),
        "related_import_batch_ids": related_batch_ids[:10],
        "confirmation_text": f"删除学生 {student.student_id}",
    }


def build_exam_task_delete_impact(task):
    subject_name = task.subject.name if task.subject else ""
    score_count = Score.query.filter_by(exam_task_id=task.id).count()
    student_count = (
        db.session.query(func.count(func.distinct(Score.student_id)))
        .filter(Score.exam_task_id == task.id, Score.student_id.isnot(None))
        .scalar()
        or 0
    )
    class_ids = (
        db.session.query(func.coalesce(Score.class_id_snapshot, Student.class_id))
        .outerjoin(Student, Score.student_id == Student.id)
        .filter(Score.exam_task_id == task.id)
        .distinct()
        .all()
    )
    class_ids = [row[0] for row in class_ids if row[0] is not None]
    classes = (
        ClassInfo.query.filter(ClassInfo.id.in_(class_ids)).all() if class_ids else []
    )
    class_names = [format_class_name(cls) for cls in classes]
    related_batch_ids = count_exam_task_related_import_batches(task.id)

    return {
        "exam_task": {
            "id": task.id,
            "name": task.name,
            "academic_year": task.academic_year,
            "entry_year": task.entry_year,
            "subject_name": subject_name,
            "full_score": task.full_score,
            "is_active": task.is_active,
        },
        "score_count": score_count,
        "student_count": student_count,
        "class_count": len(class_ids),
        "class_names": sorted(class_names),
        "related_import_batch_count": len(related_batch_ids),
        "related_import_batch_ids": related_batch_ids[:10],
        "confirmation_text": f"删除考试 {task.id}",
    }
