from functools import wraps
from flask import jsonify, request, session


def login_required(view_func):
    @wraps(view_func)
    def wrapped(*args, **kwargs):
        if request.method == "OPTIONS":
            return view_func(*args, **kwargs)

        if not session.get("user_id"):
            return jsonify({"msg": "未登录或登录已过期"}), 401
        return view_func(*args, **kwargs)

    return wrapped


def role_required(*roles):
    def decorator(view_func):
        @wraps(view_func)
        def wrapped(*args, **kwargs):
            if request.method == "OPTIONS":
                return view_func(*args, **kwargs)

            current_role = session.get("role")
            if not session.get("user_id"):
                return jsonify({"msg": "未登录或登录已过期"}), 401
            if current_role not in roles:
                return jsonify({"msg": "无权限访问该接口"}), 403
            return view_func(*args, **kwargs)

        return wrapped

    return decorator
