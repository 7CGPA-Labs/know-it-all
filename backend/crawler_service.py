import os
import re
import json
import urllib.parse
import requests
from bs4 import BeautifulSoup
from jinja2 import Environment, FileSystemLoader
from pydbus import SessionBus
from gi.repository import GLib

# --- Natural Language Helpers (Previously nlp_engine.py / sent_tokenize) ---

def get_stopwords():
    return {
        "i", "me", "my", "myself", "we", "our", "ours", "ourselves", "you", "your", "yours", 
        "yourself", "yourselves", "he", "him", "his", "himself", "she", "her", "hers", "herself", 
        "it", "its", "itself", "they", "them", "their", "theirs", "themselves", "what", "which", 
        "who", "whom", "this", "that", "these", "those", "am", "is", "are", "was", "were", "be", 
        "been", "being", "have", "has", "had", "having", "do", "does", "did", "doing", "a", "an", 
        "the", "and", "but", "if", "or", "because", "as", "until", "while", "of", "at", "by", 
        "for", "with", "about", "against", "between", "into", "through", "during", "before", 
        "after", "above", "below", "to", "from", "up", "down", "in", "out", "on", "off", "over", 
        "under", "again", "further", "then", "once", "here", "there", "when", "where", "why", 
        "how", "all", "any", "both", "each", "few", "more", "most", "other", "some", "such", 
        "no", "nor", "not", "only", "own", "same", "so", "than", "too", "very", "s", "t", "can", 
        "will", "just", "don", "should", "now", "d", "ll", "m", "o", "re", "ve", "y", "ain", 
        "aren", "couldn", "didn", "doesn", "hadn", "hasn", "haven", "isn", "ma", "mightn", 
        "mustn", "needn", "shan", "shouldn", "wasn", "weren", "won", "wouldn"
    }

def get_keywords_query(query: str) -> str:
    stop_words = get_stopwords()
    q_words = re.findall(r'\b\w+\b', query.lower())
    keywords = [w for w in q_words if w not in stop_words and len(w) > 1]
    return " ".join(keywords) if keywords else query

def split_sentences_fallback(text: str):
    sentences = re.split(r'(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\?|!)\s+', text.strip())
    return [s for s in sentences if s]

def get_sentences(text: str):
    # Pure Python sentence tokenizer fallback to completely eliminate NLTK dependency
    return split_sentences_fallback(text)


# --- Web Search Scraper (Previously scraper.py) ---

def scrape_duckduckgo(query: str, search_results_holder: list = None) -> list:
    keywords = get_keywords_query(query)
    url = "https://html.duckduckgo.com/html/"
    params = {"q": keywords}
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    results = []
    try:
        response = requests.post(url, data=params, headers=headers, timeout=10)
        if response.status_code != 200:
            return []
            
        soup = BeautifulSoup(response.text, 'html.parser')
        for result_el in soup.select(".result"):
            title_el = result_el.select_one(".result__title a")
            snippet_el = result_el.select_one(".result__snippet")
            
            if title_el:
                title = title_el.text.strip()
                raw_href = title_el.get("href", "")
                snippet = snippet_el.text.strip() if snippet_el else ""
                
                # Decode DuckDuckGo redirect link
                actual_url = raw_href
                if raw_href:
                    parsed = urllib.parse.urlparse(raw_href)
                    if parsed.path == '/l/':
                        qs = urllib.parse.parse_qs(parsed.query)
                        if 'uddg' in qs:
                            actual_url = qs['uddg'][0]
                    elif raw_href.startswith('/'):
                        actual_url = f"https://duckduckgo.com{raw_href}"
                        
                res_dict = {
                    "title": title,
                    "url": actual_url,
                    "snippet": snippet
                }
                results.append(res_dict)
                if search_results_holder is not None:
                    search_results_holder.append(res_dict)
    except Exception as e:
        print(f"Error fetching DuckDuckGo results: {e}")
        
    return results


# --- Mathematical Expression Sidekick ---

def evaluate_expression(expr: str) -> str:
    expr = expr.strip().strip('"').strip("'")
    # Strict regex validation to prevent code injection
    clean_expr = re.sub(r'[^0-9+\-*/%().\s]', '', expr)
    if not clean_expr.strip():
        return "Error: Empty or invalid expression."
    try:
        result = eval(clean_expr, {"__builtins__": None}, {})
        return str(result)
    except Exception as e:
        return f"Error: {e}"


# --- ML Caching & Pipeline Helpers (Previously summarizer.py) ---

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

def run_reranker_sidekick(query: str, context: str, config: dict) -> str:
    sentences = [s for s in get_sentences(context) if len(s.split()) >= 6]
    if not sentences:
        return "No content to rerank."
        
    embed_model = get_sentence_transformer(config["sidekicks"]["embedding"])
    from sentence_transformers import util
    query_emb = embed_model.encode(query, convert_to_tensor=True)
    sentence_embs = embed_model.encode(sentences, convert_to_tensor=True)
    scores = util.cos_sim(query_emb, sentence_embs)[0]
    scores_list = scores.tolist() if hasattr(scores, 'tolist') else list(scores)
    
    scored_sents = sorted(zip(scores_list, sentences), key=lambda x: x[0], reverse=True)[:10]
    
    reranker = get_cross_encoder(config["sidekicks"]["reranker"])
    pairs = [(query, item[1]) for item in scored_sents]
    preds = reranker.predict(pairs)
    scores = preds.tolist() if hasattr(preds, 'tolist') else list(preds)
    
    reranked_sents = sorted(zip(scores, [item[1] for item in scored_sents]), key=lambda x: x[0], reverse=True)[:8]
    return " ".join([item[1] for item in reranked_sents])

def run_intent_classifier_sidekick(query: str, config: dict) -> str:
    verifier = get_cross_encoder(config["sidekicks"]["verifier"])
    hypotheses = [
        "This query is asking for a mathematical calculation or calculation of numbers.",
        "This query is asking for real-time facts, news, or general search information.",
        "This query is a conversational prompt, greeting, or request for general writing."
    ]
    pairs = [(query, hyp) for hyp in hypotheses]
    preds = verifier.predict(pairs)
    scores = preds.tolist() if hasattr(preds, 'tolist') else list(preds)
    
    entailment_scores = [score_array[1] for score_array in scores]
    max_idx = entailment_scores.index(max(entailment_scores))
    intents = ["math", "search", "chat"]
    print(f"Classifier Intent Routing: query='{query}' classified as {intents[max_idx]} (scores: math={entailment_scores[0]:.2f}, search={entailment_scores[1]:.2f}, chat={entailment_scores[2]:.2f})")
    return intents[max_idx]

def run_verifier_sidekick(query: str, context: str, config: dict) -> str:
    sentences = [s for s in get_sentences(context) if len(s.split()) >= 6]
    if not sentences:
        return "No content to verify."
        
    verifier = get_cross_encoder(config["sidekicks"]["verifier"])
    # Transformed hypothesis mapping to ensure NLI evaluates questions correctly
    nli_pairs = [(sent, f"This text provides information about: {query}") for sent in sentences]
    preds = verifier.predict(nli_pairs)
    scores = preds.tolist() if hasattr(preds, 'tolist') else list(preds)
    
    verified = []
    for scores_array, sent in zip(scores, sentences):
        contradiction = scores_array[0]
        entailment = scores_array[1]
        neutral = scores_array[2]
        
        if contradiction > entailment and contradiction > neutral:
            continue
        verified.append(sent)
        
    if not verified:
        return "No facts could be verified."
    return " ".join(verified[:6])

def run_hallucination_guardrail(generated_text: str, context: str, config: dict) -> str:
    gen_sentences = [s for s in get_sentences(generated_text) if len(s.split()) >= 3]
    if not gen_sentences:
        return generated_text
        
    verifier = get_cross_encoder(config["sidekicks"]["verifier"])
    nli_pairs = [(context, sent) for sent in gen_sentences]
    preds = verifier.predict(nli_pairs)
    scores = preds.tolist() if hasattr(preds, 'tolist') else list(preds)
    
    clean_sentences = []
    for scores_array, sent in zip(scores, gen_sentences):
        contradiction = scores_array[0]
        entailment = scores_array[1]
        neutral = scores_array[2]
        
        if contradiction > entailment and contradiction > neutral:
            print(f"Hallucination Guardrail: Filtering out unsupported sentence: '{sent}'")
            continue
        clean_sentences.append(sent)
        
    return " ".join(clean_sentences) if clean_sentences else generated_text

# --- Classical Extractive Fallback ---

def summarize_classical(results: list, num_sentences: int, query: str) -> str:
    if not results:
        return "No results found."
    all_sentences = []
    sentence_idx = 0
    stop_words = get_stopwords()
    
    q_words = re.findall(r'\b\w+\b', query.lower())
    query_keywords = {w for w in q_words if w not in stop_words and len(w) > 1}
    
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
            
        for sub_idx, sent in enumerate(get_sentences(snippet)):
            cleaned_sent = re.sub(r'\[\d+\]', '', sent)
            cleaned_sent = re.sub(r'\(\s*\d{4}\s*\)', '', cleaned_sent).strip()
            
            if not cleaned_sent or len(cleaned_sent.split()) < 6:
                continue
                
            if any(pattern in cleaned_sent.lower() for pattern in garbage_keywords):
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


# --- Non-Sequential ReAct Agent Loop ---

def clean_final_response(response: str) -> str:
    # 1. Check for Action: FinalAnswer
    match = re.search(r'Action:\s*FinalAnswer\((.*)\)', response, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip().strip('"').strip("'")
        
    # 2. General Action: Name(...) fallback
    match_any = re.search(r'Action:\s*\w+\((.*)\)', response, re.DOTALL)
    if match_any:
        arg = match_any.group(1).strip().strip('"').strip("'")
        if "," in arg:
            parts = arg.split(",", 1)
            return parts[1].strip().strip('"').strip("'")
        return arg
        
    # 3. If no Action: block exists, but there is a Thought: block, return the text after "Thought:"
    if "Thought:" in response:
        final_match = re.search(r'FinalAnswer:\s*(.*)', response, re.DOTALL | re.IGNORECASE)
        if final_match:
            return final_match.group(1).strip()
            
        thought_match = re.search(r'Thought:\s*(.*)', response, re.DOTALL | re.IGNORECASE)
        if thought_match:
            content = thought_match.group(1).strip()
            content = re.sub(r'Action:\s*.*', '', content, flags=re.DOTALL).strip()
            return content
            
    return response

def run_agent_loop(query: str, config: dict, search_results_holder: list, initial_context: str = "", intent: str = "search") -> str:
    # 1. Resolve math queries directly
    if intent == "math":
        math_expr_match = re.search(r'([0-9+\-*/%().\s]+)', query)
        expr = math_expr_match.group(1).strip() if math_expr_match else query
        return evaluate_expression(expr)
        
    # 2. Resolve general chat directly
    if intent == "chat":
        boss_model, boss_tokenizer = get_boss_generator(config["main_boss"])
        messages = [
            {"role": "system", "content": "You are a helpful local assistant. Answer the user query naturally and concisely. Keep it under 2-3 sentences."},
            {"role": "user", "content": query}
        ]
        prompt = boss_tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        inputs = boss_tokenizer([prompt], return_tensors="pt")
        outputs = boss_model.generate(
            inputs["input_ids"],
            max_new_tokens=150,
            do_sample=True,
            temperature=0.7,
            pad_token_id=boss_tokenizer.eos_token_id
        )
        gen_ids = [output_ids[len(input_ids):] for input_ids, output_ids in zip(inputs["input_ids"], outputs)]
        return boss_tokenizer.batch_decode(gen_ids, skip_special_tokens=True)[0].strip()

    # 3. Search intent (Factual RAG pipeline)
    if not initial_context:
        return "No search results found."
        
    # Preprocessing with Sidekicks (Rerank + Verify)
    ranked_context = run_reranker_sidekick(query, initial_context, config)
    verified_context = run_verifier_sidekick(query, ranked_context, config)
    
    boss_model, boss_tokenizer = get_boss_generator(config["main_boss"])
    
    # --- Turn 1: Initial Generation ---
    system_prompt = (
        "You are a helpful local assistant. Write a detailed, comprehensive, and highly cohesive summary of the provided Context to answer the user Query. "
        "Do not mention any website metadata, citations, or irrelevant details. Answer in detail in multiple lines."
    )
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Context: {verified_context}\n\nQuery: {query}"}
    ]
    prompt = boss_tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    inputs = boss_tokenizer([prompt], return_tensors="pt")
    outputs = boss_model.generate(
        inputs["input_ids"],
        max_new_tokens=300,
        do_sample=True,
        temperature=0.7,
        pad_token_id=boss_tokenizer.eos_token_id
    )
    gen_ids = [output_ids[len(input_ids):] for input_ids, output_ids in zip(inputs["input_ids"], outputs)]
    summary_text = boss_tokenizer.batch_decode(gen_ids, skip_special_tokens=True)[0].strip()
    
    print(f"Agent Turn 1 (Initial): {summary_text}")
    
    # --- Turn 2: Reflection & Self-Correction (Cognitive Back-and-Forth) ---
    gen_sentences = [s for s in get_sentences(summary_text) if len(s.split()) >= 3]
    if gen_sentences:
        verifier = get_cross_encoder(config["sidekicks"]["verifier"])
        nli_pairs = [(verified_context, sent) for sent in gen_sentences]
        preds = verifier.predict(nli_pairs)
        scores = preds.tolist() if hasattr(preds, 'tolist') else list(preds)
        
        hallucinated_sents = []
        for scores_array, sent in zip(scores, gen_sentences):
            contradiction = scores_array[0]
            entailment = scores_array[1]
            neutral = scores_array[2]
            if contradiction > entailment and contradiction > neutral:
                hallucinated_sents.append(sent)
                
        if hallucinated_sents:
            # Warn Qwen about the hallucinations and ask it to self-correct
            warning_msg = (
                f"Your previous response was: '{summary_text}'\n\n"
                f"Warning: The following statements contradict the verified facts: '{' '.join(hallucinated_sents)}'. "
                f"Please rewrite your answer, correcting these statements based strictly on the context below:\n"
                f"Context: {verified_context}"
            )
            print(f"Hallucination Guardrail: Warning boss to self-correct on: {hallucinated_sents}")
            
            messages.append({"role": "assistant", "content": summary_text})
            messages.append({"role": "user", "content": warning_msg})
            
            prompt = boss_tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
            inputs = boss_tokenizer([prompt], return_tensors="pt")
            outputs = boss_model.generate(
                inputs["input_ids"],
                max_new_tokens=300,
                do_sample=True,
                temperature=0.7,
                pad_token_id=boss_tokenizer.eos_token_id
            )
            gen_ids = [output_ids[len(input_ids):] for input_ids, output_ids in zip(inputs["input_ids"], outputs)]
            summary_text = boss_tokenizer.batch_decode(gen_ids, skip_special_tokens=True)[0].strip()
            
            print(f"Agent Turn 2 (Self-Corrected): {summary_text}")
            
    return run_hallucination_guardrail(summary_text, verified_context, config)


# --- D-Bus Service (Previously crawler_service.py) ---

class CrawlerService(object):
    """
      <node>
        <interface name='org.knowitall.CrawlerService'>
          <method name='AskQuestion'>
            <arg type='s' name='query' direction='in'/>
            <arg type='s' name='response' direction='out'/>
          </method>
        </interface>
      </node>
    """

    def __init__(self):
        template_dir = os.path.join(os.path.dirname(__file__), 'templates')
        self.jinja_env = Environment(loader=FileSystemLoader(template_dir))

    def AskQuestion(self, query):
        print(f"Received query: {query}")
        
        # Load config file
        config_path = os.path.join(os.path.dirname(__file__), 'config.json')
        config = {}
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    config = json.load(f)
            except Exception:
                pass
                
        # Defaults
        if "sidekicks" not in config:
            config["sidekicks"] = {
                "embedding": "sentence-transformers/all-MiniLM-L6-v2",
                "reranker": "cross-encoder/ms-marco-MiniLM-L-6-v2",
                "verifier": "cross-encoder/nli-distilroberta-base"
            }
        if "main_boss" not in config:
            config["main_boss"] = "Qwen/Qwen2.5-0.5B-Instruct"

        search_results_holder = []
        summary_text = ""
        
        if _ml_pipeline_enabled:
            try:
                # 1. Run classifier sidekick to route query intent
                intent = run_intent_classifier_sidekick(query, config)
                
                initial_ctx = ""
                if intent == "search":
                    # Pre-populate context at Turn 0 using Keyword Extractor + Scraper
                    search_keywords = get_keywords_query(query)
                    search_results_holder = scrape_duckduckgo(search_keywords)
                    if search_results_holder:
                        initial_ctx = " ".join([res["snippet"] for res in search_results_holder])
                        
                # 2. Invoke the self-correcting ReAct Agent loop
                summary_text = run_agent_loop(query, config, search_results_holder, initial_ctx, intent)
            except Exception as e:
                print(f"ML Pipeline error (falling back to classical): {e}")
                
        if not summary_text:
            # Classical extractive fallback (Informant + Summarizer fallback)
            search_results_holder = scrape_duckduckgo(query)
            summary_text = summarize_classical(search_results_holder, 3, query)
            
        # Format HTML with Jinja2
        template = self.jinja_env.get_template('response.jinja2')
        html_response = template.render(
            query=query,
            summary=summary_text,
            sources=search_results_holder[:3]
        )
        return html_response


if __name__ == '__main__':
    bus = SessionBus()
    bus.publish('org.knowitall.CrawlerService', CrawlerService())
    
    loop = GLib.MainLoop()
    print("CrawlerService running...")
    loop.run()
