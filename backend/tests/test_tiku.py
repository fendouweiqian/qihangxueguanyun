from app.adapters.tiku import TikuClient


def test_tiku_client_normalizes_structured_answer_without_network():
    class Response:
        def raise_for_status(self):
            return None

        def json(self):
            return {"answer": {"bestAnswer": ["A", "C"]}}

    class Session:
        def post(self, url, **kwargs):
            assert url == "http://local.test/tiku"
            assert kwargs["json"]["type"] == 0
            assert kwargs["json"]["options"] == ["one", "two"]
            return Response()

    client = TikuClient({"provider": "adapter", "url": "http://local.test/tiku"}, Session())
    assert client.query("问题", "A. one\nB. two", "single") == "A\nC"


def test_tiku_client_requires_explicit_configuration():
    assert TikuClient({"provider": "adapter"}).query("问题") is None
