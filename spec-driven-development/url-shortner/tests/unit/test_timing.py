import re


def test_every_response_has_server_timing(client):
    for path in ["/account/signin", "/does-not-exist", "/"]:
        response = client.get(path, follow_redirects=False)

        assert re.fullmatch(r"app;dur=\d+(\.\d+)?", response.headers["server-timing"])
