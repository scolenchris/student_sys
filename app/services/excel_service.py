import io
import json
import re
from datetime import datetime

import pandas as pd

from app.models import (
    ClassInfo,
    CourseAssignment,
    ExamTask,
    GradeLeaderAssignment,
    HeadTeacherAssignment,
    PrepGroupLeaderAssignment,
    Score,
    Student,
    Subject,
    SubjectGroupLeaderAssignment,
    Teacher,
    User,
    db,
)
from app.utils.helpers import (
    _apply_teacher_status_to_account,
    _create_import_batch,
    _normalize_excel_sheet_name,
    _serialize_score,
    _serialize_student,
    _serialize_teacher,
    _serialize_user,
    _to_excel_value,
)


def build_score_rank_trend_excel(payload, entry_year, only_changed=False):
    subjects = payload.get("subjects", [])
    exams = payload.get("exams", [])
    rows = payload.get("rows", [])
    warnings = payload.get("warnings", [])

    if only_changed:
        rows = [row for row in rows if row.get("has_change")]

    if not exams:
        raise ValueError("当前筛选条件下无可导出的考试数据")

    output = io.BytesIO()
    used_sheet_names = set()

    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        total_columns = ["学号", "姓名", "班级", "状态"]
        for idx, exam in enumerate(exams):
            exam_name = exam.get("name", "")
            total_columns.append(f"{exam_name}-总分")
            total_columns.append(f"{exam_name}-级排")
            total_columns.append(f"{exam_name}-班排")
            if idx > 0:
                prev_exam_name = exams[idx - 1].get("name", "")
                total_columns.append(f"{prev_exam_name}->{exam_name}-总分变化")
                total_columns.append(f"{prev_exam_name}->{exam_name}-级排变化")
                total_columns.append(f"{prev_exam_name}->{exam_name}-班排变化")

        total_records = []
        for row in rows:
            base = {
                "学号": row.get("student_id", ""),
                "姓名": row.get("name", ""),
                "班级": row.get("class_name", ""),
                "状态": row.get("status", ""),
            }
            exam_data_map = row.get("exam_data", {})

            for idx, exam in enumerate(exams):
                exam_name = exam.get("name", "")
                exam_data = exam_data_map.get(exam_name, {})
                base[f"{exam_name}-总分"] = _to_excel_value(exam_data.get("total"))
                base[f"{exam_name}-级排"] = _to_excel_value(exam_data.get("grade_rank"))
                base[f"{exam_name}-班排"] = _to_excel_value(exam_data.get("class_rank"))
                if idx > 0:
                    prev_exam_name = exams[idx - 1].get("name", "")
                    base[f"{prev_exam_name}->{exam_name}-总分变化"] = _to_excel_value(
                        exam_data.get("total_change")
                    )
                    base[f"{prev_exam_name}->{exam_name}-级排变化"] = _to_excel_value(
                        exam_data.get("grade_rank_change")
                    )
                    base[f"{prev_exam_name}->{exam_name}-班排变化"] = _to_excel_value(
                        exam_data.get("class_rank_change")
                    )
            total_records.append(base)

        total_df = pd.DataFrame(total_records).reindex(columns=total_columns)
        total_df.to_excel(
            writer,
            index=False,
            sheet_name=_normalize_excel_sheet_name("总分变化", used_sheet_names),
        )

        for subject_name in subjects:
            subject_columns = ["学号", "姓名", "班级", "状态"]
            for idx, exam in enumerate(exams):
                exam_name = exam.get("name", "")
                subject_columns.append(f"{exam_name}-成绩")
                subject_columns.append(f"{exam_name}-级排")
                subject_columns.append(f"{exam_name}-班排")
                if idx > 0:
                    prev_exam_name = exams[idx - 1].get("name", "")
                    subject_columns.append(f"{prev_exam_name}->{exam_name}-变化")
                    subject_columns.append(f"{prev_exam_name}->{exam_name}-级排变化")
                    subject_columns.append(f"{prev_exam_name}->{exam_name}-班排变化")

            subject_records = []
            for row in rows:
                base = {
                    "学号": row.get("student_id", ""),
                    "姓名": row.get("name", ""),
                    "班级": row.get("class_name", ""),
                    "状态": row.get("status", ""),
                }
                exam_data_map = row.get("exam_data", {})

                for idx, exam in enumerate(exams):
                    exam_name = exam.get("name", "")
                    exam_data = exam_data_map.get(exam_name, {})
                    score_map = exam_data.get("scores", {}) or {}
                    score_change_map = exam_data.get("score_changes", {}) or {}

                    base[f"{exam_name}-成绩"] = _to_excel_value(
                        score_map.get(subject_name)
                    )
                    base[f"{exam_name}-级排"] = _to_excel_value(
                        exam_data.get("grade_rank")
                    )
                    base[f"{exam_name}-班排"] = _to_excel_value(
                        exam_data.get("class_rank")
                    )
                    if idx > 0:
                        prev_exam_name = exams[idx - 1].get("name", "")
                        base[f"{prev_exam_name}->{exam_name}-变化"] = _to_excel_value(
                            score_change_map.get(subject_name)
                        )
                        base[f"{prev_exam_name}->{exam_name}-级排变化"] = _to_excel_value(
                            exam_data.get("grade_rank_change")
                        )
                        base[f"{prev_exam_name}->{exam_name}-班排变化"] = _to_excel_value(
                            exam_data.get("class_rank_change")
                        )
                subject_records.append(base)

            subject_df = pd.DataFrame(subject_records).reindex(columns=subject_columns)
            subject_df.to_excel(
                writer,
                index=False,
                sheet_name=_normalize_excel_sheet_name(
                    f"{subject_name}变化", used_sheet_names
                ),
            )

        if warnings:
            warn_df = pd.DataFrame([{"提示": w} for w in warnings])
            warn_df.to_excel(
                writer,
                index=False,
                sheet_name=_normalize_excel_sheet_name("导出说明", used_sheet_names),
            )

    output.seek(0)
    suffix = "_仅变化" if only_changed else ""
    filename = f"{entry_year}级_成绩变化比较{suffix}.xlsx"
    return output, filename


def process_students_import(file):
    try:
        df = pd.read_excel(file).fillna("")

        class_col = next((col for col in df.columns if "班级" in str(col)), None)
        name_col = next((col for col in df.columns if "姓名" in str(col)), None)
        id_col = next((col for col in df.columns if "学号" in str(col)), None)

        if not class_col or not name_col or not id_col:
            return {"msg": "Excel格式错误，缺少必要列(姓名/学号/班级)"}, 400

        success_count = 0
        updated_count = 0
        warnings = []
        before_students = {}
        created_student_ids = []
        created_class_ids = []

        class_pattern = re.compile(r"(\d+)级\s*[（\(](\d+)[）\)]\s*班")

        def clean_str(val):
            s = str(val).strip()
            return s[:-2] if s.endswith(".0") else s

        for index, row in df.iterrows():
            row_num = index + 2
            class_str = str(row[class_col]).strip()
            match = class_pattern.search(class_str)

            class_id = None
            if match:
                y_str = match.group(1)
                n_str = match.group(2)
                short_year = int(y_str)
                entry_year = 2000 + short_year if short_year < 100 else short_year
                class_num = int(n_str)

                cls = ClassInfo.query.filter_by(
                    entry_year=entry_year, class_num=class_num
                ).first()
                if not cls:
                    cls = ClassInfo(entry_year=entry_year, class_num=class_num)
                    db.session.add(cls)
                    db.session.flush()
                    created_class_ids.append(
                        {"id": cls.id, "entry_year": entry_year, "class_num": class_num}
                    )
                class_id = cls.id
            else:
                warnings.append(f"行{row_num}: 班级格式无法识别【{class_str}】，已跳过。")
                continue

            student_id = clean_str(row[id_col])
            if not student_id:
                continue

            name = str(row[name_col]).strip()
            student = Student.query.filter_by(student_id=student_id).first()
            is_new = False

            if not student:
                student = Student(student_id=student_id)
                is_new = True
                created_student_ids.append(student_id)
            elif student_id not in before_students:
                before_students[student_id] = _serialize_student(student)

            student.name = name
            student.class_id = class_id
            student.gender = str(row.get("性别", "男")).strip()
            student.status = str(row.get("状态", "在读")).strip()
            student.household_registration = str(row.get("户籍", "")).strip()
            student.remarks = str(row.get("备注", "")).strip()

            student.city_school_id = clean_str(row.get("市学籍号", ""))
            student.national_school_id = clean_str(row.get("国家学籍号", ""))

            raw_id_card = str(row.get("身份证号", "")).strip()
            if raw_id_card:
                conflict_stu = Student.query.filter_by(id_card_number=raw_id_card).first()
                if conflict_stu and conflict_stu.student_id != student_id:
                    warnings.append(
                        f"行{row_num}: 学生【{name}】的身份证号与库中【{conflict_stu.name}】重复，已忽略身份证更新。"
                    )
                else:
                    student.id_card_number = raw_id_card

            if is_new:
                db.session.add(student)
                success_count += 1
            else:
                updated_count += 1

        _create_import_batch(
            import_type="student",
            source_filename=file.filename,
            scope={},
            summary={
                "added": success_count,
                "updated": updated_count,
                "warning_count": len(warnings),
            },
            snapshot={
                "before_students": list(before_students.values()),
                "created_student_ids": created_student_ids,
                "created_class_ids": created_class_ids,
            },
        )
        db.session.commit()

        msg = f"导入成功！新增 {success_count} 人，更新 {updated_count} 人。"
        if warnings:
            msg += f" (有 {len(warnings)} 条警告: {'; '.join(warnings[:3])}...)"

        return {
            "msg": msg,
            "added": success_count,
            "updated": updated_count,
            "warnings": warnings,
        }, 200

    except Exception as e:
        db.session.rollback()
        return {"msg": f"数据库错误: {str(e)}"}, 500


def export_students_excel(class_id):
    query = Student.query
    if class_id:
        query = query.filter_by(class_id=class_id)

    students = (
        query.join(ClassInfo)
        .order_by(
            ClassInfo.entry_year.desc(),
            ClassInfo.class_num.asc(),
            Student.student_id.asc(),
        )
        .all()
    )

    columns = [
        "学号",
        "姓名",
        "性别",
        "班级",
        "状态",
        "身份证号",
        "市学籍号",
        "国家学籍号",
        "户籍",
        "备注",
    ]

    data_list = []
    for s in students:
        class_name = ""
        if s.current_class_rel:
            c = s.current_class_rel
            short_year = str(c.entry_year)[-2:]
            class_num_str = str(c.class_num).zfill(2)
            class_name = f"{short_year}级({class_num_str})班"

        data_list.append(
            {
                "学号": s.student_id,
                "姓名": s.name,
                "性别": s.gender,
                "班级": class_name,
                "状态": s.status,
                "身份证号": s.id_card_number,
                "市学籍号": s.city_school_id,
                "国家学籍号": s.national_school_id,
                "户籍": s.household_registration,
                "备注": s.remarks,
            }
        )

    df = pd.DataFrame(data_list, columns=columns)

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="学生信息")

    output.seek(0)
    filename = "全体学生名单_备份.xlsx"
    if class_id:
        cls = ClassInfo.query.get(class_id)
        if cls:
            filename = f"{cls.full_name}_学生名单.xlsx"
    return output, filename


def process_teachers_import(file, academic_year):
    if not academic_year:
        return {"msg": "请选择导入的学年"}, 400

    try:
        df = pd.read_excel(file).fillna("")
    except Exception as e:
        return {"msg": f"读取Excel失败: {str(e)}"}, 400

    valid_years = [academic_year, academic_year - 1, academic_year - 2]
    valid_years_str = "/".join([f"{y}级" for y in valid_years])

    all_subjects = Subject.query.all()
    subject_map = {s.name: s.id for s in all_subjects}

    def split_str(s):
        return [x.strip() for x in re.split(r"[,，]", str(s)) if x.strip()]

    def parse_year(yr_str):
        match = re.search(r"(\d+)级?", str(yr_str))
        if match:
            y_str = match.group(1)
            return int(y_str) if len(y_str) == 4 else 2000 + int(y_str)
        return None

    errors = []
    for index, row in df.iterrows():
        row_num = index + 2
        name = str(row.get("姓名", "")).strip()
        if not name:
            continue

        gl_str = row.get("级长分配", "")
        for item in split_str(gl_str):
            entry_year = parse_year(item)
            if entry_year and entry_year not in valid_years:
                errors.append(
                    f"行{row_num} ({name}): 级长年份【{entry_year}级】在 {academic_year} 学年无效。合法范围: {valid_years_str}"
                )

        pgl_str = row.get("备课组长分配", "")
        for item in split_str(pgl_str):
            y_match = re.search(r"(\d+)级?", item)
            if y_match:
                y_str = y_match.group(1)
                entry_year = int(y_str) if len(y_str) == 4 else 2000 + int(y_str)

                if entry_year not in valid_years:
                    errors.append(
                        f"行{row_num} ({name}): 备课组年份【{entry_year}级】在 {academic_year} 学年无效。合法范围: {valid_years_str}"
                    )

            sub_name = re.sub(r"\d+级?", "", item).strip()
            if sub_name and sub_name not in subject_map:
                errors.append(f"行{row_num} ({name}): 备课组科目【{sub_name}】不存在")

    if errors:
        error_msg = "<br>".join(errors[:5])
        if len(errors) > 5:
            error_msg += f"<br>... 等共 {len(errors)} 处错误"
        return {"msg": f"数据校验未通过，请修正Excel后重试：<br>{error_msg}"}, 400

    try:
        before_assignments = {
            "grade": [
                {
                    "teacher_id": r.teacher_id,
                    "entry_year": r.entry_year,
                    "academic_year": r.academic_year,
                }
                for r in GradeLeaderAssignment.query.filter_by(
                    academic_year=academic_year
                ).all()
            ],
            "subject": [
                {
                    "teacher_id": r.teacher_id,
                    "subject_id": r.subject_id,
                    "academic_year": r.academic_year,
                }
                for r in SubjectGroupLeaderAssignment.query.filter_by(
                    academic_year=academic_year
                ).all()
            ],
            "prep": [
                {
                    "teacher_id": r.teacher_id,
                    "entry_year": r.entry_year,
                    "subject_id": r.subject_id,
                    "academic_year": r.academic_year,
                }
                for r in PrepGroupLeaderAssignment.query.filter_by(
                    academic_year=academic_year
                ).all()
            ],
        }

        db.session.query(GradeLeaderAssignment).filter_by(
            academic_year=academic_year
        ).delete()
        db.session.query(SubjectGroupLeaderAssignment).filter_by(
            academic_year=academic_year
        ).delete()
        db.session.query(PrepGroupLeaderAssignment).filter_by(
            academic_year=academic_year
        ).delete()

        added_count = 0
        updated_count = 0
        frozen_count = 0
        before_users = {}
        before_teachers = {}
        created_usernames = []
        created_teacher_user_ids = []

        for _, row in df.iterrows():
            username = str(row.get("工号", "")).strip()
            name = str(row.get("姓名", "")).strip()
            if not username or not name:
                continue

            user = User.query.filter_by(username=username).first()
            if not user:
                user = User(
                    username=username,
                    role="teacher",
                    is_approved=True,
                    must_change_password=True,
                )
                user.set_password("123456")
                db.session.add(user)
                db.session.flush()
                created_usernames.append(username)

                teacher = Teacher(user_id=user.id, name=name)
                db.session.add(teacher)
                db.session.flush()
                created_teacher_user_ids.append(user.id)
                added_count += 1
            else:
                if username not in before_users:
                    before_users[username] = _serialize_user(user)
                teacher = user.teacher_profile
                if teacher:
                    if user.id not in before_teachers:
                        before_teachers[user.id] = _serialize_teacher(teacher)
                    updated_count += 1
                else:
                    teacher = Teacher(user_id=user.id, name=name)
                    db.session.add(teacher)
                    db.session.flush()
                    created_teacher_user_ids.append(user.id)

            teacher.name = name
            teacher.gender = str(row.get("性别", teacher.gender))
            teacher.phone = str(row.get("电话", teacher.phone))
            teacher.job_title = str(row.get("职称", teacher.job_title))

            new_status = str(row.get("状态", "")).strip()
            if new_status:
                teacher.status = new_status
                _apply_teacher_status_to_account(user, new_status)
                if new_status in ["退休", "离职", "非在职"]:
                    frozen_count += 1

            gl_str = row.get("级长分配", "")
            for item in split_str(gl_str):
                entry_year = parse_year(item)
                if entry_year:
                    db.session.add(
                        GradeLeaderAssignment(
                            teacher_id=teacher.id,
                            entry_year=entry_year,
                            academic_year=academic_year,
                        )
                    )

            sgl_str = row.get("科组长分配", "")
            for item in split_str(sgl_str):
                sid = subject_map.get(item)
                if sid:
                    db.session.add(
                        SubjectGroupLeaderAssignment(
                            teacher_id=teacher.id,
                            subject_id=sid,
                            academic_year=academic_year,
                        )
                    )

            pgl_str = row.get("备课组长分配", "")
            for item in split_str(pgl_str):
                y_match = re.search(r"(\d+)级?", item)
                if y_match:
                    y_str = y_match.group(1)
                    entry_year = int(y_str) if len(y_str) == 4 else 2000 + int(y_str)
                    sub_name = item.replace(y_match.group(0), "").strip()
                    sid = subject_map.get(sub_name)

                    if entry_year and sid:
                        db.session.add(
                            PrepGroupLeaderAssignment(
                                teacher_id=teacher.id,
                                entry_year=entry_year,
                                subject_id=sid,
                                academic_year=academic_year,
                            )
                        )

        _create_import_batch(
            import_type="teacher",
            source_filename=file.filename,
            scope={"academic_year": academic_year},
            summary={
                "added": added_count,
                "updated": updated_count,
                "frozen": frozen_count,
            },
            snapshot={
                "before_assignments": before_assignments,
                "before_users": list(before_users.values()),
                "before_teachers": list(before_teachers.values()),
                "created_usernames": created_usernames,
                "created_teacher_user_ids": created_teacher_user_ids,
            },
        )
        db.session.commit()
        return {
            "msg": f"处理完成。新增 {added_count} 人，更新 {updated_count} 人，其中 {frozen_count} 人因退休/离职被冻结。"
        }, 200

    except Exception as e:
        db.session.rollback()
        return {"msg": f"导入失败: {str(e)}"}, 500


def process_course_assignments_import(file, academic_year):
    if not academic_year:
        return {"msg": "请选择导入的学年"}, 400

    try:
        df = pd.read_excel(file).fillna("")
    except Exception as e:
        return {"msg": f"Excel读取失败: {str(e)}"}, 400

    valid_years = [academic_year, academic_year - 1, academic_year - 2]
    valid_years_str = "/".join([f"{y}级" for y in valid_years])

    all_teachers = Teacher.query.all()
    teacher_map = {t.name: t.id for t in all_teachers}

    all_subjects = Subject.query.all()
    subject_map = {s.name: s.id for s in all_subjects}

    all_classes = ClassInfo.query.all()
    class_map = {}
    for c in all_classes:
        short_year = str(c.entry_year)[-2:]
        class_num_str = str(c.class_num).zfill(2)
        key = f"{short_year}级({class_num_str})班"
        class_map[key] = c.id

    class_pattern = re.compile(r"(\d+)级\s*[（\(](\d+)[）\)]\s*班")

    errors = []
    missing_teachers = set()

    class_col = next((col for col in df.columns if "班级" in str(col)), None)
    if not class_col:
        return {"msg": "Excel中未找到包含[班级]的列"}, 400

    for index, row in df.iterrows():
        row_num = index + 2
        class_name_raw = str(row[class_col]).strip()

        if not class_name_raw:
            continue

        match = class_pattern.search(class_name_raw)
        standard_key = None

        if match:
            y_str = match.group(1)
            n_str = match.group(2)

            entry_year = int(y_str) if len(y_str) == 4 else 2000 + int(y_str)
            short_year = str(entry_year)[-2:]
            class_num = int(n_str)
            standard_key = f"{short_year}级({str(class_num).zfill(2)})班"

            if entry_year not in valid_years:
                errors.append(
                    f"行{row_num}: 班级【{standard_key}】(原:{class_name_raw}) 的年份在 {academic_year} 学年无效。合法范围: {valid_years_str}"
                )
                continue

            if standard_key not in class_map:
                errors.append(
                    f"行{row_num}: 系统中找不到班级【{standard_key}】，请先在班级管理中创建"
                )
                continue
        else:
            errors.append(f"行{row_num}: 班级名格式无法识别【{class_name_raw}】")
            continue

        cls_obj = ClassInfo.query.get(class_map[standard_key])
        if cls_obj and cls_obj.entry_year not in valid_years:
            errors.append(
                f"行{row_num}: 班级【{standard_key}】是 {cls_obj.entry_year}级，不属于 {academic_year} 学年的范围"
            )

        for col_name in df.columns:
            if col_name == class_col or not str(col_name).strip():
                continue

            cell_value = str(row[col_name]).strip()
            if not cell_value:
                continue

            is_subject = col_name in subject_map
            is_ht = "班主任" in str(col_name)

            if (is_subject or is_ht) and cell_value not in teacher_map:
                missing_teachers.add(cell_value)

    if missing_teachers:
        t_list = list(missing_teachers)[:5]
        msg = f"系统不存在以下教师: {', '.join(t_list)}"
        if len(missing_teachers) > 5:
            msg += "..."
        errors.append(msg)

    if errors:
        error_html = "<br>".join(errors[:8])
        if len(errors) > 8:
            error_html += f"<br>... 等共 {len(errors)} 处问题"
        return {"msg": f"校验失败，请修正后重试：<br>{error_html}", "errors": errors}, 400

    try:
        before_course_assignments = [
            {
                "teacher_id": item.teacher_id,
                "class_id": item.class_id,
                "subject_id": item.subject_id,
                "academic_year": item.academic_year,
            }
            for item in CourseAssignment.query.filter_by(academic_year=academic_year).all()
        ]
        before_head_teacher_assignments = [
            {
                "teacher_id": item.teacher_id,
                "class_id": item.class_id,
                "academic_year": item.academic_year,
            }
            for item in HeadTeacherAssignment.query.filter_by(
                academic_year=academic_year
            ).all()
        ]

        db.session.query(CourseAssignment).filter_by(academic_year=academic_year).delete()
        db.session.query(HeadTeacherAssignment).filter_by(academic_year=academic_year).delete()

        count = 0

        for _, row in df.iterrows():
            class_name_raw = str(row[class_col]).strip()
            if not class_name_raw:
                continue

            match = class_pattern.search(class_name_raw)
            if not match:
                continue

            y_str = match.group(1)
            n_str = match.group(2)
            entry_year = int(y_str) if len(y_str) == 4 else 2000 + int(y_str)
            short_year = str(entry_year)[-2:]
            class_num = int(n_str)
            standard_key = f"{short_year}级({str(class_num).zfill(2)})班"

            if standard_key not in class_map:
                continue

            class_id = class_map[standard_key]

            for col_name in df.columns:
                teacher_name = str(row[col_name]).strip()
                if not teacher_name:
                    continue

                if "班主任" in str(col_name):
                    teacher_id = teacher_map.get(teacher_name)
                    if teacher_id:
                        db.session.add(
                            HeadTeacherAssignment(
                                teacher_id=teacher_id,
                                class_id=class_id,
                                academic_year=academic_year,
                            )
                        )
                elif col_name in subject_map:
                    teacher_id = teacher_map.get(teacher_name)
                    subject_id = subject_map[col_name]
                    if teacher_id:
                        db.session.add(
                            CourseAssignment(
                                teacher_id=teacher_id,
                                class_id=class_id,
                                subject_id=subject_id,
                                academic_year=academic_year,
                            )
                        )

            count += 1

        _create_import_batch(
            import_type="course_assign",
            source_filename=file.filename,
            scope={"academic_year": academic_year},
            summary={"updated_classes": count},
            snapshot={
                "before_course_assignments": before_course_assignments,
                "before_head_teacher_assignments": before_head_teacher_assignments,
            },
        )
        db.session.commit()
        return {
            "msg": f"导入成功！已更新 {academic_year} 学年 {count} 个班级的任课与班主任信息。"
        }, 200

    except Exception as e:
        db.session.rollback()
        return {"msg": f"数据库写入错误: {str(e)}"}, 500


def export_course_assignments_excel():
    classes = ClassInfo.query.order_by(
        ClassInfo.entry_year.desc(), ClassInfo.class_num.asc()
    ).all()
    subjects = Subject.query.order_by(Subject.id).all()

    if not classes:
        raise ValueError("暂无班级数据，请先在班级管理中创建班级")

    ht_assigns = HeadTeacherAssignment.query.all()
    ht_map = {ht.class_id: ht.teacher.name for ht in ht_assigns if ht.teacher}

    course_assigns = CourseAssignment.query.all()
    ca_map = {
        (ca.class_id, ca.subject_id): ca.teacher.name
        for ca in course_assigns
        if ca.teacher
    }

    data_list = []
    for cls in classes:
        short_year = str(cls.entry_year)[-2:]
        class_num_str = str(cls.class_num).zfill(2)
        class_name_str = f"{short_year}级({class_num_str})班"

        row = {"班级名称": class_name_str, "人数": cls.students.count(), "班主任": ht_map.get(cls.id, "")}
        for sub in subjects:
            row[sub.name] = ca_map.get((cls.id, sub.id), "")
        data_list.append(row)

    df = pd.DataFrame(data_list)
    column_order = ["班级名称", "人数", "班主任"] + [s.name for s in subjects]
    df = df.reindex(columns=column_order)

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="任课总表")

    output.seek(0)
    return output, "任课分配表(导入模板_备份).xlsx"


def export_teachers_excel(academic_year=None):
    current_year = datetime.now().year
    default_year = current_year if datetime.now().month >= 9 else current_year - 1
    target_year = academic_year or default_year

    teachers = Teacher.query.all()
    columns = [
        "工号",
        "姓名",
        "性别",
        "状态",
        "电话",
        "职称",
        "班主任分配",
        "级长分配",
        "科组长分配",
        "备课组长分配",
        "任教分配",
    ]

    data_list = []
    for t in teachers:
        user = User.query.get(t.user_id)
        username = user.username if user else ""

        ht_list = [
            h.class_info.full_name
            for h in t.head_teacher_assigns
            if h.class_info and h.academic_year == target_year
        ]
        gl_list = [
            f"{g.entry_year}级"
            for g in t.grade_leader_assigns
            if g.academic_year == target_year
        ]
        sgl_list = [
            s.subject.name
            for s in t.subject_group_assigns
            if s.subject and s.academic_year == target_year
        ]

        pgl_list = []
        for p in t.prep_group_assigns:
            if p.subject and p.academic_year == target_year:
                pgl_list.append(f"{p.entry_year}级{p.subject.name}")

        course_list = []
        for c in t.course_assignments:
            if c.class_info and c.subject and c.academic_year == target_year:
                course_list.append(f"{c.class_info.full_name}-{c.subject.name}")

        data_list.append(
            {
                "工号": username,
                "姓名": t.name,
                "性别": t.gender,
                "状态": t.status,
                "电话": t.phone,
                "职称": t.job_title,
                "班主任分配": "，".join(ht_list),
                "级长分配": "，".join(gl_list),
                "科组长分配": "，".join(sgl_list),
                "备课组长分配": "，".join(pgl_list),
                "任教分配": "，".join(course_list),
            }
        )

    df = pd.DataFrame(data_list, columns=columns)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name=f"{target_year}学年教师信息")

    output.seek(0)
    return output, f"{target_year}学年_教师信息表(备份).xlsx"


def build_score_import_template(entry_year, class_ids, subject_ids, exam_name=None):
    if not entry_year or not subject_ids:
        raise ValueError("请至少选择年级和统计科目")

    subjects = Subject.query.filter(Subject.id.in_(subject_ids)).order_by(Subject.id).all()
    subject_names = [s.name for s in subjects]

    query_cls = ClassInfo.query.filter_by(entry_year=entry_year)
    if class_ids:
        query_cls = query_cls.filter(ClassInfo.id.in_(class_ids))
    classes = query_cls.order_by(ClassInfo.class_num).all()
    target_class_ids = [c.id for c in classes]

    students = (
        Student.query.filter(
            Student.class_id.in_(target_class_ids), Student.status == "在读"
        )
        .order_by(Student.class_id, Student.student_id)
        .all()
    )

    score_map = {}
    if exam_name:
        tasks = ExamTask.query.filter(
            ExamTask.entry_year == entry_year,
            ExamTask.name == exam_name,
            ExamTask.subject_id.in_(subject_ids),
        ).all()
        task_ids = [t.id for t in tasks]
        task_subj_map = {t.id: t.subject.name for t in tasks}

        scores = Score.query.filter(
            Score.exam_task_id.in_(task_ids), Score.student_id.in_([s.id for s in students])
        ).all()

        for sc in scores:
            s_name = task_subj_map.get(sc.exam_task_id)
            val = "缺考" if sc.remark == "缺考" else sc.score
            score_map[(sc.student_id, s_name)] = val

    data_list = []
    for s in students:
        c = s.current_class_rel
        class_name_str = f"{str(c.entry_year)[-2:]}级({str(c.class_num).zfill(2)})班"

        row = {"学号": s.student_id, "姓名": s.name, "班级名称": class_name_str}
        for sub_name in subject_names:
            row[sub_name] = score_map.get((s.id, sub_name), "") if exam_name else ""
        data_list.append(row)

    df = pd.DataFrame(data_list)
    cols = ["学号", "姓名", "班级名称"] + subject_names
    df = df.reindex(columns=cols)

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        sheet_name = "成绩备份" if exam_name else "录入模版"
        df.to_excel(writer, index=False, sheet_name=sheet_name)
    output.seek(0)

    return output, f"{entry_year}级_{exam_name or '导入模版'}_成绩数据.xlsx"


def process_admin_scores_import(file, entry_year, exam_name, subject_ids, class_ids):
    if not entry_year or not exam_name or not subject_ids:
        return {"msg": "必要参数缺失(年级/考试/科目)"}, 400

    logs = {"fatal_errors": [], "warnings": [], "missing_students": []}

    try:
        df = pd.read_excel(file).fillna("")
    except Exception as e:
        return {"msg": f"Excel读取失败: {str(e)}"}, 400

    selected_subjects = Subject.query.filter(Subject.id.in_(subject_ids)).all()
    subject_map = {s.name: s.id for s in selected_subjects}
    selected_subject_names = set(subject_map.keys())

    tasks = ExamTask.query.filter(
        ExamTask.entry_year == entry_year,
        ExamTask.name == exam_name,
        ExamTask.subject_id.in_(subject_ids),
    ).all()

    existing_sub_ids = set(t.subject_id for t in tasks)
    missing_tasks = []
    task_map = {}

    for s in selected_subjects:
        if s.id not in existing_sub_ids:
            missing_tasks.append(s.name)
        else:
            t = next(x for x in tasks if x.subject_id == s.id)
            task_map[s.name] = t

    if missing_tasks:
        return {
            "msg": f"无法导入：科目 {missing_tasks} 尚未发布【{exam_name}】考试任务，请先去发布。"
        }, 400

    excel_cols = set(df.columns)
    base_cols = {"学号", "姓名", "班级名称"}
    if not base_cols.issubset(excel_cols):
        missing = base_cols - excel_cols
        return {"msg": f"Excel缺少基础列: {missing}"}, 400

    valid_subject_cols = []
    missing_subjects = selected_subject_names - excel_cols
    if missing_subjects:
        return {
            "msg": f"Excel文件缺失以下选中科目的数据列：{', '.join(missing_subjects)}。请检查是否使用了错误的模版。"
        }, 400

    for col in df.columns:
        if col in selected_subject_names:
            valid_subject_cols.append(col)
        elif col not in base_cols:
            logs["warnings"].append(f"检测到未选中的列【{col}】，已自动忽略。")

    if not valid_subject_cols:
        return {"msg": "Excel中没有找到任何与当前选中科目匹配的列"}, 400

    cls_query = ClassInfo.query.filter_by(entry_year=entry_year)
    if class_ids:
        cls_query = cls_query.filter(ClassInfo.id.in_(class_ids))
    target_classes = cls_query.all()
    target_class_ids = [c.id for c in target_classes]

    class_name_map = {}
    for c in target_classes:
        name = f"{str(c.entry_year)[-2:]}级({str(c.class_num).zfill(2)})班"
        class_name_map[name] = c.id

    db_students = Student.query.filter(
        Student.class_id.in_(target_class_ids), Student.status == "在读"
    ).all()

    student_map = {s.student_id: s for s in db_students}
    processed_ids = set()
    pending_score_map = {}

    for index, row in df.iterrows():
        row_num = index + 2
        sid = str(row["学号"]).strip()
        name = str(row["姓名"]).strip()
        cname = str(row["班级名称"]).strip()

        if not sid:
            continue

        if cname not in class_name_map:
            logs["warnings"].append(f"行{row_num}: 班级【{cname}】不在本次导入范围内，已忽略。")
            continue

        target_cid = class_name_map[cname]

        if sid not in student_map:
            logs["fatal_errors"].append(
                f"行{row_num}: 学号【{sid}】在系统中不存在 (或非在读/非选中班级)。"
            )
            continue

        stu_obj = student_map[sid]
        if stu_obj.name != name:
            logs["fatal_errors"].append(
                f"行{row_num}: 学号【{sid}】对应的姓名应为【{stu_obj.name}】，Excel中为【{name}】。"
            )
            continue

        if stu_obj.class_id != target_cid:
            logs["fatal_errors"].append(
                f"行{row_num}: 学生【{name}】系统归属班级ID不匹配，请检查班级名称。"
            )
            continue

        processed_ids.add(sid)

        for sub_name in valid_subject_cols:
            raw_val = row.get(sub_name)
            task = task_map[sub_name]

            if pd.isna(raw_val) or str(raw_val).strip() == "":
                logs["fatal_errors"].append(f"行{row_num}: 学生【{name}】缺失【{sub_name}】科目的成绩。")
                continue

            val_str = str(raw_val).strip()
            score_val = 0.0
            remark_val = ""

            if val_str == "缺考":
                score_val = 0.0
                remark_val = "缺考"
            else:
                try:
                    score_val = float(val_str)
                    if score_val < 0 or score_val > task.full_score:
                        logs["fatal_errors"].append(
                            f"行{row_num}: {sub_name}分数【{score_val}】超出满分【{task.full_score}】。"
                        )
                except Exception:
                    logs["fatal_errors"].append(
                        f"行{row_num}: {sub_name}分数【{val_str}】格式错误。"
                    )

            pending_score_map[(stu_obj.id, task.id)] = {
                "student_id": stu_obj.id,
                "exam_task_id": task.id,
                "subject_id": task.subject_id,
                "score": score_val,
                "remark": remark_val,
                "term": task.name,
                "class_id_snapshot": stu_obj.class_id,
            }

    if logs["fatal_errors"]:
        return {
            "status": "error",
            "msg": f"校验未通过，发现 {len(logs['fatal_errors'])} 个致命错误，数据未写入。",
            "logs": logs,
        }, 200

    all_target_ids = set(student_map.keys())
    missing = all_target_ids - processed_ids
    if missing:
        names = [student_map[m].name for m in list(missing)[:5]]
        msg = f"共 {len(missing)} 名选中班级的学生未在Excel中找到 ({','.join(names)}...)"
        logs["missing_students"].append(msg)

    try:
        updated_count = 0
        added_count = 0
        before_scores = {}
        created_score_keys = set()

        relevant_task_ids = [task_map[n].id for n in valid_subject_cols]
        relevant_stu_ids = list({p["student_id"] for p in pending_score_map.values()})

        existing_scores = Score.query.filter(
            Score.exam_task_id.in_(relevant_task_ids),
            Score.student_id.in_(relevant_stu_ids),
        ).all()

        existing_map = {(es.student_id, es.exam_task_id): es for es in existing_scores}

        for item in pending_score_map.values():
            key = (item["student_id"], item["exam_task_id"])
            if key in existing_map:
                sc = existing_map[key]
                old_score = float(sc.score) if sc.score is not None else 0.0
                new_score = float(item["score"]) if item["score"] is not None else 0.0
                old_remark = (sc.remark or "").strip()
                new_remark = (item["remark"] or "").strip()

                score_changed = abs(old_score - new_score) > 1e-6
                remark_changed = old_remark != new_remark

                if score_changed or remark_changed:
                    if key not in before_scores:
                        before_scores[key] = _serialize_score(sc)
                    sc.score = new_score
                    sc.remark = new_remark
                    updated_count += 1
            else:
                new_sc = Score(
                    student_id=item["student_id"],
                    subject_id=item["subject_id"],
                    exam_task_id=item["exam_task_id"],
                    score=float(item["score"]) if item["score"] is not None else 0.0,
                    remark=(item["remark"] or "").strip(),
                    term=item["term"],
                    class_id_snapshot=item.get("class_id_snapshot"),
                )
                db.session.add(new_sc)
                created_score_keys.add(key)
                added_count += 1

        _create_import_batch(
            import_type="score",
            source_filename=file.filename,
            scope={
                "entry_year": entry_year,
                "exam_name": exam_name,
                "subject_ids": subject_ids,
                "class_ids": class_ids,
            },
            summary={
                "added": added_count,
                "updated": updated_count,
                "warning_count": len(logs["warnings"]),
                "missing_student_count": len(missing),
            },
            snapshot={
                "before_scores": list(before_scores.values()),
                "created_scores": [
                    {"student_id": sid, "exam_task_id": tid}
                    for sid, tid in created_score_keys
                ],
            },
        )
        db.session.commit()

        return {
            "status": "success",
            "msg": f"导入成功！新增 {added_count} 条，更新 {updated_count} 条成绩。",
            "logs": logs,
        }, 200

    except Exception as e:
        db.session.rollback()
        return {"msg": f"数据库写入异常: {str(e)}"}, 500
