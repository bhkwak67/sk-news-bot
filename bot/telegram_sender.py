"""
텔레그램 메시지 발송 모듈
"""

import os
import requests
from datetime import datetime, timezone, timedelta

KST = timezone(timedelta(hours=9))
TELEGRAM_API = "https://api.telegram.org"


def _get_credentials() -> tuple[str, str]:
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")
    if not token:
        raise EnvironmentError("TELEGRAM_BOT_TOKEN 환경변수가 설정되지 않았습니다.")
    if not chat_id:
        raise EnvironmentError("TELEGRAM_CHAT_ID 환경변수가 설정되지 않았습니다.")
    return token, chat_id


def _build_message(news_items: list[dict]) -> str:
    yesterday = (datetime.now(KST) - timedelta(days=1)).strftime("%Y년 %m월 %d일 (%a)")
    lines = [f"📰 *SK이노베이션 뉴스* — {yesterday}\n"]

    if not news_items:
        lines.append("오늘은 새로운 뉴스가 없습니다.")
        return "\n".join(lines)

    # 출처별 그룹핑
    grouped: dict[str, list[dict]] = {}
    for item in news_items:
        grouped.setdefault(item["source"], []).append(item)

    source_emoji = {
        "Google News": "🔍",
        "Naver 뉴스": "🟢",
        "SK이노베이션 공식": "🏢",
    }

    for source, items in grouped.items():
        emoji = source_emoji.get(source, "📌")
        lines.append(f"\n{emoji} *{source}*")
        for item in items:
            title = item["title"].replace("*", "").replace("[", "").replace("]", "")
            link = item["link"]
            lines.append(f"• [{title}]({link})")

    lines.append(f"\n_발송 시각: {datetime.now(KST).strftime('%H:%M')} KST_")
    return "\n".join(lines)


def send_news(news_items: list[dict]) -> None:
    token, chat_id = _get_credentials()
    message = _build_message(news_items)

    # 메시지가 4096자를 초과하면 분할 발송
    chunks = [message[i:i+4096] for i in range(0, len(message), 4096)]
    url = f"{TELEGRAM_API}/bot{token}/sendMessage"

    for chunk in chunks:
        resp = requests.post(
            url,
            json={
                "chat_id": chat_id,
                "text": chunk,
                "parse_mode": "Markdown",
                "disable_web_page_preview": True,
            },
            timeout=10,
        )
        data = resp.json()
        if not data.get("ok"):
            raise RuntimeError(f"텔레그램 발송 실패: {data.get('description')}")

    print(f"텔레그램 발송 완료 ({len(news_items)}건)")
