from urllib.parse import quote

from flask import jsonify, request, send_file
from sqlalchemy import func, or_

from app.models import (
    ClassInfo,
    CourseAssignment,
    HeadTeacherAssignment,
    Score,
    Student,
    db,
)
from app.services.document_service import render_student_certificate

from . import admin_bp


@admin_bp.route("/classes", methods=["GET"])
def get_classes():
    paged = request.args.get("paged", default=0, type=int) == 1
    page = request.args.get("page", default=1, type=int) or 1
    page_size = request.args.get("page_size", type=int)
    if page_size is None:
        page_size = request.args.get("limit", default=20, type=int) or 20

    page = max(page, 1)
    page_size = min(max(page_size, 1), 100)

    query = ClassInfo.query.order_by(
        ClassInfo.entry_year.desc(), ClassInfo.class_num.asc()
    )
    if paged:
        pagination = query.paginate(page=page, per_page=page_size, error_out=False)
        classes = pagination.items
        total = pagination.total
    else:
        classes = query.all()
        total = len(classes)

    class_ids = [c.id for c in classes]
    student_count_map = {}
    if class_ids:
        rows = (
            db.session.query(Student.class_id, func.count(Student.id))
            .filter(Student.class_id.in_(class_ids))
            .group_by(Student.class_id)
            .all()
        )
        student_count_map = {class_id: count for class_id, count in rows}

    items = [
        {
            "id": c.id,
            "entry_year": c.entry_year,
            "class_num": c.class_num,
            "grade_name": c.grade_display,
            "student_count": student_count_map.get(c.id, 0),
        }
        for c in classes
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


@admin_bp.route("/classes", methods=["POST"])
def add_class():
    data = request.get_json()
    new_class = ClassInfo(entry_year=data["entry_year"], class_num=data["class_num"])
    db.session.add(new_class)
    db.session.commit()
    return jsonify({"msg": "班级创建成功"})


@admin_bp.route("/classes/<int:class_id>", methods=["DELETE"])
def delete_class(class_id):
    cls = ClassInfo.query.get(class_id)
    if not cls:
        return jsonify({"msg": "班级不存在"}), 404

    student_count = Student.query.filter_by(class_id=class_id).count()
    if student_count > 0:
        return (
            jsonify({"msg": f"删除失败：该班级仍有 {student_count} 名学生，请先完成学籍调整后再删除。"}),
            400,
        )

    try:
        CourseAssignment.query.filter_by(class_id=class_id).delete()
        HeadTeacherAssignment.query.filter_by(class_id=class_id).delete()

        db.session.delete(cls)
        db.session.commit()
        return jsonify({"msg": "班级删除成功"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"msg": f"班级删除失败: {str(e)}"}), 500


@admin_bp.route("/students", methods=["GET"])
def get_students():
    page = request.args.get("page", default=1, type=int) or 1
    page_size = request.args.get("page_size", type=int)
    if page_size is None:
        page_size = request.args.get("limit", default=20, type=int) or 20
    class_id = request.args.get("class_id", type=int)
    keyword = (request.args.get("keyword") or "").strip()

    page = max(page, 1)
    page_size = min(max(page_size, 1), 100)

    query = Student.query
    if class_id:
        query = query.filter_by(class_id=class_id)
    if keyword:
        like_pattern = f"%{keyword}%"
        query = query.filter(
            or_(Student.name.like(like_pattern), Student.student_id.like(like_pattern))
        )

    pagination = query.order_by(Student.student_id.asc()).paginate(
        page=page, per_page=page_size, error_out=False
    )

    data = []
    for s in pagination.items:
        class_name = "未分配"
        if s.current_class_rel:
            c = s.current_class_rel
            short_year = str(c.entry_year)[-2:]
            class_num_str = str(c.class_num).zfill(2)
            class_name = f"{short_year}级({class_num_str})班"

        data.append(
            {
                "id": s.id,
                "student_id": s.student_id,
                "name": s.name,
                "gender": s.gender,
                "class_id": s.class_id,
                "grade_class": class_name,
                "status": s.status,
                "household_registration": s.household_registration,
                "city_school_id": s.city_school_id,
                "national_school_id": s.national_school_id,
                "id_card_number": s.id_card_number,
                "remarks": s.remarks,
            }
        )

    return jsonify(
        {
            "total": pagination.total,
            "data": data,
            "page": page,
            "page_size": page_size,
        }
    )


@admin_bp.route("/students", methods=["POST"])
def add_student():
    data = request.get_json()

    if Student.query.filter_by(student_id=data["student_id"]).first():
        return jsonify({"msg": "学号已存在"}), 400

    id_card = data.get("id_card_number")
    if id_card and Student.query.filter_by(id_card_number=id_card).first():
        return jsonify({"msg": "身份证号已存在"}), 400

    city_sid = data.get("city_school_id", "")
    if city_sid and not city_sid.isdigit():
        return jsonify({"msg": "市学籍号必须为纯数字"}), 400

    student = Student(
        student_id=data["student_id"],
        name=data["name"],
        gender=data.get("gender", "男"),
        class_id=data["class_id"],
        status=data.get("status", "在读"),
        household_registration=data.get("household_registration"),
        city_school_id=city_sid,
        national_school_id=data.get("national_school_id"),
        id_card_number=id_card,
        remarks=data.get("remarks"),
    )
    db.session.add(student)
    db.session.commit()
    return jsonify({"msg": "学生添加成功"})


@admin_bp.route("/students/<int:s_id>", methods=["PUT"])
def update_student(s_id):
    data = request.get_json()
    student = Student.query.get(s_id)
    if not student:
        return jsonify({"msg": "学生不存在"}), 404

    city_sid = data.get("city_school_id", student.city_school_id)
    if city_sid and not str(city_sid).isdigit():
        return jsonify({"msg": "市学籍号必须为纯数字"}), 400

    new_id_card = data.get("id_card_number")
    if new_id_card and new_id_card != student.id_card_number:
        if Student.query.filter_by(id_card_number=new_id_card).first():
            return jsonify({"msg": "该身份证号已被其他学生占用"}), 400

    student.name = data.get("name", student.name)
    student.gender = data.get("gender", student.gender)
    student.class_id = data.get("class_id", student.class_id)
    student.status = data.get("status", student.status)
    student.household_registration = data.get(
        "household_registration", student.household_registration
    )
    student.city_school_id = city_sid
    student.national_school_id = data.get("national_school_id", student.national_school_id)
    student.id_card_number = new_id_card
    student.remarks = data.get("remarks", student.remarks)

    db.session.commit()
    return jsonify({"msg": "学生信息更新成功"})


@admin_bp.route("/students/<int:s_id>", methods=["DELETE"])
def delete_student(s_id):
    student = Student.query.get(s_id)
    if not student:
        return jsonify({"msg": "学生不存在"}), 404

    try:
        Score.query.filter_by(student_id=s_id).delete()
        db.session.delete(student)
        db.session.commit()
        return jsonify({"msg": "删除成功"})

    except Exception as e:
        db.session.rollback()
        return jsonify({"msg": f"删除失败: {str(e)}"}), 500


@admin_bp.route("/students/<int:student_id>/certificate", methods=["GET"])
def generate_certificate(student_id):
    student = Student.query.get(student_id)
    if not student:
        return jsonify({"msg": "学生不存在"}), 404

    try:
        file_stream, filename = render_student_certificate(student)
    except FileNotFoundError as e:
        return jsonify({"msg": str(e)}), 500
    except Exception as e:
        return jsonify({"msg": f"生成证明文件失败: {str(e)}"}), 500

    return send_file(
        file_stream,
        mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        as_attachment=True,
        download_name=quote(filename),
    )
