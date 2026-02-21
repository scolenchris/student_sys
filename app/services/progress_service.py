from sqlalchemy import distinct, func

from app.models import ClassInfo, CourseAssignment, Score, Student, db


def build_class_name(entry_year, class_num):
    return f"{entry_year}级({class_num})班"


def get_active_student_ids(class_id):
    rows = (
        db.session.query(Student.id)
        .filter(Student.class_id == class_id, Student.status == "在读")
        .all()
    )
    return [row.id for row in rows]


def calc_class_record_progress(exam_task_id, class_id):
    student_ids = get_active_student_ids(class_id)
    total_students = len(student_ids)

    if total_students == 0:
        return {
            "total_students": 0,
            "recorded_count": 0,
            "pending_count": 0,
            "is_completed": True,
            "student_ids": student_ids,
        }

    recorded_count = (
        db.session.query(func.count(distinct(Score.student_id)))
        .filter(Score.exam_task_id == exam_task_id, Score.student_id.in_(student_ids))
        .scalar()
        or 0
    )

    if recorded_count > total_students:
        recorded_count = total_students

    pending_count = total_students - recorded_count
    return {
        "total_students": total_students,
        "recorded_count": recorded_count,
        "pending_count": pending_count,
        "is_completed": recorded_count >= total_students,
        "student_ids": student_ids,
    }


def calc_exam_task_progress(task):
    class_rows = (
        db.session.query(ClassInfo.id, ClassInfo.entry_year, ClassInfo.class_num)
        .join(CourseAssignment, CourseAssignment.class_id == ClassInfo.id)
        .filter(
            CourseAssignment.subject_id == task.subject_id,
            CourseAssignment.academic_year == task.academic_year,
            ClassInfo.entry_year == task.entry_year,
        )
        .distinct()
        .all()
    )

    total_classes = len(class_rows)
    completed_classes = 0
    class_details = []

    for row in class_rows:
        class_progress = calc_class_record_progress(task.id, row.id)
        class_name = build_class_name(row.entry_year, row.class_num)

        if class_progress["is_completed"]:
            completed_classes += 1

        class_details.append(
            {
                "class_id": row.id,
                "class_name": class_name,
                "recorded_count": class_progress["recorded_count"],
                "total_students": class_progress["total_students"],
                "is_completed": class_progress["is_completed"],
            }
        )

    completion_rate = 0.0
    if total_classes > 0:
        completion_rate = round(completed_classes * 100.0 / total_classes, 1)

    return {
        "assigned_class_count": total_classes,
        "completed_class_count": completed_classes,
        "pending_class_count": max(total_classes - completed_classes, 0),
        "completion_rate": completion_rate,
        "progress_text": f"{completed_classes}/{total_classes}",
        "is_fully_completed": total_classes > 0 and completed_classes == total_classes,
        "class_details": class_details,
    }
