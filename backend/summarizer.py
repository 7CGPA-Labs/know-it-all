import re
import os
import json
from nlp_engine import get_stopwords

# Fallback sentence tokenization
def split_sentences_fallback(text: str):
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

# Cache loaded ML models to avoid reloading on every D-Bus call
_cached_models = {}
_ml_pipeline_enabled = os.environ.get("KNOWITALL_TESTING") != "1"

def get_sentence_transformer(model_name):
    if model_name not in _cached_models:
        from sentence_transformers import SentenceTransformer
        _cached_models[model_name] = SentenceTransformer(model_name)
    return _cached_models[model_name]

def get_cross_encoder(model_name):
    if model_name not in _cached_models:
        from sentence_transformers import CrossEncoder
        _cached_models[model_name] = CrossEncoder(model_name)
    return _cached_models[model_name]

def get_boss_generator(model_name):
    if model_name not in _cached_models:
        from transformers import AutoModelForCausalLM, AutoTokenizer
        tokenizer = AutoTokenizer.from_pretrained(model_name)
        model = AutoModelForCausalLM.from_pretrained(model_name)
        _cached_models[model_name] = (model, tokenizer)
    return _cached_models[model_name]

def summarize_classical(results: list, num_sentences: int, query: str, stop_words, query_keywords) -> str:
    # Preprocess and score sentences using word frequencies (classical fallback)
    all_sentences = []
    sentence_idx = 0
    garbage_keywords = {
        "cookie", "privacy policy", "click here", "read more", "min read", 
        "subscribe", "written by", "published by", "posted on", "follow us", 
        "sign up", "all rights reserved", "terms of service", "rss feed",
        "share on", "facebook", "twitter", "linkedin", "email to"
    }

    for res in results:
        snippet = res.get('snippet', '')
        if not snippet:
            continue
            
        snippet_sentences = get_sentences(snippet)
        for sub_idx, sent in enumerate(snippet_sentences):
            cleaned_sent = re.sub(r'\[\d+\]', '', sent)
            cleaned_sent = re.sub(r'\(\s*\d{4}\s*\)', '', cleaned_sent)
            cleaned_sent = cleaned_sent.strip()
            
            if not cleaned_sent or len(cleaned_sent.split()) < 6:
                continue
                
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

    text_corpus = " ".join([s["original"] for s in all_sentences])
    all_words = re.findall(r'\b\w+\b', text_corpus.lower())
    
    freq_dict = {}
    for word in all_words:
        if word not in stop_words and len(word) > 1:
            freq_dict[word] = freq_dict.get(word, 0) + 1

    scored_sentences = []
    for sent in all_sentences:
        sent_words = re.findall(r'\b\w+\b', sent["original"].lower())
        word_count = len(sent_words)
        
        if word_count < 6 or word_count > 45:
            score = 0
        else:
            score = sum(freq_dict.get(w, 0) for w in sent_words if w in freq_dict)
            if sent["is_first_in_snippet"]:
                score += 5.0
            matches = sum(1 for w in sent_words if w in query_keywords)
            score += matches * 3.0

        scored_sentences.append((score, sent["global_idx"], sent["original"]))

    top_sentences = sorted(scored_sentences, key=lambda x: x[0], reverse=True)[:num_sentences]
    top_sentences_ordered = sorted(top_sentences, key=lambda x: x[1])

    return " ".join([item[2] for item in top_sentences_ordered])


def summarize_with_ml_pipeline(results: list, query: str, config: dict) -> str:
    from sentence_transformers import util
    
    # Collect flat list of sentences from snippets
    all_sentences = []
    sentence_idx = 0
    for res in results:
        snippet = res.get('snippet', '')
        if not snippet:
            continue
        for sub_idx, sent in enumerate(get_sentences(snippet)):
            cleaned_sent = re.sub(r'\[\d+\]', '', sent)
            cleaned_sent = re.sub(r'\(\s*\d{4}\s*\)', '', cleaned_sent).strip()
            if len(cleaned_sent.split()) < 6:
                continue
            all_sentences.append({
                "original": cleaned_sent,
                "global_idx": sentence_idx
            })
            sentence_idx += 1

    if not all_sentences:
        return "No content to summarize."

    # Stage 1: Semantic Filtering (Embedding Sidekick)
    embed_model = get_sentence_transformer(config["sidekicks"]["embedding"])
    sentences_text = [s["original"] for s in all_sentences]
    
    query_emb = embed_model.encode(query, convert_to_tensor=True)
    sentence_embs = embed_model.encode(sentences_text, convert_to_tensor=True)
    
    scores = util.cos_sim(query_emb, sentence_embs)[0].tolist()
    scored_sents = sorted(zip(scores, all_sentences), key=lambda x: x[0], reverse=True)[:10]
    
    # Stage 2: Cross-Encoder Reranking Sidekick
    reranker = get_cross_encoder(config["sidekicks"]["reranker"])
    pairs = [(query, item[1]["original"]) for item in scored_sents]
    rerank_preds = reranker.predict(pairs)
    rerank_scores = rerank_preds.tolist() if hasattr(rerank_preds, 'tolist') else list(rerank_preds)
    
    reranked_sents = sorted(zip(rerank_scores, [item[1] for item in scored_sents]), key=lambda x: x[0], reverse=True)[:5]
    
    # Stage 3: NLI Verification Sidekick
    verifier = get_cross_encoder(config["sidekicks"]["verifier"])
    nli_pairs = [(item[1]["original"], query) for item in reranked_sents]
    nli_preds = verifier.predict(nli_pairs)
    nli_scores = nli_preds.tolist() if hasattr(nli_preds, 'tolist') else list(nli_preds)
    
    verified_sents = []
    for scores_array, item in zip(nli_scores, reranked_sents):
        # nli-distilroberta-base classes: 0=contradiction, 1=entailment, 2=neutral
        contradiction = scores_array[0]
        entailment = scores_array[1]
        neutral = scores_array[2]
        
        # Filter out contradiction if it is strictly dominant
        if contradiction > entailment and contradiction > neutral:
            print(f"Fact Check Alert: Filtering contradictory sentence: {item[1]['original']}")
            continue
        verified_sents.append(item[1])

    if not verified_sents:
        # Fallback to the top reranked sentence if all got filtered out by NLI
        verified_sents = [reranked_sents[0][1]]

    # Stage 4: Generative Synthesis (Main Boss Qwen)
    boss_model, boss_tokenizer = get_boss_generator(config["main_boss"])
    
    # Sort verified sentences by original order for contextual flow
    verified_sents_ordered = sorted(verified_sents, key=lambda x: x["global_idx"])
    context = " ".join([s["original"] for s in verified_sents_ordered])
    
    messages = [
        {
            "role": "system", 
            "content": "You are a helpful local assistant. Write a short, highly cohesive, and natural summary of the provided Context to answer the user Query. Do not mention any website metadata, citations, or irrelevant details. Keep the final response under 3-4 sentences."
        },
        {
            "role": "user", 
            "content": f"Context: {context}\n\nQuery: {query}"
        }
    ]
    
    prompt = boss_tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    inputs = boss_tokenizer([prompt], return_tensors="pt")
    
    # Generate on CPU
    outputs = boss_model.generate(
        inputs["input_ids"],
        max_new_tokens=150,
        do_sample=True,
        temperature=0.7,
        top_p=0.9,
        pad_token_id=boss_tokenizer.eos_token_id
    )
    
    # Decode generation outputs only
    gen_ids = [output_ids[len(input_ids):] for input_ids, output_ids in zip(inputs["input_ids"], outputs)]
    summary = boss_tokenizer.batch_decode(gen_ids, skip_special_tokens=True)[0].strip()
    return summary


def summarize(results: list, num_sentences: int = 3, query: str = None) -> str:
    if not results:
        return "No results found."

    stop_words = get_stopwords()
    query_keywords = set()
    if query:
        q_words = re.findall(r'\b\w+\b', query.lower())
        query_keywords = {w for w in q_words if w not in stop_words and len(w) > 1}

    # Load config file
    config_path = os.path.join(os.path.dirname(__file__), 'config.json')
    config = {}
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
        except Exception:
            pass
            
    # Default configs
    if "sidekicks" not in config:
        config["sidekicks"] = {
            "embedding": "sentence-transformers/all-MiniLM-L6-v2",
            "reranker": "cross-encoder/ms-marco-MiniLM-L-6-v2",
            "verifier": "cross-encoder/nli-distilroberta-base"
        }
    if "main_boss" not in config:
        config["main_boss"] = "Qwen/Qwen2.5-0.5B-Instruct"

    # Execute ML pipeline if enabled
    if _ml_pipeline_enabled:
        try:
            return summarize_with_ml_pipeline(results, query or "", config)
        except Exception as e:
            print(f"ML Pipeline error (falling back to classical): {e}")

    # Fallback to classical extractive method
    return summarize_classical(results, num_sentences, query or "", stop_words, query_keywords)
