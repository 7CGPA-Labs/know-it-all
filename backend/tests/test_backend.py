import os
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
        # Ensure all expected keywords are present (handling potential stopword differences)
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
        
        # Extractive summary should select the most representative sentences
        summary = summarizer.summarize(results, num_sentences=2)
        self.assertIsNotNone(summary)
        self.assertTrue(len(summary) > 0)


class TestScraper(unittest.TestCase):
    @patch('requests.post')
    def test_scrape_duckduckgo_success(self, mock_post):
        # Mock HTML response
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
        
        # Test redirect url decoding
        self.assertEqual(results[0]["title"], "Welcome to Python.org")
        self.assertEqual(results[0]["url"], "https://python.org/")
        self.assertEqual(results[0]["snippet"], "The official home of the Python Programming Language.")

        # Test direct url preservation
        self.assertEqual(results[1]["title"], "Example Domain")
        self.assertEqual(results[1]["url"], "https://example.com/direct-link")
        self.assertEqual(results[1]["snippet"], "Example website with no redirect.")

    @patch('requests.post')
    def test_scrape_duckduckgo_failure(self, mock_post):
        mock_post.side_effect = Exception("Connection error")
        results = scraper.scrape_duckduckgo("python")
        self.assertEqual(results, [])

if __name__ == '__main__':
    unittest.main()
