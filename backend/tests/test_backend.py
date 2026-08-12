import os
os.environ["KNOWITALL_TESTING"] = "1"

import sys
import unittest
from unittest.mock import patch, MagicMock

# Add backend directory to sys.path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

import crawler_service

class TestMonolithicBackend(unittest.TestCase):
    
    def test_get_keywords_query(self):
        query = "What is the best way to compile clean C++ code?"
        expected = ["best", "way", "compile", "clean", "code"]
        keywords = crawler_service.get_keywords_query(query)
        for word in expected:
            self.assertIn(word, keywords)

    def test_evaluate_expression(self):
        self.assertEqual(crawler_service.evaluate_expression("45 * 2"), "90")
        self.assertEqual(crawler_service.evaluate_expression("120 / (4 + 6)"), "12.0")
        self.assertTrue("Error" in crawler_service.evaluate_expression("import os; os.system('ls')"))

    def test_summarize_classical_empty(self):
        self.assertEqual(crawler_service.summarize_classical([], 3, "test"), "No results found.")

    def test_summarize_classical_success(self):
        results = [
            {"snippet": "Python is a popular programming language. It is known for its readability and simplicity and it is a long sentence."},
            {"snippet": "Many developers use Python for web development and data science. Data science with Python is extremely powerful and long."},
            {"snippet": "It has a large community and rich ecosystem of libraries and it is long."}
        ]
        summary = crawler_service.summarize_classical(results, 2, "python")
        self.assertIsNotNone(summary)
        self.assertTrue(len(summary) > 0)

    @patch('requests.post')
    def test_scrape_duckduckgo_success(self, mock_post):
        mock_html = """
        <html>
        <body>
            <div id="links">
                <div class="result">
                    <h2 class="result__title">
                        <a class="result__url" href="/l/?kh=-1&uddg=https%3A%2F%2Fpython.org%2F">Welcome to Python.org</a>
                    </h2>
                    <div class="result__snippet">The official home of the Python Programming Language.</div>
                </div>
            </div>
        </body>
        </html>
        """
        mock_response = MagicMock()
        mock_response.text = mock_html
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        results = crawler_service.scrape_duckduckgo("python")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["title"], "Welcome to Python.org")
        self.assertEqual(results[0]["url"], "https://python.org/")

    @patch('requests.post')
    def test_scrape_duckduckgo_failure(self, mock_post):
        mock_post.side_effect = Exception("Connection error")
        results = crawler_service.scrape_duckduckgo("python")
        self.assertEqual(results, [])


class TestAgentLoopMock(unittest.TestCase):
    
    @patch('crawler_service.get_sentence_transformer')
    @patch('crawler_service.get_cross_encoder')
    @patch('crawler_service.get_boss_generator')
    @patch('crawler_service.scrape_duckduckgo')
    def test_agent_loop_scrape_and_answer(self, mock_scrape, mock_get_boss, mock_get_cross, mock_get_transformer):
        # Mock Scrape to append results to holder
        def custom_scrape(query, holder_list=None):
            res = [{"title": "Test", "url": "https://test.com", "snippet": "Argentina won the 2022 world cup in Qatar."}]
            if holder_list is not None:
                holder_list.extend(res)
            return res
        mock_scrape.side_effect = custom_scrape
        
        # Mock Sidekicks
        mock_transformer = MagicMock()
        mock_get_transformer.return_value = mock_transformer
        
        mock_cross = MagicMock()
        mock_get_cross.return_value = mock_cross
        
        # Similarity mock returns
        with patch('sentence_transformers.util.cos_sim') as mock_cos_sim:
            mock_tensor = MagicMock()
            mock_tensor.tolist.return_value = [0.9]
            mock_cos_sim.return_value = [mock_tensor]
            
            # Mock Cross-Encoder scores for NLI (contradiction=0.1, entailment=0.8, neutral=0.1)
            mock_cross.predict.return_value = [[0.1, 0.8, 0.1]]
            
            # Mock Main Boss (Qwen)
            mock_model = MagicMock()
            mock_tokenizer = MagicMock()
            
            mock_tokenizer.apply_chat_template.return_value = "<mock_prompt>"
            mock_tokenizer.return_value = {"input_ids": MagicMock()}
            mock_tokenizer.batch_decode.side_effect = [
                # Turn 1: Action: Scrape
                ["Thought: I need to search the web.\nAction: Scrape(\"latest world cup winner\")"],
                # Turn 2: Action: Verify
                ["Thought: I should verify the details.\nAction: Verify(\"latest world cup winner\", \"Argentina won the 2022 world cup\")"],
                # Turn 3: Action: FinalAnswer
                ["Thought: The facts are verified.\nAction: FinalAnswer(\"Argentina won the 2022 world cup.\")"]
            ]
            mock_get_boss.return_value = (mock_model, mock_tokenizer)
            
            config = {
                "sidekicks": {
                    "embedding": "sentence-transformers/all-MiniLM-L6-v2",
                    "reranker": "cross-encoder/ms-marco-MiniLM-L-6-v2",
                    "verifier": "cross-encoder/nli-distilroberta-base"
                },
                "main_boss": "Qwen/Qwen2.5-0.5B-Instruct"
            }
            
            holder = []
            answer = crawler_service.run_agent_loop("Who won the latest world cup?", config, holder)
            self.assertEqual(answer, "Argentina won the 2022 world cup.")
            self.assertEqual(len(holder), 1)

if __name__ == '__main__':
    unittest.main()
