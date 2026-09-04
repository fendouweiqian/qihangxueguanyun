from app.application.progress_parser import ProgressDetailParser


def test_progress_parser_extracts_profile_course_and_exam_rows():
    parser = ProgressDetailParser()
    profile = parser.parse_student_profile('<p class="user-name">张三</p><div>专业：计算机</div>')
    courses = parser.parse_course_items('<div class="course"><span class="course-name">Python</span><span>学习进度 100%</span></div>')
    exams = parser.parse_exam_items('<table><tr><th>考试名称</th><th>成绩</th><th>提交状态</th></tr><tr><td>期末</td><td>88</td><td>已提交</td></tr></table>')
    assert profile == {"studentName": "张三", "major": "计算机"}
    assert courses[0]["courseName"] == "Python"
    assert courses[0]["learningPercent"] == 100.0
    assert exams[0]["examStatus"] == 1
    assert exams[0]["score"] == 88.0
