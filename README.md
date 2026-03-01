# Mini Monitor News — สงคราม สหรัฐ อิหร่าน

ดึงข่าวเกี่ยวกับ "สงคราม สหรัฐ อิหร่าน" จากแหล่งข่าวทั่วโลก แล้วสร้างเป็นหน้าเว็บ Static HTML

## แหล่งข่าว

| แหล่ง | ภาษา | วิธี |
|---|---|---|
| Google News | EN + TH | RSS Search |
| BBC News | EN | RSS Feed |
| Reuters | EN | RSS Feed |
| Al Jazeera | EN | RSS Feed |
| ไทยรัฐ | TH | Web Scraping |
| มติชน | TH | Web Scraping |

## วิธีใช้งาน

```bash
# 1. ติดตั้ง dependencies
pip install -r requirements.txt

# 2. รัน scraper
python scraper.py

# 3. เปิดดูข่าว
open index.html
```

## Tech Stack

- **Python** — requests, BeautifulSoup4, feedparser
- **HTML** — Tailwind CSS via CDN
- ไม่ต้องรัน server ใดๆ
