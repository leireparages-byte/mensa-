"""Downloads today's Mensa Campo menu, translates it to English and
estimates calories/macros with Claude. Saves the result as menu.json."""
import json, os, re, urllib.request
from datetime import datetime
from zoneinfo import ZoneInfo
import anthropic

URL = "https://www.imensa.de/bonn/mensa-campo/index.html"  # Mensa Campo, "today" page

req = urllib.request.Request(URL, headers={"User-Agent": "Mozilla/5.0"})
html = urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "ignore")
html = re.sub(r"(?is)<(script|style).*?</\1>", " ", html)
text = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html))
start = text.find("Speiseplan für")
text = text[start:start + 6000] if start != -1 else text[:6000]

prompt = f"""Below is the text of a German university canteen (Mensa) page with today's menu.
Extract every dish (ignore prices, allergens, ratings and 'ZULETZT' dates).
For each dish give an English name and an estimate for ONE typical portion
(include the usual side only if it is part of the dish name).
Return ONLY a JSON array, no other text. Each item:
{{"name_de": str, "name_en": str, "category": one of ["Special","Main","Side","Dessert","Soup","Buffet","Pan"],
"kcal": int, "protein": int, "carbs": int, "fat": int, "note": short English note (max 8 words)}}

PAGE TEXT:
{text}"""

client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from the environment
msg = client.messages.create(
    model="claude-haiku-4-5-20251001",
    max_tokens=3000,
    messages=[{"role": "user", "content": prompt}],
)
raw = msg.content[0].text.strip()
raw = re.sub(r"^```(?:json)?|```$", "", raw, flags=re.M).strip()
items = json.loads(raw)

out = {
    "mensa": "Mensa Campo",
    "date": datetime.now(ZoneInfo("Europe/Berlin")).strftime("%a %d %b %Y"),
    "items": items,
}
with open("menu.json", "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=1)
print(f"Saved {len(items)} dishes")
