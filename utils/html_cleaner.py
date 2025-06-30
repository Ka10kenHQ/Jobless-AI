import re
import html
from typing import Optional, Dict, List
from bs4 import BeautifulSoup
import logging


class HTMLCleaner:
    """Utility for cleaning HTML content and extracting text"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Common HTML entities to clean
        self.html_entities = {
            '&nbsp;': ' ',
            '&amp;': '&',
            '&lt;': '<',
            '&gt;': '>',
            '&quot;': '"',
            '&#x27;': "'",
            '&#39;': "'",
            '&ldquo;': '"',
            '&rdquo;': '"',
            '&lsquo;': "'",
            '&rsquo;': "'",
        }
        
        # Tags that should be converted to line breaks
        self.block_tags = {
            'div', 'p', 'br', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 
            'ul', 'ol', 'li', 'section', 'article', 'header', 'footer'
        }
        
        # Tags that should be completely removed with content
        self.remove_tags = {
            'script', 'style', 'head', 'meta', 'link', 'noscript'
        }
        
    def clean_html_text(self, html_content: str, 
                       preserve_formatting: bool = False,
                       max_length: Optional[int] = None) -> str:
        """
        Clean HTML content and extract readable text
        
        Args:
            html_content: Raw HTML string
            preserve_formatting: Keep some basic formatting (line breaks)
            max_length: Maximum length of output text
            
        Returns:
            Cleaned text content
        """
        if not html_content or not html_content.strip():
            return ""
            
        try:
            # First pass: remove problematic tags completely
            cleaned = self._remove_unwanted_tags(html_content)
            
            # Parse with BeautifulSoup for proper HTML handling
            soup = BeautifulSoup(cleaned, 'html.parser')
            
            # Convert block elements to line breaks if preserving formatting
            if preserve_formatting:
                self._convert_block_elements_to_breaks(soup)
            
            # Extract text
            text = soup.get_text(separator=' ' if not preserve_formatting else '\n')
            
            # Clean up the extracted text
            text = self._clean_extracted_text(text)
            
            # Apply length limit if specified
            if max_length and len(text) > max_length:
                text = text[:max_length].rsplit(' ', 1)[0] + '...'
                
            return text
            
        except Exception as e:
            self.logger.error(f"Error cleaning HTML: {e}")
            # Fallback to simple regex cleaning
            return self._fallback_html_clean(html_content)
    
    def extract_structured_content(self, html_content: str) -> Dict:
        """
        Extract structured information from HTML
        
        Returns:
            Dictionary with extracted elements like headers, lists, links, etc.
        """
        if not html_content:
            return {}
            
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Remove unwanted elements
            for tag_name in self.remove_tags:
                for tag in soup.find_all(tag_name):
                    tag.decompose()
                    
            return {
                'title': self._extract_title(soup),
                'headers': self._extract_headers(soup),
                'paragraphs': self._extract_paragraphs(soup),
                'lists': self._extract_lists(soup),
                'links': self._extract_links(soup),
                'tables': self._extract_tables(soup),
                'text_content': soup.get_text(separator=' ').strip()
            }
            
        except Exception as e:
            self.logger.error(f"Error extracting structured content: {e}")
            return {'text_content': self._fallback_html_clean(html_content)}
    
    def _remove_unwanted_tags(self, html_content: str) -> str:
        """Remove script, style, and other unwanted tags"""
        for tag in self.remove_tags:
            pattern = rf'<{tag}[^>]*>.*?</{tag}>'
            html_content = re.sub(pattern, '', html_content, flags=re.DOTALL | re.IGNORECASE)
            
        return html_content
    
    def _convert_block_elements_to_breaks(self, soup: BeautifulSoup):
        """Convert block elements to line breaks"""
        for tag_name in self.block_tags:
            for tag in soup.find_all(tag_name):
                # Add line break before the tag
                tag.insert_before('\n')
                # Add line break after if it's a block element
                if tag_name in {'div', 'p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6'}:
                    tag.insert_after('\n')
    
    def _clean_extracted_text(self, text: str) -> str:
        """Clean up extracted text"""
        if not text:
            return ""
            
        # Decode HTML entities
        text = html.unescape(text)
        
        # Replace custom HTML entities
        for entity, replacement in self.html_entities.items():
            text = text.replace(entity, replacement)
        
        # Remove URLs
        text = re.sub(r'http[s]?://\S+', '', text)
        
        # Remove email addresses
        text = re.sub(r'\S+@\S+\.\S+', '', text)
        
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove excessive punctuation
        text = re.sub(r'[.]{3,}', '...', text)
        text = re.sub(r'[-]{3,}', '---', text)
        
        # Remove control characters
        text = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', text)
        
        return text.strip()
    
    def _fallback_html_clean(self, html_content: str) -> str:
        """Fallback method using regex when BeautifulSoup fails"""
        if not html_content:
            return ""
            
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', ' ', html_content)
        
        # Clean up
        return self._clean_extracted_text(text)
    
    def _extract_title(self, soup: BeautifulSoup) -> str:
        """Extract title from HTML"""
        title_tag = soup.find('title')
        if title_tag:
            return title_tag.get_text().strip()
        
        # Try h1 as fallback
        h1_tag = soup.find('h1')
        if h1_tag:
            return h1_tag.get_text().strip()
            
        return ""
    
    def _extract_headers(self, soup: BeautifulSoup) -> List[Dict]:
        """Extract headers (h1-h6) from HTML"""
        headers = []
        for i in range(1, 7):
            for header in soup.find_all(f'h{i}'):
                headers.append({
                    'level': i,
                    'text': header.get_text().strip()
                })
        return headers
    
    def _extract_paragraphs(self, soup: BeautifulSoup) -> List[str]:
        """Extract paragraphs from HTML"""
        paragraphs = []
        for p in soup.find_all('p'):
            text = p.get_text().strip()
            if text:
                paragraphs.append(text)
        return paragraphs
    
    def _extract_lists(self, soup: BeautifulSoup) -> List[Dict]:
        """Extract lists from HTML"""
        lists = []
        
        for ul in soup.find_all('ul'):
            items = [li.get_text().strip() for li in ul.find_all('li')]
            if items:
                lists.append({
                    'type': 'unordered',
                    'items': items
                })
        
        for ol in soup.find_all('ol'):
            items = [li.get_text().strip() for li in ol.find_all('li')]
            if items:
                lists.append({
                    'type': 'ordered',
                    'items': items
                })
                
        return lists
    
    def _extract_links(self, soup: BeautifulSoup) -> List[Dict]:
        """Extract links from HTML"""
        links = []
        for a in soup.find_all('a', href=True):
            text = a.get_text().strip()
            href = a['href']
            if text and href:
                links.append({
                    'text': text,
                    'url': href
                })
        return links
    
    def _extract_tables(self, soup: BeautifulSoup) -> List[Dict]:
        """Extract tables from HTML"""
        tables = []
        for table in soup.find_all('table'):
            rows = []
            for tr in table.find_all('tr'):
                cells = [td.get_text().strip() for td in tr.find_all(['td', 'th'])]
                if cells:
                    rows.append(cells)
            if rows:
                tables.append({
                    'rows': rows,
                    'num_rows': len(rows),
                    'num_cols': len(rows[0]) if rows else 0
                })
        return tables

    def is_html_content(self, text: str) -> bool:
        """Check if text contains HTML tags"""
        if not text:
            return False
        return bool(re.search(r'<[^>]+>', text))

    def get_text_to_html_ratio(self, html_content: str) -> float:
        """Get ratio of text content to HTML markup"""
        if not html_content:
            return 0.0
            
        text_content = self.clean_html_text(html_content)
        text_length = len(text_content)
        html_length = len(html_content)
        
        if html_length == 0:
            return 0.0
            
        return text_length / html_length 