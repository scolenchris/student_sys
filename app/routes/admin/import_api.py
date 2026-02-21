import json
from datetime import datetime
from urllib.parse import quote

from flask import jsonify, request, send_file

from app.models import ImportBatch, db
from app.services import excel_service, rollback_service
from app.utils.helpers import _json_loads

from . import admin_bp

IMPORT_TYPE_LABELS = {
    "student": "学生名单",
    "teacher": "教师信息",
    "course_assign": "任课分配",
    "score": "成绩",
}


@admin_bp.route("/students/import", methods=["POST"])
def import_students_excel():
    if "file" not in request.files:
        return jsonify({"msg": "没有上传文件"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"msg": "文件名为空"}), 400

    result, status = excel_service.process_students_import(file)
    return jsonify(result), status


@admin_bp.route("/students/export", methods=["GET"])
def export_students():
    class_id = request.args.get("class_id", type=int)
    output, filename = excel_service.export_students_excel(class_id)
    return send_file(
        output,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name=quote(filename),
        max_age=0,
    )


@admin_bp.route("/teachers/import", methods=["POST"])
def import_teachers_excel():
    if "file" not in request.files:
        return jsonify({"msg": "没有上传文件"}), 400
    file = request.files["file"]
    academic_year = request.form.get("academic_year", type=int)
    result, status = excel_service.process_teachers_import(file, academic_year)
    return jsonify(result), status


@admin_bp.route("/teachers/export", methods=["GET"])
def export_teachers():
    academic_year = request.args.get("academic_year", type=int)
    output, filename = excel_service.export_teachers_excel(academic_year)
    return send_file(
        output,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name=quote(filename),
        max_age=0,
    )


@admin_bp.route("/assignments/import", methods=["POST"])
def import_course_assignments():
    if "file" not in request.files:
        return jsonify({"msg": "没有上传文件"}), 400

    file = request.files["file"]
    academic_year = request.form.get("academic_year", type=int)
    result, status = excel_service.process_course_assignments_import(file, academic_year)
    return jsonify(result), status


@admin_bp.route("/assignments/export", methods=["GET"])
def export_course_assignments():
    try:
        output, filename = excel_service.export_course_assignments_excel()
    except ValueError as e:
        return jsonify({"msg": str(e)}), 400

    return send_file(
        output,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name=quote(filename),
        max_age=0,
    )


@admin_bp.route("/stats/score_template", methods=["POST"])
def get_score_import_template():
    data = request.get_json() or {}
    entry_year = data.get("entry_year")
    class_ids = data.get("class_ids", [])
    subject_ids = data.get("subject_ids", [])
    exam_name = data.get("exam_name")

    try:
        output, filename = excel_service.build_score_import_template(
            entry_year=entry_year,
            class_ids=class_ids,
            subject_ids=subject_ids,
            exam_name=exam_name,
        )
    except ValueError as e:
        return jsonify({"msg": str(e)}), 400

    return send_file(
        output,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name=quote(filename),
        max_age=0,
    )


@admin_bp.route("/stats/import_scores", methods=["POST"])
def import_admin_scores():
    if "file" not in request.files:
        return jsonify({"msg": "未上传文件"}), 400

    file = request.files["file"]
    entry_year = request.form.get("entry_year", type=int)
    exam_name = request.form.get("exam_name")

    try:
        subject_ids = json.loads(request.form.get("subject_ids", "[]"))
        class_ids = json.loads(request.form.get("class_ids", "[]"))
    except Exception:
        return jsonify({"msg": "参数解析错误"}), 400

    result, status = excel_service.process_admin_scores_import(
        file=file,
        entry_year=entry_year,
        exam_name=exam_name,
        subject_ids=subject_ids,
        class_ids=class_ids,
    )
    return jsonify(result), status


@admin_bp.route("/imports/history", methods=["GET"])
def get_import_history():
    page = request.args.get("page", default=1, type=int)
    page_size = request.args.get("page_size", default=20, type=int)
    import_type = request.args.get("import_type", default="", type=str).strip()

    page = max(page, 1)
    page_size = min(max(page_size, 1), 100)

    query = ImportBatch.query
    if import_type:
        query = query.filter_by(import_type=import_type)

    pagination = query.order_by(
        ImportBatch.create_time.desc(), ImportBatch.id.desc()
    ).paginate(page=page, per_page=page_size, error_out=False)

    items = []
    for b in pagination.items:
        scope = _json_loads(b.scope_json, {})
        summary = _json_loads(b.summary_json, {})
        items.append(
            {
                "id": b.id,
                "import_type": b.import_type,
                "import_type_label": IMPORT_TYPE_LABELS.get(b.import_type, b.import_type),
                "source_filename": b.source_filename,
                "scope": scope,
                "summary": summary,
                "can_rollback": bool(b.can_rollback),
                "rolled_back_at": b.rolled_back_at.isoformat() if b.rolled_back_at else None,
                "rollback_note": b.rollback_note,
                "create_time": b.create_time.isoformat() if b.create_time else None,
            }
        )

    return jsonify(
        {"items": items, "total": pagination.total, "page": page, "page_size": page_size}
    )


@admin_bp.route("/imports/<int:batch_id>/rollback", methods=["POST"])
def rollback_import_batch(batch_id):
    batch = ImportBatch.query.get(batch_id)
    if not batch:
        return jsonify({"msg": "导入记录不存在"}), 404

    if not batch.can_rollback:
        return jsonify({"msg": "该批次已回退，不能重复回退"}), 400

    newer_batch = (
        ImportBatch.query.filter(
            ImportBatch.import_type == batch.import_type,
            ImportBatch.id > batch.id,
            ImportBatch.can_rollback.is_(True),
        )
        .order_by(ImportBatch.id.asc())
        .first()
    )
    if newer_batch:
        return (
            jsonify({"msg": f"请先回退更新的同类批次（ID: {newer_batch.id}），再回退当前记录。"}),
            400,
        )

    snapshot = _json_loads(batch.snapshot_json, {})
    scope = _json_loads(batch.scope_json, {})

    try:
        if batch.import_type == "student":
            rollback_service.rollback_students(snapshot)
        elif batch.import_type == "teacher":
            rollback_service.rollback_teacher(snapshot, scope)
        elif batch.import_type == "course_assign":
            rollback_service.rollback_course_assign(snapshot, scope)
        elif batch.import_type == "score":
            rollback_service.rollback_score(snapshot)
        else:
            return jsonify({"msg": "不支持的导入类型，无法回退"}), 400

        batch.can_rollback = False
        batch.rolled_back_at = datetime.now()
        batch.rollback_note = "手动回退完成"
        db.session.commit()
        return jsonify({"msg": f"回退成功：{IMPORT_TYPE_LABELS.get(batch.import_type, batch.import_type)}"})
    except ValueError as e:
        db.session.rollback()
        return jsonify({"msg": str(e)}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({"msg": f"回退失败: {str(e)}"}), 500

