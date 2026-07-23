import requests
from bs4 import BeautifulSoup
import urllib.parse

def scrape_duckduckgo(query: str):
    url = "https://html.duckduckgo.com/html/"
    params = {"q": query}
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    try:
        response = requests.post(url, data=params, headers=headers, timeout=10)
        response.raise_for_status()
    except Exception as e:
        print(f"Error fetching DuckDuckGo results: {e}")
        return []

    soup = BeautifulSoup(response.text, "html.parser")
    results = []

    for result_el in soup.select(".result"):
        title_el = result_el.select_one(".result__title a")
        snippet_el = result_el.select_one(".result__snippet")

        if not title_el:
            continue

        title = title_el.text.strip()
        raw_href = title_el.get("href", "")
        snippet = snippet_el.text.strip() if snippet_el else ""

        # Decode DuckDuckGo redirect link if present
        actual_url = raw_href
        if raw_href:
            parsed = urllib.parse.urlparse(raw_href)
            if parsed.path == '/l/':
                qs = urllib.parse.parse_qs(parsed.query)
                if 'uddg' in qs:
                    actual_url = qs['uddg'][0]
            elif raw_href.startswith('/'):
                actual_url = f"https://duckduckgo.com{raw_href}"

        results.append({
            "title": title,
            "snippet": snippet,
            "url": actual_url
        })

    return results
