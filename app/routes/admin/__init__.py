from flask import Blueprint

from app.auth_utils import require_auth

admin_bp = Blueprint("admin", __name__)


@admin_bp.before_request
def _admin_auth_guard():
    return require_auth(required_roles={"admin"})


from . import (
    account,
    audit_api,
    course_mgmt,
    exam_mgmt,
    import_api,
    stats_api,
    student_mgmt,
    teacher_mgmt,
)  # noqa: E402,F401
