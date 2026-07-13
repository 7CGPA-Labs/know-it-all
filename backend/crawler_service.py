import sys
from pydbus import SessionBus
from gi.repository import GLib
import nlp_engine
import scraper
import summarizer
from jinja2 import Environment, FileSystemLoader
import os

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
        # 1. NLP extraction
        keywords = nlp_engine.extract_keywords(query)
        
        # 2. Scrape results
        search_results = scraper.scrape_duckduckgo(" ".join(keywords))
        
        # 3. Summarize
        summary_text = summarizer.summarize(search_results)
        
        # 4. Format with Jinja2
        template = self.jinja_env.get_template('response.jinja2')
        html_response = template.render(
            query=query,
            summary=summary_text,
            sources=search_results[:3]
        )
        return html_response

if __name__ == '__main__':
    bus = SessionBus()
    bus.publish('org.knowitall.CrawlerService', CrawlerService())
    
    loop = GLib.MainLoop()
    print("CrawlerService running...")
    loop.run()
