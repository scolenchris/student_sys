from app.models import (
    ClassInfo,
    CourseAssignment,
    GradeLeaderAssignment,
    HeadTeacherAssignment,
    PrepGroupLeaderAssignment,
    Score,
    Student,
    SubjectGroupLeaderAssignment,
    Teacher,
    User,
    db,
)


def rollback_students(snapshot):
    before_students = snapshot.get("before_students", [])
    created_student_ids = snapshot.get("created_student_ids", [])
    created_class_ids = snapshot.get("created_class_ids", [])

    before_sid_set = {
        item.get("student_id") for item in before_students if item.get("student_id")
    }

    for sid in created_student_ids:
        if sid in before_sid_set:
            continue
        stu = Student.query.filter_by(student_id=sid).first()
        if not stu:
            continue
        if Score.query.filter_by(student_id=stu.id).first():
            raise ValueError(f"学生 {sid} 已产生后续成绩数据，无法自动删除，请先清理相关成绩。")
        db.session.delete(stu)

    for data in before_students:
        sid = data.get("student_id")
        if not sid:
            continue

        stu = Student.query.filter_by(student_id=sid).first()
        if not stu:
            stu = Student(student_id=sid)
            db.session.add(stu)

        stu.name = data.get("name", "")
        stu.gender = data.get("gender", "男")
        stu.class_id = data.get("class_id")
        stu.status = data.get("status", "在读")
        stu.household_registration = data.get("household_registration")
        stu.city_school_id = data.get("city_school_id")
        stu.national_school_id = data.get("national_school_id")
        stu.id_card_number = data.get("id_card_number")
        stu.remarks = data.get("remarks")

    for item in created_class_ids:
        class_id = item.get("id")
        if not class_id:
            continue
        cls = ClassInfo.query.get(class_id)
        if not cls:
            continue
        if cls.students.count() > 0:
            continue
        if HeadTeacherAssignment.query.filter_by(class_id=cls.id).first():
            continue
        if CourseAssignment.query.filter_by(class_id=cls.id).first():
            continue
        db.session.delete(cls)


def rollback_teacher(snapshot, scope):
    academic_year = scope.get("academic_year")
    if not academic_year:
        raise ValueError("教师导入记录缺少学年信息，无法回退。")

    before_assignments = snapshot.get("before_assignments", {})
    before_users = snapshot.get("before_users", [])
    before_teachers = snapshot.get("before_teachers", [])
    created_usernames = snapshot.get("created_usernames", [])
    created_teacher_user_ids = snapshot.get("created_teacher_user_ids", [])

    db.session.query(GradeLeaderAssignment).filter_by(academic_year=academic_year).delete()
    db.session.query(SubjectGroupLeaderAssignment).filter_by(
        academic_year=academic_year
    ).delete()
    db.session.query(PrepGroupLeaderAssignment).filter_by(academic_year=academic_year).delete()

    for item in before_assignments.get("grade", []):
        db.session.add(
            GradeLeaderAssignment(
                teacher_id=item["teacher_id"],
                entry_year=item["entry_year"],
                academic_year=item["academic_year"],
            )
        )
    for item in before_assignments.get("subject", []):
        db.session.add(
            SubjectGroupLeaderAssignment(
                teacher_id=item["teacher_id"],
                subject_id=item["subject_id"],
                academic_year=item["academic_year"],
            )
        )
    for item in before_assignments.get("prep", []):
        db.session.add(
            PrepGroupLeaderAssignment(
                teacher_id=item["teacher_id"],
                entry_year=item["entry_year"],
                subject_id=item["subject_id"],
                academic_year=item["academic_year"],
            )
        )

    before_usernames = set()
    for item in before_users:
        username = item.get("username")
        if not username:
            continue
        before_usernames.add(username)
        user = User.query.filter_by(username=username).first()
        if not user:
            user = User(username=username)
            db.session.add(user)
        user.real_name = item.get("real_name")
        user.role = item.get("role", "teacher")
        user.is_approved = bool(item.get("is_approved", False))
        user.must_change_password = bool(item.get("must_change_password", False))
        user.password_hash = item.get("password_hash")

    before_teacher_user_ids = set()
    for item in before_teachers:
        user_id = item.get("user_id")
        if not user_id:
            continue
        before_teacher_user_ids.add(user_id)
        teacher = Teacher.query.filter_by(user_id=user_id).first()
        if not teacher:
            teacher = Teacher(user_id=user_id, name=item.get("name", ""))
            db.session.add(teacher)
        teacher.name = item.get("name", "")
        teacher.gender = item.get("gender", "男")
        teacher.ethnicity = item.get("ethnicity", "汉族")
        teacher.phone = item.get("phone")
        teacher.status = item.get("status", "在职")
        teacher.job_title = item.get("job_title")
        teacher.education = item.get("education")
        teacher.major = item.get("major")
        teacher.remarks = item.get("remarks")

    for user_id in created_teacher_user_ids:
        if user_id in before_teacher_user_ids:
            continue
        teacher = Teacher.query.filter_by(user_id=user_id).first()
        if not teacher:
            continue
        if HeadTeacherAssignment.query.filter_by(teacher_id=teacher.id).first():
            raise ValueError(f"教师 {teacher.name} 已有后续班主任分配，无法自动删除。")
        if CourseAssignment.query.filter_by(teacher_id=teacher.id).first():
            raise ValueError(f"教师 {teacher.name} 已有后续任课分配，无法自动删除。")
        if GradeLeaderAssignment.query.filter_by(teacher_id=teacher.id).first():
            raise ValueError(f"教师 {teacher.name} 已有后续级长分配，无法自动删除。")
        if SubjectGroupLeaderAssignment.query.filter_by(teacher_id=teacher.id).first():
            raise ValueError(f"教师 {teacher.name} 已有后续科组长分配，无法自动删除。")
        if PrepGroupLeaderAssignment.query.filter_by(teacher_id=teacher.id).first():
            raise ValueError(f"教师 {teacher.name} 已有后续备课组分配，无法自动删除。")
        db.session.delete(teacher)

    for username in created_usernames:
        if username in before_usernames:
            continue
        user = User.query.filter_by(username=username).first()
        if not user:
            continue
        if user.teacher_profile:
            raise ValueError(f"账号 {username} 已关联教师档案，无法自动删除。")
        db.session.delete(user)


def rollback_course_assign(snapshot, scope):
    academic_year = scope.get("academic_year")
    if not academic_year:
        raise ValueError("任课导入记录缺少学年信息，无法回退。")

    db.session.query(CourseAssignment).filter_by(academic_year=academic_year).delete()
    db.session.query(HeadTeacherAssignment).filter_by(academic_year=academic_year).delete()

    for item in snapshot.get("before_course_assignments", []):
        db.session.add(
            CourseAssignment(
                teacher_id=item["teacher_id"],
                class_id=item["class_id"],
                subject_id=item["subject_id"],
                academic_year=item["academic_year"],
            )
        )
    for item in snapshot.get("before_head_teacher_assignments", []):
        db.session.add(
            HeadTeacherAssignment(
                teacher_id=item["teacher_id"],
                class_id=item["class_id"],
                academic_year=item["academic_year"],
            )
        )


def rollback_score(snapshot):
    before_scores = snapshot.get("before_scores", [])
    created_scores = snapshot.get("created_scores", [])

    for key in created_scores:
        sid = key.get("student_id")
        tid = key.get("exam_task_id")
        if sid is None or tid is None:
            continue
        rows = Score.query.filter_by(student_id=sid, exam_task_id=tid).all()
        for row in rows:
            db.session.delete(row)

    for item in before_scores:
        sid = item.get("student_id")
        tid = item.get("exam_task_id")
        if sid is None or tid is None:
            continue
        row = Score.query.filter_by(student_id=sid, exam_task_id=tid).first()
        if not row:
            row = Score(student_id=sid, exam_task_id=tid)
            db.session.add(row)

        row.subject_id = item.get("subject_id")
        row.score = item.get("score", 0.0)
        row.remark = item.get("remark", "")
        row.term = item.get("term")
        row.class_id_snapshot = item.get("class_id_snapshot")

