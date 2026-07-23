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

def summarize(results: list, num_sentences: int = 3) -> str:
    if not results:
        return "No results found."
    
    # Combine snippets into a single text body
    snippets = [r.get('snippet', '') for r in results if r.get('snippet')]
    if not snippets:
        return "No content to summarize."
        
    text = " ".join(snippets)
    
    # Tokenize into sentences
    sentences = get_sentences(text)
    if len(sentences) <= num_sentences:
        return text

    # Compute word frequencies across the whole text
    stop_words = get_stopwords()
    words = re.findall(r'\b\w+\b', text.lower())
    
    freq_dict = {}
    for word in words:
        if word not in stop_words and len(word) > 1:
            freq_dict[word] = freq_dict.get(word, 0) + 1
            
    # Score sentences
    sentence_scores = []
    for idx, sentence in enumerate(sentences):
        sentence_words = re.findall(r'\b\w+\b', sentence.lower())
        score = sum(freq_dict.get(w, 0) for w in sentence_words if w in freq_dict)
        sentence_scores.append((score, idx, sentence))
        
    # Sort by score descending to find the top scoring sentences
    top_sentences = sorted(sentence_scores, key=lambda x: x[0], reverse=True)[:num_sentences]
    
    # Re-sort the top sentences by original index to keep flow/ordering
    top_sentences_ordered = sorted(top_sentences, key=lambda x: x[1])
    
    summary = " ".join([item[2] for item in top_sentences_ordered])
    return summary
