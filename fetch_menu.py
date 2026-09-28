"""FREE version: downloads today's Mensa Campo menu, translates the dish names
with a built-in dictionary and estimates macros from a built-in table.
No API key, no paid service. Saves the result as menu.json."""
import json, re, urllib.request
from datetime import datetime
from zoneinfo import ZoneInfo

URL = "https://www.imensa.de/bonn/mensa-campo/index.html"

# ---------- 1. download and clean the page ----------
req = urllib.request.Request(URL, headers={"User-Agent": "Mozilla/5.0"})
html = urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "ignore")
html = re.sub(r"(?is)<(script|style).*?</\1>", " ", html)
text = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html))
text = re.sub(r"&nbsp;|&#160;", " ", text).replace("&amp;", "&").replace("&quot;", '"')

# ---------- 2. cut it into sections and dishes ----------
HEADERS = {"Unser Spezial": "Special", "Hauptgericht": "Main", "Beilagen": "Side",
           "Dessert": "Dessert", "Suppe & Eintopf": "Soup", "Buffet": "Buffet",
           "Aus der Pfanne": "Pan"}
head_re = "|".join(re.escape(h) for h in HEADERS)
first = re.search(head_re, text)
end = text.find("Standort und Umgebung")
body = text[first.start(): end if end != -1 else None]

TAGS = r"(?:fleischlos|vegan|vegetarisch|Geflügel|Knoblauch|Schwein|Rind|Fisch|Lamm|Wild|ZUSATZ|ALLERGEN|ZULETZT)"
stop = re.compile(rf"\s(?={TAGS}(?:\s|$))|\s\d{{2}}\.\d{{2}}\.\d{{4}}")
parts = re.split(rf"({head_re})", body)
dishes = []
for i in range(1, len(parts), 2):
    category = HEADERS[parts[i]]
    for chunk in re.split(r"\d+,\d\d\s*€", parts[i + 1]):
        chunk = chunk.strip()
        if not chunk:
            continue
        name = stop.split(" " + chunk, 1)[0].strip()
        if len(name) > 2 and "defekt" not in name.lower():
            dishes.append((category, name))

# ---------- 3. translation dictionary (German -> English) ----------
DICT = [("Hähnchenbruststreifen", "chicken breast strips"), ("Hähnchen", "chicken"),
 ("Schweineschnitzel", "pork schnitzel"), ("Schnitzel", "schnitzel"), ("Rinderhack", "minced beef"),
 ("Bolognese", "Bolognese"), ("Gerstenrisotto", "barley risotto"), ("Risotto", "risotto"),
 ("Wokpfanne", "wok pan"), ("süß-sauer", "sweet & sour"), ("mit Soja", "with soy"),
 ("Naturreis", "brown rice"), ("Basmatireis", "basmati rice"), ("Reis", "rice"),
 ("Gemüse", "vegetables"), ("Auflauf", "bake"), ("Paprikasalsa", "pepper salsa"),
 ("Paprika", "pepper"), ("Rosmarinsauce", "rosemary sauce"), ("Rosmarin", "rosemary"), ("sauce", "sauce"), ("Sauce", "sauce"),
 ("Blattsalat", "leaf salad"), ("Salatbuffet", "salad buffet"), ("Salat", "salad"),
 ("Broccoli", "broccoli"), ("Kaisergemüse", "mixed vegetables"), ("Nudeln", "noodles"),
 ("Pudding", "pudding"), ("Spitzkohl", "pointed cabbage"), ("Möhren", "carrots"),
 ("Eintopf", "stew"), ("Suppe", "soup"), ("Zitronen", "lemon"), ("Zitrone", "lemon"),
 ("Kartoffel", "potato"), ("Pommes", "fries"), ("Püree", "mash"), ("Lachs", "salmon"),
 ("Wildlachs", "wild salmon"), ("Fisch", "fish"), ("Kichererbsen", "chickpeas"),
 ("Linsen", "lentils"), ("Kokos", "coconut"), ("Pfeffer", "pepper"), ("Rahm", "cream"),
 ("Pilz", "mushroom"), ("Käse", "cheese"), ("Ei", "egg"), ("Pizza", "pizza"),
 ("Currywurst", "curry sausage"), ("Bratwurst", "bratwurst"), ("Frische", "fresh"),
 ("Bio", "organic"), ("und", "and"), ("mit", "with"), ("vom", "from the"), ("in", "in"),
 ("Spätzle", "spaetzle"), ("Ragout", "ragout"), ("Tofu", "tofu"), ("Kürbis", "pumpkin"),
 ("Tomaten", "tomato"), ("Hackfleisch", "minced meat"), ("Rind", "beef"), ("Schwein", "pork")]
def translate(s):
    out = s
    for de, en in sorted(DICT, key=lambda p: -len(p[0])):
        out = re.sub(rf"(?<![A-Za-zäöüÄÖÜß]){re.escape(de)}", en, out)
    return out[0].upper() + out[1:]

# ---------- 4. macro estimates: kcal, protein, carbs, fat ----------
BY_KEYWORD = [
 (["pizza"], 800, 32, 100, 28), (["döner", "kebab"], 750, 35, 70, 34),
 (["currywurst", "wurst"], 780, 26, 70, 44), (["schnitzel"], 560, 34, 28, 33),
 (["burger"], 850, 32, 70, 46), (["pasta", "spaghetti", "nudel", "penne", "lasagne"], 700, 26, 95, 24),
 (["hähnchen", "geflügel", "pute"], 620, 40, 70, 18), (["fisch", "lachs", "forelle"], 580, 36, 55, 22),
 (["curry", "linsen", "kichererbsen", "chili", "dal"], 620, 22, 88, 16),
 (["risotto", "reis"], 620, 16, 100, 14), (["kartoffel", "püree", "pommes"], 560, 12, 80, 20),
 (["wok", "tofu", "falafel", "gemüse"], 540, 18, 75, 16), (["auflauf", "gratin"], 620, 20, 80, 24)]
SIDES = [(["salat"], 70, 2, 6, 4), (["nudel", "reis", "kartoffel", "pommes", "spätzle"], 260, 8, 52, 2),
         (["gemüse", "broccoli", "möhren", "kohl"], 60, 4, 7, 2)]
BY_CATEGORY = {"Dessert": (220, 6, 34, 7), "Soup": (230, 7, 32, 7), "Buffet": (150, 5, 12, 9)}

def estimate(cat, name):
    n = name.lower()
    if cat in BY_CATEGORY:
        return BY_CATEGORY[cat], "Category estimate"
    if cat == "Side":
        for kws, *m in SIDES:
            if any(k in n for k in kws):
                return tuple(m), "Side estimate"
        return (150, 4, 25, 3), "Generic side estimate"
    for kws, *m in BY_KEYWORD:
        if any(k in n for k in kws):
            return tuple(m), "Estimate from dish type"
    return (600, 24, 70, 22), "Generic estimate (dish not recognised)"

items = []
for cat, name in dishes:
    (kcal, p, c, f), note = estimate(cat, name)
    items.append({"name_de": name, "name_en": translate(name), "category": cat,
                  "kcal": kcal, "protein": p, "carbs": c, "fat": f, "note": note})

out = {"mensa": "Mensa Campo",
       "date": datetime.now(ZoneInfo("Europe/Berlin")).strftime("%a %d %b %Y"),
       "items": items}
with open("menu.json", "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=1)
print(f"Saved {len(items)} dishes")
