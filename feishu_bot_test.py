import json
import os
import sys
from urllib import error, request


TOKEN_URL = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
MESSAGE_URL_TEMPLATE = (
    "https://open.feishu.cn/open-apis/im/v1/messages"
    "?receive_id_type={receive_id_type}"
)


def env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def post_json(url: str, payload: dict, headers: dict | None = None) -> dict:
    body = json.dumps(payload).encode("utf-8")
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


def fetch_tenant_access_token(app_id: str, app_secret: str) -> str:
    payload = {"app_id": app_id, "app_secret": app_secret}
    data = post_json(TOKEN_URL, payload)
    if data.get("code") != 0:
        raise RuntimeError(f"Token request failed: {data}")
    return data["tenant_access_token"]


def send_text_message(token: str, receive_id_type: str, receive_id: str, text: str) -> dict:
    payload = {
        "receive_id": receive_id,
        "msg_type": "text",
        "content": json.dumps({"text": text}, ensure_ascii=False),
    }
    headers = {"Authorization": f"Bearer {token}"}
    data = post_json(MESSAGE_URL_TEMPLATE.format(receive_id_type=receive_id_type), payload, headers)
    if data.get("code") != 0:
        raise RuntimeError(f"Send message failed: {data}")
    return data


def main() -> int:
    try:
        app_id = env("FEISHU_APP_ID")
        app_secret = env("FEISHU_APP_SECRET")
        receive_id_type = os.getenv("FEISHU_RECEIVE_ID_TYPE", "open_id").strip() or "open_id"
        receive_id = env("FEISHU_RECEIVE_ID")

        default_message = "Feishu bot test from stock watcher"
        message = sys.argv[1] if len(sys.argv) > 1 else default_message

        token = fetch_tenant_access_token(app_id, app_secret)
        result = send_text_message(token, receive_id_type, receive_id, message)
        print("Message sent successfully.")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except Exception as exc:  # noqa: BLE001
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
