from app.adapters.chaoxing_crypto import encrypt_login


def test_chaoxing_sm4_login_vectors():
    assert encrypt_login("example-account") == "gD3oi0E6TsFgtysqIgbC9Q=="
    assert encrypt_login("example-password") == "$ShowMe$df4u3LYw7PN2GGgP1Nsk3CQ7IZp6IZcb9ofTDCChYc="
