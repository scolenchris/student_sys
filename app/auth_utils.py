from functools import wraps
import hashlib
import hmac

from flask import current_app, g, jsonify, request
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from app.models import User

TOKEN_SALT = "student-sys-access-token-v1"


def _get_serializer():
    return URLSafeTimedSerializer(current_app.config["SECRET_KEY"])


def _get_token_ttl_seconds():
    return int(current_app.config.get("AUTH_TOKEN_EXPIRES_SECONDS", 12 * 60 * 60))


def _build_password_signature(user):
    key = str(current_app.config.get("SECRET_KEY", "")).encode("utf-8")
    pwd_hash = str(user.password_hash or "").encode("utf-8")
    return hmac.new(key, pwd_hash, hashlib.sha256).hexdigest()


def issue_access_token(user):
    payload = {
        "uid": user.id,
        "role": user.role,
        "pwd_sig": _build_password_signature(user),
    }
    return _get_serializer().dumps(payload, salt=TOKEN_SALT)


def _extract_bearer_token():
    auth_header = request.headers.get("Authorization", "").strip()
    if not auth_header:
        return None

    parts = auth_header.split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None

    token = parts[1].strip()
    return token or None


def require_auth(required_roles=None, enforce_password_change=True):
    if request.method == "OPTIONS":
        return None

    token = _extract_bearer_token()
    if not token:
        return jsonify({"msg": "未登录或登录已过期，请重新登录"}), 401

    try:
        payload = _get_serializer().loads(
            token,
            salt=TOKEN_SALT,
            max_age=_get_token_ttl_seconds(),
        )
    except SignatureExpired:
        return jsonify({"msg": "登录状态已过期，请重新登录"}), 401
    except BadSignature:
        return jsonify({"msg": "登录凭证无效，请重新登录"}), 401

    user_id = payload.get("uid")
    token_role = payload.get("role")
    token_pwd_sig = payload.get("pwd_sig")

    if not isinstance(user_id, int) or not token_role or not token_pwd_sig:
        return jsonify({"msg": "登录凭证格式非法，请重新登录"}), 401

    user = User.query.get(user_id)
    if not user:
        return jsonify({"msg": "账号不存在，请重新登录"}), 401

    if not user.is_approved:
        return jsonify({"msg": "账号不可用，请联系管理员"}), 403

    if user.role != token_role:
        return jsonify({"msg": "账号权限已变更，请重新登录"}), 401

    if token_pwd_sig != _build_password_signature(user):
        return jsonify({"msg": "登录状态已失效，请重新登录"}), 401

    if enforce_password_change and user.must_change_password:
        return jsonify({"msg": "为了账号安全，请先修改初始密码"}), 403

    roles = set(required_roles or [])
    if roles and user.role not in roles:
        return jsonify({"msg": "无权访问该接口"}), 403

    g.current_user = user
    return None


def auth_required(required_roles=None, enforce_password_change=True):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            auth_error = require_auth(
                required_roles=required_roles,
                enforce_password_change=enforce_password_change,
            )
            if auth_error:
                return auth_error
            return func(*args, **kwargs)

        return wrapper

    return decorator
