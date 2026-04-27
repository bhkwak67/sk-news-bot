"""
뉴스 수집 모듈
- Google News RSS
- Naver 뉴스 검색 API
- SK이노베이션 공식 보도자료
"""

import os
import re
import feedparser
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime

KST = timezone(timedelta(hours=9))
QUERY = "SK이노베이션"
MAX_PER_SOURCE = 10  # 필터링 후 줄어드므로 넉넉하게 수집


def _is_relevant(title: str) -> bool:
    """SK이노베이션 관련 기사인지 확인 (제목 기준)"""
    return "SK이노베이션" in title


def _is_today(date_str: str) -> bool:
    """날짜 문자열이 오늘(KST 기준)인지 확인"""
    if not date_str:
        return True  # 날짜 없으면 일단 포함
    try:
        dt = parsedate_to_datetime(date_str).astimezone(KST)
        return dt.date() == datetime.now(KST).date()
    except Exception:
        return True


# ── 1. Google News RSS ───────────────────────────────────────────────────────

def fetch_google_news() -> list[dict]:
    url = (
        "https://news.google.com/rss/search"
        f"?q={requests.utils.quote(QUERY)}&hl=ko&gl=KR&ceid=KR:ko"
    )
    feed = feedparser.parse(url)
    results = []
    for entry in feed.entries[:MAX_PER_SOURCE]:
        published = entry.get("published", "")
        title = entry.get("title", "").strip()
        if not _is_today(published) or not _is_relevant(title):
            continue
        results.append({
            "title": title,
            "link": entry.get("link", ""),
            "source": "Google News",
        })
    return results


# ── 2. Naver 뉴스 API ────────────────────────────────────────────────────────

def fetch_naver_news() -> list[dict]:
    client_id = os.environ.get("NAVER_CLIENT_ID", "")
    client_secret = os.environ.get("NAVER_CLIENT_SECRET", "")
    if not client_id or not client_secret:
        print("[Naver] API 키 미설정 → 건너뜀")
        return []

    url = "https://openapi.naver.com/v1/search/news.json"
    headers = {
        "X-Naver-Client-Id": client_id,
        "X-Naver-Client-Secret": client_secret,
    }
    params = {"query": QUERY, "display": MAX_PER_SOURCE, "sort": "date"}
    resp = requests.get(url, headers=headers, params=params, timeout=10)
    resp.raise_for_status()

    results = []
    for item in resp.json().get("items", []):
        title = BeautifulSoup(item.get("title", ""), "html.parser").get_text()
        if not _is_today(item.get("pubDate", "")) or not _is_relevant(title):
            continue
        results.append({
            "title": title.strip(),
            "link": item.get("originallink") or item.get("link", ""),
            "source": "Naver 뉴스",
        })
    return results


# ── 3. SK이노베이션 공식 보도자료 ────────────────────────────────────────────

def fetch_sk_official() -> list[dict]:
    url = "https://www.skinnovation.com/kr/news/pressReleases.do"
    headers = {"User-Agent": "Mozilla/5.0 (compatible; NewsBot/1.0)"}
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
    except Exception as e:
        print(f"[SK공식] 요청 실패: {e}")
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    results = []

    # 보도자료 목록 파싱 (사이트 구조 변경 시 셀렉터 수정 필요)
    for item in soup.select(".board-list li, .press-item, article")[:MAX_PER_SOURCE]:
        a_tag = item.find("a")
        if not a_tag:
            continue
        title = a_tag.get_text(strip=True)
        href = a_tag.get("href", "")
        if href and not href.startswith("http"):
            href = "https://www.skinnovation.com" + href
        if title:
            results.append({"title": title, "link": href, "source": "SK이노베이션 공식"})

    return results


# ── 통합 수집 ────────────────────────────────────────────────────────────────

def fetch_all_news() -> list[dict]:
    all_items = []

    sources = [
        ("Google News",       fetch_google_news),
        ("Naver 뉴스",         fetch_naver_news),
        ("SK이노베이션 공식",  fetch_sk_official),
    ]

    for name, fn in sources:
        try:
            items = fn()
            print(f"[{name}] {len(items)}건 수집")
            all_items.extend(items)
        except Exception as e:
            print(f"[{name}] 수집 실패: {e}")

    # 중복 제거 (제목 기준)
    seen, unique = set(), []
    for item in all_items:
        key = re.sub(r"\s+", "", item["title"])  # 공백 제거 후 비교
        if key not in seen:
            seen.add(key)
            unique.append(item)

    print(f"최종 {len(unique)}건 (중복 제거 후)")
    return unique
