from __future__ import annotations

import json
import time
from urllib import error, request

from .config import FeishuConfig


TOKEN_URL = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
MESSAGE_URL_TEMPLATE = (
    "https://open.feishu.cn/open-apis/im/v1/messages"
    "?receive_id_type={receive_id_type}"
)


def post_json(url: str, payload: dict, headers: dict | None = None) -> dict:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request_headers = {"Content-Type": "application/json; charset=utf-8"}
    if headers:
        request_headers.update(headers)

    req = request.Request(url, data=body, headers=request_headers, method="POST")
    try:
        with request.urlopen(req, timeout=20) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code}: {raw}") from exc


class FeishuBot:
    def __init__(self, config: FeishuConfig) -> None:
        self.config = config
        self._token = ""
        self._token_expires_at = 0.0

    def _fetch_token(self) -> str:
        payload = {"app_id": self.config.app_id, "app_secret": self.config.app_secret}
        data = post_json(TOKEN_URL, payload)
        if data.get("code") != 0:
            raise RuntimeError(f"Token request failed: {data}")
        self._token = data["tenant_access_token"]
        self._token_expires_at = time.time() + int(data.get("expire", 7200)) - 300
        return self._token

    def token(self) -> str:
        if not self._token or time.time() >= self._token_expires_at:
            return self._fetch_token()
        return self._token

    def send_text(self, text: str) -> dict:
        payload = {
            "receive_id": self.config.receive_id,
            "msg_type": "text",
            "content": json.dumps({"text": text}, ensure_ascii=False),
        }
        headers = {"Authorization": f"Bearer {self.token()}"}
        url = MESSAGE_URL_TEMPLATE.format(receive_id_type=self.config.receive_id_type)
        data = post_json(url, payload, headers)
        if data.get("code") != 0:
            raise RuntimeError(f"Send message failed: {data}")
        return data
