import json
import requests
from bs4 import BeautifulSoup
from pathlib import Path
from datetime import datetime, timezone
import re
import urllib.parse
import time

# ----------------------------
# CONFIG
# ----------------------------
YEAR = datetime.now(timezone.utc).year
INPUT_FILE = Path("data/conferences.json")
OUTPUT_DIR = Path("generated")
OUTPUT_DIR.mkdir(exist_ok=True)

# ----------------------------
# UTILITIES
# ----------------------------

def clean_url(url):
    """Clean and validate URL"""
    if not url or url == "TBA":
        return None
    
    # Remove DuckDuckGo redirect wrapper
    if 'uddg=' in url:
        match = re.search(r'uddg=([^&]+)', url)
        if match:
            url = urllib.parse.unquote(match.group(1))
    
    # Ensure URL has scheme
    if url.startswith('//'):
        url = 'https:' + url
    elif not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    
    # Validate URL structure
    try:
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme and parsed.netloc:
            return url
    except:
        pass
    
    return None


def update_year_in_url(url, new_year):
    """Update year references in URL"""
    if not url:
        return url
    
    # Find all 4-digit years in the URL
    current_years = re.findall(r'\b(20\d{2})\b', url)
    if not current_years:
        return url
    
    # Replace with new year
    for old_year in set(current_years):
        url = url.replace(old_year, str(new_year))
    
    # Also handle 2-digit years
    for old_year in set(current_years):
        old_short = old_year[2:]
        new_short = str(new_year)[2:]
        url = url.replace(old_short, new_short)
    
    return url


def search_bing(query, num_results=8):
    """
    Search using Bing (scraping results page)
    No API key required
    """
    try:
        search_url = f"https://www.bing.com/search?q={urllib.parse.quote_plus(query)}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        }
        
        r = requests.get(search_url, headers=headers, timeout=15)
        r.raise_for_status()
        
        soup = BeautifulSoup(r.text, "html.parser")
        urls = []
        
        # Bing search results are in <li class="b_algo">
        for result in soup.find_all('li', class_='b_algo'):
            link = result.find('a')
            if link and link.get('href'):
                url = link['href']
                if url.startswith('http'):
                    urls.append(url)
                    if len(urls) >= num_results:
                        break
        
        # Also try cite tags which contain URLs
        if len(urls) < num_results:
            for cite in soup.find_all('cite'):
                url_text = cite.get_text()
                if url_text and not url_text.startswith('http'):
                    url_text = 'https://' + url_text
                if url_text and url_text.startswith('http'):
                    cleaned = clean_url(url_text)
                    if cleaned and cleaned not in urls:
                        urls.append(cleaned)
                        if len(urls) >= num_results:
                            break
        
        return urls
    except Exception as e:
        print(f"    Bing search failed: {e}")
        return []


def search_startpage(query, num_results=8):
    """
    Search using Startpage (privacy-focused search engine)
    No API key required
    """
    try:
        search_url = f"https://www.startpage.com/do/search?q={urllib.parse.quote_plus(query)}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        
        r = requests.get(search_url, headers=headers, timeout=15)
        r.raise_for_status()
        
        soup = BeautifulSoup(r.text, "html.parser")
        urls = []
        
        # Startpage results
        for result in soup.find_all('a', class_='w-gl__result-url'):
            url = result.get('href')
            if url and url.startswith('http'):
                urls.append(url)
                if len(urls) >= num_results:
                    break
        
        return urls
    except Exception as e:
        print(f"    Startpage search failed: {e}")
        return []


def search_mojeek(query, num_results=8):
    """
    Search using Mojeek (independent search engine)
    No API key required
    """
    try:
        search_url = f"https://www.mojeek.com/search?q={urllib.parse.quote_plus(query)}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        
        r = requests.get(search_url, headers=headers, timeout=15)
        r.raise_for_status()
        
        soup = BeautifulSoup(r.text, "html.parser")
        urls = []
        
        # Mojeek results
        for result in soup.find_all('a', class_='ob'):
            url = result.get('href')
            if url and url.startswith('http'):
                urls.append(url)
                if len(urls) >= num_results:
                    break
        
        return urls
    except Exception as e:
        print(f"    Mojeek search failed: {e}")
        return []


def search_web(conf_name, year, max_results=8):
    """
    Search the web for conference CFP using free search engines
    No API keys required - safe for public repositories
    """
    query = f"{conf_name} {year} CFP call for papers"
    print(f"    🔍 Web search: '{query}'")
    
    all_urls = []
    
    # Try Bing first (most reliable for scraping)
    print(f"      • Trying Bing...")
    urls = search_bing(query, max_results)
    if urls:
        print(f"        ✓ Found {len(urls)} results")
        all_urls.extend(urls)
    else:
        print(f"        ✗ No results")
    
    # If we have enough URLs, return them
    if len(all_urls) >= max_results:
        return all_urls[:max_results]
    
    time.sleep(1)  # Rate limiting
    
    # Try Startpage as backup
    print(f"      • Trying Startpage...")
    urls = search_startpage(query, max_results - len(all_urls))
    if urls:
        print(f"        ✓ Found {len(urls)} results")
        all_urls.extend(urls)
    else:
        print(f"        ✗ No results")
    
    # If still need more, try Mojeek
    if len(all_urls) < max_results:
        time.sleep(1)  # Rate limiting
        print(f"      • Trying Mojeek...")
        urls = search_mojeek(query, max_results - len(all_urls))
        if urls:
            print(f"        ✓ Found {len(urls)} results")
            all_urls.extend(urls)
        else:
            print(f"        ✗ No results")
    
    # Remove duplicates
    unique_urls = []
    seen = set()
    for url in all_urls:
        if url not in seen:
            seen.add(url)
            unique_urls.append(url)
    
    if not unique_urls:
        print(f"      ⚠ No search results found")
    
    return unique_urls[:max_results]


def get_candidate_urls(conf_name, year, base_url=None):
    """
    Generate candidate URLs to check for conference CFP
    Priority: base_url with year update -> web search -> common patterns
    """
    urls = []
    
    # Priority 1: If base_url provided, try it with updated year
    if base_url:
        print(f"    📌 Using base URL: {base_url}")
        urls.append(base_url)
        
        # Try with updated year
        updated = update_year_in_url(base_url, year)
        if updated != base_url:
            urls.append(updated)
            print(f"    📌 Year-updated URL: {updated}")
    
    # Priority 2: Web search for actual CFP pages
    search_urls = search_web(conf_name, year, max_results=8)
    urls.extend(search_urls)
    
    # Priority 3: Common URL patterns as final fallback
    clean_name = re.sub(r'[^\w\s-]', '', conf_name.lower())
    clean_name = re.sub(r'\s+', '', clean_name)
    
    patterns = [
        f"https://{clean_name}{year}.org",
        f"https://www.{clean_name}.org/{year}",
        f"https://{year}.{clean_name}.org",
        f"https://conf.researchr.org/home/{clean_name}-{year}",
        f"https://{clean_name}.org/conferences/{year}",
    ]
    
    urls.extend(patterns)
    
    # Remove duplicates and clean URLs
    seen = set()
    unique_urls = []
    for url in urls:
        cleaned = clean_url(url)
        if cleaned and cleaned not in seen:
            seen.add(cleaned)
            unique_urls.append(cleaned)
    
    return unique_urls


def extract_dates_from_text(text):
    """Extract dates from text using multiple patterns, handling multiple submission cycles"""
    dates = {
        "cfp_deadline": None,
        "abstract_deadline": None,
        "conference_start": None,
        "conference_end": None
    }
    
    # Common date patterns
    patterns = [
        r'(\d{1,2})\s+(January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*,?\s+(\d{4})',
        r'(January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+(\d{1,2}),?\s+(\d{4})',
        r'(\d{4})[/-](\d{1,2})[/-](\d{1,2})',
    ]
    
    # Keywords to identify deadline types
    abstract_keywords = ["abstract", "abstract deadline", "abstract due", "abstract submission", "paper abstract submission deadline"]
    submission_keywords = ["submission deadline", "paper deadline", "full paper", "paper due", "submission due", "submissions due", "deadline:", "paper submission"]
    conf_keywords = ["conference date", "event date", "will be held", "taking place", "conference:", "dates:"]
    
    # Clean text: replace em-dash and en-dash with regular dash
    text = text.replace('—', '-').replace('–', '-')
    lines = text.lower().split('\n')
    
    # Find ALL submission deadlines (for multiple cycles)
    all_deadlines = []
    all_abstract_deadlines = []
    
    for i, line in enumerate(lines):
        # Abstract deadlines
        if any(kw in line for kw in abstract_keywords):
            for pattern in patterns:
                matches = re.findall(pattern, line, re.IGNORECASE)
                for match in matches:
                    date_str = ' '.join(str(x) for x in match if x).strip()
                    all_abstract_deadlines.append(date_str)
        
        # Submission/CFP deadlines
        if any(kw in line for kw in submission_keywords):
            for pattern in patterns:
                matches = re.findall(pattern, line, re.IGNORECASE)
                for match in matches:
                    date_str = ' '.join(str(x) for x in match if x).strip()
                    all_deadlines.append(date_str)
        
        # Conference dates
        if any(kw in line for kw in conf_keywords) and not dates["conference_start"]:
            context = ' '.join(lines[i:min(i+4, len(lines))])
            for pattern in patterns:
                matches = re.findall(pattern, context, re.IGNORECASE)
                if len(matches) >= 1:
                    dates["conference_start"] = ' '.join(str(x) for x in matches[0] if x).strip() if isinstance(matches[0], tuple) else matches[0]
                if len(matches) >= 2:
                    dates["conference_end"] = ' '.join(str(x) for x in matches[1] if x).strip() if isinstance(matches[1], tuple) else matches[1]
                if dates["conference_start"]:
                    break
    
    # Find the earliest FUTURE deadline from all found deadlines
    now = datetime.now()
    future_deadlines = []
    future_abstract_deadlines = []
    
    for deadline_str in all_deadlines:
        deadline_date = parse_date_flexible(deadline_str)
        if deadline_date and deadline_date >= now:
            future_deadlines.append((deadline_date, deadline_str))
    
    for deadline_str in all_abstract_deadlines:
        deadline_date = parse_date_flexible(deadline_str)
        if deadline_date and deadline_date >= now:
            future_abstract_deadlines.append((deadline_date, deadline_str))
    
    # Use the earliest future deadline
    if future_deadlines:
        future_deadlines.sort(key=lambda x: x[0])
        dates["cfp_deadline"] = future_deadlines[0][1]
    elif all_deadlines:
        # If no future deadlines, use the last one found (might be most recent past deadline)
        dates["cfp_deadline"] = all_deadlines[-1]
    
    if future_abstract_deadlines:
        future_abstract_deadlines.sort(key=lambda x: x[0])
        dates["abstract_deadline"] = future_abstract_deadlines[0][1]
    elif all_abstract_deadlines:
        dates["abstract_deadline"] = all_abstract_deadlines[-1]
    
    return dates


def scrape_cfp_page(url):
    """Scrape CFP page for CFP deadline, conference dates, and location"""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        }
        r = requests.get(url, headers=headers, timeout=15, allow_redirects=True)
        r.raise_for_status()
        
        soup = BeautifulSoup(r.text, "html.parser")
        
        # Remove script and style elements
        for script in soup(["script", "style", "noscript"]):
            script.decompose()
            
        text = soup.get_text(separator="\n", strip=True)
        
        # Extract dates
        dates = extract_dates_from_text(text)
        
        # Use abstract deadline if no CFP deadline found
        if not dates["cfp_deadline"] and dates["abstract_deadline"]:
            dates["cfp_deadline"] = dates["abstract_deadline"]
        
        cfp_deadline = dates["cfp_deadline"] or "TBA"
        
        # Check if this is a multi-cycle conference
        cycle_keywords = ["cycle", "round", "deadline 1", "deadline 2", "spring", "fall", "summer", "winter"]
        has_multiple_cycles = any(keyword in text.lower() for keyword in cycle_keywords)
        
        # Conference dates
        conf_dates = []
        if dates["conference_start"]:
            conf_dates.append(dates["conference_start"])
        if dates["conference_end"] and dates["conference_end"] != dates["conference_start"]:
            conf_dates.append(dates["conference_end"])
        conference_dates = " to ".join(conf_dates) if conf_dates else "TBA"
        
        # Location extraction
        location = "TBA"
        location_patterns = [
            r"(?:Location|Venue|City|Place)[:\-\s]+([A-Z][A-Za-z\s,]+(?:,\s*[A-Z]{2,})?)",
            r"(?:held in|taking place in|will be in)\s+([A-Z][A-Za-z\s,]+)",
        ]
        
        for pattern in location_patterns:
            matches = re.findall(pattern, text[:5000])
            if matches:
                location = matches[0].strip()
                location = re.sub(r'\s+', ' ', location)
                if len(location) > 50:
                    continue
                break
        
        return {
            "cfp_deadline": cfp_deadline,
            "conference_dates": conference_dates,
            "location": location,
            "url": url,
            "has_multiple_cycles": has_multiple_cycles
        }
    except Exception as e:
        return {
            "cfp_deadline": "TBA",
            "conference_dates": "TBA",
            "location": "TBA",
            "url": url,
            "has_multiple_cycles": False
        }


def parse_date_flexible(date_str):
    """Parse various date formats and return datetime object"""
    if not date_str or date_str == "TBA":
        return None
    
    date_str = re.sub(r'\s+', ' ', date_str.strip())
    
    formats = [
        "%d %B %Y", "%d %b %Y",
        "%B %d %Y", "%b %d %Y",
        "%d-%B-%Y", "%d-%b-%Y",
        "%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y",
        "%A, %d %B %Y", "%A, %B %d %Y",
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    
    # Try extracting just the date part
    for pattern in [r"(\d{1,2}\s+\w+\s+\d{4})", r"(\w+\s+\d{1,2}\s+\d{4})"]:
        match = re.search(pattern, date_str)
        if match:
            for fmt in formats:
                try:
                    return datetime.strptime(match.group(1), fmt)
                except ValueError:
                    continue
    
    return None


def is_past_deadline(cfp_deadline):
    """Return True if CFP deadline is already past"""
    deadline_date = parse_date_flexible(cfp_deadline)
    if deadline_date is None:
        return False
    return deadline_date < datetime.now()


# ----------------------------
# MAIN
# ----------------------------

def main():
    # Load conferences
    try:
        with open(INPUT_FILE) as f:
            conferences = json.load(f)
        print(f"📚 Loaded {len(conferences)} conferences from {INPUT_FILE}")
    except FileNotFoundError:
        print(f"❌ ERROR: {INPUT_FILE} not found!")
        print("Please create a JSON file with format:")
        print('[{"name": "CONFERENCE_NAME", "core_rank": "A*", "base_url": "https://..."}, ...]')
        return
    except json.JSONDecodeError as e:
        print(f"❌ ERROR: Invalid JSON in {INPUT_FILE}: {e}")
        return
    
    cfp_out = []
    dates_out = []
    
    print("\n" + "="*70)
    print("🚀 Starting conference CFP scraping...")
    print("="*70)
    
    for idx, conf in enumerate(conferences, 1):
        name = conf.get("name", "Unknown")
        core_rank = conf.get("core_rank", "TBA")
        base_url = conf.get("base_url")
        
        print(f"\n[{idx}/{len(conferences)}] 🎯 Processing: {name}")
        
        current_year = YEAR
        cfp_info = None
        best_url = "TBA"
        
        # Try current year, then next year if deadline has passed
        for attempt in range(2):
            year_to_search = current_year + attempt
            print(f"  📅 Searching for {year_to_search}...")
            
            # Get potential URLs (base_url + web search + patterns)
            urls = get_candidate_urls(name, year_to_search, base_url)
            
            if not urls:
                print(f"    ⚠ No URLs found to try")
                continue
            
            # Try each URL
            found = False
            for url_idx, url in enumerate(urls[:10], 1):  # Limit to first 10 URLs
                print(f"    [{url_idx}] Trying: {url[:70]}...")
                
                cfp_info = scrape_cfp_page(url)
                
                if cfp_info["cfp_deadline"] != "TBA":
                    best_url = url
                    found = True
                    
                    # Check if deadline has passed
                    if is_past_deadline(cfp_info["cfp_deadline"]) and attempt == 0:
                        print(f"         ⏰ Deadline passed ({cfp_info['cfp_deadline']}), trying next year...")
                        break  # Try next year
                    else:
                        cycle_note = " (earliest cycle)" if cfp_info.get("has_multiple_cycles") else ""
                        print(f"         ✅ CFP deadline: {cfp_info['cfp_deadline']}{cycle_note}")
                        if cfp_info["conference_dates"] != "TBA":
                            print(f"         ✅ Conference: {cfp_info['conference_dates']}")
                        if cfp_info["location"] != "TBA":
                            print(f"         ✅ Location: {cfp_info['location']}")
                        break  # Success!
                
                time.sleep(0.5)  # Rate limiting
            
            if found and not is_past_deadline(cfp_info.get("cfp_deadline", "TBA")):
                break  # Found valid future deadline
        
        # If still no info, create default entry
        if not cfp_info or cfp_info["cfp_deadline"] == "TBA":
            print(f"    ❌ No CFP information found")
            cfp_info = {
                "cfp_deadline": "TBA",
                "conference_dates": "TBA",
                "location": "TBA"
            }
        
        # Append outputs
        cfp_note = "Earliest deadline from multiple cycles" if cfp_info.get("has_multiple_cycles") else ""
        
        cfp_out.append({
            "name": name,
            "core_rank": core_rank,
            "cfp_deadline": cfp_info["cfp_deadline"],
            "cfp_url": best_url,
            "note": cfp_note
        })
        
        dates_out.append({
            "name": name,
            "location": cfp_info["location"],
            "conference_dates": cfp_info["conference_dates"],
            "conf_url": best_url
        })
    
    # Write JSON files
    cfp_output_file = OUTPUT_DIR / "cfp.json"
    dates_output_file = OUTPUT_DIR / "confdates.json"
    
    with open(cfp_output_file, "w") as f:
        json.dump(cfp_out, f, indent=2)
    
    with open(dates_output_file, "w") as f:
        json.dump(dates_out, f, indent=2)
    
    print(f"\n{'='*70}")
    print(f"✅ Conference data updated successfully!")
    print(f"   📄 CFP deadlines: {cfp_output_file}")
    print(f"   📄 Conference dates: {dates_output_file}")
    print(f"{'='*70}\n")


if __name__ == "__main__":
    main()
