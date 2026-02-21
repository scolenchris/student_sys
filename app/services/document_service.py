import io
import os
import sys
from datetime import datetime

from docxtpl import DocxTemplate


def _resolve_template_path(template_name):
    if getattr(sys, "frozen", False):
        root_dir = os.path.dirname(sys.executable)
    else:
        root_dir = os.path.abspath(
            os.path.join(os.path.abspath(os.path.dirname(__file__)), "..", "..")
        )
    return os.path.join(root_dir, template_name)


def render_student_certificate(student):
    entry_year = "____"
    class_num = "__"
    if student.current_class_rel:
        entry_year = str(student.current_class_rel.entry_year)
        class_num = str(student.current_class_rel.class_num)

    school_id = student.city_school_id or student.national_school_id or "暂无数据"
    id_card = student.id_card_number or "暂无数据"
    now = datetime.now()

    context = {
        "name": student.name,
        "gender": student.gender,
        "entry_year": entry_year,
        "class_num": class_num,
        "status": student.status,
        "school_id": school_id,
        "id_card": id_card,
        "year": now.year,
        "month": now.month,
        "day": now.day,
    }

    template_path = _resolve_template_path("certificate_template.docx")
    if not os.path.exists(template_path):
        raise FileNotFoundError("服务器端缺少证书模板文件(certificate_template.docx)")

    tpl = DocxTemplate(template_path)
    tpl.render(context)

    file_stream = io.BytesIO()
    tpl.save(file_stream)
    file_stream.seek(0)
    return file_stream, f"{student.name}_学籍证明.docx"

