from app.domain.progress import CourseProgress, CourseProgressItem, ExamProgress, ExamProgressItem


def test_progress_ids_are_strings():
    course = CourseProgress.model_validate({"progress_id": 1, "order_id": 2, "tenant_id": "DEMO", "video_status": 1, "work_status": 1, "exam_status": 0})
    exam = ExamProgress.model_validate({"exam_progress_id": 3, "order_id": 2, "tenant_id": "DEMO", "status": 0})
    item = CourseProgressItem.model_validate({"item_id": 4, "order_id": 2, "tenant_id": "DEMO", "course_name": "课程"})
    exam_item = ExamProgressItem.model_validate({"item_id": 5, "order_id": 2, "tenant_id": "DEMO", "exam_name": "考试"})
    assert (course.order_id, exam.order_id, item.item_id, exam_item.item_id) == ("2", "2", "4", "5")

