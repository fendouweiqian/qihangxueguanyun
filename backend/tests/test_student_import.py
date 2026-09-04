from io import BytesIO

from openpyxl import Workbook


def test_parse_student_xlsx_uses_chinese_headers_and_skips_blank_rows():
    from app.api.students import _parse_student_rows

    workbook = Workbook()
    sheet = workbook.active
    sheet.append(["账号", "密码", "姓名"])
    sheet.append(["student-a", "secret-a", "张三"])
    sheet.append([None, None, None])
    payload = BytesIO()
    workbook.save(payload)

    assert _parse_student_rows(payload.getvalue(), ".xlsx") == [
        ("student-a", "secret-a", "张三")
    ]


def test_parse_student_xlsx_rejects_missing_required_headers():
    from app.api.students import _parse_student_rows

    workbook = Workbook()
    sheet = workbook.active
    sheet.append(["账号", "姓名"])
    sheet.append(["student-a", "张三"])
    payload = BytesIO()
    workbook.save(payload)

    try:
        _parse_student_rows(payload.getvalue(), ".xlsx")
    except ValueError as exc:
        assert str(exc) == "导入文件必须包含账号、密码列"
    else:
        raise AssertionError("missing password header should fail")
