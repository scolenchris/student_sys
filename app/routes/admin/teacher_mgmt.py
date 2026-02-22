from datetime import datetime

from flask import jsonify, request
from sqlalchemy import or_
from sqlalchemy.orm import selectinload

from app.models import (
    CourseAssignment,
    GradeLeaderAssignment,
    HeadTeacherAssignment,
    PrepGroupLeaderAssignment,
    SubjectGroupLeaderAssignment,
    Teacher,
    User,
    db,
)
from app.utils.helpers import _apply_teacher_status_to_account

from . import admin_bp


@admin_bp.route("/teachers", methods=["GET"])
def get_teachers():
    current_year = datetime.now().year
    default_year = current_year if datetime.now().month >= 9 else current_year - 1

    academic_year = request.args.get("academic_year", default_year, type=int)
    status_filter = request.args.get("status", "在职")
    keyword = (request.args.get("keyword") or "").strip()
    paged = request.args.get("paged", default=0, type=int) == 1
    page = request.args.get("page", default=1, type=int) or 1
    page_size = request.args.get("page_size", type=int)
    if page_size is None:
        page_size = request.args.get("limit", default=20, type=int) or 20
    page = max(page, 1)
    page_size = min(max(page_size, 1), 100)

    query = (
        db.session.query(Teacher, User)
        .join(User, Teacher.user_id == User.id)
        .options(
            selectinload(Teacher.head_teacher_assigns).selectinload(
                HeadTeacherAssignment.class_info
            ),
            selectinload(Teacher.grade_leader_assigns),
            selectinload(Teacher.subject_group_assigns).selectinload(
                SubjectGroupLeaderAssignment.subject
            ),
            selectinload(Teacher.prep_group_assigns).selectinload(
                PrepGroupLeaderAssignment.subject
            ),
            selectinload(Teacher.course_assignments).selectinload(
                CourseAssignment.class_info
            ),
            selectinload(Teacher.course_assignments).selectinload(
                CourseAssignment.subject
            ),
        )
    )
    if status_filter != "全部":
        query = query.filter(Teacher.status == status_filter)
    if keyword:
        like_pattern = f"%{keyword}%"
        query = query.filter(
            or_(Teacher.name.like(like_pattern), User.username.like(like_pattern))
        )
    query = query.order_by(Teacher.id.desc())
    if paged:
        total = query.count()
        teachers = query.offset((page - 1) * page_size).limit(page_size).all()
    else:
        teachers = query.all()

    result = []
    for t, u in teachers:
        ht_list = [
            h.class_info.full_name
            for h in t.head_teacher_assigns
            if h.academic_year == academic_year and h.class_info
        ]
        ht_str = "、".join(ht_list) if ht_list else "否"

        gl_list = [
            g.grade_name
            for g in t.grade_leader_assigns
            if g.academic_year == academic_year
        ]
        gl_str = "、".join(gl_list) if gl_list else "否"

        sgl_list = [
            s.subject.name
            for s in t.subject_group_assigns
            if s.academic_year == academic_year and s.subject
        ]
        sgl_str = "、".join(sgl_list) if sgl_list else "否"

        pgl_list = [
            f"{p.grade_name}{p.subject.name}"
            for p in t.prep_group_assigns
            if p.academic_year == academic_year and p.subject
        ]
        pgl_str = "、".join(pgl_list) if pgl_list else "否"

        my_courses = [c for c in t.course_assignments if c.academic_year == academic_year]
        teaching_grades = sorted(
            list(set([c.class_info.grade_display for c in my_courses if c.class_info]))
        )
        teaching_classes = sorted(
            list(set([c.class_info.full_name for c in my_courses if c.class_info]))
        )
        teaching_subjects = sorted(
            list(set([c.subject.name for c in my_courses if c.subject]))
        )

        duty_parts = []
        if ht_list:
            duty_parts.append("班主任")
        if gl_list:
            duty_parts.append("级长")
        if sgl_list:
            duty_parts.append("科组长")
        if pgl_list:
            duty_parts.append("备课组长")
        if not duty_parts:
            duty_parts.append("科任")

        result.append(
            {
                "id": t.id,
                "username": u.username,
                "name": t.name,
                "gender": t.gender,
                "ethnicity": t.ethnicity,
                "status": t.status,
                "job_duty_display": "、".join(duty_parts),
                "job_title": t.job_title,
                "education": t.education,
                "major": t.major,
                "phone": t.phone,
                "head_teacher_desc": ht_str,
                "grade_leader_desc": gl_str,
                "subject_group_desc": sgl_str,
                "prep_group_desc": pgl_str,
                "teaching_grades": "、".join(teaching_grades) if teaching_grades else "-",
                "teaching_classes": "、".join(teaching_classes) if teaching_classes else "未分配",
                "teaching_subjects": "、".join(teaching_subjects) if teaching_subjects else "-",
                "remarks": t.remarks,
            }
        )

    if paged:
        return jsonify(
            {
                "items": result,
                "total": total,
                "page": page,
                "page_size": page_size,
            }
        )
    return jsonify(result)


@admin_bp.route("/teachers/<int:t_id>", methods=["PUT"])
def update_teacher(t_id):
    data = request.get_json()
    teacher = Teacher.query.get(t_id)
    if not teacher:
        return jsonify({"msg": "找不到该教师"}), 404

    req_year = data.get("academic_year")
    if req_year:
        target_year = int(req_year)
    else:
        now = datetime.now()
        target_year = now.year if now.month >= 9 else now.year - 1

    teacher.name = data.get("name", teacher.name)
    teacher.gender = data.get("gender", teacher.gender)
    teacher.ethnicity = data.get("ethnicity", teacher.ethnicity)
    teacher.phone = data.get("phone", teacher.phone)
    teacher.job_title = data.get("job_title", teacher.job_title)
    teacher.education = data.get("education", teacher.education)
    teacher.major = data.get("major", teacher.major)
    teacher.remarks = data.get("remarks", teacher.remarks)

    if "status" in data:
        new_status = data.get("status")
        if isinstance(new_status, str):
            new_status = new_status.strip()
        if new_status:
            teacher.status = new_status
            _apply_teacher_status_to_account(teacher.user, new_status)

    HeadTeacherAssignment.query.filter_by(
        teacher_id=teacher.id, academic_year=target_year
    ).delete()
    if "head_teacher_ids" in data:
        for cid in data["head_teacher_ids"]:
            db.session.add(
                HeadTeacherAssignment(
                    teacher_id=teacher.id, class_id=cid, academic_year=target_year
                )
            )

    GradeLeaderAssignment.query.filter_by(
        teacher_id=teacher.id, academic_year=target_year
    ).delete()
    if "grade_leader_years" in data:
        for year in data["grade_leader_years"]:
            db.session.add(
                GradeLeaderAssignment(
                    teacher_id=teacher.id, entry_year=year, academic_year=target_year
                )
            )

    SubjectGroupLeaderAssignment.query.filter_by(
        teacher_id=teacher.id, academic_year=target_year
    ).delete()
    if "subject_group_ids" in data:
        for sid in data["subject_group_ids"]:
            db.session.add(
                SubjectGroupLeaderAssignment(
                    teacher_id=teacher.id, subject_id=sid, academic_year=target_year
                )
            )

    PrepGroupLeaderAssignment.query.filter_by(
        teacher_id=teacher.id, academic_year=target_year
    ).delete()
    if "prep_group_data" in data:
        for item in data["prep_group_data"]:
            if item.get("entry_year") and item.get("subject_id"):
                db.session.add(
                    PrepGroupLeaderAssignment(
                        teacher_id=teacher.id,
                        entry_year=item["entry_year"],
                        subject_id=item["subject_id"],
                        academic_year=target_year,
                    )
                )

    db.session.commit()
    return jsonify({"msg": f"教师信息已更新 (针对 {target_year} 学年)"})


@admin_bp.route("/teachers/<int:t_id>/reset_password", methods=["POST"])
def reset_teacher_password(t_id):
    teacher = Teacher.query.get(t_id)
    if not teacher or not teacher.user:
        return jsonify({"msg": "教师账号不存在"}), 404

    user = teacher.user
    user.set_password("123456")
    user.must_change_password = True
    db.session.commit()

    return jsonify({"msg": f"教师 {teacher.name} 的密码已重置为 123456"})
