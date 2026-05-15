import hashlib
import hmac
import json
import os
import re
import sys
from datetime import date, datetime


PRODUCT_ID = "student_sys"
LICENSE_FILENAME = "student_sys.lic"
STATE_FILENAME = "student_sys_license_state.json"
LICENSE_FILE_ENV = "STUDENT_SYS_LICENSE_FILE"

_LICENSE_SECRET = bytes.fromhex(
    "a1be520f95fb2fac123331c6af1a12c38bd1dc2417cf1b803c19d444ee459783"
    "a5361d151cfd7f33c5c045f41642e873c8ef0bdede13e1c77f053af700d9f501"
)
_DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class LicenseError(RuntimeError):
    """授权凭证校验失败。"""


def _runtime_dir():
    if getattr(sys, "frozen", False) or "__compiled__" in globals():
        return os.path.dirname(sys.executable)
    return os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))


def get_license_path():
    env_path = os.environ.get(LICENSE_FILE_ENV, "").strip()
    if env_path:
        return os.path.abspath(env_path)
    return os.path.join(_runtime_dir(), LICENSE_FILENAME)


def _get_state_path(license_path):
    env_path = os.environ.get(LICENSE_FILE_ENV, "").strip()
    if env_path:
        return os.path.join(os.path.dirname(os.path.abspath(license_path)), STATE_FILENAME)
    return os.path.join(_runtime_dir(), STATE_FILENAME)


def _canonical_payload(payload):
    try:
        raw = json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
    except (TypeError, ValueError):
        raise LicenseError("授权凭证内容包含不支持的数据格式")
    return raw.encode("utf-8")


def build_signature(payload):
    return hmac.new(
        _LICENSE_SECRET,
        _canonical_payload(payload),
        hashlib.sha256,
    ).hexdigest()


def _parse_date(value, label):
    if not isinstance(value, str) or not _DATE_PATTERN.match(value):
        raise LicenseError(f"授权凭证中的{label}格式不正确")
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise LicenseError(f"授权凭证中的{label}不是有效日期")


def _load_json(path, missing_message):
    if not os.path.exists(path):
        raise LicenseError(missing_message)

    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        raise LicenseError("授权凭证格式错误，无法解析")
    except OSError as e:
        raise LicenseError(f"授权凭证读取失败: {e}")


def _load_license_document(path):
    return _load_json(
        path,
        f"未检测到授权凭证文件，请将 {LICENSE_FILENAME} 放在程序目录后再启动",
    )


def _verify_document(document):
    if not isinstance(document, dict):
        raise LicenseError("授权凭证格式错误")

    payload = document.get("payload")
    signature = document.get("signature")
    if not isinstance(payload, dict) or not isinstance(signature, str):
        raise LicenseError("授权凭证缺少必要字段")

    expected_signature = build_signature(payload)
    provided_signature = signature.strip().lower()
    if not hmac.compare_digest(provided_signature, expected_signature):
        raise LicenseError("授权凭证签名校验失败，文件可能已被修改")

    if payload.get("product") != PRODUCT_ID:
        raise LicenseError("授权凭证不适用于当前系统")

    for field, label in (
        ("license_id", "授权编号"),
        ("customer", "授权客户"),
        ("issued_at", "签发时间"),
    ):
        if not str(payload.get(field) or "").strip():
            raise LicenseError(f"授权凭证缺少{label}")

    return payload


def _load_state(state_path):
    if not os.path.exists(state_path):
        return {}

    try:
        with open(state_path, "r", encoding="utf-8") as f:
            state = json.load(f)
    except json.JSONDecodeError:
        raise LicenseError("授权状态文件异常，请联系管理员处理")
    except OSError as e:
        raise LicenseError(f"授权状态文件读取失败: {e}")

    if not isinstance(state, dict):
        raise LicenseError("授权状态文件异常，请联系管理员处理")
    return state


def _write_state(state_path, payload, today):
    state_data = {
        "product": PRODUCT_ID,
        "license_id": str(payload.get("license_id") or ""),
        "customer": str(payload.get("customer") or ""),
        "last_valid_date": today.isoformat(),
        "updated_at": datetime.now().isoformat(timespec="seconds"),
    }

    try:
        os.makedirs(os.path.dirname(state_path), exist_ok=True)
        tmp_path = f"{state_path}.tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(state_data, f, ensure_ascii=False, indent=2)
            f.write("\n")
        os.replace(tmp_path, state_path)
    except OSError as e:
        raise LicenseError(f"授权状态文件写入失败，请检查程序目录权限: {e}")


def _check_clock_rollback(payload, today, state_path):
    state = _load_state(state_path)
    last_valid_date = state.get("last_valid_date")
    last_date = None
    if last_valid_date:
        last_date = _parse_date(last_valid_date, "上次校验日期")

    if last_date and today < last_date:
        raise LicenseError(
            f"检测到系统日期早于上次授权校验日期 {last_date.isoformat()}，"
            "请校准电脑日期后再使用"
        )

    same_license = state.get("license_id") == payload.get("license_id")
    if last_date == today and same_license:
        return

    _write_state(state_path, payload, today)


def validate_license(current_date=None):
    license_path = get_license_path()
    document = _load_license_document(license_path)
    payload = _verify_document(document)

    valid_from = _parse_date(payload.get("valid_from"), "有效开始日期")
    valid_until = _parse_date(payload.get("valid_until"), "有效截止日期")
    if valid_until < valid_from:
        raise LicenseError("授权凭证有效期配置不正确")

    today = current_date or date.today()
    if today < valid_from:
        raise LicenseError(f"授权尚未生效，有效开始日期为 {valid_from.isoformat()}")
    if today > valid_until:
        raise LicenseError(f"授权已过期，有效期至 {valid_until.isoformat()}")

    state_path = _get_state_path(license_path)
    _check_clock_rollback(payload, today, state_path)

    return {
        "license_path": license_path,
        "license_id": str(payload.get("license_id") or ""),
        "customer": str(payload.get("customer") or ""),
        "valid_from": valid_from.isoformat(),
        "valid_until": valid_until.isoformat(),
    }
