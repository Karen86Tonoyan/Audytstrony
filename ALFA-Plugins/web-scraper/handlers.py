"""Web Scraper Plugin

Intelligent web scraping with AI-powered filtering and data extraction.
"""

from typing import Any, Dict, List, Optional
import asyncio
import re
from urllib.parse import urljoin, urlparse

try:
    from bs4 import BeautifulSoup
    import requests
except ImportError:
    BeautifulSoup = None
    requests = None


class WebScraperHandler:
    """Handler for web scraping operations"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.timeout = config.get('timeout', 30)
        self.user_agent = config.get('user_agent', 
            'Mozilla/5.0 (compatible; OllamaAgent/1.0)')
        self.max_retries = config.get('max_retries', 3)
        self.ollama_client = None
        
        if not BeautifulSoup or not requests:
            raise ImportError(
                "BeautifulSoup4 and requests are required for web-scraper plugin. "
                "Install with: pip install beautifulsoup4 requests lxml"
            )
        
    async def initialize(self, agent):
        """Initialize plugin with agent reference"""
        self.ollama_client = agent.ollama
        print("Web Scraper Plugin initialized")
        
    async def execute(self, action: str, params: Dict[str, Any]) -> Any:
        """Execute plugin action"""
        actions = {
            'scrape_page': self._scrape_page,
            'extract_data': self._extract_data,
            'find_links': self._find_links,
            'smart_extract': self._smart_extract,
        }
        
        handler = actions.get(action)
        if not handler:
            raise ValueError(f"Unknown action: {action}")
            
        return await handler(params)
        
    async def _scrape_page(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Scrape a web page and return HTML content"""
        url = params.get('url')
        if not url:
            raise ValueError("URL is required")
            
        headers = {'User-Agent': self.user_agent}
        
        try:
            response = requests.get(
                url, 
                headers=headers, 
                timeout=self.timeout
            )
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'lxml')
            
            return {
                'url': url,
                'status_code': response.status_code,
                'title': soup.title.string if soup.title else None,
                'html': str(soup),
                'text': soup.get_text(strip=True),
            }
        except Exception as e:
            return {
                'url': url,
                'error': str(e),
                'status_code': None,
            }
            
    async def _extract_data(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract structured data from HTML"""
        html = params.get('html')
        selector = params.get('selector')
        
        if not html:
            raise ValueError("HTML content is required")
            
        soup = BeautifulSoup(html, 'lxml')
        
        if selector:
            elements = soup.select(selector)
        else:
            elements = soup.find_all()
            
        results = []
        for element in elements:
            results.append({
                'tag': element.name,
                'text': element.get_text(strip=True),
                'attributes': element.attrs,
            })
            
        return results
        
    async def _find_links(self, params: Dict[str, Any]) -> List[str]:
        """Find all links on a page"""
        html = params.get('html')
        base_url = params.get('base_url', '')
        
        if not html:
            raise ValueError("HTML content is required")
            
        soup = BeautifulSoup(html, 'lxml')
        links = []
        
        for link in soup.find_all('a', href=True):
            href = link['href']
            # Convert relative URLs to absolute
            if base_url:
                href = urljoin(base_url, href)
            links.append(href)
            
        return list(set(links))  # Remove duplicates
        
    async def _smart_extract(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Use AI to intelligently extract data from a page"""
        url = params.get('url')
        query = params.get('query', 'Extract all important information')
        
        # First, scrape the page
        page_data = await self._scrape_page({'url': url})
        
        if 'error' in page_data:
            return page_data
            
        # Use AI to analyze and extract
        prompt = f"""Analyze this web page and {query}.

Page Title: {page_data['title']}
Page Text (first 3000 chars):
{page_data['text'][:3000]}

Extract the relevant information in a structured format:"""
        
        response = await self.ollama_client.generate(
            model="llama3.2",
            prompt=prompt,
            temperature=0.3
        )
        
        return {
            'url': url,
            'title': page_data['title'],
            'extracted_data': response,
            'full_text': page_data['text'],
        }
        
    async def shutdown(self):
        """Clean up resources"""
        print("Web Scraper Plugin shutting down")


__version__ = "1.0.0"
__plugin__ = WebScraperHandler
