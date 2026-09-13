import os
import sys
import logging
from typing import Optional
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import trafilatura
import markdown

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("gedit-research-daemon")

app = FastAPI(title="Gedit AI Research & Markdown Copilot Daemon", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Models and generator initialization
MODEL_DIR = Path(os.environ.get("MODEL_DIR", Path(__file__).parent / "models" / "qwen2.5-0.5b-onnx"))
genai_model = None
genai_tokenizer = None

def load_onnx_model():
    global genai_model, genai_tokenizer
    if MODEL_DIR.exists() and (MODEL_DIR / "genai_config.json").exists():
        try:
            import onnxruntime_genai as og
            logger.info(f"Loading ONNX Runtime GenAI model from {MODEL_DIR}...")
            genai_model = og.Model(str(MODEL_DIR))
            genai_tokenizer = og.Tokenizer(genai_model)
            logger.info("ONNX Runtime GenAI model loaded successfully.")
        except Exception as e:
            logger.warning(f"Could not load ONNX model via onnxruntime-genai: {e}. Will use extractive fallback.")
    else:
        logger.info(f"ONNX Model directory {MODEL_DIR} not found or incomplete. Fallback summarizer enabled.")

@app.on_event("startup")
async def startup_event():
    load_onnx_model()

class ScrapeRequest(BaseModel):
    url: str
    query: Optional[str] = "Summarize the key points of this webpage."

class RenderMdRequest(BaseModel):
    markdown: str

def generate_llm_summary(prompt: str) -> str:
    global genai_model, genai_tokenizer
    if genai_model is not None and genai_tokenizer is not None:
        try:
            import onnxruntime_genai as og
            params = og.GeneratorParams(genai_model)
            params.set_search_options(max_length=512, top_p=0.9, temperature=0.7)
            
            tokens = genai_tokenizer.encode(prompt)
            params.input_ids = tokens
            
            generator = og.Generator(genai_model, params)
            output_tokens = []
            while not generator.is_done():
                generator.generate_next_token()
                new_token = generator.get_next_tokens()
                if new_token:
                    output_tokens.extend(new_token)
            
            return genai_tokenizer.decode(output_tokens)
        except Exception as e:
            logger.error(f"Error during ONNX inference: {e}")
    
    return ""

def fallback_summarize(text: str, query: str, max_sentences: int = 5) -> str:
    """Intelligent extractive fallback summary if ONNX model is unavailable."""
    sentences = [s.strip() for s in text.replace("\n", ". ").split(".") if len(s.strip()) > 15]
    if not sentences:
        return "No readable content could be extracted from the specified URL."
    
    # Query keyword scoring
    keywords = set(query.lower().split())
    scored_sentences = []
    for idx, s in enumerate(sentences):
        score = sum(1 for kw in keywords if kw in s.lower())
        scored_sentences.append((score, -idx, s))
    
    scored_sentences.sort(reverse=True)
    top_sentences = [s[2] for s in scored_sentences[:max_sentences]]
    
    bullet_points = "\n".join([f"- {s}" for s in top_sentences])
    return f"### Summary & Key Insights\n\n{bullet_points}"

@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "gedit-research-daemon",
        "onnx_model_loaded": genai_model is not None
    }

@app.post("/scrape-and-summarize")
def scrape_and_summarize(req: ScrapeRequest):
    logger.info(f"Fetching URL: {req.url}")
    downloaded = trafilatura.fetch_url(req.url)
    if not downloaded:
        raise HTTPException(status_code=400, detail="Failed to fetch webpage content from URL.")
    
    extracted_text = trafilatura.extract(downloaded, include_links=True, include_formatting=False)
    if not extracted_text:
        raise HTTPException(status_code=400, detail="Could not extract readable text from webpage.")
    
    # Limit text length to prevent context explosion
    truncated_text = extracted_text[:4000]
    
    system_prompt = (
        "<|im_start|>system\n"
        "You are an expert AI Web Research Copilot for Gedit. Your goal is to synthesize web content into clean, "
        "well-structured, factual Markdown notes according to the user's research query.<|im_end|>\n"
        f"<|im_start|>user\nResearch Query: {req.query}\nWeb Content:\n{truncated_text}<|im_end|>\n"
        "<|im_start|>assistant\n"
    )
    
    summary = generate_llm_summary(system_prompt)
    if not summary or len(summary.strip()) < 10:
        summary = fallback_summarize(truncated_text, req.query)
        
    return {
        "url": req.url,
        "query": req.query,
        "summary": summary,
        "status": "success"
    }

@app.post("/render-md")
def render_md(req: RenderMdRequest):
    raw_html = markdown.markdown(
        req.markdown,
        extensions=["fenced_code", "tables", "toc", "nl2br"]
    )
    
    styled_html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
    :root {{
        --bg-color: #1e1e2e;
        --fg-color: #cdd6f4;
        --accent-color: #89b4fa;
        --code-bg: #181825;
        --border-color: #313244;
    }}
    @media (prefers-color-scheme: light) {{
        :root {{
            --bg-color: #ffffff;
            --fg-color: #1c1c1e;
            --accent-color: #0066cc;
            --code-bg: #f2f2f7;
            --border-color: #e5e5ea;
        }}
    }}
    body {{
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        background-color: var(--bg-color);
        color: var(--fg-color);
        line-height: 1.6;
        padding: 16px;
        margin: 0;
    }}
    h1, h2, h3, h4, h5, h6 {{
        color: var(--accent-color);
        border-bottom: 1px solid var(--border-color);
        padding-bottom: 4px;
    }}
    code {{
        background-color: var(--code-bg);
        padding: 2px 6px;
        border-radius: 4px;
        font-family: monospace;
    }}
    pre {{
        background-color: var(--code-bg);
        padding: 12px;
        border-radius: 6px;
        overflow-x: auto;
        border: 1px solid var(--border-color);
    }}
    blockquote {{
        border-left: 4px solid var(--accent-color);
        margin-left: 0;
        padding-left: 12px;
        opacity: 0.85;
    }}
    table {{
        border-collapse: collapse;
        width: 100%;
        margin: 12px 0;
    }}
    th, td {{
        border: 1px solid var(--border-color);
        padding: 8px;
        text-align: left;
    }}
    th {{
        background-color: var(--code-bg);
    }}
</style>
</head>
<body>
{raw_html}
</body>
</html>"""

    return {"html": styled_html}

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 5055))
    uvicorn.run("server:app", host="0.0.0.0", port=port, reload=False)
