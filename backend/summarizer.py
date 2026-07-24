import re
from nlp_engine import get_stopwords

def split_sentences_fallback(text: str):
    # Simple regex fallback to split text into sentences
    sentences = re.split(r'(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\?|!)\s+', text.strip())
    return [s for s in sentences if s]

def get_sentences(text: str):
    try:
        import nltk
        try:
            return nltk.sent_tokenize(text)
        except LookupError:
            nltk.download('punkt', quiet=True)
            return nltk.sent_tokenize(text)
    except Exception:
        return split_sentences_fallback(text)

def summarize(results: list, num_sentences: int = 3, query: str = None) -> str:
    if not results:
        return "No results found."

    stop_words = get_stopwords()
    query_keywords = set()
    if query:
        # Extract query keywords
        q_words = re.findall(r'\b\w+\b', query.lower())
        query_keywords = {w for w in q_words if w not in stop_words and len(w) > 1}

    # Step 1: Collect sentences from all result snippets, identifying position inside snippet
    all_sentences = []
    sentence_idx = 0

    # Garbage patterns to filter out common web metadata lines
    garbage_keywords = {
        "cookie", "privacy policy", "click here", "read more", "min read", 
        "subscribe", "written by", "published by", "posted on", "follow us", 
        "sign up", "all rights reserved", "terms of service", "rss feed",
        "article 6 min read", "article 5 min read", "article 4 min read",
        "article 3 min read", "article 2 min read", "article 1 min read",
        "share on", "facebook", "twitter", "linkedin", "email to"
    }

    for res in results:
        snippet = res.get('snippet', '')
        if not snippet:
            continue
            
        snippet_sentences = get_sentences(snippet)
        for sub_idx, sent in enumerate(snippet_sentences):
            # Clean square bracket citations like [1] and parenthetical years like (2020)
            cleaned_sent = re.sub(r'\[\d+\]', '', sent)
            cleaned_sent = re.sub(r'\(\s*\d{4}\s*\)', '', cleaned_sent)
            cleaned_sent = cleaned_sent.strip()
            
            # Basic sanity checks (minimum length and basic content check)
            if not cleaned_sent or len(cleaned_sent.split()) < 6:
                continue
                
            # Filter garbage metadata sentences
            sent_lower = cleaned_sent.lower()
            if any(pattern in sent_lower for pattern in garbage_keywords):
                continue
                
            all_sentences.append({
                "original": cleaned_sent,
                "is_first_in_snippet": (sub_idx == 0),
                "global_idx": sentence_idx
            })
            sentence_idx += 1

    if not all_sentences:
        return "No content to summarize."

    if len(all_sentences) <= num_sentences:
        return " ".join([s["original"] for s in all_sentences])

    # Step 2: Compute word frequencies across all collected sentences
    text_corpus = " ".join([s["original"] for s in all_sentences])
    all_words = re.findall(r'\b\w+\b', text_corpus.lower())
    
    freq_dict = {}
    for word in all_words:
        if word not in stop_words and len(word) > 1:
            freq_dict[word] = freq_dict.get(word, 0) + 1

    # Step 3: Score sentences
    scored_sentences = []
    for sent in all_sentences:
        sent_words = re.findall(r'\b\w+\b', sent["original"].lower())
        word_count = len(sent_words)
        
        # Penalize sentences that are too long/short to avoid metadata list noise
        if word_count < 6 or word_count > 45:
            score = 0
        else:
            # Base frequency score
            score = sum(freq_dict.get(w, 0) for w in sent_words if w in freq_dict)
            
            # Boost if first sentence in snippet (highly informative topic sentences)
            if sent["is_first_in_snippet"]:
                score += 5.0
                
            # Boost if contains query keywords (query relevance)
            matches = sum(1 for w in sent_words if w in query_keywords)
            score += matches * 3.0

        scored_sentences.append((score, sent["global_idx"], sent["original"]))

    # Step 4: Extract top sentences and re-sort by global index for readability
    top_sentences = sorted(scored_sentences, key=lambda x: x[0], reverse=True)[:num_sentences]
    top_sentences_ordered = sorted(top_sentences, key=lambda x: x[1])

    summary = " ".join([item[2] for item in top_sentences_ordered])
    return summary
