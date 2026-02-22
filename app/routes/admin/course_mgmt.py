from flask import jsonify, request

from app.models import ClassInfo, CourseAssignment, Subject, Teacher, db

from . import admin_bp


@admin_bp.route("/assignments", methods=["GET"])
def get_assignments():
    academic_year = request.args.get("academic_year", type=int)
    paged = request.args.get("paged", default=0, type=int) == 1
    page = request.args.get("page", default=1, type=int) or 1
    page_size = request.args.get("page_size", type=int)
    if page_size is None:
        page_size = request.args.get("limit", default=20, type=int) or 20

    page = max(page, 1)
    page_size = min(max(page_size, 1), 100)

    query = (
        db.session.query(
            CourseAssignment.id,
            Teacher.name.label("teacher_name"),
            ClassInfo.entry_year,
            ClassInfo.class_num,
            Subject.name.label("subject_name"),
        )
        .join(Teacher, CourseAssignment.teacher_id == Teacher.id)
        .join(ClassInfo, CourseAssignment.class_id == ClassInfo.id)
        .join(Subject, CourseAssignment.subject_id == Subject.id)
    )

    if academic_year:
        query = query.filter(CourseAssignment.academic_year == academic_year)

    query = query.order_by(CourseAssignment.id.desc())
    if paged:
        total = query.count()
        results = query.offset((page - 1) * page_size).limit(page_size).all()
    else:
        results = query.all()

    items = [
        {
            "id": r.id,
            "teacher_name": r.teacher_name,
            "grade_class": f"{r.entry_year}级({r.class_num})班",
            "subject_name": r.subject_name,
        }
        for r in results
    ]

    if paged:
        return jsonify(
            {
                "items": items,
                "total": total,
                "page": page,
                "page_size": page_size,
            }
        )
    return jsonify(items)


@admin_bp.route("/assignments", methods=["POST"])
def add_assignment():
    data = request.get_json()
    exists = CourseAssignment.query.filter_by(
        teacher_id=data["teacher_id"],
        class_id=data["class_id"],
        subject_id=data["subject_id"],
    ).first()

    if exists:
        return jsonify({"msg": "该分配已存在"}), 400

    new_assign = CourseAssignment(
        teacher_id=data["teacher_id"],
        class_id=data["class_id"],
        subject_id=data["subject_id"],
    )
    db.session.add(new_assign)
    db.session.commit()
    return jsonify({"msg": "分配成功"})


@admin_bp.route("/assignments/<int:a_id>", methods=["DELETE"])
def delete_assignment(a_id):
    assign = CourseAssignment.query.get(a_id)
    if assign:
        db.session.delete(assign)
        db.session.commit()
    return jsonify({"msg": "已取消该任课分配"})


@admin_bp.route("/subjects", methods=["GET"])
def get_all_subjects():
    subs = Subject.query.order_by(Subject.id.asc()).all()
    return jsonify([{"id": s.id, "name": s.name} for s in subs])
