import os
# Set KNOWITALL_TESTING environment variable to skip downloading large models in test runs
os.environ["KNOWITALL_TESTING"] = "1"

import sys
import unittest
from unittest.mock import patch, MagicMock

# Add backend directory to sys.path to resolve imports
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

import nlp_engine
import summarizer
import scraper

class TestNLPEngine(unittest.TestCase):
    def test_extract_keywords(self):
        query = "What is the best way to compile clean C++ code?"
        expected = ["best", "way", "compile", "clean", "code"]
        keywords = nlp_engine.extract_keywords(query)
        for word in expected:
            self.assertIn(word, keywords)

    def test_extract_keywords_empty(self):
        query = "what is this"
        keywords = nlp_engine.extract_keywords(query)
        self.assertTrue(len(keywords) > 0)
        self.assertNotIn("what", keywords)


class TestSummarizer(unittest.TestCase):
    def test_summarize_empty(self):
        self.assertEqual(summarizer.summarize([]), "No results found.")
        self.assertEqual(summarizer.summarize([{"title": "x"}]), "No content to summarize.")

    def test_summarize_extractive(self):
        results = [
            {"snippet": "Python is a popular programming language. It is known for its readability and simplicity."},
            {"snippet": "Many developers use Python for web development and data science. Data science with Python is extremely powerful."},
            {"snippet": "It has a large community and rich ecosystem of libraries."}
        ]
        
        summary = summarizer.summarize(results, num_sentences=2)
        self.assertIsNotNone(summary)
        self.assertTrue(len(summary) > 0)


class TestScraper(unittest.TestCase):
    @patch('requests.post')
    def test_scrape_duckduckgo_success(self, mock_post):
        mock_html = """
        <html>
        <body>
            <div id="links">
                <div class="result">
                    <h2 class="result__title">
                        <a class="result__a" href="/l/?kh=-1&uddg=https%3A%2F%2Fpython.org%2F">Welcome to Python.org</a>
                    </h2>
                    <div class="result__snippet">The official home of the Python Programming Language.</div>
                </div>
                <div class="result">
                    <h2 class="result__title">
                        <a class="result__a" href="https://example.com/direct-link">Example Domain</a>
                    </h2>
                    <div class="result__snippet">Example website with no redirect.</div>
                </div>
            </div>
        </body>
        </html>
        """
        mock_response = MagicMock()
        mock_response.text = mock_html
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        results = scraper.scrape_duckduckgo("python")
        
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]["title"], "Welcome to Python.org")
        self.assertEqual(results[0]["url"], "https://python.org/")
        self.assertEqual(results[0]["snippet"], "The official home of the Python Programming Language.")
        self.assertEqual(results[1]["title"], "Example Domain")
        self.assertEqual(results[1]["url"], "https://example.com/direct-link")
        self.assertEqual(results[1]["snippet"], "Example website with no redirect.")

    @patch('requests.post')
    def test_scrape_duckduckgo_failure(self, mock_post):
        mock_post.side_effect = Exception("Connection error")
        results = scraper.scrape_duckduckgo("python")
        self.assertEqual(results, [])


class TestMLPipeline(unittest.TestCase):
    @patch('summarizer.get_sentence_transformer')
    @patch('summarizer.get_cross_encoder')
    @patch('summarizer.get_boss_generator')
    def test_ml_pipeline_execution(self, mock_get_boss, mock_get_cross, mock_get_transformer):
        # 1. Mock SentenceTransformer
        mock_transformer = MagicMock()
        mock_transformer.encode.return_value = MagicMock()
        mock_get_transformer.return_value = mock_transformer

        # Mock cosine similarity utilities
        with patch('sentence_transformers.util.cos_sim') as mock_cos_sim:
            mock_tensor = MagicMock()
            # 6 input sentences, returns list of mock scores
            mock_tensor.tolist.return_value = [0.8, 0.9, 0.7, 0.6, 0.5, 0.4]
            mock_cos_sim.return_value = [mock_tensor]

            # 2. Mock CrossEncoder
            mock_cross = MagicMock()
            mock_cross.predict.return_value = MagicMock()
            mock_cross.predict.return_value.tolist.return_value = [0.95, 0.85, 0.75, 0.65, 0.55]
            mock_get_cross.return_value = mock_cross

            # NLI CrossEncoder mock: returns arrays of 3 values (contradiction, entailment, neutral)
            # Make sure entailment is strictly dominant so NLI passes them
            mock_cross.predict.side_effect = [
                # Reranking predictions
                [0.95, 0.85, 0.75, 0.65, 0.55],
                # NLI predictions (5 pairs): contradiction=0.1, entailment=0.8, neutral=0.1
                [[0.1, 0.8, 0.1], [0.1, 0.8, 0.1], [0.1, 0.8, 0.1], [0.1, 0.8, 0.1], [0.1, 0.8, 0.1]]
            ]

            # 3. Mock Boss Generator (Qwen)
            mock_model = MagicMock()
            mock_tokenizer = MagicMock()
            
            mock_tokenizer.apply_chat_template.return_value = "<mock_prompt>"
            mock_tokenizer.return_value = {"input_ids": MagicMock()}
            mock_model.generate.return_value = MagicMock()
            mock_tokenizer.batch_decode.return_value = ["This is a mocked RAG answer."]
            mock_get_boss.return_value = (mock_model, mock_tokenizer)

            # Execution
            results = [
                {"snippet": "Sentence one is here and it is long. Sentence two is there and it is long. Sentence three is other and it is long."},
                {"snippet": "Sentence four is this and it is long. Sentence five is that and it is long. Sentence six is what and it is long."}
            ]
            config = {
                "sidekicks": {
                    "embedding": "sentence-transformers/all-MiniLM-L6-v2",
                    "reranker": "cross-encoder/ms-marco-MiniLM-L-6-v2",
                    "verifier": "cross-encoder/nli-distilroberta-base"
                },
                "main_boss": "Qwen/Qwen2.5-0.5B-Instruct"
            }
            
            response = summarizer.summarize_with_ml_pipeline(results, "test query", config)
            self.assertEqual(response, "This is a mocked RAG answer.")

if __name__ == '__main__':
    unittest.main()
