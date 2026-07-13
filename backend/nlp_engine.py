import re

def extract_keywords(query: str):
    # Basic stub: remove stop words
    stop_words = {"what", "is", "the", "how", "to", "do", "i", "a", "an", "of", "and"}
    words = re.findall(r'\b\w+\b', query.lower())
    keywords = [w for w in words if w not in stop_words]
    return keywords if keywords else ["default", "query"]
