from datetime import datetime, timedelta

from flask import g, jsonify, request
from sqlalchemy import or_

from app.models import AuditLog

from . import admin_bp


def _parse_date(date_text):
    if not date_text:
        return None
    try:
        return datetime.strptime(date_text, "%Y-%m-%d")
    except ValueError:
        return None


@admin_bp.route("/audit_logs", methods=["GET"])
def get_audit_logs():
    current_user = g.current_user
    if not current_user or current_user.username != "adminwds":
        return jsonify({"msg": "仅超级管理员可查看审计日志"}), 403

    page = request.args.get("page", type=int) or 1
    page_size = request.args.get("page_size", type=int) or 20
    page = max(page, 1)
    page_size = min(max(page_size, 1), 100)

    keyword = (request.args.get("keyword") or "").strip()
    action_type = (request.args.get("action_type") or "").strip()
    source = (request.args.get("source") or "").strip()
    start_date_text = (request.args.get("start_date") or "").strip()
    end_date_text = (request.args.get("end_date") or "").strip()

    query = AuditLog.query

    if action_type:
        query = query.filter(AuditLog.action_type == action_type)

    if source:
        query = query.filter(AuditLog.source == source)

    if keyword:
        like_pattern = f"%{keyword}%"
        query = query.filter(
            or_(
                AuditLog.actor_username.like(like_pattern),
                AuditLog.actor_real_name.like(like_pattern),
                AuditLog.target_student_no.like(like_pattern),
                AuditLog.target_student_name.like(like_pattern),
                AuditLog.exam_task_name.like(like_pattern),
                AuditLog.subject_name.like(like_pattern),
                AuditLog.class_name_snapshot.like(like_pattern),
                AuditLog.detail_text.like(like_pattern),
            )
        )

    if start_date_text:
        start_date = _parse_date(start_date_text)
        if not start_date:
            return jsonify({"msg": "开始日期格式错误，应为 YYYY-MM-DD"}), 400
        query = query.filter(AuditLog.create_time >= start_date)

    if end_date_text:
        end_date = _parse_date(end_date_text)
        if not end_date:
            return jsonify({"msg": "结束日期格式错误，应为 YYYY-MM-DD"}), 400
        query = query.filter(AuditLog.create_time < (end_date + timedelta(days=1)))

    total = query.count()
    items = (
        query.order_by(AuditLog.create_time.desc(), AuditLog.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return jsonify(
        {
            "total": total,
            "page": page,
            "page_size": page_size,
            "items": [
                {
                    "id": item.id,
                    "create_time": item.create_time.strftime("%Y-%m-%d %H:%M:%S")
                    if item.create_time
                    else "",
                    "action_type": item.action_type,
                    "source": item.source,
                    "actor_username": item.actor_username,
                    "actor_real_name": item.actor_real_name,
                    "actor_role": item.actor_role,
                    "target_student_no": item.target_student_no,
                    "target_student_name": item.target_student_name,
                    "exam_task_name": item.exam_task_name,
                    "subject_name": item.subject_name,
                    "class_name_snapshot": item.class_name_snapshot,
                    "old_value": item.old_value,
                    "new_value": item.new_value,
                    "detail_text": item.detail_text,
                    "client_ip": item.client_ip,
                }
                for item in items
            ],
        }
    )
