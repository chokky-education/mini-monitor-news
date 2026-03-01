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
    """Generate a beautiful static HTML page with an exciting dark mode design."""

    now = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

    def article_card(article: dict) -> str:
        title_escaped = html.escape(article["title"])
        source_escaped = html.escape(article["source"])
        desc_escaped = html.escape(article["description"]) if article["description"] else ""
        date_str = article["date"] if article["date"] else ""
        link = html.escape(article["link"])

        date_html = f'<span class="text-xs text-slate-400 font-medium tracking-wide">{date_str}</span>' if date_str else ""
        desc_html = f'<p class="text-slate-400 text-sm mt-3 line-clamp-2 leading-relaxed">{desc_escaped}</p>' if desc_escaped else ""

        return f"""
        <a href="{link}" target="_blank" rel="noopener noreferrer"
           class="block bg-slate-900 border border-slate-800 rounded-2xl p-6 hover:shadow-[0_0_30px_-5px_rgba(220,38,38,0.15)] hover:border-red-500/40 hover:bg-slate-800/80 transition-all duration-300 group cursor-pointer relative overflow-hidden">
            <div class="absolute top-0 left-0 w-1 h-full bg-gradient-to-b from-red-600 to-orange-600 opacity-0 group-hover:opacity-100 transition-opacity duration-300"></div>
            <div class="flex items-start justify-between gap-4">
                <h3 class="text-lg font-bold text-slate-100 group-hover:text-white transition-colors leading-snug flex-1 font-newsreader">
                    {title_escaped}
                </h3>
                <div class="bg-slate-800 p-2 rounded-full group-hover:bg-red-500/20 transition-colors">
                    <svg class="w-4 h-4 text-slate-400 group-hover:text-red-400 flex-shrink-0 transition-colors" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"/>
                    </svg>
                </div>
            </div>
            {desc_html}
            <div class="flex items-center justify-between gap-3 mt-5 pt-4 border-t border-slate-800/50">
                <span class="inline-flex items-center px-3 py-1 rounded-full text-xs font-bold bg-slate-800 text-red-400 border border-red-500/20">
                    <span class="w-1.5 h-1.5 rounded-full bg-red-500 mr-1.5 animate-pulse"></span>
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
    max_count = max(source_counts.values()) if source_counts else 1
    top_sources = source_counts.most_common(5)
    
    chart_html = ""
    colors = ["from-red-600 to-red-400", "from-orange-600 to-orange-400", "from-amber-600 to-amber-400", "from-rose-600 to-rose-400", "from-red-700 to-orange-500"]
    for i, (source, count) in enumerate(top_sources):
        width_percent = (count / max_count) * 100
        color = colors[i % len(colors)]
        chart_html += f"""
        <div class="mb-4 group">
            <div class="flex justify-between text-sm mb-1.5">
                <span class="font-medium text-slate-300 group-hover:text-white transition-colors">{html.escape(source)}</span>
                <span class="text-red-400 font-bold">{count} <span class="text-slate-500 font-normal">ข่าว</span></span>
            </div>
            <div class="w-full bg-slate-800 rounded-full h-2 overflow-hidden border border-slate-700">
                <div class="h-full rounded-full bg-gradient-to-r {color} relative shadow-[0_0_10px_rgba(220,38,38,0.5)]" style="width: {width_percent}%">
                    <div class="absolute inset-0 bg-white/20 w-full h-full animate-[shimmer_2s_infinite] -translate-x-full"></div>
                </div>
            </div>
        </div>
        """
    
    dashboard_section = f"""
    <div class="max-w-7xl mx-auto px-4 py-8 relative z-10">
        <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <!-- Source Chart Widget -->
            <div class="lg:col-span-2 bg-slate-900/80 backdrop-blur-md border border-slate-800 rounded-2xl p-8 shadow-2xl relative overflow-hidden">
                <div class="absolute top-0 right-0 w-64 h-64 bg-red-600/5 rounded-full blur-3xl -mr-20 -mt-20"></div>
                <div class="flex items-center gap-3 mb-8 relative z-10">
                    <div class="p-2.5 bg-red-500/10 rounded-xl border border-red-500/20">
                        <svg class="w-6 h-6 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"></path>
                        </svg>
                    </div>
                    <h2 class="text-xl font-bold text-white tracking-tight">Active News Sources</h2>
                </div>
                <div class="relative z-10">
                    {chart_html}
                </div>
            </div>
            
            <!-- Quick Stats Widget -->
            <div class="bg-gradient-to-br from-slate-900 to-slate-950 border border-slate-800 rounded-2xl p-8 shadow-2xl flex flex-col justify-center relative overflow-hidden">
                <div class="absolute inset-0 bg-[url('https://www.transparenttextures.com/patterns/cubes.png')] opacity-30 mix-blend-overlay"></div>
                
                <div class="text-center relative z-10 mb-8">
                    <div class="inline-flex items-center px-3 py-1 rounded-full bg-red-500/10 text-red-500 border border-red-500/20 text-xs font-bold tracking-widest uppercase mb-4">
                        <span class="w-1.5 h-1.5 rounded-full bg-red-500 mr-2 animate-ping"></span>
                        Live Coverage
                    </div>
                    <div class="text-7xl font-black text-transparent bg-clip-text bg-gradient-to-br from-white via-red-100 to-slate-400 tracking-tighter mb-2 drop-shadow-lg">{total}</div>
                    <div class="text-sm font-semibold text-slate-500 uppercase tracking-[0.2em]">Total Reports</div>
                </div>
                
                <div class="grid grid-cols-2 gap-4 mt-auto border-t border-slate-800 pt-6 relative z-10">
                    <div class="text-center group">
                        <div class="text-3xl font-bold text-white group-hover:text-red-400 transition-colors mb-1">{en_count}</div>
                        <div class="text-xs font-semibold uppercase tracking-wider text-slate-500">Global</div>
                    </div>
                    <div class="text-center border-l border-slate-800 group">
                        <div class="text-3xl font-bold text-white group-hover:text-red-400 transition-colors mb-1">{th_count}</div>
                        <div class="text-xs font-semibold uppercase tracking-wider text-slate-500">Thai</div>
                    </div>
                </div>
            </div>
        </div>
    </div>
    """

    no_en = '<div class="col-span-full py-12 text-center border-2 border-dashed border-slate-800 rounded-2xl"><p class="text-slate-500 font-medium">No English reports found</p></div>' if en_count == 0 else ""
    no_th = '<div class="col-span-full py-12 text-center border-2 border-dashed border-slate-800 rounded-2xl"><p class="text-slate-500 font-medium">No Thai reports found</p></div>' if th_count == 0 else ""

    return f"""<!DOCTYPE html>
<html lang="th" class="scroll-smooth">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>⚡ WAR MONITOR: US vs Iran</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&family=Newsreader:opsz,wght@6..72,500;6..72,600;6..72,700;6..72,800&family=Sarabun:wght@300;400;500;600;700&display=swap');
        
        :root {{
            color-scheme: dark;
        }}
        
        body {{ 
            font-family: 'Inter', 'Sarabun', sans-serif; 
            background-color: #020617; /* slate-950 */
            background-image: 
                radial-gradient(at 0% 0%, hsla(348,83%,47%,0.08) 0, transparent 50%), 
                radial-gradient(at 100% 0%, hsla(348,83%,47%,0.05) 0, transparent 50%);
            background-attachment: fixed;
        }}
        
        .font-newsreader {{
            font-family: 'Newsreader', serif;
        }}

        .line-clamp-2 {{
            display: -webkit-box;
            -webkit-line-clamp: 2;
            -webkit-box-orient: vertical;
            overflow: hidden;
        }}
        
        @keyframes shimmer {{
            100% {{ transform: translateX(100%); }}
        }}
        
        /* Custom scrollbar */
        ::-webkit-scrollbar {{
            width: 8px;
        }}
        ::-webkit-scrollbar-track {{
            background: #0f172a; 
        }}
        ::-webkit-scrollbar-thumb {{
            background: #334155; 
            border-radius: 4px;
        }}
        ::-webkit-scrollbar-thumb:hover {{
            background: #475569; 
        }}
    </style>
</head>
<body class="text-slate-300 min-h-screen antialiased selection:bg-red-500/30 selection:text-red-200">

    <!-- Header -->
    <header class="bg-slate-950/80 border-b border-white/5 sticky top-0 z-50 backdrop-blur-xl supports-[backdrop-filter]:bg-slate-950/60 transition-all">
        <div class="max-w-7xl mx-auto px-4 py-4">
            <div class="flex items-center justify-between flex-wrap gap-4">
                <div class="flex items-center gap-4">
                    <div class="relative flex items-center justify-center w-12 h-12 rounded-xl bg-red-600 shadow-[0_0_20px_rgba(220,38,38,0.4)]">
                        <svg class="w-6 h-6 text-white" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" d="M13 10V3L4 14h7v7l9-11h-7z"/>
                        </svg>
                    </div>
                    <div>
                        <h1 class="text-2xl font-black text-white tracking-tight flex items-center gap-2 uppercase">
                            MONITOR <span class="text-red-500 font-light">|</span> NEWS
                        </h1>
                        <p class="text-sm text-slate-400 mt-0.5 font-medium flex items-center gap-2">
                            TARGET: <span class="bg-slate-800 text-slate-200 px-2.5 py-0.5 rounded text-xs tracking-wider border border-slate-700">สงคราม สหรัฐ อิหร่าน</span>
                        </p>
                    </div>
                </div>
                <div class="text-right flex flex-col items-end">
                    <div class="flex items-center gap-2 text-xs font-bold tracking-widest text-slate-500 uppercase bg-slate-900 px-3 py-1.5 rounded-lg border border-slate-800">
                        <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"/>
                        </svg>
                        UPDATED: {now}
                    </div>
                </div>
            </div>
        </div>
    </header>

    <!-- Dashboard -->
    {dashboard_section}

    <!-- News Feed -->
    <main class="max-w-7xl mx-auto px-4 pb-20 mt-4">
        <!-- International News -->
        <section class="mb-16 relative">
            <div class="absolute -left-4 top-0 bottom-0 w-0.5 bg-gradient-to-b from-red-600 via-red-600/10 to-transparent hidden md:block"></div>
            <div class="flex items-end justify-between mb-8 pb-4 border-b border-slate-800/60">
                <div>
                    <div class="flex items-center gap-3 mb-2">
                        <div class="w-10 h-1 bg-red-600 rounded-full"></div>
                        <span class="text-red-500 font-bold tracking-widest text-xs uppercase">Global Intel</span>
                    </div>
                    <h2 class="text-3xl font-black text-white font-newsreader tracking-tight">International Feed</h2>
                </div>
                <div class="text-slate-500 font-medium text-sm hidden sm:block">Real-time Global Coverage</div>
            </div>
            <div class="grid gap-5 md:grid-cols-2 lg:grid-cols-3">
                {en_cards}
                {no_en}
            </div>
        </section>

        <!-- Thai News -->
        <section class="relative">
            <div class="absolute -left-4 top-0 bottom-0 w-0.5 bg-gradient-to-b from-orange-500 via-orange-500/10 to-transparent hidden md:block"></div>
            <div class="flex items-end justify-between mb-8 pb-4 border-b border-slate-800/60">
                <div>
                    <div class="flex items-center gap-3 mb-2">
                        <div class="w-10 h-1 bg-orange-500 rounded-full"></div>
                        <span class="text-orange-500 font-bold tracking-widest text-xs uppercase">Local Intel</span>
                    </div>
                    <h2 class="text-3xl font-black text-white font-newsreader tracking-tight">Thai Feed</h2>
                </div>
                <div class="text-slate-500 font-medium text-sm hidden sm:block">Coverage in Thailand</div>
            </div>
            <div class="grid gap-5 md:grid-cols-2 lg:grid-cols-3">
                {th_cards}
                {no_th}
            </div>
        </section>
    </main>

    <!-- Footer -->
    <footer class="bg-slate-950 border-t border-white/5 pt-12 pb-8 relative overflow-hidden">
        <div class="absolute top-0 left-1/2 -translate-x-1/2 w-1/2 h-px bg-gradient-to-r from-transparent via-red-500/50 to-transparent"></div>
        <div class="max-w-7xl mx-auto px-4 flex flex-col items-center">
            <div class="w-12 h-12 bg-slate-900 rounded-full flex items-center justify-center border border-slate-800 mb-6 shadow-[0_0_15px_rgba(0,0,0,0.5)]">
                <svg class="w-5 h-5 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"/>
                </svg>
            </div>
            <p class="text-slate-400 font-medium mb-3">MINI MONITOR NEWS — TACTICAL DASHBOARD</p>
            <p class="text-sm text-slate-500">
                Execute <code class="font-mono text-xs bg-slate-900 border border-slate-800 text-red-400 px-2 py-1 rounded-md mx-1 shadow-inner">python scraper.py</code> to refresh data stream
            </p>
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
