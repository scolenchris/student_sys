import json
import re

from app.models import ImportBatch, db


def _json_dumps(data):
    return json.dumps(data, ensure_ascii=False)


def _json_loads(raw, default):
    if not raw:
        return default
    try:
        return json.loads(raw)
    except Exception:
        return default


def _serialize_user(user):
    return {
        "username": user.username,
        "real_name": user.real_name,
        "role": user.role,
        "is_approved": bool(user.is_approved),
        "must_change_password": bool(user.must_change_password),
        "password_hash": user.password_hash,
    }


def _serialize_teacher(teacher):
    return {
        "user_id": teacher.user_id,
        "name": teacher.name,
        "gender": teacher.gender,
        "ethnicity": teacher.ethnicity,
        "phone": teacher.phone,
        "status": teacher.status,
        "job_title": teacher.job_title,
        "education": teacher.education,
        "major": teacher.major,
        "remarks": teacher.remarks,
    }


def _apply_teacher_status_to_account(user, status):
    if not user:
        return

    normalized = str(status).strip()
    if normalized in ["退休", "离职", "非在职"]:
        user.is_approved = False
    elif normalized in ["在职", "返聘"]:
        user.is_approved = True


def _serialize_student(student):
    return {
        "student_id": student.student_id,
        "name": student.name,
        "gender": student.gender,
        "class_id": student.class_id,
        "status": student.status,
        "household_registration": student.household_registration,
        "city_school_id": student.city_school_id,
        "national_school_id": student.national_school_id,
        "id_card_number": student.id_card_number,
        "remarks": student.remarks,
    }


def _serialize_score(score):
    return {
        "student_id": score.student_id,
        "exam_task_id": score.exam_task_id,
        "subject_id": score.subject_id,
        "score": score.score,
        "remark": score.remark,
        "term": score.term,
        "class_id_snapshot": score.class_id_snapshot,
    }


def _normalize_excel_sheet_name(raw_name, used_names):
    name = re.sub(r"[\\/*?:\[\]]", "_", str(raw_name or "Sheet")).strip()
    name = name.strip("'")
    if not name:
        name = "Sheet"
    name = name[:31]

    base_name = name
    index = 2
    while name in used_names:
        suffix = f"_{index}"
        name = f"{base_name[: 31 - len(suffix)]}{suffix}"
        index += 1

    used_names.add(name)
    return name


def _to_excel_value(value):
    if value is None:
        return "-"
    if isinstance(value, float):
        return round(value, 1)
    return value


def _create_import_batch(import_type, source_filename, scope, summary, snapshot):
    batch = ImportBatch(
        import_type=import_type,
        source_filename=(source_filename or "")[:255],
        scope_json=_json_dumps(scope or {}),
        summary_json=_json_dumps(summary or {}),
        snapshot_json=_json_dumps(snapshot or {}),
        can_rollback=True,
    )
    db.session.add(batch)
    return batch

