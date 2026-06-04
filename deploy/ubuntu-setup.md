# Ubuntu 22.04 deployment notes

Target server: Ubuntu 22.04 x64, Hong Kong VPS.

## 1. Base packages

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip git unzip curl
```

## 2. App user and directory

```bash
sudo useradd --system --create-home --shell /usr/sbin/nologin stockwatcher
sudo mkdir -p /opt/stock-watcher
sudo chown -R stockwatcher:stockwatcher /opt/stock-watcher
```

Upload this project into `/opt/stock-watcher`.

## 3. Python environment

```bash
cd /opt/stock-watcher
sudo -u stockwatcher python3 -m venv .venv
sudo -u stockwatcher .venv/bin/python -m pip install --upgrade pip
sudo -u stockwatcher .venv/bin/python -m pip install -r requirements.txt
```

## 4. Environment

Create `/opt/stock-watcher/.env` from `.env.example`.

Required values:

```bash
FEISHU_APP_ID=cli_xxx
FEISHU_APP_SECRET=replace_me
FEISHU_RECEIVE_ID_TYPE=open_id
FEISHU_RECEIVE_ID=ou_xxx
MOOMOO_OPEND_HOST=127.0.0.1
MOOMOO_OPEND_PORT=11111
```

## 5. Moomoo OpenD

Install and log in to OpenD on the server. Keep its quote port on `11111`
unless you also change `MOOMOO_OPEND_PORT`.

Before starting the watcher, verify:

```bash
nc -vz 127.0.0.1 11111
```

## 6. systemd service

```bash
sudo cp deploy/stock-watcher.service /etc/systemd/system/stock-watcher.service
sudo systemctl daemon-reload
sudo systemctl enable stock-watcher
sudo systemctl start stock-watcher
sudo systemctl status stock-watcher
```

Logs:

```bash
sudo journalctl -u stock-watcher -f
```
