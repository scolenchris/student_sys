from flask import jsonify, request

from app.models import SystemSetting, Teacher, User, db

from . import admin_bp


@admin_bp.route("/pending_users", methods=["GET"])
def get_pending_users():
    users = User.query.filter_by(is_approved=False).all()
    results = []

    for user in users:
        if user.teacher_profile:
            name = user.teacher_profile.name
            current_status = user.teacher_profile.status
        else:
            name = user.real_name if user.real_name else "未填"
            current_status = "新注册"

        results.append(
            {
                "id": user.id,
                "username": user.username,
                "role": user.role,
                "name": name,
                "current_status": current_status,
            }
        )

    return jsonify(results)


@admin_bp.route("/approve_user/<int:user_id>", methods=["POST"])
def approve_user(user_id):
    user = User.query.get(user_id)
    if not user:
        return jsonify({"msg": "用户不存在"}), 404

    if user.role == "teacher" and not user.teacher_profile:
        t_name = user.real_name if user.real_name else user.username
        new_teacher = Teacher(user_id=user.id, name=t_name, status="在职")
        db.session.add(new_teacher)
        print(f">> [自动建档] 已为 {user.username} 创建教师档案")

    user.is_approved = True
    db.session.commit()
    return jsonify({"msg": "审核已通过，教师档案已建立"})


@admin_bp.route("/reject_user/<int:user_id>", methods=["DELETE"])
def reject_user(user_id):
    user = User.query.get(user_id)
    if user:
        if user.teacher_profile:
            db.session.delete(user.teacher_profile)
        db.session.delete(user)
        db.session.commit()
    return jsonify({"msg": "申请已拒绝"})


@admin_bp.route("/system/settings", methods=["GET"])
def get_system_settings():
    allow_reg = SystemSetting.query.get("allow_register")
    return jsonify({"allow_register": allow_reg.value == "1" if allow_reg else True})


@admin_bp.route("/system/settings", methods=["POST"])
def update_system_settings():
    data = request.get_json()
    allow = data.get("allow_register")

    val = "1" if allow else "0"
    setting = SystemSetting.query.get("allow_register")
    if not setting:
        setting = SystemSetting(key="allow_register", value=val)
        db.session.add(setting)
    else:
        setting.value = val

    db.session.commit()
    return jsonify({"msg": "系统设置已更新"})

