from sqlalchemy import func

from app.models import (
    ClassInfo,
    CourseAssignment,
    ExamTask,
    Score,
    Student,
    Subject,
    db,
)

SUBJECT_PRIORITY = [
    "语文",
    "数学",
    "英语",
    "英语听说",
    "物理",
    "化学",
    "道德与法治",
    "历史",
    "生物",
    "地理",
    "体育与健康",
    "信息科技",
    "美术",
    "音乐",
]


def _to_bool(value):
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y", "on"}
    return False


def _resolve_pagination(data):
    paged = _to_bool(data.get("paged", False))
    page = data.get("page", 1)
    page_size = data.get("page_size", 20)

    try:
        page = int(page)
    except (TypeError, ValueError):
        page = 1
    try:
        page_size = int(page_size)
    except (TypeError, ValueError):
        page_size = 20

    page = max(page, 1)
    page_size = min(max(page_size, 1), 100)
    return paged, page, page_size


def build_class_report(class_id, term):
    if not class_id or not term:
        return {"subjects": [], "report": [], "subject_averages": {}}

    subjects = Subject.query.all()
    subject_map = {s.id: s.name for s in subjects}
    students = Student.query.filter_by(class_id=class_id).all()

    report_data = []
    subject_stats = {s.name: {"sum": 0, "count": 0} for s in subjects}

    for stu in students:
        scores = Score.query.filter_by(student_id=stu.id, term=term).all()
        score_detail = {}
        student_total = 0

        for score in scores:
            sub_name = subject_map.get(score.subject_id)
            if not sub_name:
                continue
            if score.remark == "缺考":
                score_detail[sub_name] = "缺考"
                student_total += 0
            else:
                score_detail[sub_name] = score.score
                student_total += score.score

            subject_stats[sub_name]["sum"] += score.score
            subject_stats[sub_name]["count"] += 1

        report_data.append(
            {
                "student_id": stu.student_id,
                "name": stu.name,
                "scores": score_detail,
                "total": round(student_total, 1),
            }
        )

    class_subject_averages = {}
    for sub_name, stats in subject_stats.items():
        if stats["count"] > 0:
            class_subject_averages[sub_name] = round(stats["sum"] / stats["count"], 1)
        else:
            class_subject_averages[sub_name] = "-"

    report_data.sort(key=lambda x: x["total"], reverse=True)
    for index, item in enumerate(report_data):
        item["rank"] = index + 1

    return {
        "subjects": [s.name for s in subjects],
        "report": report_data,
        "subject_averages": class_subject_averages,
    }


def get_exam_names_by_entry_year(entry_year):
    if not entry_year:
        return []

    names = (
        db.session.query(ExamTask.name)
        .filter_by(entry_year=entry_year)
        .group_by(ExamTask.name)
        .order_by(func.min(ExamTask.id).asc())
        .all()
    )
    return [n[0] for n in names]


def build_comprehensive_report(data):
    entry_year = data.get("entry_year")
    exam_name = data.get("exam_name")
    subject_ids = data.get("subject_ids", [])
    class_ids = data.get("class_ids", [])
    keyword = str(data.get("keyword", "")).strip()

    if not entry_year or not exam_name or not subject_ids:
        return None, ("请选择完整的筛选条件（年级、考试、科目）", 400)
    paged, page, page_size = _resolve_pagination(data)

    all_classes = ClassInfo.query.filter_by(entry_year=entry_year).all()
    class_map = {c.id: c.full_name for c in all_classes}
    all_grade_class_ids = [c.id for c in all_classes]

    tasks = ExamTask.query.filter(
        ExamTask.entry_year == entry_year,
        ExamTask.name == exam_name,
        ExamTask.subject_id.in_(subject_ids),
    ).all()

    if not tasks:
        if paged:
            return {
                "items": [],
                "data": [],
                "total": 0,
                "page": page,
                "page_size": page_size,
                "subjects": [],
            }, None
        return {"data": [], "subjects": []}, None

    task_map = {t.id: t.subject_id for t in tasks}
    task_ids = [t.id for t in tasks]
    total_full_score = sum([t.full_score for t in tasks])

    students = Student.query.filter(Student.class_id.in_(all_grade_class_ids)).all()
    student_map = {s.id: s for s in students}

    scores = Score.query.filter(
        Score.exam_task_id.in_(task_ids), Score.student_id.in_(student_map.keys())
    ).all()

    stats_data = {}

    subjects = (
        Subject.query.filter(Subject.id.in_(subject_ids))
        .order_by(Subject.id.asc())
        .all()
    )

    subject_name_map = {s.id: s.name for s in subjects}
    ordered_subject_names = [s.name for s in subjects]

    for stu in students:
        stats_data[stu.id] = {"obj": stu, "score_map": {}, "total": 0}

    for sc in scores:
        sid = sc.student_id
        if sid in stats_data:
            subj_id = task_map.get(sc.exam_task_id)
            subj_name = subject_name_map.get(subj_id)
            if subj_name:
                if sc.remark == "缺考":
                    stats_data[sid]["score_map"][subj_name] = "缺考"
                    stats_data[sid]["total"] += 0
                else:
                    stats_data[sid]["score_map"][subj_name] = sc.score
                    stats_data[sid]["total"] += sc.score

    result_list = list(stats_data.values())

    def sort_key(item):
        sm = item["score_map"]
        compare_tuple = [item["total"]]
        for sub in SUBJECT_PRIORITY:
            val = sm.get(sub, 0)
            if val == "缺考":
                val = 0
            compare_tuple.append(val)
        return tuple(compare_tuple)

    result_list.sort(key=sort_key, reverse=True)

    for i, item in enumerate(result_list):
        item["grade_rank_dense"] = i + 1
        if i > 0 and item["total"] < result_list[i - 1]["total"]:
            item["grade_rank_skip"] = i + 1
        elif i == 0:
            item["grade_rank_skip"] = 1
        else:
            item["grade_rank_skip"] = result_list[i - 1]["grade_rank_skip"]

    class_groups = {}
    for item in result_list:
        cid = item["obj"].class_id
        if cid not in class_groups:
            class_groups[cid] = []
        class_groups[cid].append(item)

    for _, items in class_groups.items():
        items.sort(key=sort_key, reverse=True)
        for i, sub_item in enumerate(items):
            sub_item["class_rank_dense"] = i + 1
            if i > 0 and sub_item["total"] < items[i - 1]["total"]:
                sub_item["class_rank_skip"] = i + 1
            elif i == 0:
                sub_item["class_rank_skip"] = 1
            else:
                sub_item["class_rank_skip"] = items[i - 1]["class_rank_skip"]

    target_class_ids = set(class_ids) if class_ids else set(all_grade_class_ids)
    final_output = []

    for item in result_list:
        stu = item["obj"]
        if stu.class_id in target_class_ids:
            final_output.append(
                {
                    "student_id": stu.student_id,
                    "name": stu.name,
                    "class_name": class_map.get(stu.class_id, "未知班级"),
                    "status": stu.status,
                    "full_score": total_full_score,
                    "total": round(item["total"], 1),
                    "grade_rank_skip": item["grade_rank_skip"],
                    "grade_rank_dense": item["grade_rank_dense"],
                    "class_rank_skip": item.get("class_rank_skip", "-"),
                    "class_rank_dense": item.get("class_rank_dense", "-"),
                    "scores": item["score_map"],
                }
            )

    if keyword:
        final_output = [
            item
            for item in final_output
            if keyword in str(item.get("name", ""))
            or keyword in str(item.get("student_id", ""))
        ]

    if paged:
        total = len(final_output)
        start = (page - 1) * page_size
        end = start + page_size
        page_items = final_output[start:end]
        return {
            "items": page_items,
            "data": page_items,
            "total": total,
            "page": page,
            "page_size": page_size,
            "subjects": ordered_subject_names,
        }, None

    return {"data": final_output, "subjects": ordered_subject_names}, None


def build_score_rank_trend_payload(data):
    entry_year = data.get("entry_year")
    exam_names_raw = data.get("exam_names", [])
    subject_ids_raw = data.get("subject_ids", [])
    class_ids_raw = data.get("class_ids", [])
    paged, page, page_size = _resolve_pagination(data)
    only_changed = _to_bool(data.get("only_changed", False))
    keyword = str(data.get("keyword", "")).strip()

    try:
        entry_year = int(entry_year)
    except (TypeError, ValueError):
        return None, ("请选择有效的年级", 400)

    exam_names = []
    seen_exam_names = set()
    for name in exam_names_raw if isinstance(exam_names_raw, list) else []:
        exam_name = str(name).strip()
        if not exam_name or exam_name in seen_exam_names:
            continue
        seen_exam_names.add(exam_name)
        exam_names.append(exam_name)

    subject_ids = []
    seen_subject_ids = set()
    for sid in subject_ids_raw if isinstance(subject_ids_raw, list) else []:
        try:
            sid_int = int(sid)
        except (TypeError, ValueError):
            continue
        if sid_int in seen_subject_ids:
            continue
        seen_subject_ids.add(sid_int)
        subject_ids.append(sid_int)

    class_ids = []
    seen_class_ids = set()
    for cid in class_ids_raw if isinstance(class_ids_raw, list) else []:
        try:
            cid_int = int(cid)
        except (TypeError, ValueError):
            continue
        if cid_int in seen_class_ids:
            continue
        seen_class_ids.add(cid_int)
        class_ids.append(cid_int)

    if not exam_names:
        return None, ("请至少选择一次考试", 400)
    if not subject_ids:
        return None, ("请至少选择一个科目", 400)

    grade_classes = (
        ClassInfo.query.filter_by(entry_year=entry_year)
        .order_by(ClassInfo.class_num.asc())
        .all()
    )
    if not grade_classes:
        payload = {"subjects": [], "exams": [], "rows": [], "warnings": []}
        if paged:
            payload.update({"total": 0, "page": page, "page_size": page_size})
        return payload, None

    all_grade_class_ids = [c.id for c in grade_classes]
    class_name_map = {c.id: c.full_name for c in grade_classes}
    class_num_map = {c.id: c.class_num for c in grade_classes}

    if class_ids:
        target_class_ids = set([cid for cid in class_ids if cid in all_grade_class_ids])
    else:
        target_class_ids = set(all_grade_class_ids)

    if not target_class_ids:
        payload = {
            "subjects": [],
            "exams": [],
            "rows": [],
            "warnings": ["筛选班级不属于当前年级，未返回数据。"],
        }
        if paged:
            payload.update({"total": 0, "page": page, "page_size": page_size})
        return payload, None

    students = (
        Student.query.filter(
            Student.class_id.in_(all_grade_class_ids), Student.status == "在读"
        )
        .order_by(Student.student_id.asc())
        .all()
    )
    if not students:
        payload = {"subjects": [], "exams": [], "rows": [], "warnings": []}
        if paged:
            payload.update({"total": 0, "page": page, "page_size": page_size})
        return payload, None

    student_ids = [s.id for s in students]

    subjects = Subject.query.filter(Subject.id.in_(subject_ids)).all()
    subject_obj_map = {s.id: s for s in subjects}
    ordered_subject_ids = [sid for sid in subject_ids if sid in subject_obj_map]
    ordered_subject_names = [subject_obj_map[sid].name for sid in ordered_subject_ids]
    subject_name_by_id = {sid: subject_obj_map[sid].name for sid in ordered_subject_ids}

    if not ordered_subject_ids:
        payload = {"subjects": [], "exams": [], "rows": [], "warnings": []}
        if paged:
            payload.update({"total": 0, "page": page, "page_size": page_size})
        return payload, None

    tie_break_subjects = [n for n in SUBJECT_PRIORITY if n in ordered_subject_names]
    tie_break_subjects.extend(
        [n for n in ordered_subject_names if n not in tie_break_subjects]
    )

    raw_tasks = ExamTask.query.filter(
        ExamTask.entry_year == entry_year,
        ExamTask.name.in_(exam_names),
        ExamTask.subject_id.in_(ordered_subject_ids),
    ).all()

    task_by_exam_subject = {}
    for task in raw_tasks:
        key = (task.name, task.subject_id)
        prev = task_by_exam_subject.get(key)
        if not prev or task.id > prev.id:
            task_by_exam_subject[key] = task

    exams = []
    task_info_by_id = {}
    warnings = []

    for exam_name in exam_names:
        task_map = {}
        for sid in ordered_subject_ids:
            task = task_by_exam_subject.get((exam_name, sid))
            if task:
                task_map[sid] = task
                task_info_by_id[task.id] = (exam_name, sid)

        if not task_map:
            warnings.append(
                f"【{exam_name}】未找到选中科目的考试任务，已从比较中忽略。"
            )
            continue

        missing_subjects = [
            subject_name_by_id[sid] for sid in ordered_subject_ids if sid not in task_map
        ]
        if missing_subjects:
            warnings.append(
                f"【{exam_name}】缺少科目任务：{'、'.join(missing_subjects)}，该部分按0分处理。"
            )

        full_score = sum(t.full_score for t in task_map.values())
        exams.append(
            {
                "name": exam_name,
                "full_score": round(full_score, 1),
                "missing_subjects": missing_subjects,
            }
        )

    if not exams:
        payload = {
            "subjects": ordered_subject_names,
            "exams": [],
            "rows": [],
            "warnings": warnings,
        }
        if paged:
            payload.update({"total": 0, "page": page, "page_size": page_size})
        return payload, None

    all_task_ids = list(task_info_by_id.keys())
    score_map = {}
    class_snapshot_map = {}

    if all_task_ids:
        score_rows = Score.query.filter(
            Score.exam_task_id.in_(all_task_ids), Score.student_id.in_(student_ids)
        ).all()

        for sc in score_rows:
            task_info = task_info_by_id.get(sc.exam_task_id)
            if not task_info:
                continue
            exam_name, subject_id = task_info
            skey = (sc.student_id, exam_name, subject_id)
            prev = score_map.get(skey)
            if not prev or sc.id > prev.id:
                score_map[skey] = sc

            if sc.class_id_snapshot:
                ckey = (sc.student_id, exam_name)
                if ckey not in class_snapshot_map:
                    class_snapshot_map[ckey] = sc.class_id_snapshot

    exam_student_metrics = {}

    def build_sort_key(item):
        vals = [item["total_raw"]]
        for subject_name in tie_break_subjects:
            vals.append(item["score_numeric"].get(subject_name, 0.0))
        vals.append(-item["student"].id)
        return tuple(vals)

    for exam in exams:
        exam_name = exam["name"]
        per_exam = {}

        for stu in students:
            score_display = {}
            score_numeric = {}
            total_raw = 0.0

            for sid in ordered_subject_ids:
                subject_name = subject_name_by_id[sid]
                sc = score_map.get((stu.id, exam_name, sid))

                if sc:
                    if (sc.remark or "").strip() == "缺考":
                        display_val = "缺考"
                        numeric_val = 0.0
                    else:
                        numeric_val = float(sc.score) if sc.score is not None else 0.0
                        display_val = round(numeric_val, 1)
                else:
                    display_val = "-"
                    numeric_val = 0.0

                score_display[subject_name] = display_val
                score_numeric[subject_name] = numeric_val
                total_raw += numeric_val

            rank_class_id = class_snapshot_map.get((stu.id, exam_name)) or stu.class_id

            per_exam[stu.id] = {
                "student": stu,
                "rank_class_id": rank_class_id,
                "score_display": score_display,
                "score_numeric": score_numeric,
                "total_raw": total_raw,
                "total": round(total_raw, 1),
                "grade_rank": None,
                "class_rank": None,
            }

        grade_sorted = sorted(per_exam.values(), key=build_sort_key, reverse=True)
        for i, item in enumerate(grade_sorted):
            item["grade_rank"] = i + 1

        class_groups = {}
        for item in per_exam.values():
            cid = item["rank_class_id"]
            if cid not in class_groups:
                class_groups[cid] = []
            class_groups[cid].append(item)

        for _, group_items in class_groups.items():
            group_items.sort(key=build_sort_key, reverse=True)
            for i, item in enumerate(group_items):
                item["class_rank"] = i + 1

        exam_student_metrics[exam_name] = per_exam

    target_students = [s for s in students if s.class_id in target_class_ids]
    target_students.sort(
        key=lambda s: (class_num_map.get(s.class_id, 999), str(s.student_id))
    )

    rows = []
    for stu in target_students:
        row_exam_data = {}
        row_has_change = False

        for idx, exam in enumerate(exams):
            exam_name = exam["name"]
            current = exam_student_metrics.get(exam_name, {}).get(stu.id)
            if not current:
                continue

            if idx > 0:
                prev_exam_name = exams[idx - 1]["name"]
                prev = exam_student_metrics.get(prev_exam_name, {}).get(stu.id)
            else:
                prev = None

            score_changes = {}
            for subject_name in ordered_subject_names:
                if not prev:
                    score_changes[subject_name] = None
                    continue

                curr_display = current["score_display"].get(subject_name, "-")
                prev_display = prev["score_display"].get(subject_name, "-")
                if curr_display == "-" and prev_display == "-":
                    score_changes[subject_name] = None
                else:
                    score_changes[subject_name] = round(
                        current["score_numeric"].get(subject_name, 0.0)
                        - prev["score_numeric"].get(subject_name, 0.0),
                        1,
                    )

            if not prev:
                total_change = None
                grade_rank_change = None
                class_rank_change = None
            else:
                total_change = round(current["total_raw"] - prev["total_raw"], 1)
                grade_rank_change = prev["grade_rank"] - current["grade_rank"]
                class_rank_change = prev["class_rank"] - current["class_rank"]

                if (
                    abs(total_change) > 1e-9
                    or grade_rank_change != 0
                    or class_rank_change != 0
                ):
                    row_has_change = True

                if not row_has_change:
                    for change_val in score_changes.values():
                        if change_val is not None and abs(change_val) > 1e-9:
                            row_has_change = True
                            break

            row_exam_data[exam_name] = {
                "scores": current["score_display"],
                "score_changes": score_changes,
                "total": current["total"],
                "total_change": total_change,
                "grade_rank": current["grade_rank"],
                "grade_rank_change": grade_rank_change,
                "class_rank": current["class_rank"],
                "class_rank_change": class_rank_change,
            }

        rows.append(
            {
                "student_id": stu.student_id,
                "name": stu.name,
                "class_name": class_name_map.get(stu.class_id, "未知班级"),
                "status": stu.status,
                "has_change": row_has_change,
                "exam_data": row_exam_data,
            }
        )

    if keyword:
        rows = [
            row
            for row in rows
            if keyword in str(row.get("name", ""))
            or keyword in str(row.get("student_id", ""))
        ]

    if only_changed:
        rows = [row for row in rows if row.get("has_change")]

    payload = {
        "subjects": ordered_subject_names,
        "exams": exams,
        "rows": rows,
        "warnings": warnings,
    }
    if paged:
        total = len(rows)
        start = (page - 1) * page_size
        end = start + page_size
        payload["rows"] = rows[start:end]
        payload["total"] = total
        payload["page"] = page
        payload["page_size"] = page_size

    return payload, None


def build_class_score_stats(data):
    entry_year = data.get("entry_year")
    exam_name = data.get("exam_name")
    subject_ids = data.get("subject_ids", [])

    th_exc = data.get("threshold_excellent", 85) / 100.0
    th_pass = data.get("threshold_pass", 60) / 100.0
    th_low = data.get("threshold_low", 30) / 100.0

    if not entry_year or not exam_name or not subject_ids:
        return None, ("请选择完整的筛选条件", 400)

    tasks = ExamTask.query.filter(
        ExamTask.entry_year == entry_year,
        ExamTask.name == exam_name,
        ExamTask.subject_id.in_(subject_ids),
    ).all()

    if not tasks:
        return [], None

    full_score_sum = sum(t.full_score for t in tasks)
    task_ids = [t.id for t in tasks]
    subject_names = sorted(list(set([t.subject.name for t in tasks])))
    subjects_display = "、".join(subject_names)

    classes = (
        ClassInfo.query.filter_by(entry_year=entry_year)
        .order_by(ClassInfo.class_num)
        .all()
    )
    class_ids = [c.id for c in classes]

    students = Student.query.filter(
        Student.class_id.in_(class_ids), Student.status == "在读"
    ).all()
    student_class_map = {s.id: s.class_id for s in students}

    scores = Score.query.filter(
        Score.exam_task_id.in_(task_ids), Score.student_id.in_([s.id for s in students])
    ).all()

    student_stats = {s.id: {"total": 0, "valid_subjects": 0} for s in students}
    for sc in scores:
        sid = sc.student_id
        if sid in student_stats:
            if sc.remark != "缺考":
                student_stats[sid]["total"] += sc.score
                student_stats[sid]["valid_subjects"] += 1

    grade_total_score = 0
    grade_exam_count = 0
    valid_student_data = []
    for sid, stat in student_stats.items():
        if stat["valid_subjects"] > 0:
            grade_total_score += stat["total"]
            grade_exam_count += 1
            valid_student_data.append(
                {"class_id": student_class_map[sid], "total": stat["total"]}
            )

    grade_avg = grade_total_score / grade_exam_count if grade_exam_count > 0 else 0

    result = []
    for cls in classes:
        cls_student_ids = [s.id for s in cls.students if s.status == "在读"]
        total_people = len(cls_student_ids)

        cls_valid_data = [d for d in valid_student_data if d["class_id"] == cls.id]
        cls_exam_scores = [d["total"] for d in cls_valid_data]
        exam_people = len(cls_exam_scores)

        cls_sum = sum(cls_exam_scores)
        cls_avg = cls_sum / exam_people if exam_people > 0 else 0
        cls_max = max(cls_exam_scores) if exam_people > 0 else 0
        cls_min = min(cls_exam_scores) if exam_people > 0 else 0

        cnt_exc = sum(1 for s in cls_exam_scores if s >= full_score_sum * th_exc)
        cnt_pass = sum(1 for s in cls_exam_scores if s >= full_score_sum * th_pass)
        cnt_low = sum(1 for s in cls_exam_scores if s <= full_score_sum * th_low)
        cnt_fail = sum(1 for s in cls_exam_scores if s < full_score_sum * th_pass)

        ratio = (cls_avg / grade_avg * 100) if grade_avg > 0 else 0

        def calc_rate(cnt, total):
            return round(cnt / total * 100, 1) if total > 0 else 0

        result.append(
            {
                "class_name": cls.full_name,
                "subjects": subjects_display,
                "full_score": full_score_sum,
                "total_people": total_people,
                "exam_people": exam_people,
                "excellent_count": cnt_exc,
                "excellent_rate": calc_rate(cnt_exc, exam_people),
                "pass_count": cnt_pass,
                "pass_rate": calc_rate(cnt_pass, exam_people),
                "fail_count": cnt_fail,
                "fail_rate": calc_rate(cnt_fail, exam_people),
                "low_count": cnt_low,
                "low_rate": calc_rate(cnt_low, exam_people),
                "max_score": cls_max,
                "min_score": cls_min,
                "sum_score": cls_sum,
                "avg_score": round(cls_avg, 1),
                "grade_ratio": round(ratio, 1),
            }
        )

    return result, None


def build_teacher_score_stats(data):
    entry_year = data.get("entry_year")
    academic_year = data.get("academic_year")
    exam_name = data.get("exam_name")
    keyword = str(data.get("keyword", "")).strip()

    th_exc_rate = data.get("threshold_excellent", 85) / 100.0
    th_pass_rate = data.get("threshold_pass", 60) / 100.0

    if not entry_year or not academic_year or not exam_name:
        return None, ("请选择完整的筛选条件", 400)

    all_subjects = Subject.query.order_by(Subject.id).all()
    final_result = []

    classes = ClassInfo.query.filter_by(entry_year=entry_year).all()
    class_map = {c.id: c for c in classes}
    if not classes:
        return [], None

    grade_class_ids = [c.id for c in classes]

    for sub in all_subjects:
        task = ExamTask.query.filter_by(
            entry_year=entry_year,
            academic_year=academic_year,
            subject_id=sub.id,
            name=exam_name,
        ).first()

        if not task:
            continue

        full_score = task.full_score
        assignments = (
            db.session.query(CourseAssignment)
            .join(ClassInfo)
            .filter(
                CourseAssignment.subject_id == sub.id,
                CourseAssignment.academic_year == academic_year,
                ClassInfo.entry_year == entry_year,
            )
            .all()
        )

        teacher_map = {}
        for assign in assignments:
            tid = assign.teacher_id
            if tid not in teacher_map:
                teacher_map[tid] = {
                    "teacher": assign.teacher,
                    "class_ids": [],
                    "class_names": [],
                }
            teacher_map[tid]["class_ids"].append(assign.class_id)
            c_obj = class_map.get(assign.class_id)
            if c_obj:
                teacher_map[tid]["class_names"].append(f"({c_obj.class_num})班")

        all_scores = Score.query.filter(Score.exam_task_id == task.id).all()
        students = Student.query.filter(
            Student.class_id.in_(grade_class_ids), Student.status == "在读"
        ).all()
        student_cls_map = {s.id: s.class_id for s in students}

        valid_scores_map = {}
        for sc in all_scores:
            if sc.student_id in student_cls_map and sc.remark != "缺考":
                valid_scores_map[sc.student_id] = sc.score

        grade_total_students = len(students)
        grade_exam_scores = []
        for sid in student_cls_map:
            if sid in valid_scores_map:
                grade_exam_scores.append(valid_scores_map[sid])

        grade_exam_count = len(grade_exam_scores)
        grade_sum = sum(grade_exam_scores)
        grade_avg = grade_sum / grade_exam_count if grade_exam_count > 0 else 0

        def calc_stats(score_list):
            count = len(score_list)
            if count == 0:
                return 0, 0, 0, 0, 0

            exc_cnt = sum(1 for s in score_list if s >= full_score * th_exc_rate)
            pass_cnt = sum(1 for s in score_list if s >= full_score * th_pass_rate)
            avg = sum(score_list) / count

            return (
                exc_cnt,
                round(exc_cnt / count * 100, 1),
                pass_cnt,
                round(pass_cnt / count * 100, 1),
                round(avg, 2),
            )

        teacher_rows = []
        for _, t_data in teacher_map.items():
            t_class_ids = set(t_data["class_ids"])
            t_stu_ids = [
                sid for sid, cid in student_cls_map.items() if cid in t_class_ids
            ]
            t_total_people = len(t_stu_ids)
            t_scores = [
                valid_scores_map[sid] for sid in t_stu_ids if sid in valid_scores_map
            ]
            t_exam_people = len(t_scores)

            exc_n, exc_r, pass_n, pass_r, t_avg = calc_stats(t_scores)
            t_data["class_names"].sort()
            full_class_names = [f"{entry_year}级{n}" for n in t_data["class_names"]]

            teacher_rows.append(
                {
                    "name": t_data["teacher"].name,
                    "academic_year": f"{academic_year}学年",
                    "subject": sub.name,
                    "exam_name": exam_name,
                    "full_score": full_score,
                    "classes": "，".join(full_class_names),
                    "total_people": t_total_people,
                    "exam_people": t_exam_people,
                    "excellent_count": exc_n,
                    "excellent_rate": exc_r,
                    "pass_count": pass_n,
                    "pass_rate": pass_r,
                    "avg_score": t_avg,
                    "grade_ratio": round(t_avg / grade_avg, 2) if grade_avg > 0 else 0,
                    "_sort_key": t_avg,
                }
            )

        teacher_rows.sort(key=lambda x: x["_sort_key"], reverse=True)
        for i, row in enumerate(teacher_rows):
            row["rank"] = i + 1
            row.pop("_sort_key", None)

        g_exc_n, g_exc_r, g_pass_n, g_pass_r, g_avg_res = calc_stats(grade_exam_scores)
        total_row = {
            "name": f"{entry_year}级{sub.name}总计",
            "academic_year": f"{academic_year}学年",
            "subject": sub.name,
            "exam_name": exam_name,
            "full_score": full_score,
            "classes": "全年级",
            "total_people": grade_total_students,
            "exam_people": grade_exam_count,
            "excellent_count": g_exc_n,
            "excellent_rate": g_exc_r,
            "pass_count": g_pass_n,
            "pass_rate": g_pass_r,
            "avg_score": round(g_avg_res, 2),
            "grade_ratio": 1.0,
            "rank": "-",
        }

        final_result.extend(teacher_rows)
        if teacher_rows or grade_exam_count > 0:
            final_result.append(total_row)

    if keyword:
        final_result = [
            row for row in final_result if keyword in str(row.get("name", ""))
        ]

    return final_result, None
