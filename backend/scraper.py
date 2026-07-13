def scrape_duckduckgo(query: str):
    # Stub: Normally we'd use requests + BeautifulSoup here to fetch DDG html.
    # For now, return mock data.
    return [
        {"title": f"Result for {query}", "snippet": f"This is a simulated result for {query}.", "url": "https://example.com/1"},
        {"title": f"More info on {query}", "snippet": f"Here is some more detailed simulated info regarding {query}.", "url": "https://example.com/2"}
    ]
