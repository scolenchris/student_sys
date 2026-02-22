from urllib.parse import quote

from flask import jsonify, request, send_file

from app.services import excel_service, stats_service

from . import admin_bp


@admin_bp.route("/stats/class_report", methods=["GET"])
def get_class_report():
    class_id = request.args.get("class_id")
    term = request.args.get("term")
    return jsonify(stats_service.build_class_report(class_id, term))


@admin_bp.route("/stats/exam_names", methods=["GET"])
def get_grade_exam_names():
    entry_year = request.args.get("entry_year", type=int)
    return jsonify(stats_service.get_exam_names_by_entry_year(entry_year))


@admin_bp.route("/stats/comprehensive_report", methods=["POST"])
def get_comprehensive_report():
    payload, err = stats_service.build_comprehensive_report(request.get_json() or {})
    if err:
        msg, status = err
        return jsonify({"msg": msg}), status
    return jsonify(payload)


@admin_bp.route("/stats/comprehensive_report_export", methods=["POST"])
def export_comprehensive_report_excel():
    data = request.get_json() or {}
    export_query = dict(data)
    export_query["paged"] = False
    export_query.pop("page", None)
    export_query.pop("page_size", None)

    payload, err = stats_service.build_comprehensive_report(export_query)
    if err:
        msg, status = err
        return jsonify({"msg": msg}), status

    try:
        output, filename = excel_service.build_comprehensive_report_excel(
            payload=payload,
            entry_year=str(data.get("entry_year", "")).strip() or "未指定年级",
            exam_name=str(data.get("exam_name", "")).strip() or "未命名考试",
        )
    except ValueError as e:
        return jsonify({"msg": str(e)}), 400

    return send_file(
        output,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name=quote(filename),
    )


@admin_bp.route("/stats/score_rank_trend", methods=["POST"])
def get_score_rank_trend():
    payload, err = stats_service.build_score_rank_trend_payload(request.get_json() or {})
    if err:
        msg, status = err
        return jsonify({"msg": msg}), status
    return jsonify(payload)


@admin_bp.route("/stats/score_rank_trend_export", methods=["POST"])
def export_score_rank_trend_excel():
    data = request.get_json() or {}
    only_changed = bool(data.get("only_changed", False))

    payload, err = stats_service.build_score_rank_trend_payload(data)
    if err:
        msg, status = err
        return jsonify({"msg": msg}), status

    try:
        output, filename = excel_service.build_score_rank_trend_excel(
            payload=payload,
            entry_year=str(data.get("entry_year", "")).strip() or "未指定年级",
            only_changed=only_changed,
        )
    except ValueError as e:
        return jsonify({"msg": str(e)}), 400

    return send_file(
        output,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name=quote(filename),
    )


@admin_bp.route("/stats/class_score_stats", methods=["POST"])
def get_class_score_stats():
    payload, err = stats_service.build_class_score_stats(request.get_json() or {})
    if err:
        msg, status = err
        return jsonify({"msg": msg}), status
    return jsonify(payload)


@admin_bp.route("/stats/teacher_score_stats", methods=["POST"])
def get_teacher_score_stats():
    payload, err = stats_service.build_teacher_score_stats(request.get_json() or {})
    if err:
        msg, status = err
        return jsonify({"msg": msg}), status
    return jsonify(payload)


@admin_bp.route("/stats/teacher_score_stats_export", methods=["POST"])
def export_teacher_score_stats_excel():
    data = request.get_json() or {}
    payload, err = stats_service.build_teacher_score_stats(data)
    if err:
        msg, status = err
        return jsonify({"msg": msg}), status

    try:
        output, filename = excel_service.build_teacher_score_stats_excel(
            rows=payload,
            entry_year=str(data.get("entry_year", "")).strip() or "未指定年级",
            exam_name=str(data.get("exam_name", "")).strip() or "未命名考试",
            academic_year=data.get("academic_year"),
        )
    except ValueError as e:
        return jsonify({"msg": str(e)}), 400

    return send_file(
        output,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name=quote(filename),
    )
