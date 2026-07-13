def summarize(results: list) -> str:
    if not results:
        return "No results found."
    # Stub: Combine snippets
    combined = " ".join([r['snippet'] for r in results])
    return f"Summary: {combined}"
