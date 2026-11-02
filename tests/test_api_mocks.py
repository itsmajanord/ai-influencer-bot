"""Kontrollerar att API-anropen byggs rätt, utan att nå nätet."""
import json

from bot import content, instagram, tiktok


class FakeResp:
    def __init__(self, data, status=200):
        self._data, self.status_code, self.content = data, status, b"x"
        self.text = json.dumps(data)

    def json(self):
        return self._data


def test_instagram_carousel_flow(monkeypatch):
    calls = []

    def fake_request(method, url, params=None, timeout=None):
        calls.append((method, url, dict(params)))
        if url.endswith("/media_publish"):
            return FakeResp({"id": "MEDIA1"})
        if method == "GET":
            return FakeResp({"status_code": "FINISHED"})
        return FakeResp({"id": f"C{len(calls)}"})

    monkeypatch.setattr(instagram.requests, "request", fake_request)
    media_id = instagram.publish("IG", "TOK", ["https://x/1.jpg", "https://x/2.jpg"], "cap", "v26.0")
    assert media_id == "MEDIA1"
    posts = [c for c in calls if c[0] == "POST"]
    assert posts[0][2]["is_carousel_item"] == "true"
    carousel = [c for c in posts if c[2].get("media_type") == "CAROUSEL"][0]
    assert carousel[2]["caption"] == "cap" and "," in carousel[2]["children"]
    assert all(c[2]["access_token"] == "TOK" for c in calls)


def test_tiktok_inbox_body(monkeypatch):
    sent = {}

    def fake_post(url, headers=None, json=None, timeout=None, data=None):
        sent["url"], sent["body"] = url, json
        return FakeResp({"data": {"publish_id": "P1"}, "error": {"code": "ok"}})

    monkeypatch.setattr(tiktok.requests, "post", fake_post)
    pid = tiktok.publish_photos("AT", ["https://x/1.jpg"], "titel", "text #AI", mode="inbox")
    assert pid == "P1"
    assert sent["body"]["post_mode"] == "MEDIA_UPLOAD"
    assert sent["body"]["media_type"] == "PHOTO"
    assert sent["body"]["post_info"]["is_aigc"] is True
    assert sent["url"].endswith("/post/publish/content/init/")


def test_parse_claude_json_with_extra_text():
    text = 'Här är planen:\n[{"scene": "a", "caption": "b", "hashtags": []}]\nLycka till!'
    assert content._parse_json_list(text)[0]["scene"] == "a"
