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
    
    reranked_sents = sorted(zip(scores, [item[1] for item in scored_sents]), key=lambda x: x[0], reverse=True)[:3]
    return " ".join([item[1] for item in reranked_sents])

def run_verifier_sidekick(query: str, context: str, config: dict) -> str:
    sentences = [s for s in get_sentences(context) if len(s.split()) >= 6]
    if not sentences:
        return "No content to verify."
        
    verifier = get_cross_encoder(config["sidekicks"]["verifier"])
    nli_pairs = [(s, query) for s in sentences]
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
    return " ".join(verified[:3])


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
    # Safely extract inner arguments if the model ends on a raw Action string
    match = re.search(r'Action:\s*\w+\((.*)\)', response, re.DOTALL)
    if match:
        arg = match.group(1).strip().strip('"').strip("'")
        if "," in arg:
            parts = arg.split(",", 1)
            # Try to get the second argument (the text context/response) if present
            return parts[1].strip().strip('"').strip("'")
        return arg
    return response

def run_agent_loop(query: str, config: dict, search_results_holder: list) -> str:
    system_prompt = (
        "You are a helpful local assistant. Solve the user query step-by-step by generating Thoughts and Actions.\n"
        "Available actions:\n"
        "- Scrape(query): Searches the web for query terms and returns snippet text.\n"
        "- Calculate(expression): Solves a simple mathematical expression (e.g. 5+5, 12*4).\n"
        "- Rerank(query, text): Reranks sentences in text and returns the top 3 relevant sentences.\n"
        "- Verify(query, text): Verifies facts in text, filtering out contradictions.\n"
        "- FinalAnswer(response): Concludes and outputs the final answer to the user.\n\n"
        "You MUST respond in the following format:\n"
        "Thought: <your reasoning>\n"
        "Action: <ActionName>(<arguments>)\n\n"
        "Example:\n"
        "Thought: I need to search the web for python.\n"
        "Action: Scrape(\"python programming\")"
    )
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Query: {query}"}
    ]
    
    current_context = ""
    
    for turn in range(3):
        boss_model, boss_tokenizer = get_boss_generator(config["main_boss"])
        prompt = boss_tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        inputs = boss_tokenizer([prompt], return_tensors="pt")
        
        outputs = boss_model.generate(
            inputs["input_ids"],
            max_new_tokens=150,
            do_sample=True,
            temperature=0.7,
            top_p=0.9,
            pad_token_id=boss_tokenizer.eos_token_id
        )
        
        gen_ids = [output_ids[len(input_ids):] for input_ids, output_ids in zip(inputs["input_ids"], outputs)]
        assistant_resp = boss_tokenizer.batch_decode(gen_ids, skip_special_tokens=True)[0].strip()
        
        print(f"Agent Turn {turn+1}: {assistant_resp}")
        
        # Parse thought and action
        action_match = re.search(r'Action:\s*(\w+)\((.*)\)', assistant_resp)
        if not action_match:
            # Fallback parsing for 0.5B model inconsistencies
            action_names = ["Scrape", "Calculate", "Rerank", "Verify", "FinalAnswer"]
            found = False
            for name in action_names:
                if name in assistant_resp:
                    inner_match = re.search(fr'{name}\s*[\(\"\']+(.*?)[\)\"\']+', assistant_resp)
                    if inner_match:
                        action_name = name
                        action_args = inner_match.group(1)
                        found = True
                        break
            if not found:
                return assistant_resp
        else:
            action_name = action_match.group(1)
            action_args = action_match.group(2).strip().strip('"').strip("'")
            
        messages.append({"role": "assistant", "content": assistant_resp})
        
        if action_name == "FinalAnswer":
            return action_args
        elif action_name == "Scrape":
            results = scrape_duckduckgo(action_args, search_results_holder)
            if results:
                observation = " ".join([res["snippet"] for res in results])
                current_context = observation
                obs_text = f"Observation: Scraped content: {observation[:800]}..."
            else:
                obs_text = "Observation: No search results found."
        elif action_name == "Calculate":
            result = evaluate_expression(action_args)
            obs_text = f"Observation: Calculation result is: {result}"
        elif action_name == "Rerank":
            text_to_rank = action_args if action_args else current_context
            ranked_sentences = run_reranker_sidekick(query, text_to_rank, config)
            obs_text = f"Observation: Reranked sentences: {ranked_sentences}"
        elif action_name == "Verify":
            text_to_verify = action_args if action_args else current_context
            verified_sentences = run_verifier_sidekick(query, text_to_verify, config)
            obs_text = f"Observation: Verified sentences: {verified_sentences}"
        else:
            obs_text = f"Observation: Unknown action {action_name}."
            
        messages.append({"role": "user", "content": obs_text})
        
    return clean_final_response(assistant_resp)


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
                summary_text = run_agent_loop(query, config, search_results_holder)
            except Exception as e:
                print(f"ML Agent loop error (falling back to classical): {e}")
                
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
