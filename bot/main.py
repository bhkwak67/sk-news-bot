"""
SK이노베이션 뉴스 봇 진입점
"""

from news_fetcher import fetch_all_news
from telegram_sender import send_news


def main():
    print("=== SK이노베이션 뉴스 봇 시작 ===")
    news_items = fetch_all_news()
    send_news(news_items)
    print("=== 완료 ===")


if __name__ == "__main__":
    main()
