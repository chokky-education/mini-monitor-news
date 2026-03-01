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

import json
from collections import defaultdict

def generate_html(articles_en: list[dict], articles_th: list[dict]) -> str:
    """Generate a beautiful static HTML page with an exciting dark mode design."""

    now = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

    def article_card(article: dict) -> str:
        title_escaped = html.escape(article["title"])
        source_escaped = html.escape(article["source"])
        desc_escaped = html.escape(article["description"]) if article["description"] else ""
        date_str = article["date"] if article["date"] else ""
        link = html.escape(article["link"])
        lang = article.get("lang", "en")

        date_html = f'<span class="text-xs dark:text-slate-400 text-slate-500 font-medium tracking-wide">{date_str}</span>' if date_str else ""
        desc_html = f'<p class="dark:text-slate-400 text-slate-600 text-sm mt-3 line-clamp-2 leading-relaxed">{desc_escaped}</p>' if desc_escaped else ""

        return f"""
        <article class="article-card block dark:bg-slate-900 bg-white border dark:border-slate-800 border-slate-200 rounded-2xl p-6 hover:shadow-[0_0_30px_-5px_rgba(220,38,38,0.15)] dark:hover:border-red-500/40 hover:border-red-500/40 dark:hover:bg-slate-800/80 hover:bg-slate-50 transition-all duration-300 group relative overflow-hidden"
           data-source="{source_escaped}" data-lang="{lang}" data-date="{date_str}" data-title="{title_escaped.lower()}">
            <a href="{link}" target="_blank" rel="noopener noreferrer" class="absolute inset-0 z-10"></a>
            <div class="absolute top-0 left-0 w-1 h-full bg-gradient-to-b from-red-600 to-orange-600 opacity-0 group-hover:opacity-100 transition-opacity duration-300"></div>
            <div class="flex items-start justify-between gap-4 relative z-20 pointer-events-none">
                <h3 class="text-lg font-bold dark:text-slate-100 text-slate-800 group-hover:text-red-600 dark:group-hover:text-white transition-colors leading-snug flex-1 font-newsreader">
                    {title_escaped}
                </h3>
                <div class="dark:bg-slate-800 bg-slate-100 p-2 rounded-full group-hover:bg-red-500/20 dark:group-hover:bg-red-500/20 transition-colors">
                    <svg class="w-4 h-4 dark:text-slate-400 text-slate-500 group-hover:text-red-600 dark:group-hover:text-red-400 flex-shrink-0 transition-colors" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"/>
                    </svg>
                </div>
            </div>
            <div class="relative z-20 pointer-events-none">
                {desc_html}
            </div>
            <div class="flex items-center justify-between gap-3 mt-5 pt-4 border-t dark:border-slate-800/50 border-slate-200 relative z-20 pointer-events-none">
                <span class="inline-flex items-center px-3 py-1 rounded-full text-xs font-bold dark:bg-slate-800 bg-slate-100 dark:text-red-400 text-red-600 border dark:border-red-500/20 border-red-500/20">
                    <span class="w-1.5 h-1.5 rounded-full bg-red-500 mr-1.5 animate-pulse"></span>
                    {source_escaped}
                </span>
                {date_html}
            </div>
        </article>
        """

    en_cards = "\n".join(article_card(a) for a in articles_en)
    th_cards = "\n".join(article_card(a) for a in articles_th)

    en_count = len(articles_en)
    th_count = len(articles_th)
    total = en_count + th_count
    
    # --- Generate Data for Chart & Filters ---
    all_articles = articles_en + articles_th
    
    # Filter sources
    unique_sources = sorted(list(set(a["source"] for a in all_articles)))
    source_options = "\n".join(f'<option value="{html.escape(s)}">{html.escape(s)}</option>' for s in unique_sources)

    # Chart data (Trend over time)
    dates_count = defaultdict(int)
    for a in all_articles:
        if a["date"]:
            # extract string matching YYYY-MM-DD
            d = a["date"].split(" ")[0]
            dates_count[d] += 1
    
    if not dates_count:
        dates_count["N/A"] = total

    sorted_dates = sorted(dates_count.keys())
    date_labels = json.dumps(sorted_dates)
    date_counts = json.dumps([dates_count[d] for d in sorted_dates])
    
    dashboard_section = f"""
    <div class="max-w-7xl mx-auto px-4 py-8 relative z-10">
        <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <!-- Source Chart Widget -->
            <div class="lg:col-span-2 dark:bg-slate-900/80 bg-white backdrop-blur-md border dark:border-slate-800 border-slate-200 rounded-2xl p-8 shadow-xl relative overflow-hidden">
                <div class="absolute top-0 right-0 w-64 h-64 bg-red-600/5 rounded-full blur-3xl -mr-20 -mt-20"></div>
                <div class="flex items-center gap-3 mb-8 relative z-10">
                    <div class="p-2.5 bg-red-500/10 rounded-xl border border-red-500/20">
                        <svg class="w-6 h-6 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 12l3-3 3 3 4-4M8 21l4-4 4 4M3 4h18M4 4h16v12a1 1 0 01-1 1H5a1 1 0 01-1-1V4z"></path>
                        </svg>
                    </div>
                    <h2 class="text-xl font-bold dark:text-white text-slate-800 tracking-tight">Timeline & Trend</h2>
                </div>
                <div class="relative z-10 w-full h-48">
                    <canvas id="trendChart"></canvas>
                </div>
            </div>
            
            <!-- Quick Stats Widget -->
            <div class="bg-gradient-to-br dark:from-slate-900 dark:to-slate-950 from-slate-100 to-slate-200 border dark:border-slate-800 border-slate-300 rounded-2xl p-8 shadow-xl flex flex-col justify-center relative overflow-hidden">
                <div class="absolute inset-0 bg-[url('https://www.transparenttextures.com/patterns/cubes.png')] opacity-30 mix-blend-overlay"></div>
                
                <div class="text-center relative z-10 mb-8">
                    <div class="inline-flex items-center px-3 py-1 rounded-full bg-red-500/10 text-red-600 dark:text-red-500 border border-red-500/20 text-xs font-bold tracking-widest uppercase mb-4">
                        <span class="w-1.5 h-1.5 rounded-full bg-red-500 mr-2 animate-ping"></span>
                        Live Coverage
                    </div>
                    <div class="text-7xl font-black text-transparent bg-clip-text bg-gradient-to-br dark:from-white dark:via-red-100 dark:to-slate-400 from-slate-800 via-red-800 to-slate-600 tracking-tighter mb-2 drop-shadow-lg">{total}</div>
                    <div class="text-sm font-semibold dark:text-slate-500 text-slate-600 uppercase tracking-[0.2em]">Total Reports</div>
                </div>
                
                <div class="grid grid-cols-2 gap-4 mt-auto border-t dark:border-slate-800 border-slate-300 pt-6 relative z-10">
                    <div class="text-center group">
                        <div class="text-3xl font-bold dark:text-white text-slate-800 group-hover:text-red-500 dark:group-hover:text-red-400 transition-colors mb-1">{en_count}</div>
                        <div class="text-xs font-semibold uppercase tracking-wider dark:text-slate-500 text-slate-600">Global</div>
                    </div>
                    <div class="text-center border-l dark:border-slate-800 border-slate-300 group">
                        <div class="text-3xl font-bold dark:text-white text-slate-800 group-hover:text-red-500 dark:group-hover:text-red-400 transition-colors mb-1">{th_count}</div>
                        <div class="text-xs font-semibold uppercase tracking-wider dark:text-slate-500 text-slate-600">Thai</div>
                    </div>
                </div>
            </div>
        </div>
    </div>
    
    <!-- Filters & Search -->
    <div class="max-w-7xl mx-auto px-4 mt-4 relative z-10">
        <div class="dark:bg-slate-900/80 bg-white/80 backdrop-blur-md border dark:border-slate-800 border-slate-200 rounded-2xl p-4 shadow-lg flex flex-col md:flex-row gap-4 items-center justify-between">
            <div class="w-full md:flex-1 relative">
                <div class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                    <svg class="w-5 h-5 dark:text-slate-500 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"></path></svg>
                </div>
                <input type="text" id="searchInput" placeholder="ค้นหาหัวข้อข่าว..." class="w-full pl-10 pr-4 py-2.5 rounded-xl dark:bg-slate-950 bg-slate-50 border border-slate-200 dark:border-slate-800 focus:border-red-500 dark:focus:border-red-500 focus:ring-1 focus:ring-red-500 dark:text-white text-slate-900 transition-colors outline-none">
            </div>
            <div class="w-full md:w-auto flex gap-3 flex-wrap sm:flex-nowrap">
                <div class="flex-1 sm:flex-none">
                    <select id="sourceFilter" class="w-full py-2.5 pl-4 pr-8 rounded-xl dark:bg-slate-950 bg-slate-50 border border-slate-200 dark:border-slate-800 focus:border-red-500 focus:ring-1 focus:ring-red-500 dark:text-white text-slate-900 outline-none appearance-none cursor-pointer">
                        <option value="all">ทุกสำนักข่าว</option>
                        {source_options}
                    </select>
                </div>
                <div class="flex-1 sm:flex-none">
                    <select id="langFilter" class="w-full py-2.5 pl-4 pr-8 rounded-xl dark:bg-slate-950 bg-slate-50 border border-slate-200 dark:border-slate-800 focus:border-red-500 focus:ring-1 focus:ring-red-500 dark:text-white text-slate-900 outline-none appearance-none cursor-pointer">
                        <option value="all">ทุกภาษา</option>
                        <option value="th">ภาษาไทย</option>
                        <option value="en">English</option>
                    </select>
                </div>
                <div class="flex-1 sm:flex-none">
                    <input type="date" id="dateFilter" class="w-full py-2.5 px-4 rounded-xl dark:bg-slate-950 bg-slate-50 border border-slate-200 dark:border-slate-800 focus:border-red-500 focus:ring-1 focus:ring-red-500 dark:text-white text-slate-900 outline-none cursor-pointer">
                </div>
            </div>
        </div>
    </div>
    """

    no_en = '<div class="col-span-full py-12 text-center border-2 border-dashed dark:border-slate-800 border-slate-300 rounded-2xl" id="no-en-msg"><p class="dark:text-slate-500 text-slate-400 font-medium">No English reports found</p></div>'
    no_th = '<div class="col-span-full py-12 text-center border-2 border-dashed dark:border-slate-800 border-slate-300 rounded-2xl" id="no-th-msg"><p class="dark:text-slate-500 text-slate-400 font-medium">No Thai reports found</p></div>'

    return f"""<!DOCTYPE html>
<html lang="th" class="scroll-smooth dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>⚡ WAR MONITOR: US vs Iran</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script>
        tailwind.config = {{
            darkMode: 'class',
        }}
    </script>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&family=Newsreader:opsz,wght@6..72,500;6..72,600;6..72,700;6..72,800&family=Sarabun:wght@300;400;500;600;700&display=swap');
        
        body {{ 
            font-family: 'Inter', 'Sarabun', sans-serif; 
        }}
        .dark body {{
            background-color: #020617; /* slate-950 */
            background-image: 
                radial-gradient(at 0% 0%, hsla(348,83%,47%,0.08) 0, transparent 50%), 
                radial-gradient(at 100% 0%, hsla(348,83%,47%,0.05) 0, transparent 50%);
            background-attachment: fixed;
            color: #cbd5e1; /* slate-300 */
        }}
        body {{
            background-color: #f8fafc; /* slate-50 */
            background-image: 
                radial-gradient(at 0% 0%, hsla(348,83%,47%,0.05) 0, transparent 50%), 
                radial-gradient(at 100% 0%, hsla(348,83%,47%,0.03) 0, transparent 50%);
            background-attachment: fixed;
            color: #334155; /* slate-700 */
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
            background: #f1f5f9; 
        }}
        .dark ::-webkit-scrollbar-track {{
            background: #0f172a; 
        }}
        ::-webkit-scrollbar-thumb {{
            background: #cbd5e1; 
            border-radius: 4px;
        }}
        .dark ::-webkit-scrollbar-thumb {{
            background: #334155; 
        }}
        ::-webkit-scrollbar-thumb:hover {{
            background: #94a3b8; 
        }}
        .dark ::-webkit-scrollbar-thumb:hover {{
            background: #475569; 
        }}
    </style>
</head>
<body class="min-h-screen antialiased selection:bg-red-500/30 selection:text-red-800 dark:selection:text-red-200 transition-colors duration-300">

    <!-- Header -->
    <header class="dark:bg-slate-950/80 bg-white/80 border-b dark:border-white/5 border-slate-200 sticky top-0 z-50 backdrop-blur-xl supports-[backdrop-filter]:dark:bg-slate-950/60 supports-[backdrop-filter]:bg-white/60 transition-all">
        <div class="max-w-7xl mx-auto px-4 py-4">
            <div class="flex items-center justify-between flex-wrap gap-4">
                <div class="flex items-center gap-4">
                    <div class="relative flex items-center justify-center w-12 h-12 rounded-xl bg-red-600 shadow-[0_0_20px_rgba(220,38,38,0.4)]">
                        <svg class="w-6 h-6 text-white" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" d="M13 10V3L4 14h7v7l9-11h-7z"/>
                        </svg>
                    </div>
                    <div>
                        <h1 class="text-2xl font-black dark:text-white text-slate-900 tracking-tight flex items-center gap-2 uppercase">
                            MONITOR <span class="text-red-500 font-light">|</span> NEWS
                        </h1>
                        <p class="text-sm dark:text-slate-400 text-slate-500 mt-0.5 font-medium flex items-center gap-2">
                            TARGET: <span class="dark:bg-slate-800 bg-slate-200 dark:text-slate-200 text-slate-700 px-2.5 py-0.5 rounded text-xs tracking-wider border dark:border-slate-700 border-slate-300">สงคราม สหรัฐ อิหร่าน</span>
                        </p>
                    </div>
                </div>
                <div class="text-right flex flex-row items-center gap-4">
                    <!-- Dark Mode Toggle Button -->
                    <button id="theme-toggle" type="button" class="text-slate-500 dark:text-slate-400 hover:bg-slate-200 dark:hover:bg-slate-800 focus:outline-none focus:ring-4 focus:ring-slate-200 dark:focus:ring-slate-800 rounded-lg text-sm p-2.5 transition-colors">
                        <svg id="theme-toggle-dark-icon" class="hidden w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                            <path d="M17.293 13.293A8 8 0 016.707 2.707a8.001 8.001 0 1010.586 10.586z"></path>
                        </svg>
                        <svg id="theme-toggle-light-icon" class="hidden w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                            <path d="M10 2a1 1 0 011 1v1a1 1 0 11-2 0V3a1 1 0 011-1zm4 8a4 4 0 11-8 0 4 4 0 018 0zm-.464 4.95l.707.707a1 1 0 001.414-1.414l-.707-.707a1 1 0 00-1.414 1.414zm2.12-10.607a1 1 0 010 1.414l-.706.707a1 1 0 11-1.414-1.414l.707-.707a1 1 0 011.414 0zM17 11a1 1 0 100-2h-1a1 1 0 100 2h1zm-7 4a1 1 0 011 1v1a1 1 0 11-2 0v-1a1 1 0 011-1zM5.05 6.464A1 1 0 106.465 5.05l-.708-.707a1 1 0 00-1.414 1.414l.707.707zm1.414 8.486l-.707.707a1 1 0 01-1.414-1.414l.707-.707a1 1 0 011.414 1.414zM4 11a1 1 0 100-2H3a1 1 0 000 2h1z" fill-rule="evenodd" clip-rule="evenodd"></path>
                        </svg>
                    </button>
                    
                    <div class="flex items-center gap-2 text-xs font-bold tracking-widest text-slate-500 uppercase dark:bg-slate-900 bg-slate-100 px-3 py-1.5 rounded-lg border dark:border-slate-800 border-slate-300">
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
    <main class="max-w-7xl mx-auto px-4 pb-20 mt-4" id="newsContainer">
        <!-- International News -->
        <section class="mb-16 relative" id="en-section">
            <div class="absolute -left-4 top-0 bottom-0 w-0.5 bg-gradient-to-b from-red-600 via-red-600/10 to-transparent hidden md:block"></div>
            <div class="flex items-end justify-between mb-8 pb-4 border-b dark:border-slate-800/60 border-slate-200">
                <div>
                    <div class="flex items-center gap-3 mb-2">
                        <div class="w-10 h-1 bg-red-600 rounded-full"></div>
                        <span class="text-red-500 font-bold tracking-widest text-xs uppercase">Global Intel</span>
                    </div>
                    <h2 class="text-3xl font-black dark:text-white text-slate-900 font-newsreader tracking-tight">International Feed</h2>
                </div>
                <div class="text-slate-500 font-medium text-sm hidden sm:block">Real-time Global Coverage</div>
            </div>
            <div class="grid gap-5 md:grid-cols-2 lg:grid-cols-3" id="en-grid">
                {en_cards}
                {no_en if en_count == 0 else '<div class="col-span-full py-12 text-center border-2 border-dashed dark:border-slate-800 border-slate-300 rounded-2xl hidden" id="no-en-msg"><p class="dark:text-slate-500 text-slate-500 font-medium">No English reports matching filter</p></div>'}
            </div>
        </section>

        <!-- Thai News -->
        <section class="relative" id="th-section">
            <div class="absolute -left-4 top-0 bottom-0 w-0.5 bg-gradient-to-b from-orange-500 via-orange-500/10 to-transparent hidden md:block"></div>
            <div class="flex items-end justify-between mb-8 pb-4 border-b dark:border-slate-800/60 border-slate-200">
                <div>
                    <div class="flex items-center gap-3 mb-2">
                        <div class="w-10 h-1 bg-orange-500 rounded-full"></div>
                        <span class="text-orange-500 font-bold tracking-widest text-xs uppercase">Local Intel</span>
                    </div>
                    <h2 class="text-3xl font-black dark:text-white text-slate-900 font-newsreader tracking-tight">Thai Feed</h2>
                </div>
                <div class="text-slate-500 font-medium text-sm hidden sm:block">Coverage in Thailand</div>
            </div>
            <div class="grid gap-5 md:grid-cols-2 lg:grid-cols-3" id="th-grid">
                {th_cards}
                {no_th if th_count == 0 else '<div class="col-span-full py-12 text-center border-2 border-dashed dark:border-slate-800 border-slate-300 rounded-2xl hidden" id="no-th-msg"><p class="dark:text-slate-500 text-slate-500 font-medium">No Thai reports matching filter</p></div>'}
            </div>
        </section>
    </main>

    <!-- Footer -->
    <footer class="dark:bg-slate-950 bg-slate-50 border-t dark:border-white/5 border-slate-200 pt-12 pb-8 relative overflow-hidden transition-colors">
        <div class="absolute top-0 left-1/2 -translate-x-1/2 w-1/2 h-px bg-gradient-to-r from-transparent via-red-500/50 to-transparent"></div>
        <div class="max-w-7xl mx-auto px-4 flex flex-col items-center">
            <div class="w-12 h-12 dark:bg-slate-900 bg-white rounded-full flex items-center justify-center border dark:border-slate-800 border-slate-200 mb-6 shadow-[0_0_15px_rgba(0,0,0,0.1)] dark:shadow-[0_0_15px_rgba(0,0,0,0.5)] transition-colors">
                <svg class="w-5 h-5 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"/>
                </svg>
            </div>
            <p class="text-slate-500 dark:text-slate-400 font-medium mb-3">MINI MONITOR NEWS — TACTICAL DASHBOARD</p>
            <p class="text-sm text-slate-500">
                Execute <code class="font-mono text-xs dark:bg-slate-900 bg-slate-200 border dark:border-slate-800 border-slate-300 text-red-500 dark:text-red-400 px-2 py-1 rounded-md mx-1 shadow-inner">python scraper.py</code> to refresh data stream
            </p>
        </div>
    </footer>

    <script>
        // --- Dark Mode Toggle Logic ---
        const themeToggleBtn = document.getElementById('theme-toggle');
        const darkIcon = document.getElementById('theme-toggle-dark-icon');
        const lightIcon = document.getElementById('theme-toggle-light-icon');

        // Initial check theme
        if (localStorage.getItem('color-theme') === 'dark' || (!('color-theme' in localStorage) && window.matchMedia('(prefers-color-scheme: dark)').matches)) {{
            document.documentElement.classList.add('dark');
            lightIcon.classList.remove('hidden');
        }} else {{
            document.documentElement.classList.remove('dark');
            darkIcon.classList.remove('hidden');
        }}

        // Listen for toggle button
        themeToggleBtn.addEventListener('click', function() {{
            darkIcon.classList.toggle('hidden');
            lightIcon.classList.toggle('hidden');
            if (localStorage.getItem('color-theme')) {{
                if (localStorage.getItem('color-theme') === 'light') {{
                    document.documentElement.classList.add('dark');
                    localStorage.setItem('color-theme', 'dark');
                }} else {{
                    document.documentElement.classList.remove('dark');
                    localStorage.setItem('color-theme', 'light');
                }}
            }} else {{
                if (document.documentElement.classList.contains('dark')) {{
                    document.documentElement.classList.remove('dark');
                    localStorage.setItem('color-theme', 'light');
                }} else {{
                    document.documentElement.classList.add('dark');
                    localStorage.setItem('color-theme', 'dark');
                }}
            }}
            updateChartTheme(); // Update chart on theme change
        }});

        // --- Chart.js Integration ---
        const ctx = document.getElementById('trendChart').getContext('2d');
        const rawDates = {date_labels};
        const rawCounts = {date_counts};
        
        let trendChart = new Chart(ctx, {{
            type: 'line',
            data: {{
                labels: rawDates,
                datasets: [{{
                    label: 'News Articles',
                    data: rawCounts,
                    borderColor: '#ef4444',
                    backgroundColor: 'rgba(239, 68, 68, 0.1)',
                    borderWidth: 2,
                    tension: 0.3,
                    fill: true,
                    pointBackgroundColor: '#ef4444',
                    pointBorderColor: '#fff',
                    pointHoverBackgroundColor: '#fff',
                    pointHoverBorderColor: '#ef4444'
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{
                    legend: {{ display: false }},
                    tooltip: {{ 
                        mode: 'index', 
                        intersect: false,
                        backgroundColor: 'rgba(15, 23, 42, 0.9)',
                        titleColor: '#fff',
                        bodyColor: '#cbd5e1',
                        borderColor: '#334155',
                        borderWidth: 1
                    }}
                }},
                scales: {{
                    y: {{ 
                        beginAtZero: true, 
                        ticks: {{ stepSize: 1, color: '#94a3b8' }},
                        grid: {{ color: 'rgba(148, 163, 184, 0.1)' }}
                    }},
                    x: {{
                        ticks: {{ color: '#94a3b8' }},
                        grid: {{ display: false }}
                    }}
                }},
                interaction: {{
                    mode: 'nearest',
                    axis: 'x',
                    intersect: false
                }}
            }}
        }});
        
        function updateChartTheme() {{
            const isDark = document.documentElement.classList.contains('dark');
            const gridColor = isDark ? 'rgba(148, 163, 184, 0.1)' : 'rgba(148, 163, 184, 0.2)';
            const tooltipBg = isDark ? 'rgba(15, 23, 42, 0.9)' : 'rgba(255, 255, 255, 0.9)';
            const tooltipTitle = isDark ? '#fff' : '#0f172a';
            const tooltipBody = isDark ? '#cbd5e1' : '#334155';
            const tooltipBorder = isDark ? '#334155' : '#e2e8f0';
            
            trendChart.options.scales.y.grid.color = gridColor;
            trendChart.options.plugins.tooltip.backgroundColor = tooltipBg;
            trendChart.options.plugins.tooltip.titleColor = tooltipTitle;
            trendChart.options.plugins.tooltip.bodyColor = tooltipBody;
            trendChart.options.plugins.tooltip.borderColor = tooltipBorder;
            trendChart.update();
        }}
        
        // Setup initial chart theme
        updateChartTheme();

        // --- Filter & Search Logic ---
        const searchInput = document.getElementById('searchInput');
        const sourceFilter = document.getElementById('sourceFilter');
        const langFilter = document.getElementById('langFilter');
        const dateFilter = document.getElementById('dateFilter');
        const articles = document.querySelectorAll('.article-card');
        
        const noEnMsg = document.getElementById('no-en-msg');
        const noThMsg = document.getElementById('no-th-msg');

        function filterArticles() {{
            const searchTerm = searchInput.value.toLowerCase();
            const selectedSource = sourceFilter.value;
            const selectedLang = langFilter.value;
            const selectedDate = dateFilter.value; // YYYY-MM-DD format

            let visibleEn = 0;
            let visibleTh = 0;

            articles.forEach(article => {{
                const title = article.getAttribute('data-title');
                const source = article.getAttribute('data-source');
                const lang = article.getAttribute('data-lang');
                const date = article.getAttribute('data-date'); // expected format: YYYY-MM-DD HH:MM

                const matchSearch = title.includes(searchTerm);
                const matchSource = selectedSource === 'all' || source === selectedSource;
                const matchLang = selectedLang === 'all' || lang === selectedLang;
                const matchDate = !selectedDate || date.startsWith(selectedDate);

                if (matchSearch && matchSource && matchLang && matchDate) {{
                    article.style.display = '';
                    if (lang === 'en') visibleEn++;
                    if (lang === 'th') visibleTh++;
                }} else {{
                    article.style.display = 'none';
                }}
            }});
            
            // Toggle No items messages
            if(noEnMsg) noEnMsg.style.display = (visibleEn === 0 && selectedLang !== 'th') ? 'block' : 'none';
            if(noThMsg) noThMsg.style.display = (visibleTh === 0 && selectedLang !== 'en') ? 'block' : 'none';
            
            // Hide section entirely if language filter tells us so
            const enSection = document.getElementById('en-section');
            const thSection = document.getElementById('th-section');
            if(enSection) enSection.style.display = (selectedLang === 'th') ? 'none' : 'block';
            if(thSection) thSection.style.display = (selectedLang === 'en') ? 'none' : 'block';
        }}

        searchInput.addEventListener('input', filterArticles);
        sourceFilter.addEventListener('change', filterArticles);
        langFilter.addEventListener('change', filterArticles);
        dateFilter.addEventListener('change', filterArticles);

    </script>
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
