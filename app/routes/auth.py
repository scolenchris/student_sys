from flask import Blueprint, request, jsonify, session, g
from app.models import db, User, SystemSetting
from app.auth import login_required

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/register", methods=["POST"])
def register():
    # 注册开关由系统设置控制。
    setting = SystemSetting.query.get("allow_register")
    if setting and setting.value == "0":
        return jsonify({"msg": "管理员已暂时关闭注册功能"}), 403

    data = request.get_json()
    username = data.get("username")
    password = data.get("password")
    role = data.get("role")
    real_name = data.get("name")

    if User.query.filter_by(username=username).first():
        return jsonify({"msg": "用户名已存在"}), 400

    new_user = User(
        username=username,
        role=role,
        real_name=real_name,
        is_approved=False,
    )
    new_user.set_password(password)

    db.session.add(new_user)

    # 教师档案不在注册时创建，审核通过后再建档。
    db.session.commit()
    return jsonify({"msg": "注册申请已提交，请等待管理员审核"}), 201


@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    user = User.query.filter_by(username=data.get("username")).first()

    if not user or not user.check_password(data.get("password")):
        return jsonify({"msg": "用户名或密码错误"}), 401

    if not user.is_approved:
        return jsonify({"msg": "账号正在审核中，请联系系主任"}), 403

    session["user_id"] = user.id
    session["role"] = user.role

    return (
        jsonify(
            {
                "msg": "登录成功",
                "role": user.role,
                "username": user.username,
                "user_id": user.id,
                "must_change_password": user.must_change_password,
            }
        ),
        200,
    )


@auth_bp.route("/change_password", methods=["POST"])
@login_required
def change_password():
    data = request.get_json()
    old_password = data.get("old_password")
    new_password = data.get("new_password")

    user = g.current_user
    if not user:
        return jsonify({"msg": "用户不存在"}), 404

    if not user.check_password(old_password):
        return jsonify({"msg": "旧密码错误"}), 400

    user.set_password(new_password)
    user.must_change_password = False
    db.session.commit()

    return jsonify({"msg": "密码修改成功，请重新登录"}), 200


@auth_bp.route("/register_config", methods=["GET"])
def get_register_config():
    # 默认开放注册；仅当配置显式为 "0" 时关闭。
    setting = SystemSetting.query.get("allow_register")
    is_open = True
    if setting and setting.value == "0":
        is_open = False
    return jsonify({"allow_register": is_open})


@auth_bp.route("/logout", methods=["POST"])
@login_required
def logout():
    session.clear()
    return jsonify({"msg": "已退出登录"}), 200
