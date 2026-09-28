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
    for chunk in re.split(r"\d+,\d\d\s*€", parts[i + 1])[:-1]:  # last piece = text after final price, never a dish
        chunk = chunk.strip()
        if not chunk:
            continue
        name = stop.split(" " + chunk, 1)[0].strip()
        if len(name) > 2 and "defekt" not in name.lower() and not name.startswith("Speiseplan"):
            dishes.append((category, name))

# ---------- 3. translation dictionary (German -> English) ----------
# Words of 5+ letters are also replaced inside long German compound words.
DICT = {
 # meat & fish
 "Hähnchenbruststreifen":"chicken breast strips","Hähnchenstreifen":"chicken strips","Hähnchenbrust":"chicken breast",
 "Hähnchen":"chicken","Hühnchen":"chicken","Geflügel":"poultry","Putenbrust":"turkey breast","Pute":"turkey",
 "Schweineschnitzel":"pork schnitzel","Schnitzel":"schnitzel","Schweinebraten":"roast pork","Schweine":"pork",
 "Rinderhackfleisch":"minced beef","Rinderhack":"minced beef","Rindergulasch":"beef goulash","Gulasch":"goulash",
 "Rinder":"beef","Hackfleisch":"minced meat","Hackbraten":"meatloaf","Frikadelle":"meatball","Fleischbällchen":"meatballs",
 "Currywurst":"curry sausage","Bratwurst":"bratwurst","Wurst":"sausage","Schinken":"ham","Speck":"bacon",
 "Wildlachs":"wild salmon","Lachs":"salmon","Seelachs":"pollock","Fischstäbchen":"fish fingers","Fisch":"fish",
 "Garnelen":"prawns","Thunfisch":"tuna","Forelle":"trout",
 # veg & plant-based
 "Gemüse":"vegetables","Kaisergemüse":"mixed vegetables","Ofengemüse":"oven vegetables","Gemüsecurry":"vegetable curry",
 "Blattsalat":"leaf salad","Salatbuffet":"salad buffet","Salat":"salad","Broccoli":"broccoli","Brokkoli":"broccoli",
 "Blumenkohl":"cauliflower","Spitzkohl":"pointed cabbage","Rotkohl":"red cabbage","Weißkohl":"white cabbage","Kohl":"cabbage",
 "Möhren":"carrots","Karotten":"carrots","Kürbis":"pumpkin","Zucchini":"zucchini","Aubergine":"aubergine",
 "Paprika":"pepper","Tomaten":"tomato","Tomate":"tomato","Spinat":"spinach","Champignon":"mushroom","Pilz":"mushroom",
 "Röstzwiebeln":"fried onions","Zwiebeln":"onions","Zwiebel":"onion","Würstchen":"sausages","Pilze":"mushrooms","Knoblauch":"garlic","Mais":"corn","Erbsen":"peas","Bohnen":"beans","Kichererbsen":"chickpeas",
 "Linsen":"lentils","Tofu":"tofu","Falafel":"falafel","Soja":"soy","Kokos":"coconut","Erdnuss":"peanut",
 # carbs
 "Basmatireis":"basmati rice","Naturreis":"brown rice","Vollkornreis":"whole grain rice","Risotto":"risotto",
 "Gerstenrisotto":"barley risotto","Reis":"rice","Nudeln":"noodles","Spaghetti":"spaghetti","Tortellini":"tortellini",
 "Lasagne":"lasagne","Gnocchi":"gnocchi","Spätzle":"spaetzle","Kartoffeln":"potatoes","Kartoffel":"potato",
 "Bratkartoffeln":"fried potatoes","Pommes":"fries","Püree":"mash","Reibekuchen":"potato pancakes","Klöße":"dumplings",
 "Knödel":"dumplings","Brot":"bread","Pizza":"pizza","Burger":"burger","Döner":"doner",
 # dishes, sauces, dessert
 "Wokpfanne":"wok pan","Pfanne":"pan","Auflauf":"bake","Eintopf":"stew","Suppe":"soup","Curry":"curry",
 "Bolognese":"Bolognese","Rahmsauce":"cream sauce","Rahm":"cream","Sahne":"cream","Sauce":"sauce","Soße":"sauce",
 "Ragout":"ragout","Salsa":"salsa","Dip":"dip","Pudding":"pudding","Kuchen":"cake","Kaiserschmarrn":"shredded pancake",
 "Pfannkuchen":"pancakes","Apfelmus":"apple sauce","Quark":"quark","Joghurt":"yoghurt","Obst":"fruit","Eis":"ice cream",
 "Käse":"cheese","Mozzarella":"mozzarella","Feta":"feta","Ei":"egg","Eier":"eggs","Rührei":"scrambled egg",
 # flavours & misc
 "Zitronen":"lemon","Zitrone":"lemon","Rosmarin":"rosemary","Basilikum":"basil","Mandel":"almond","Pesto":"pesto",
 "Pfeffer":"pepper","Kräuter":"herbs","Senf":"mustard","Honig":"honey","süß-sauer":"sweet & sour","Bio":"organic",
 "Frische":"fresh","frische":"fresh","gebraten":"fried","gebackene":"baked","gebackener":"baked","gegrillt":"grilled",
 "überbacken":"gratinated","gefüllte":"stuffed","gefüllter":"stuffed","Art":"style",
 "und":"and","mit":"with","vom":"from the","auf":"on","dazu":"plus","Soja":"soy"}
def translate(s):
    out = s
    for de, en in sorted(DICT.items(), key=lambda p: -len(p[0])):
        if de.lower() == en.lower():
            continue
        if len(de) >= 5:
            out = re.sub(re.escape(de), " " + en + " ", out, flags=re.I)
        else:
            out = re.sub(rf"(?<![A-Za-zäöüÄÖÜß]){re.escape(de)}(?![A-Za-zäöüÄÖÜß])", en, out)
    out = out.replace('"', "")
    out = re.sub(r"\s*-\s*", " ", out)
    out = re.sub(r"\s+", " ", out).strip()
    return out[:1].upper() + out[1:]

# ---------- 4. macro estimates: kcal, protein, carbs, fat ----------
# First match wins, so specific words come before general ones.
BY_KEYWORD = [
 (["pizza"], 800, 32, 100, 28), (["döner", "kebab"], 750, 35, 70, 34),
 (["currywurst"], 780, 26, 70, 44), (["burger"], 850, 32, 70, 46),
 (["kaiserschmarrn", "pfannkuchen", "germknödel"], 720, 16, 100, 26),
 (["fischstäbchen"], 520, 24, 60, 18), (["schnitzel", "cordon"], 560, 34, 28, 33),
 (["braten", "gulasch", "hackbraten", "frikadelle", "fleischbällchen"], 600, 38, 40, 28),
 (["bratwurst", "wurst"], 700, 24, 55, 42), (["käsespätzle", "spätzle"], 720, 26, 85, 28),
 (["tortellini", "lasagne", "spaghetti", "penne", "pasta", "nudel"], 700, 26, 95, 24),
 (["gnocchi"], 650, 16, 105, 16), (["reibekuchen", "kartoffelpuffer"], 600, 10, 70, 30),
 (["hähnchen", "hühnchen", "geflügel", "pute"], 620, 40, 70, 18),
 (["lachs", "forelle", "fisch", "seelachs", "garnelen", "thunfisch"], 580, 36, 55, 22),
 (["chili", "curry", "linsen", "kichererbsen", "dal"], 620, 22, 88, 16),
 (["risotto", "reis"], 620, 16, 100, 14), (["kartoffel", "püree", "pommes", "klöße", "knödel"], 560, 12, 80, 20),
 (["auflauf", "gratin", "überbacken"], 620, 20, 80, 24), (["wok", "tofu", "falafel", "gemüse", "veggie"], 540, 18, 75, 16),
 (["salatteller", "salat"], 350, 12, 25, 22), (["suppe", "eintopf"], 300, 12, 38, 10),
 (["ei ", "omelett", "rührei"], 520, 24, 40, 28)]
SIDES = [(["salat"], 70, 2, 6, 4), (["nudel", "reis", "kartoffel", "pommes", "spätzle", "püree", "brot"], 260, 8, 52, 2),
         (["gemüse", "broccoli", "brokkoli", "möhren", "karotten", "kohl", "spinat", "bohnen"], 60, 4, 7, 2)]
DEFAULT_BY_CATEGORY = {"Special": (800, 30, 95, 30), "Main": (600, 24, 72, 22), "Pan": (600, 30, 70, 20),
                       "Dessert": (220, 6, 34, 7), "Soup": (230, 7, 32, 7), "Buffet": (150, 5, 12, 9),
                       "Side": (150, 4, 25, 3)}

def estimate(cat, name):
    n = name.lower() + " "
    if cat == "Dessert":
        return DEFAULT_BY_CATEGORY[cat]
    if cat == "Side":
        for kws, *m in SIDES:
            if any(k in n for k in kws):
                return tuple(m)
        return DEFAULT_BY_CATEGORY[cat]
    if cat in ("Soup", "Buffet"):
        return DEFAULT_BY_CATEGORY[cat]
    for kws, *m in BY_KEYWORD:
        if any(k in n for k in kws):
            return tuple(m)
    return DEFAULT_BY_CATEGORY.get(cat, (600, 24, 70, 22))

items = []
for cat, name in dishes:
    kcal, p, c, f = estimate(cat, name)
    items.append({"name_de": name, "name_en": translate(name), "category": cat,
                  "kcal": kcal, "protein": p, "carbs": c, "fat": f, "note": "Rough estimate"})

out = {"mensa": "Mensa Campo",
       "date": datetime.now(ZoneInfo("Europe/Berlin")).strftime("%a %d %b %Y"),
       "items": items}
with open("menu.json", "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=1)
print(f"Saved {len(items)} dishes")
