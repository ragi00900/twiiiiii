#!/usr/bin/env python3
"""
ツイキャス配信検知 → Pushover通知（鳴り続けるアラーム）スクリプト
GitHub Actions上で動かすバージョン（設定値はすべて環境変数から読む）

ローカルで動作確認したい場合は、以下のように環境変数を渡して実行できます:

  TWITCASTING_CLIENT_ID=xxx \
  TWITCASTING_CLIENT_SECRET=xxx \
  PUSHOVER_USER_KEY=xxx \
  PUSHOVER_API_TOKEN=xxx \
  python3 check_live.py
"""

import base64
import json
import os
import sys
import requests

# 監視したい配信者の screen_id（URL の twitcasting.tv/◯◯◯ の部分）
TARGET_USERS = ["kokage_nite", "mikanseip"]

# 緊急通知（Emergency Priority）の鳴らし方設定
PUSHOVER_RETRY_SECONDS = 60      # 何秒おきに再通知するか（最低30秒）
PUSHOVER_EXPIRE_SECONDS = 3600   # 確認するまで最大何秒鳴らし続けるか（最大10800=3時間）

STATE_FILE = "state.json"  # リポジトリ内に置かれ、実行後にコミットされる

TWITCASTING_CLIENT_ID = os.environ["TWITCASTING_CLIENT_ID"]
TWITCASTING_CLIENT_SECRET = os.environ["TWITCASTING_CLIENT_SECRET"]
PUSHOVER_USER_KEY = os.environ["PUSHOVER_USER_KEY"]
PUSHOVER_API_TOKEN = os.environ["PUSHOVER_API_TOKEN"]


def twitcasting_headers():
    raw = f"{TWITCASTING_CLIENT_ID}:{TWITCASTING_CLIENT_SECRET}".encode("utf-8")
    basic = base64.b64encode(raw).decode("utf-8")
    return {
        "Accept": "application/json",
        "X-Api-Version": "2.0",
        "Authorization": f"Basic {basic}",
    }


def is_user_live(screen_id):
    url = f"https://apiv2.twitcasting.tv/users/{screen_id}"
    res = requests.get(url, headers=twitcasting_headers(), timeout=10)
    res.raise_for_status()
    user = res.json()["user"]
    return user["is_live"], user["name"]


def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return json.load(f)
    return {}


def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)


def send_pushover_alarm(streamer_name, screen_id):
    url = "https://api.pushover.net/1/messages.json"
    payload = {
        "token": PUSHOVER_API_TOKEN,
        "user": PUSHOVER_USER_KEY,
        "title": f"\U0001F534 {streamer_name} が配信開始！",
        "message": f"twitcasting.tv/{screen_id} で配信中です",
        "url": f"https://twitcasting.tv/{screen_id}",
        "url_title": "配信を見る",
        "priority": 2,
        "retry": PUSHOVER_RETRY_SECONDS,
        "expire": PUSHOVER_EXPIRE_SECONDS,
        "sound": "persistent",
    }
    res = requests.post(url, data=payload, timeout=10)
    res.raise_for_status()
    print(f"[OK] Pushover通知を送信: {streamer_name}")


def main():
    state = load_state()
    for screen_id in TARGET_USERS:
        try:
            live, name = is_user_live(screen_id)
        except Exception as e:
            print(f"[ERROR] {screen_id} のチェックに失敗: {e}", file=sys.stderr)
            continue

        was_live = state.get(screen_id, False)

        if live and not was_live:
            print(f"[LIVE START] {name}（{screen_id}）")
            send_pushover_alarm(name, screen_id)
        elif not live and was_live:
            print(f"[LIVE END] {name}（{screen_id}）")
        else:
            print(f"[no change] {name}（{screen_id}）live={live}")

        state[screen_id] = live

    save_state(state)


if __name__ == "__main__":
    main()
