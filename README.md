# Feishu Stock Watcher

This project watches US stocks through moomoo OpenAPI/OpenD and sends private
Feishu bot alerts when a symbol moves more than the configured percentage inside
a short time window.

Full Chinese usage guide:

- `使用说明书.md`
- `使用说明书.html`

## Current status

- Feishu private bot smoke test is ready.
- Moomoo quote watcher is implemented.
- Ubuntu 22.04 systemd deployment notes are included.

## 1. Install dependencies locally

```powershell
python -m pip install -r requirements.txt
```

## 2. Configure Feishu

Use environment variables or create a local `.env` file. Do not commit real
secrets.

```powershell
$env:FEISHU_APP_ID="cli_aaaae2560b38dccd"
$env:FEISHU_APP_SECRET="replace_me"
$env:FEISHU_RECEIVE_ID_TYPE="open_id"
$env:FEISHU_RECEIVE_ID="ou_xxx"
```

`FEISHU_RECEIVE_ID` should be your personal `open_id` by default. If you only
have another identifier, switch `FEISHU_RECEIVE_ID_TYPE` to the matching
Feishu-supported value.

## 3. Send a test message

```powershell
python .\feishu_bot_test.py "Stock watcher bot is online"
```

If the script succeeds, the private robot chat path is ready. You already
verified this once.

## 4. Configure positions

Create `positions.json` from `positions.example.json`.

```json
[
  { "symbol": "AAPL", "name": "Apple", "enabled": true },
  { "symbol": "NVDA", "name": "NVIDIA", "enabled": true }
]
```

Use plain US tickers. The watcher converts `AAPL` to moomoo code `US.AAPL`.

## 5. Configure moomoo OpenD

Run moomoo OpenD first, then keep the quote port aligned with `.env`:

```text
MOOMOO_OPEND_HOST=127.0.0.1
MOOMOO_OPEND_PORT=11111
```

## 6. Run the watcher

Fetch one quote batch and exit:

```powershell
python .\watch.py --once
```

Run continuously:

```powershell
python .\watch.py
```

Default watcher behavior:

- window: 5 minutes
- threshold: 1%
- poll interval: 10 seconds
- cooldown: same stock and direction alerts once every 10 minutes

## 7. Deploy later

See `deploy/ubuntu-setup.md` after the Hong Kong server is ready.

## Security note

The Feishu `App Secret` was pasted into chat while testing. Rotate it in the
Feishu developer console before deploying the real watcher.
