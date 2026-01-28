import json
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import re

HEADERS = {"User-Agent": "sysconf-tracker-bot"}

NOW = datetime.utcnow()
CUTOFF = NOW + timedelta(days=365)

def google_like_search(query):
    url = f"https://dblp.org/search?q={query}"
    r = requests.get(url, headers=HEADERS, timeout=10)
    soup = BeautifulSoup(r.text, "html.parser")
    for a in soup.find_all("a", href=True):
        if "conference" in a["href"] or "symposium" in a["href"]:
            return a["href"]
    return None

def find_homepage(conf):
    known = {
        "OSDI": "https://www.usenix.org/conference/osdi",
        "SOSP": "https://www.sosp.org",
        "ASPLOS": "https://www.asplos-conference.org",
        "EuroSys": "https://www.eurosys.org",
        "USENIX ATC": "https://www.usenix.org/conference/atc",
        "FAST": "https://www.usenix.org/conference/fast"
    }
    return known.get(conf) or google_like_search(conf)

def find_cfp_page(homepage):
    if not homepage:
        return None
    r = requests.get(homepage, headers=HEADERS, timeout=10)
    soup = BeautifulSoup(r.text, "html.parser")
    for a in soup.find_all("a", href=True):
        if "call for papers" in a.text.lower() or "cfp" in a["href"].lower():
            return a["href"] if a["href"].startswith("http") else homepage + a["href"]
    return None

def extract_deadline(cfp_url):
    if not cfp_url:
        return "TBA"
    r = requests.get(cfp_url, headers=HEADERS, timeout=10)
    text = r.text
    matches = re.findall(r"\b(20\d{2}[-/]\d{1,2}[-/]\d{1,2})\b", text)
    for m in matches:
        try:
            d = datetime.fromisoformat(m.replace("/", "-"))
            if NOW <= d <= CUTOFF:
                return d.strftime("%Y-%m-%d")
        except:
            pass
    return "TBA"

def extract_dates_and_location(homepage):
    if not homepage:
        return ("TBA", "TBA", "TBA")
    r = requests.get(homepage, headers=HEADERS, timeout=10)
    text = r.text
    dates = re.findall(r"\b(20\d{2})\b", text)
    location = "TBA"
    if "usa" in text.lower():
        location = "USA"
    return ("TBA", "TBA", location)

with open("data/conferences.json") as f:
    conferences = json.load(f)

cfp_out = []
dates_out = []

for c in conferences:
    name = c["name"]
    rank = c["core_rank"]

    homepage = find_homepage(name)
    cfp_url = find_cfp_page(homepage)
    deadline = extract_deadline(cfp_url)
    start, end, location = extract_dates_and_location(homepage)

    cfp_out.append({
        "name": name,
        "core_rank": rank,
        "cfp_deadline": deadline,
        "cfp_url": cfp_url or "TBA"
    })

    dates_out.append({
        "name": name,
        "core_rank": rank,
        "start_date": start,
        "end_date": end,
        "location": location,
        "homepage": homepage or "TBA"
    })

with open("generated/cfp.json", "w") as f:
    json.dump(cfp_out, f, indent=2)

with open("generated/confdates.json", "w") as f:
    json.dump(dates_out, f, indent=2)
