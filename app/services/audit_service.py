from app.models import AuditLog, db


ROLE_LABELS = {
    "admin": "管理员",
    "teacher": "普通教师",
}


def format_score_value(score, remark):
    if remark == "缺考":
        return "缺考"

    if score is None:
        return "-"

    try:
        value = float(score)
        if value.is_integer():
            return str(int(value))
        return f"{value:g}"
    except (TypeError, ValueError):
        return str(score)


def append_score_update_audit_log(
    *,
    actor_user,
    student_obj,
    task_obj,
    old_score,
    old_remark,
    new_score,
    new_remark,
    source,
    class_id=None,
    class_name="",
    client_ip="",
):
    old_value = format_score_value(old_score, old_remark)
    new_value = format_score_value(new_score, new_remark)

    if old_value == new_value:
        return None

    actor_name = (actor_user.real_name or "").strip() or actor_user.username
    actor_role_label = ROLE_LABELS.get(actor_user.role, actor_user.role or "未知角色")
    subject_name = task_obj.subject.name if task_obj.subject else ""
    exam_subject_label = (
        f"{task_obj.name}-{subject_name}" if subject_name else (task_obj.name or "未命名考试")
    )

    resolved_class_id = class_id if class_id is not None else student_obj.class_id
    resolved_class_name = class_name
    if not resolved_class_name:
        cls = getattr(student_obj, "current_class_rel", None)
        if cls:
            resolved_class_name = cls.full_name

    detail_text = (
        f"{actor_name}({actor_role_label}) 修改了 {student_obj.name} 的 [{exam_subject_label}] 成绩，"
        f"从 [{old_value}] 改为 [{new_value}]。"
    )

    log = AuditLog(
        action_type="score_update",
        source=source,
        actor_user_id=actor_user.id,
        actor_username=actor_user.username or "",
        actor_real_name=actor_name,
        actor_role=actor_user.role or "",
        target_student_id=student_obj.id,
        target_student_no=student_obj.student_id or "",
        target_student_name=student_obj.name or "",
        exam_task_id=task_obj.id,
        exam_task_name=task_obj.name or "",
        subject_name=subject_name,
        class_id_snapshot=resolved_class_id,
        class_name_snapshot=resolved_class_name or "",
        old_value=old_value,
        new_value=new_value,
        detail_text=detail_text,
        client_ip=client_ip or "",
    )
    db.session.add(log)
    return log
