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

## การทำงานแบบอัตโนมัติ (GitHub Actions)
โปรเจกต์นี้ตั้งค่าให้อัปเดตอัตโนมัติผ่าน GitHub Actions:
- ข้อมูลจำทำการดึงใหม่ทุกๆ 2 ชั่วโมง (หรือตามที่ตั้งค่าใน `.github/workflows/update_news.yml`)
- หลังจากดึงข่าวมาใหม่ ระบบจะนำไฟล์ `index.html` ขึ้นมารันบน Repo และทำเว็บออนไลน์ผ่าน GitHub Pages
- หากต้องการดูเว็บออนไลน์ เข้าไปที่แท็บ [Settings > Pages ใน GitHub] เพื่อตั้งค่าให้ Branch `main` โฮสต์ผ่านหน้า Pages

## Tech Stack

- **Python** — requests, BeautifulSoup4, feedparser
- **HTML** — Tailwind CSS via CDN
- ไม่ต้องรัน server ใดๆ
