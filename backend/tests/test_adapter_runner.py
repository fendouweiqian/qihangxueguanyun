from app.adapters.base import AdapterContext, AdapterTask, TaskKind
from app.adapters.chaoxing import ChaoxingAdapter, ChaoxingClient, account_kind
from app.adapters.chaoxing_learning import (
    Chapter,
    ChaoxingLearningClient,
    decode_course_cards,
    decode_course_list,
    parse_work_questions,
    parse_chapters,
)
from app.adapters.chengkaoyun import ChengKaoYunAdapter, ChengKaoYunClient
from app.adapters.mock import MockAdapter
from app.adapters.registry import AdapterRegistry
from app.application.task_runner import TaskRunner


class Gateway:
    def __init__(self):
        self.submitted = []

    def claim(self, limit, runner_id, task_types=None):
        return [{"taskId": "9000000000000000002", "orderId": "9000000000000000003", "tenantId": "DEMO", "taskType": 1, "studentId": "9000000000000000001", "schoolId": "38", "studentAccount": "masked", "studentPassword": "masked"}]

    def submit_result(self, *args):
        self.submitted.append(args)
        return True

    def upsert_course_progress(self, payload):
        pass

    def upsert_exam_progress(self, payload):
        pass

    def replace_course_progress_items(self, payload):
        return 0

    def replace_exam_progress_items(self, payload):
        return 0

    def record_tiku_failure(self, payload):
        pass


def test_mock_adapter_and_runner():
    adapter = MockAdapter()
    context = AdapterContext("DEMO", "38", "9000000000000000001", "masked", "masked")
    result = adapter.execute(AdapterTask("1", "2", "DEMO", TaskKind.STUDY), context)
    assert result.ok is True
    gateway = Gateway()
    original_claim = gateway.claim
    gateway.claim = lambda limit, runner_id, task_types=None: [{**original_claim(limit, runner_id, task_types)[0], "adapter": "mock"}]
    assert TaskRunner(gateway, AdapterRegistry()).run_once() == 1
    assert gateway.submitted[0][1] is True


def test_runner_refuses_to_default_to_mock_for_unconfigured_task():
    gateway = Gateway()
    assert TaskRunner(gateway, AdapterRegistry()).run_once() == 1
    assert gateway.submitted[0][1:] == (False, "adapter_missing", "任务未配置平台适配器", 1)


def test_chengkaoyun_login_uses_token_and_profile_without_network():
    class Response:
        def __init__(self, payload):
            self.payload = payload

        def raise_for_status(self):
            return None

        def json(self):
            return self.payload

    class Session:
        def post(self, url, **kwargs):
            assert url.endswith("/api/v1/user/password/check")
            assert kwargs["json"]["password"] == "masked"
            return Response({"code": 200, "data": {"token": "temporary-token"}})

        def get(self, url, **kwargs):
            assert url.endswith("/api/v1/student/mobile/management")
            assert kwargs["headers"]["Authorization"] == "temporary-token"
            return Response({"code": 200, "data": [{"name": "测试学生"}]})

    adapter = ChengKaoYunAdapter(
        {"base_url": "http://local.test"},
        client_factory=lambda url, timeout: ChengKaoYunClient(url, Session(), timeout),
    )
    result = adapter.login(AdapterContext("T", "1", "2", "account", "masked", {"studentOpenId": "open-id", "schoolUrl": "http://local.test"}))
    assert result.ok is True
    assert result.data["studentName"] == "测试学生"


def test_chaoxing_default_study_discovers_course_and_flushes_progress(monkeypatch):
    """默认学习任务无需手工传入课程和章节参数。"""

    class Learning:
        def __init__(self, base_url, session, timeout):
            self.base_url = base_url

        def _url(self, path):
            return f"http://local.test/{path}"

        def fetch_courses(self):
            return [{"title": "数据结构", "courseId": "1", "clazzId": "2", "cpi": "3"}]

        def fetch_chapters(self, course_url):
            assert "courseId=1" in course_url
            return [Chapter("4", "第一章", course_url, "1")]

        def fetch_jobs(self, course, chapter_id):
            return ([{"type": "video"}], {})

        def execute_job(self, course, job, info, tiku_client, font_map_path):
            return True, "video_completed"

    monkeypatch.setattr("app.adapters.chaoxing.ChaoxingLearningClient", Learning)
    adapter = ChaoxingAdapter()
    adapter._clients["student"] = type("Client", (), {"base_url": "http://local.test", "session": object()})()
    task = AdapterTask("task", "order", "T", TaskKind.STUDY, {"courseName": "数据结构"})
    result = adapter.execute(task, AdapterContext("T", "1", "student", "account", "password"))
    assert result.ok is True
    assert result.data["course_progress"]["videoStatus"] == 1
    assert result.data["course_progress_items"]["items"][0]["learningPercent"] == 100


def test_task_runner_passes_platform_context_to_adapter():
    captured = {}

    class CaptureAdapter:
        name = "capture"

        def login(self, context):
            captured.update(context.extra)
            return MockAdapter().login(context)

        def execute(self, task, context):
            return MockAdapter().execute(task, context)

    gateway = Gateway()
    task = gateway.claim(1, "runner-a")[0]
    task.update({"studentOpenId": "open-id", "schoolUrl": "http://local.test", "platformName": "成考云"})
    gateway.claim = lambda limit, runner_id, task_types=None: [task]
    assert TaskRunner(gateway, AdapterRegistry([CaptureAdapter()])).run_once(adapter_name="capture") == 1
    assert captured["studentOpenId"] == "open-id"
    assert captured["schoolUrl"] == "http://local.test"


def test_default_registry_contains_external_adapter_boundary():
    assert AdapterRegistry().get("chengkaoyun").name == "chengkaoyun"
    assert AdapterRegistry().get("chaoxing").name == "chaoxing"
    result = AdapterRegistry().get("chengkaoyun").execute(AdapterTask("1", "2", "T", TaskKind.STUDY), AdapterContext("T", "1", "2", "a", "b"))
    assert result.ok is False


def test_registry_infers_platform_without_using_mock_default():
    registry = AdapterRegistry()
    assert registry.resolve_name({"platformName": "成考云"}) == "chengkaoyun"
    assert registry.resolve_name({"platformName": "超星学习通"}) == "chaoxing"
    assert registry.resolve_name({"platformName": "未知平台"}) == ""


def test_chaoxing_login_encrypts_form_and_accepts_redirect_without_network():
    class Response:
        status_code = 302
        headers = {"Location": "/base"}
        text = ""

        def raise_for_status(self):
            return None

    class Session:
        def get(self, url, **kwargs):
            assert url.endswith("/login")
            return type("LoginPage", (), {"text": '<form id="loginForm"><input name="enToken" value="token"></form>', "raise_for_status": lambda self: None})()

        def post(self, url, **kwargs):
            assert "userName=" in kwargs["data"]
            assert "passWord=" in kwargs["data"]
            assert "enToken=token" in kwargs["data"]
            return Response()

    adapter = ChaoxingAdapter(
        {"base_url": "http://local.test"},
        client_factory=lambda url, timeout: ChaoxingClient(url, Session(), timeout),
    )
    result = adapter.login(AdapterContext("T", "1", "2", "example-account", "example-password", {"verifyCode": "0000"}))
    assert result.ok is True


def test_chaoxing_account_kind_matches_go_phone_login_rule():
    """手机号账号应进入与 Go 执行器一致的手机号登录诊断分支。"""
    example_phone = "138" + "0" * 8
    assert account_kind(example_phone) == "phone"
    assert account_kind(f" {example_phone} ") == "phone"
    assert account_kind("0" * 18) == "username"
    assert account_kind("student-account") == "username"


def test_chaoxing_captcha_protocol_uses_explicit_coordinate_without_solver():
    class Response:
        def __init__(self, text="", payload=None, content=b"", status_code=200):
            self.text = text
            self._payload = payload
            self.content = content
            self.status_code = status_code
            self.headers = {}

        def raise_for_status(self):
            return None

        def json(self):
            return self._payload

    class Session:
        def get(self, url, **kwargs):
            if url.endswith("/captcha/get/conf"):
                return Response("cb({\"t\":123456})")
            if url.endswith("/captcha/get/verification/image"):
                return Response('cb({"token":"cap-token","imageVerificationVo":{"shadeImage":"http://local/shade","cutoutImage":"http://local/cutout"}})')
            if url.endswith("/captcha/check/verification/result"):
                return Response('cb({"result":true,"extraData":"{\\"validate\\":\\"validated\\"}"})')
            raise AssertionError(url)

    client = ChaoxingClient("http://local.test", Session())
    captcha = client.fetch_captcha("captcha-id")
    assert captcha["token"] == "cap-token"
    assert client.verify_captcha("captcha-id", "slide", "1.1.20", captcha["token"], 42, captcha["iv"]) == "validated"


def test_chaoxing_resolves_captcha_id_from_login_script():
    """登录页未内联验证码标识时继续读取 loadSlide.js。"""

    class Response:
        def __init__(self, text):
            self.text = text

        def raise_for_status(self):
            return None

    class Session:
        def get(self, url, **kwargs):
            if url.endswith("/login"):
                return Response('<script src="/js/loadSlide.js?v=1"></script>')
            assert url == "http://local.test/js/loadSlide.js?v=1"
            return Response("window.conf={captchaId: 'resolved-id'}")

    assert ChaoxingClient("http://local.test", Session()).resolve_captcha_id() == "resolved-id"


def test_chaoxing_login_reads_captcha_settings_from_environment(monkeypatch):
    captured = {}

    class Client:
        def fetch_captcha(self, captcha_id, captcha_type, version):
            captured.update({"captcha_id": captcha_id, "captcha_type": captcha_type, "version": version})
            return {"token": "token", "shadeImage": "", "cutoutImage": "", "iv": "iv"}

        def verify_captcha(self, captcha_id, captcha_type, version, token, x, iv):
            assert x == 42
            return "validated"

        def login(self, username, password, verify_code, role_status):
            captured["verify_code"] = verify_code
            return type("Response", (), {"status_code": 302, "headers": {"Location": "/base"}, "text": ""})()

        @staticmethod
        def extract_nickname(text):
            return ""

    monkeypatch.setenv("EDUCATION_CHAOXING_CAPTCHA_ID", "env-captcha")
    adapter = ChaoxingAdapter({"base_url": "http://local.test"}, client_factory=lambda url, timeout: Client())
    result = adapter.login(AdapterContext("T", "1", "2", "account", "password", {"captchaX": 42}))
    assert result.ok is True
    assert captured == {"captcha_id": "env-captcha", "captcha_type": "slide", "version": "1.1.20", "verify_code": "validated"}


def test_chaoxing_course_and_chapter_parsers_preserve_platform_fields():
    course_html = """
    <div class="course" id="course-1" info="info" roleid="1">
      <input class="clazzId" value="11"><input class="courseId" value="22">
      <a href="/studentstudy?chapterId=33&cpi=44"><span class="course-name">数据结构</span></a>
      <p class="margint10">基础课程</p><p class="color3">测试教师</p>
    </div>
    <div class="course"><a class="not-open-tip" href="#"><span class="course-name">未开放</span></a></div>
    """
    courses = decode_course_list(course_html)
    assert courses == [{
        "id": "course-1", "info": "info", "roleid": "1", "clazzId": "11", "courseId": "22",
        "cpi": "44", "title": "数据结构", "desc": "基础课程", "teacher": "测试教师",
    }]
    chapters = parse_chapters(
        '<a href="/studentstudy?chapterId=33" aria-label="第一章"><span class="chapterNumber">1</span><span class="articlename">绪论</span><input class="knowledgeJobCount" value="2"></a>',
        "http://local.test/course",
    )
    assert chapters[0].chapter_id == "33"
    assert chapters[0].title == "第一章"
    assert chapters[0].job_count == "2"


def test_chaoxing_card_parser_filters_passed_jobs_and_keeps_tokens():
    html = 'mArg={"defaults":{"ktoken":"k","knowledgeid":"n"},"attachments":[' \
           '{"type":"video","job":{},"jobid":"j1","objectId":"o1","isPassed":false},' \
           '{"type":"document","job":{},"jobid":"j2","jtoken":"t","isPassed":true},' \
           '{"type":"workid","job":{},"jobid":"j3","enc":"e","isPassed":false}]};'
    jobs, info = decode_course_cards(html)
    assert info["ktoken"] == "k"
    assert [job["type"] for job in jobs] == ["video", "workid"]


def test_chaoxing_adapter_discovers_courses_after_explicit_login():
    class Response:
        def __init__(self, text="", status_code=200, payload=None, url="http://local.test"):
            self.text = text
            self.status_code = status_code
            self._payload = payload
            self.url = url
            self.headers = {"Location": "/base"} if status_code == 302 else {}

        def raise_for_status(self):
            if self.status_code >= 400:
                raise RuntimeError("http error")

        def json(self):
            return self._payload

    class Session:
        def __init__(self):
            import requests
            self.cookies = requests.cookies.RequestsCookieJar()
            self.headers = {}
            self.posts = []

        def get(self, url, **kwargs):
            if url.endswith("/login"):
                return Response('<form id="loginForm"><input name="enToken" value="token"></form>')
            assert url.endswith("/mooc2-ans/visit/interaction")
            return Response("<html></html>")

        def post(self, url, **kwargs):
            if "/commonlogin/" in url:
                return Response(status_code=302)
            self.posts.append((url, kwargs))
            return Response('<div class="course" id="c"><input class="clazzId" value="11"><input class="courseId" value="22"><a href="?cpi=44"><span class="course-name">课程</span></a></div>')

    session = Session()
    adapter = ChaoxingAdapter(
        {"base_url": "http://local.test"},
        client_factory=lambda url, timeout: ChaoxingClient(url, session, timeout),
    )
    context = AdapterContext("T", "1", "2", "account", "password", {"verifyCode": "0000", "schoolUrl": "http://local.test"})
    assert adapter.login(context).ok is True
    result = adapter.execute(AdapterTask("task", "order", "T", TaskKind.STUDY, {"operation": "list_courses"}), context)
    assert result.ok is True
    assert result.code == "courses_fetched"
    assert result.data["courses"][0]["courseId"] == "22"


def test_chaoxing_video_progress_requires_platform_pass_confirmation():
    class Response:
        status_code = 200

        def __init__(self, payload):
            self.payload = payload
            self.text = ""

        def raise_for_status(self):
            return None

        def json(self):
            return self.payload

    class Session:
        def __init__(self):
            import requests
            self.cookies = requests.cookies.RequestsCookieJar()
            self.cookies.set("_uid", "u")
            self.cookies.set("fid", "f")
            self.calls = []

        def get(self, url, **kwargs):
            self.calls.append((url, kwargs))
            if "/ananas/status/" in url:
                return Response({"status": "success", "dtoken": "d", "duration": 10})
            return Response({"isPassed": True})

    session = Session()
    client = ChaoxingLearningClient("http://local.test", session)
    ok, code = client.execute_job(
        {"courseId": "22", "clazzId": "11", "cpi": "44"},
        {"type": "video", "jobid": "j", "objectid": "o", "otherinfo": ""},
        {},
    )
    assert (ok, code) == (True, "video_completed")
    assert any("multimedia/log/a/44/d" in url for url, _ in session.calls)


def test_chaoxing_work_submission_uses_explicit_tiku_and_full_coverage():
    html = """
    <form><input name="workRelationId" value="r1">
      <div class="singleQuesId" data="q1"><div class="TiMu" data="0"></div>
        <div class="Zy_TItle">1 + 1 = ?</div><ul><li aria-label="A. 1"></li><li aria-label="B. 2"></li></ul>
      </div>
    </form>
    """
    form, questions = parse_work_questions(html)
    assert form == {"workRelationId": "r1"}
    assert questions[0]["type"] == "single"
    assert questions[0]["options"] == ["A. 1", "B. 2"]

    class Response:
        def __init__(self, status_code=200, text="", payload=None):
            self.status_code = status_code
            self.text = text
            self._payload = payload
            self.url = "http://local.test/mooc-ans/api/work"

        def raise_for_status(self):
            return None

        def json(self):
            return self._payload

    class Session:
        def __init__(self):
            self.calls = []

        def get(self, url, **kwargs):
            self.calls.append(("get", url, kwargs))
            return Response(text=html)

        def post(self, url, **kwargs):
            self.calls.append(("post", url, kwargs))
            assert kwargs["data"]["answerq1"] == "B"
            return Response(payload={"status": True})

    class Tiku:
        cover_rate = 1.0
        submit = True
        true_list = []
        false_list = []

        def query(self, question, options, question_type):
            assert question == "1 + 1 = ?"
            assert question_type == "single"
            return "B"

    client = ChaoxingLearningClient("http://local.test", Session())
    ok, code = client.execute_job(
        {"courseId": "22", "clazzId": "11", "cpi": "44"},
        {"type": "workid", "jobid": "work-j1", "enc": "e"},
        {"ktoken": "k", "knowledgeid": "n", "cpi": "44"},
        Tiku(),
    )
    assert (ok, code) == (True, "work_completed")


def test_chengkaoyun_exam_flow_requires_explicit_code_and_writes_answer():
    class Response:
        def __init__(self, payload=None, status_code=200):
            self._payload = payload or {}
            self.status_code = status_code

        def raise_for_status(self):
            if self.status_code >= 400:
                raise RuntimeError("http error")

        def json(self):
            return self._payload

    class Session:
        def __init__(self):
            self.saved = None

        def post(self, url, **kwargs):
            if url.endswith("/api/v1/user/password/check"):
                return Response({"code": 200, "data": {"token": "token"}})
            if url.endswith("/api/v1/examination/sign"):
                assert kwargs["json"]["code"] == "1234"
                return Response({"code": 200, "msg": "签到成功"})
            if url.endswith("/api/v1/examination/mobile/management"):
                return Response({"code": 200, "type": 1, "exam_id": "exam-1", "ques_list": [{
                    "id": "q1", "type": "radio", "html": "1+1?",
                    "options": [{"option_num": "A", "title": "1"}, {"option_num": "B", "title": "2"}],
                }]})
            if url.endswith("/api/v1/answer/mobile/save"):
                self.saved = kwargs["json"]
                assert self.saved["question_list"][0]["options"][1]["is_selected"] is True
                return Response({"code": 200})
            if url.endswith("/tiku"):
                return Response({"answer": {"answerText": "B"}})
            raise AssertionError(url)

        def get(self, url, **kwargs):
            if url.endswith("/api/v1/student/mobile/management"):
                return Response({"code": 200, "data": [{"name": "测试学生"}]})
            if url.endswith("/api/v1/examination/programexam"):
                return Response({"code": 200, "data": [{"crs_id": "course-1", "ques_id": "q-list", "is_sign": 0, "stu_exam": {"exam_id": "exam-1"}}]})
            raise AssertionError(url)

        def put(self, url, **kwargs):
            assert url.endswith("/api/v1/examination/mobile/management")
            assert kwargs["json"]["exam_id"] == "exam-1"
            return Response({"code": 200})

    session = Session()
    adapter = ChengKaoYunAdapter(
        {"base_url": "http://local.test"},
        client_factory=lambda url, timeout: ChengKaoYunClient(url, session, timeout),
    )
    context = AdapterContext("T", "1", "2", "phone", "password", {"studentOpenId": "open", "schoolUrl": "http://local.test"})
    assert adapter.login(context).ok is True
    result = adapter.execute(AdapterTask("task", "order", "T", TaskKind.EXAM, {
        "semesterId": "2025", "stuId": "student", "signCode": "1234", "submitExam": True,
        "tiku": {"provider": "adapter", "url": "http://local.test/tiku"},
    }), context)
    assert result.ok is True
    assert result.code == "exam_completed"


def test_chengkaoyun_exam_flow_can_solve_explicit_captcha_service():
    class Response:
        status_code = 200
        content = b"image"

        def __init__(self, payload=None):
            self._payload = payload or {}

        def raise_for_status(self):
            return None

        def json(self):
            return self._payload

    class Session:
        def post(self, url, **kwargs):
            if url.endswith("/api/v1/user/password/check"):
                return Response({"code": 200, "data": {"token": "token"}})
            if url.endswith("/api/v1/examination/sign"):
                assert kwargs["json"]["code"] == "5678"
                return Response({"code": 200})
            if url.endswith("/api/v1/examination/mobile/management"):
                return Response({"code": 200, "ques_list": []})
            if url.endswith("/solver"):
                assert kwargs["json"]["image"]
                return Response({"code": 10000, "data": {"data": "5678"}})
            raise AssertionError(url)

        def get(self, url, **kwargs):
            if url.endswith("/api/v1/student/mobile/management"):
                return Response({"data": [{"name": "测试学生"}]})
            if url.endswith("/api/v1/examination/makecode"):
                return Response()
            if url.endswith("/api/v1/examination/programexam"):
                return Response({"code": 200, "data": [{"crs_id": "c", "ques_id": "q", "is_sign": 0, "stu_exam": {"exam_id": "e"}}]})
            raise AssertionError(url)

    session = Session()
    adapter = ChengKaoYunAdapter({"base_url": "http://local.test"}, client_factory=lambda url, timeout: ChengKaoYunClient(url, session, timeout))
    context = AdapterContext("T", "1", "2", "phone", "password", {"studentOpenId": "open", "schoolUrl": "http://local.test"})
    assert adapter.login(context).ok is True
    result = adapter.execute(AdapterTask("task", "order", "T", TaskKind.EXAM, {
        "semesterId": "s", "captchaApiUrl": "http://local.test/solver", "captchaApiToken": "temporary",
        "tiku": {"provider": "adapter", "url": "http://local.test/tiku"},
    }), context)
    assert result.code == "exam_questions_missing"
