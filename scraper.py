#!/usr/bin/env python3
"""
Mini Monitor News — สงคราม สหรัฐ อิหร่าน
Scrape ข่าวจากแหล่งข่าวทั่วโลก แล้ว generate เป็นหน้า Static HTML
"""

import feedparser
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from urllib.parse import quote
from collections import Counter
import html
import re
import time

# ─── Configuration ───────────────────────────────────────────────────────────

SEARCH_QUERIES = {
    "en": [
        "US Iran war",
        "United States Iran conflict",
        "Iran US military",
    ],
    "th": [
        "สงคราม สหรัฐ อิหร่าน",
        "สหรัฐ อิหร่าน",
    ],
}

# Google News RSS search URL template
GOOGLE_NEWS_RSS = "https://news.google.com/rss/search?q={query}&hl={hl}&gl={gl}&ceid={ceid}"

# Direct RSS feeds (Middle East / World sections)
DIRECT_FEEDS = [
    {
        "name": "BBC News - Middle East",
        "url": "https://feeds.bbci.co.uk/news/world/middle_east/rss.xml",
        "lang": "en",
        "keywords": ["iran", "us ", "united states", "american", "tehran", "pentagon", "military"],
    },

    {
        "name": "Al Jazeera - Middle East",
        "url": "https://www.aljazeera.com/xml/rss/all.xml",
        "lang": "en",
        "keywords": ["iran", "us ", "united states", "american", "tehran", "military"],
    },
    {
        "name": "THE STANDARD - World",
        "url": "https://thestandard.co/category/news/world/feed/",
        "lang": "th",
        "keywords": ["สหรัฐ", "อิหร่าน", "iran", "สงคราม", "อิสราเอล"],
    },
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

MAX_ARTICLES_PER_SOURCE = 15
MAX_TOTAL_ARTICLES = 60

# ─── Scraping Functions ──────────────────────────────────────────────────────


def fetch_feed(url: str) -> feedparser.FeedParserDict:
    """Fetch RSS feed using requests with proper headers, then parse with feedparser."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        return feedparser.parse(resp.text)
    except Exception as e:
        print(f"  ⚠ Error fetching feed: {e}")
        return feedparser.FeedParserDict(entries=[])


def fetch_google_news(query: str, lang: str = "en") -> list[dict]:
    """Fetch news from Google News RSS search."""
    articles = []

    if lang == "th":
        url = GOOGLE_NEWS_RSS.format(
            query=quote(query), hl="th", gl="TH", ceid="TH:th"
        )
    else:
        url = GOOGLE_NEWS_RSS.format(
            query=quote(query), hl="en-US", gl="US", ceid="US:en"
        )

    try:
        feed = fetch_feed(url)
        for entry in feed.entries[:MAX_ARTICLES_PER_SOURCE]:
            # Extract source from title (Google News format: "Title - Source")
            title = entry.get("title", "")
            source = "Google News"
            if " - " in title:
                parts = title.rsplit(" - ", 1)
                title = parts[0].strip()
                source = parts[1].strip()

            pub_date = ""
            if hasattr(entry, "published_parsed") and entry.published_parsed:
                pub_date = time.strftime("%Y-%m-%d %H:%M", entry.published_parsed)

            articles.append({
                "title": html.unescape(title),
                "link": entry.get("link", ""),
                "source": source,
                "date": pub_date,
                "lang": lang,
                "description": html.unescape(
                    BeautifulSoup(entry.get("description", ""), "html.parser").get_text()[:200]
                ),
            })
    except Exception as e:
        print(f"  ⚠ Error fetching Google News ({query}): {e}")

    return articles


def fetch_direct_feed(feed_config: dict) -> list[dict]:
    """Fetch and filter articles from a direct RSS feed."""
    articles = []
    name = feed_config["name"]
    url = feed_config["url"]
    lang = feed_config["lang"]
    keywords = feed_config["keywords"]

    try:
        feed = fetch_feed(url)
        for entry in feed.entries:
            title = html.unescape(entry.get("title", ""))
            description = html.unescape(
                BeautifulSoup(entry.get("description", entry.get("summary", "")), "html.parser").get_text()[:200]
            )
            text = (title + " " + description).lower()

            # Filter by keywords
            if any(kw in text for kw in keywords):
                pub_date = ""
                if hasattr(entry, "published_parsed") and entry.published_parsed:
                    pub_date = time.strftime("%Y-%m-%d %H:%M", entry.published_parsed)

                articles.append({
                    "title": title,
                    "link": entry.get("link", ""),
                    "source": name,
                    "date": pub_date,
                    "lang": lang,
                    "description": description,
                })

                if len(articles) >= MAX_ARTICLES_PER_SOURCE:
                    break
    except Exception as e:
        print(f"  ⚠ Error fetching {name}: {e}")

    return articles


def scrape_thairath() -> list[dict]:
    """Scrape news from Thairath related to US-Iran."""
    articles = []
    keywords = ["สหรัฐ", "อิหร่าน", "iran", "สงคราม"]
    url = "https://www.thairath.co.th/news/foreign"

    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        # Find article links
        for a_tag in soup.find_all("a", href=True):
            title_text = a_tag.get_text(strip=True)
            if len(title_text) < 10:
                continue

            text_lower = title_text.lower()
            if any(kw in text_lower for kw in keywords):
                link = a_tag["href"]
                if not link.startswith("http"):
                    link = "https://www.thairath.co.th" + link

                articles.append({
                    "title": title_text,
                    "link": link,
                    "source": "ไทยรัฐ",
                    "date": "",
                    "lang": "th",
                    "description": "",
                })

                if len(articles) >= MAX_ARTICLES_PER_SOURCE:
                    break
    except Exception as e:
        print(f"  ⚠ Error scraping Thairath: {e}")

    return articles





# ─── Deduplication ───────────────────────────────────────────────────────────


def deduplicate(articles: list[dict]) -> list[dict]:
    """Remove duplicate articles based on title similarity."""
    seen_titles = set()
    unique = []

    for article in articles:
        # Normalize title for comparison
        normalized = re.sub(r"[^\w\s]", "", article["title"].lower().strip())
        normalized = re.sub(r"\s+", " ", normalized)

        # Simple dedup: skip if first 50 chars match
        key = normalized[:50]
        if key not in seen_titles:
            seen_titles.add(key)
            unique.append(article)

    return unique


# ─── HTML Generation ─────────────────────────────────────────────────────────


def generate_html(articles_en: list[dict], articles_th: list[dict]) -> str:
    """Generate a beautiful static HTML page."""

    now = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

    def article_card(article: dict) -> str:
        title_escaped = html.escape(article["title"])
        source_escaped = html.escape(article["source"])
        desc_escaped = html.escape(article["description"]) if article["description"] else ""
        date_str = article["date"] if article["date"] else ""
        link = html.escape(article["link"])

        date_html = f'<span class="text-sm text-gray-400">{date_str}</span>' if date_str else ""
        desc_html = f'<p class="text-gray-500 text-sm mt-2 line-clamp-2">{desc_escaped}</p>' if desc_escaped else ""

        return f"""
        <a href="{link}" target="_blank" rel="noopener noreferrer"
           class="block bg-white border border-gray-200 rounded-xl p-5 hover:shadow-lg hover:border-blue-300 transition-all duration-200 group">
            <div class="flex items-start justify-between gap-3">
                <h3 class="text-base font-semibold text-gray-800 group-hover:text-blue-600 transition-colors leading-snug flex-1">
                    {title_escaped}
                </h3>
                <svg class="w-4 h-4 text-gray-300 group-hover:text-blue-500 flex-shrink-0 mt-1 transition-colors" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"/>
                </svg>
            </div>
            {desc_html}
            <div class="flex items-center gap-3 mt-3">
                <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-50 text-blue-700">
                    {source_escaped}
                </span>
                {date_html}
            </div>
        </a>
        """

    en_cards = "\n".join(article_card(a) for a in articles_en)
    th_cards = "\n".join(article_card(a) for a in articles_th)

    en_count = len(articles_en)
    th_count = len(articles_th)
    total = en_count + th_count
    
    # --- Generate Chart Sources ---
    all_articles = articles_en + articles_th
    source_counts = Counter([a["source"] for a in all_articles])
    # หายอดสูงสุดเพื่อทำความยาวของกราฟขีดสุดที่ 100%
    max_count = max(source_counts.values()) if source_counts else 1
    top_sources = source_counts.most_common(5) # เอาแค่ 5 อันดับแรก
    
    chart_html = ""
    for source, count in top_sources:
        width_percent = (count / max_count) * 100
        chart_html += f"""
        <div class="mb-3">
            <div class="flex justify-between text-sm mb-1">
                <span class="font-medium text-gray-700">{html.escape(source)}</span>
                <span class="text-gray-500 font-semibold">{count} ข่าว</span>
            </div>
            <div class="w-full bg-gray-200 rounded-full h-2.5">
                <div class="bg-blue-600 h-2.5 rounded-full" style="width: {width_percent}%"></div>
            </div>
        </div>
        """
    
    dashboard_section = f"""
    <div class="max-w-6xl mx-auto px-4 py-6">
        <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
            <!-- Source Chart Widget -->
            <div class="bg-white border border-gray-200 rounded-xl p-6 shadow-sm">
                <div class="flex items-center gap-2 mb-4">
                    <svg class="w-5 h-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"></path>
                    </svg>
                    <h2 class="text-lg font-semibold text-gray-800">สำนักข่าวที่รายงานมากที่สุด</h2>
                </div>
                <div>
                    {chart_html}
                </div>
            </div>
            
            <!-- Quick Stats Widget -->
            <div class="bg-white border border-gray-200 rounded-xl p-6 shadow-sm flex flex-col justify-center">
                <div class="text-center">
                    <div class="text-4xl font-bold text-gray-900 mb-2">{total}</div>
                    <div class="text-sm font-medium text-gray-500 uppercase tracking-wider">จำนวนข่าวทั้งหมดที่พบ</div>
                </div>
                <div class="grid grid-cols-2 gap-4 mt-6 border-t border-gray-100 pt-6">
                    <div class="text-center">
                        <div class="text-2xl font-semibold text-blue-600 mb-1">{en_count}</div>
                        <div class="text-xs text-gray-500">ข่าวต่างประเทศ</div>
                    </div>
                    <div class="text-center">
                        <div class="text-2xl font-semibold text-green-600 mb-1">{th_count}</div>
                        <div class="text-xs text-gray-500">ข่าวประเทศไทย</div>
                    </div>
                </div>
            </div>
        </div>
    </div>
    """

    no_en = '<p class="text-gray-400 text-center py-8">ไม่พบข่าวภาษาอังกฤษที่เกี่ยวข้อง</p>' if en_count == 0 else ""
    no_th = '<p class="text-gray-400 text-center py-8">ไม่พบข่าวภาษาไทยที่เกี่ยวข้อง</p>' if th_count == 0 else ""

    return f"""<!DOCTYPE html>
<html lang="th">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Mini Monitor News — สงคราม สหรัฐ อิหร่าน</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Sarabun:wght@300;400;500;600;700&display=swap');
        body {{ font-family: 'Inter', 'Sarabun', sans-serif; }}
        .line-clamp-2 {{
            display: -webkit-box;
            -webkit-line-clamp: 2;
            -webkit-box-orient: vertical;
            overflow: hidden;
        }}
    </style>
</head>
<body class="bg-gray-50 min-h-screen">

    <!-- Header -->
    <header class="bg-white border-b border-gray-200 sticky top-0 z-50">
        <div class="max-w-6xl mx-auto px-4 py-4">
            <div class="flex items-center justify-between flex-wrap gap-3">
                <div>
                    <h1 class="text-2xl font-bold text-gray-900 flex items-center gap-2">
                        <svg class="w-7 h-7 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 20H5a2 2 0 01-2-2V6a2 2 0 012-2h10a2 2 0 012 2v1m2 13a2 2 0 01-2-2V7m2 13a2 2 0 002-2V9a2 2 0 00-2-2h-2m-4-3H9M7 16h6M7 8h6v4H7V8z"/>
                        </svg>
                        Mini Monitor News
                    </h1>
                    <p class="text-sm text-gray-500 mt-1">
                        คำค้น: <span class="font-medium text-gray-700">สงคราม สหรัฐ อิหร่าน</span>
                    </p>
                </div>
                <div class="text-right">
                    <div class="flex items-center gap-2 text-sm text-gray-500">
                        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"/>
                        </svg>
                        อัปเดตล่าสุด: {now}
                    </div>
                    <div class="text-sm text-gray-400 mt-1">
                        พบข่าวทั้งหมด {total} รายการ
                    </div>
                </div>
            </div>
        </div>
    </header>

    <!-- Dashboard -->
    {dashboard_section}

    <!-- International News -->
    <main class="max-w-6xl mx-auto px-4 pb-12">
        <section class="mb-10">
            <div class="flex items-center gap-2 mb-4">
                <span class="w-2 h-2 bg-blue-500 rounded-full"></span>
                <h2 class="text-lg font-semibold text-gray-800">ข่าวสากล (International)</h2>
            </div>
            <div class="grid gap-3 md:grid-cols-2">
                {en_cards}
                {no_en}
            </div>
        </section>

        <!-- Thai News -->
        <section>
            <div class="flex items-center gap-2 mb-4">
                <span class="w-2 h-2 bg-green-500 rounded-full"></span>
                <h2 class="text-lg font-semibold text-gray-800">ข่าวไทย (Thai)</h2>
            </div>
            <div class="grid gap-3 md:grid-cols-2">
                {th_cards}
                {no_th}
            </div>
        </section>
    </main>

    <!-- Footer -->
    <footer class="bg-white border-t border-gray-200 py-6">
        <div class="max-w-6xl mx-auto px-4 text-center text-sm text-gray-400">
            <p>Mini Monitor News — Auto-generated by Python scraper</p>
            <p class="mt-1">รัน <code class="bg-gray-100 px-2 py-0.5 rounded text-gray-600">python scraper.py</code> เพื่ออัปเดตข่าว</p>
        </div>
    </footer>

</body>
</html>"""


# ─── Main ────────────────────────────────────────────────────────────────────


def main():
    print("=" * 60)
    print("  Mini Monitor News — สงคราม สหรัฐ อิหร่าน")
    print("=" * 60)
    print()

    all_en = []
    all_th = []

    # 1) Google News — English queries
    for query in SEARCH_QUERIES["en"]:
        print(f"📡 Google News (EN): {query}")
        articles = fetch_google_news(query, lang="en")
        print(f"   → พบ {len(articles)} ข่าว")
        all_en.extend(articles)
        time.sleep(1)

    # 2) Google News — Thai queries
    for query in SEARCH_QUERIES["th"]:
        print(f"📡 Google News (TH): {query}")
        articles = fetch_google_news(query, lang="th")
        print(f"   → พบ {len(articles)} ข่าว")
        all_th.extend(articles)
        time.sleep(1)

    # 3) Direct RSS feeds
    for feed_config in DIRECT_FEEDS:
        print(f"📡 RSS: {feed_config['name']}")
        articles = fetch_direct_feed(feed_config)
        print(f"   → พบ {len(articles)} ข่าวที่เกี่ยวข้อง")
        if feed_config.get("lang") == "th":
            all_th.extend(articles)
        else:
            all_en.extend(articles)
        time.sleep(0.5)

    # 4) Thai news scraping
    print("📡 Scraping: ไทยรัฐ")
    articles = scrape_thairath()
    print(f"   → พบ {len(articles)} ข่าว")
    all_th.extend(articles)


    # 5) Deduplicate
    print()
    print("🔄 กำลังลบข่าวซ้ำ...")
    all_en = deduplicate(all_en)
    all_th = deduplicate(all_th)

    # Limit total
    all_en = all_en[:MAX_TOTAL_ARTICLES]
    all_th = all_th[:MAX_TOTAL_ARTICLES]

    print(f"   EN: {len(all_en)} ข่าว | TH: {len(all_th)} ข่าว")

    # 6) Generate HTML
    print()
    print("📄 กำลังสร้างหน้า HTML...")
    html_content = generate_html(all_en, all_th)

    output_path = "index.html"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    print(f"✅ สร้างไฟล์ {output_path} สำเร็จ!")
    print(f"   เปิดดูได้ด้วย: open {output_path}")
    print()


if __name__ == "__main__":
    main()
