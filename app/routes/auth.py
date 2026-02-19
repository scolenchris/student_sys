from flask import Blueprint, request, jsonify, g
from app.models import db, User, SystemSetting
from app.auth_utils import issue_access_token, auth_required

auth_bp = Blueprint("auth", __name__)


def _text(v):
    if v is None:
        return ""
    return str(v).strip()


@auth_bp.route("/register", methods=["POST"])
def register():
    # 注册开关由系统设置控制。
    setting = SystemSetting.query.get("allow_register")
    if setting and setting.value == "0":
        return jsonify({"msg": "管理员已暂时关闭注册功能"}), 403

    data = request.get_json(silent=True) or {}
    username = _text(data.get("username"))
    password = str(data.get("password") or "")
    role = _text(data.get("role"))
    real_name = _text(data.get("name"))

    if not username or not password or not real_name:
        return jsonify({"msg": "请填写完整注册信息"}), 400

    if role not in {"teacher", "admin"}:
        return jsonify({"msg": "申请身份不合法"}), 400

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
    data = request.get_json(silent=True) or {}
    username = _text(data.get("username"))
    password = str(data.get("password") or "")

    if not username or not password:
        return jsonify({"msg": "用户名或密码不能为空"}), 400

    user = User.query.filter_by(username=username).first()

    if not user or not user.check_password(password):
        return jsonify({"msg": "用户名或密码错误"}), 401

    if not user.is_approved:
        return jsonify({"msg": "账号正在审核中，请联系系主任"}), 403

    access_token = issue_access_token(user)

    return (
        jsonify(
            {
                "msg": "登录成功",
                "role": user.role,
                "username": user.username,
                "user_id": user.id,
                "must_change_password": user.must_change_password,
                "access_token": access_token,
            }
        ),
        200,
    )


@auth_bp.route("/change_password", methods=["POST"])
@auth_required(required_roles={"admin", "teacher"}, enforce_password_change=False)
def change_password():
    data = request.get_json(silent=True) or {}
    old_password = str(data.get("old_password") or "")
    new_password = str(data.get("new_password") or "")

    if not old_password or not new_password:
        return jsonify({"msg": "旧密码和新密码不能为空"}), 400

    user = g.current_user
    user_id = data.get("user_id")
    if user_id is not None:
        try:
            if int(user_id) != user.id:
                return jsonify({"msg": "禁止修改其他账号密码"}), 403
        except (TypeError, ValueError):
            return jsonify({"msg": "用户参数不合法"}), 400

    if not user.check_password(old_password):
        return jsonify({"msg": "旧密码错误"}), 400

    if old_password == new_password:
        return jsonify({"msg": "新密码不能与旧密码相同"}), 400

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
