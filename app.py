# app.py
import os
import time
import json
import logging
import requests
import uuid
import re
from urllib.parse import urlparse, urljoin
from typing import Dict, List, Any, Optional, Set
import datetime

import nltk
from nltk.tokenize import sent_tokenize
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
from bs4 import BeautifulSoup

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect, Depends, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse
from pydantic import BaseModel
import uvicorn
from dotenv import load_dotenv

# Hard-coded website URL
WEBSITE_URL = "https://staging-31ef-vicecards.wpcomstaging.com/"
MAX_SCAN_DEPTH = 3  # Depth for recursive scanning
MAX_SCAN_PAGES = 200  # Maximum number of pages to scan

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize the FastAPI app
app = FastAPI(title="Context-Aware Website Chatbot")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Download NLTK resources at startup
nltk.download('punkt')
nltk.download('stopwords')
nltk.download('wordnet')
nltk.download('punkt_tab')  # Also download punkt_tab which is needed for tokenization

# EmailJS credentials
EMAILJS_SERVICE_ID = 'service_3jl7kuy'
EMAILJS_TEMPLATE_ID = 'template_hiuxjep'
EMAILJS_PUBLIC_KEY = 'yBoW6wqsMfU5ftCfY'
EMAILJS_URL = 'https://api.emailjs.com/api/v1.0/email/send'

# Initialize Google Gemini API
gemini_api_key = os.getenv("GEMINI_API_KEY")
if not gemini_api_key:
    logger.warning("GEMINI_API_KEY not found in environment variables")


# Pydantic models for API validation
class Query(BaseModel):
    query: str


class WebsiteScanner:
    def __init__(self):
        self.stop_words = set(stopwords.words('english'))
        self.lemmatizer = WordNetLemmatizer()
        self.website_content = {}  # Cache for website content
        self.website_sections = {}  # Cache for website sections
        self.context_prompt = {}  # Cache for generated context prompts
        self.last_scan_time = {}  # Store last scan time for each URL
        self.context_expiry_time = 72 * 60 * 60  # 72 hours in seconds

    def extract_text_from_url(self, url: str) -> tuple:
        """Extract text content from a URL"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Cache-Control': 'max-age=0'
            }
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()

            # Create BeautifulSoup object with the HTML parser explicitly specified
            soup = BeautifulSoup(response.text, 'html.parser')

            # Store original full HTML for link extraction
            full_soup = BeautifulSoup(response.text, 'html.parser')  # Create a fresh copy instead of using .copy()

            # First, remove elements that usually contain non-content
            for selector in [
                'script', 'style', 'noscript', 'iframe', 'img', 'svg',
                '[class*="footer"]', '[class*="sidebar"]', '[class*="widget"]',
                '[class*="banner"]', '[class*="ad-"]', '[id*="ad-"]'
            ]:
                for element in soup.select(selector):
                    if element:
                        element.decompose()

            # Find the main content area if it exists
            main_content = None
            main_selectors = [
                'main', 'article', '[role="main"]', '.content', '#content',
                '.main', '#main', '.post', '.entry', '.page-content',
                '[class*="content"]', '[id*="content"]'
            ]

            main_candidates = []
            for selector in main_selectors:
                elements = soup.select(selector)
                if elements:
                    main_candidates.extend(elements)

            if main_candidates:
                try:
                    # Try to find the main content with the most text
                    main_content = max(main_candidates, key=lambda x: len(x.get_text(strip=True) or ""))
                except (TypeError, ValueError) as e:
                    # If there's an error finding the main content, continue without it
                    logger.warning(f"Error finding main content on {url}: {e}")
                    main_content = None

            # If we found a main content area, use that, otherwise use the whole page
            if main_content:
                # Get text from just this section
                content_soup = main_content
                logger.info(f"Found main content section on {url}")
            else:
                # Remove header/nav/footer before text extraction
                content_soup = soup
                for selector in ['header', 'nav', '[class*="nav"]', '[class*="menu"]', '[id*="menu"]']:
                    for element in content_soup.select(selector):
                        if element:
                            element.decompose()
                logger.info(f"No main content section found, using full page for {url}")

            # Get text with spacing to maintain structure - safely
            text = ""
            for tag_name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'li', 'div']:
                for element in content_soup.find_all(tag_name):
                    try:
                        element_text = element.get_text(strip=True)
                        if element_text:
                            if tag_name.startswith('h'):
                                text += f"\n\n{element_text}\n\n"
                            elif tag_name == 'p':
                                text += f"{element_text}\n\n"
                            elif tag_name == 'li':
                                text += f"• {element_text}\n"
                            else:
                                text += f"{element_text} "
                    except Exception as e:
                        logger.error(f"Error extracting text from {tag_name} element: {e}")
                        continue

            # Clean text
            lines = [line.strip() for line in text.splitlines()]
            chunks = []
            for line in lines:
                line_chunks = [phrase.strip() for phrase in line.split("  ")]
                chunks.extend(line_chunks)
            text = ' '.join(chunk for chunk in chunks if chunk)

            # Remove extra spacing
            text = ' '.join(text.split())

            # Add page title at the beginning for context - safely
            title = url
            if soup.title:
                title_text = soup.title.string
                if title_text:
                    title = title_text

            text = f"PAGE TITLE: {title}\n\n{text}"

            # Add any visible meta descriptions - safely
            meta_desc = soup.find('meta', attrs={'name': 'description'})
            if meta_desc and meta_desc.has_attr('content'):
                meta_content = meta_desc['content']
                if meta_content:
                    text = f"{text}\n\nMETA DESCRIPTION: {meta_content}"

            return text, full_soup
        except Exception as e:
            logger.error(f"Error extracting text from {url}: {e}")
            return "", None

    def get_all_links(self, soup: BeautifulSoup, base_url: str) -> Set[str]:
        """Extract all links from a webpage that belong to the same domain using a simpler approach"""
        if not soup:
            return set()

        # Get base domain for comparison
        base_domain = urlparse(base_url).netloc
        links = set()

        # Common non-content URL patterns to skip
        skip_patterns = [
            '.jpg', '.jpeg', '.png', '.gif', '.pdf', '.zip', '.doc', '.docx',
            '#', 'mailto:', 'tel:', 'javascript:',
            '/tag/', '/category/', '/author/', '/wp-content/', '/wp-admin/'
        ]

        # Get all links
        try:
            for a_tag in soup.find_all('a', href=True):
                href = a_tag.get('href', '').strip()

                # Skip empty hrefs
                if not href:
                    continue

                # Skip unwanted patterns
                if any(pattern in href.lower() for pattern in skip_patterns):
                    continue

                # Fix double slashes (except after protocol)
                while '//' in href and not href.startswith('http'):
                    href = href.replace('//', '/')

                # Make absolute URL
                if href.startswith('/'):
                    href = urljoin(base_url, href)
                elif not href.startswith(('http://', 'https://')):
                    href = urljoin(base_url, href)

                # Remove trailing slashes for consistency
                href = href.rstrip('/')

                # Only include links from same domain
                if urlparse(href).netloc == base_domain:
                    links.add(href)

            return links
        except Exception as e:
            logger.error(f"Error extracting links from page: {e}")
            return set()

    def preprocess_text(self, text: str) -> str:
        """Preprocess text by removing stopwords and lemmatizing"""
        # Convert to lowercase
        text = text.lower()

        # Tokenize
        words = text.split()

        # Remove stopwords and lemmatize
        processed_words = [self.lemmatizer.lemmatize(word) for word in words if word not in self.stop_words]

        return ' '.join(processed_words)

    def split_into_sections(self, text: str, url: str) -> List[Dict[str, Any]]:
        """Split text into meaningful sections - Simplified version"""
        # For the simpler approach, we'll just create a single section from the entire page
        # This avoids the complexity of trying to detect sections and headers

        if not text or len(text.strip()) < 10:
            return []

        # Create a single section for the entire page
        return [{
            "title": f"Content from {url}",
            "content": self.preprocess_text(text),
            "raw_content": text,
            "url": url
        }]

    def scan_website_recursive(self, base_url: str, depth: int = 3, max_pages: int = 50) -> List[Dict[str, Any]]:
        """Scan website with a simpler, more robust approach"""
        logger.info(f"Starting website scan: {base_url} (depth: {depth}, max_pages: {max_pages})")

        # Initialize tracking
        visited = set()  # URLs already processed
        to_visit = [base_url]  # Queue of URLs to process
        all_sections = []  # Collected content
        pages_scanned = 0

        # Common important page patterns to prioritize
        important_patterns = [
            '/about', '/about-us', '/contact', '/faq',
            '/products', '/services', '/company'
        ]

        # Reorder the to_visit list to prioritize important URLs
        def prioritize_urls(urls):
            important = []
            normal = []
            for url in urls:
                if any(pattern in url.lower() for pattern in important_patterns):
                    important.append(url)
                else:
                    normal.append(url)
            return important + normal

        # Process each URL up to max_pages
        while to_visit and pages_scanned < max_pages:
            # Sort to prioritize important pages
            to_visit = prioritize_urls(to_visit)

            # Get next URL to process
            current_url = to_visit.pop(0)

            # Skip if already visited
            if current_url in visited:
                continue

            # Mark as visited
            visited.add(current_url)
            pages_scanned += 1

            logger.info(f"Scanning page {pages_scanned}/{max_pages}: {current_url}")

            try:
                # Extract content from page
                page_text, page_soup = self.extract_text_from_url(current_url)

                if page_text:
                    # Create a section from this page
                    section = {
                        "title": f"Content from {current_url}",
                        "content": self.preprocess_text(page_text),
                        "raw_content": page_text,
                        "url": current_url
                    }

                    # Add to sections
                    all_sections.append(section)
                    logger.info(f"Added content from {current_url}")

                    # Don't get links if we've reached max depth
                    if depth > 1 and pages_scanned < max_pages:
                        # Get links from this page
                        links = self.get_all_links(page_soup, current_url)

                        # Add unvisited links to queue
                        for link in links:
                            if link not in visited and link not in to_visit:
                                to_visit.append(link)

                else:
                    logger.warning(f"No content extracted from {current_url}")

            except Exception as e:
                logger.error(f"Error processing {current_url}: {e}")

        logger.info(f"Scan complete: processed {pages_scanned} pages, found {len(all_sections)} content sections")

        # Try to get content from specific important pages if we don't have enough
        if len(all_sections) < 3 and pages_scanned < max_pages:
            logger.warning(f"Limited content found ({len(all_sections)} sections). Trying specific URLs...")

            # List of important pages to try
            extra_urls = [
                f"{base_url}/about",
                f"{base_url}/about-us",
                f"{base_url}/company",
                f"{base_url}/products"
            ]

            for extra_url in extra_urls:
                if extra_url not in visited and pages_scanned < max_pages:
                    try:
                        logger.info(f"Trying specific URL: {extra_url}")
                        page_text, _ = self.extract_text_from_url(extra_url)

                        if page_text:
                            section = {
                                "title": f"Content from {extra_url}",
                                "content": self.preprocess_text(page_text),
                                "raw_content": page_text,
                                "url": extra_url
                            }
                            all_sections.append(section)
                            pages_scanned += 1
                            logger.info(f"Added content from {extra_url}")
                    except Exception as e:
                        logger.error(f"Error processing {extra_url}: {e}")

        return all_sections

    def generate_context_prompt(self, sections: List[Dict[str, Any]], website_url: str) -> str:
        """Generate a comprehensive context prompt from all website sections"""
        if not sections:
            return f"""You are a helpful AI assistant for the website: {website_url}. 

The website appears to have limited content available. Answer user questions politely, and if you don't know information about the website, simply acknowledge that the information is not available.

You must strive to be human-like in all interactions:
- Show empathy and emotional intelligence
- Recognize user frustration or confusion quickly
- Maintain conversation context between messages
- Be proactive in offering solutions
- Escalate to a human agent when appropriate

If the user seems frustrated, confused, or if you cannot fully answer their question after 2-3 attempts, offer to connect them with a human team member by asking for their email address.
"""

        # Sort sections by their URLs to group content from the same pages together
        sections_by_url = {}
        for section in sections:
            url = section.get("url", website_url)
            if url not in sections_by_url:
                sections_by_url[url] = []
            sections_by_url[url].append(section)

        # Build the context prompt
        context = f"""You are a helpful AI assistant for the website: {website_url}

You are the official chatbot for this website. You must respond in a human-like, conversational manner with emotional intelligence. Always try to be helpful, but recognize when a situation needs human escalation.

IMPORTANT RULES:
1. Always respond in a conversational, human-like manner
2. Detect and adapt to user emotions in your responses
3. If a user seems frustrated, confused, or if you cannot fully answer their question after 2-3 attempts, offer to connect them with a human team member
4. When escalation is appropriate, ask for their email address
5. Maintain the conversation context throughout the interaction
6. Be proactive in offering solutions

The following is information extracted from the website. Use this information to answer user questions:
"""

        # First include content from About pages if available
        about_sections = []
        for url, url_sections in sections_by_url.items():
            if "about" in url.lower():
                about_sections.extend(url_sections)

        if about_sections:
            context += "\nABOUT THE COMPANY/WEBSITE:\n"
            for section in about_sections[:3]:  # Limit to avoid token issues
                context += f"{section['raw_content']}\n\n"

        # Add other important content
        page_count = 0
        for url, url_sections in sections_by_url.items():
            # Skip About pages which we've already included
            if "about" in url.lower():
                continue

            # Limit total pages to avoid exceeding token limits
            if page_count >= 30:
                break

            # Use the first section from each URL to avoid duplication
            if url_sections:
                context += f"\n--- CONTENT FROM: {url} ---\n\n"
                context += f"{url_sections[0]['raw_content']}\n\n"
                page_count += 1

        context += """
INSTRUCTIONS:
1. Answer questions based ONLY on the information provided above.
2. If the answer cannot be found in the provided information, say so clearly.
3. Respond as if you are the official chatbot for this website.
4. Be concise but thorough in your responses.
5. Cite specific pages/URLs when possible in your answers.
6. Use a conversational, friendly tone while remaining professional.
7. Show empathy when users express confusion or frustration.
8. Offer escalation to a human team member if:
   - You detect user frustration
   - The user has repeated the same question multiple times
   - You cannot provide a satisfactory answer
   - The request is complex or requires human judgment
   - The user explicitly asks for human assistance

ESCALATION PROCEDURE:
If escalation is needed, say: "I'd be happy to connect you with a team member who can help further. Could you please provide your email address so they can contact you?"
"""

        return context

    def scan_website(self, website_url: str, force: bool = False) -> Dict[str, Any]:
        """Scan website and generate context prompt for the chatbot"""
        current_time = time.time()

        # Check if we need to rescan the website
        if not force and website_url in self.last_scan_time and self.context_prompt.get(website_url):
            time_since_last_scan = current_time - self.last_scan_time[website_url]
            if time_since_last_scan < self.context_expiry_time:
                logger.info(
                    f"Using cached context for {website_url} (expires in {(self.context_expiry_time - time_since_last_scan) / 3600:.1f} hours)")
                return {
                    "context_prompt": self.context_prompt[website_url],
                    "sections_count": len(self.website_sections.get(website_url, [])),
                    "last_scan_time": self.last_scan_time[website_url],
                    "from_cache": True
                }

        try:
            # Scan website and all subpages
            logger.info(
                f"Starting thorough scan of {website_url} with depth={MAX_SCAN_DEPTH}, max_pages={MAX_SCAN_PAGES}")
            sections = self.scan_website_recursive(website_url, depth=MAX_SCAN_DEPTH, max_pages=MAX_SCAN_PAGES)

            if not sections:
                logger.warning(f"No content extracted from {website_url}")
                return {
                    "context_prompt": f"No content could be extracted from {website_url}",
                    "sections_count": 0,
                    "last_scan_time": current_time,
                    "from_cache": False
                }

            # Print debug info about which URLs were actually crawled
            urls_crawled = set(section["url"] for section in sections)
            logger.info(f"Successfully crawled {len(urls_crawled)} unique URLs:")
            for url in urls_crawled:
                logger.info(f"  - {url}")

            # Generate context prompt
            context_prompt = self.generate_context_prompt(sections, website_url)

            # Update cache
            self.website_sections[website_url] = sections
            self.context_prompt[website_url] = context_prompt
            self.last_scan_time[website_url] = current_time

            return {
                "context_prompt": context_prompt,
                "sections_count": len(sections),
                "last_scan_time": current_time,
                "from_cache": False
            }
        except Exception as e:
            logger.error(f"Error in website scanning: {e}")
            return {
                "context_prompt": f"Error scanning website {website_url}: {str(e)}",
                "sections_count": 0,
                "last_scan_time": current_time,
                "from_cache": False
            }


class ChatbotManager:
    def __init__(self, website_url):
        self.scanner = WebsiteScanner()
        self.website_url = website_url
        self.context_prompt = None
        self.last_scan_time = None
        self.history = []
        self.escalation_requested = False
        self.init_context()

    def init_context(self):
        """Initialize context by scanning the website"""
        logger.info(f"Initializing context for {self.website_url}")
        try:
            # Set a default context in case of failure
            self.context_prompt = f"You are a helpful AI assistant for the website: {self.website_url}. Answer user questions about this website and its content in a friendly, professional manner. If you don't know the answer, simply say so politely."
            self.last_scan_time = time.time()

            # Try to scan the website completely
            scan_result = self.scanner.scan_website(self.website_url, force=True)

            if scan_result["sections_count"] > 0:
                self.context_prompt = scan_result["context_prompt"]
                self.last_scan_time = scan_result["last_scan_time"]
                logger.info(f"Context initialized with {scan_result['sections_count']} sections")

                # If we didn't get many sections, retry with a deeper scan
                if scan_result["sections_count"] < 5:
                    logger.warning(f"Found only {scan_result['sections_count']} sections, trying deeper scan...")

                    # Force a deeper scan (depth 3, more pages)
                    sections = self.scanner.scan_website_recursive(self.website_url, depth=3, max_pages=100)

                    if len(sections) > scan_result["sections_count"]:
                        # Generate a new context prompt with the additional sections
                        new_context = self.scanner.generate_context_prompt(sections, self.website_url)
                        self.context_prompt = new_context
                        self.last_scan_time = time.time()
                        logger.info(f"Deep scan successful, expanded to {len(sections)} sections")
                    else:
                        logger.warning(f"Deep scan did not find additional content")
            else:
                logger.warning(f"No sections found for {self.website_url}, using default context")
        except Exception as e:
            logger.error(f"Error initializing context: {e}")
            # We already set a default context above, so no need to set it again

    def refresh_context_if_needed(self):
        """Check if context needs refreshing (after 72 hours)"""
        current_time = time.time()
        if self.last_scan_time is None or (current_time - self.last_scan_time > self.scanner.context_expiry_time):
            logger.info(f"Context expired. Refreshing...")
            self.init_context()

    def get_response(self, query: str) -> Dict[str, Any]:
        """Generate a response based on the website content using AI"""
        # Check if context needs refreshing
        self.refresh_context_if_needed()

        # Generate response using AI
        response_data = self._generate_ai_response(query)

        # Add escalation check
        response_data = self._check_for_escalation_request(query, response_data)

        # Update history
        self.history.append({
            "query": query,
            "response": response_data["response"],
            "timestamp": time.time(),
            "escalation_requested": self.escalation_requested
        })

        return response_data

    def _check_for_escalation_request(self, query: str, response_data: Dict[str, Any]) -> Dict[str, Any]:
        """Check if the user is requesting to speak with a human agent or if the situation requires escalation"""
        # Keywords that might indicate frustration or a need for escalation
        escalation_keywords = [
            "speak to a human", "talk to a human", "speak to a person", "talk to a person",
            "speak to someone", "talk to someone", "speak to an agent", "talk to an agent",
            "speak to a representative", "talk to a representative", "speak to a team member",
            "talk to a team member", "speak to staff", "talk to staff", "contact me",
            "get in touch with me", "call me", "email me", "real person", "real human",
            "not helpful", "useless", "unhelpful", "not working", "frustrated", "annoying",
            "doesn't work", "doesn't understand", "don't understand", "stupid", "can't help",
            "manager", "supervisor", "human support", "live chat", "wrong", "incorrect",
            "not what i asked", "not answering", "waste of time", "terrible", "awful",
            "ridiculous", "joke", "terrible service", "poor service", "not satisfied",
            "agent", "representative", "customer service", "help desk", "support team"
        ]

        # Frustration indicators (punctuation, capitalization, etc.)
        frustration_patterns = [
            r'\?{2,}',  # Multiple question marks
            r'\!{2,}',  # Multiple exclamation marks
            r'[A-Z]{3,}',  # ALL CAPS (3+ letters)
            r'\bWHY\b',  # "WHY" in all caps
            r'\bNOT\b',  # "NOT" in all caps
            r'\bCAN\'T\b',  # "CAN'T" in all caps
            r'\bHELP\b'  # "HELP" in all caps
        ]

        # Check conversation length - proactively offer help for long conversations
        conversation_too_long = len(self.history) >= 5  # Offer escalation after 5 exchanges

        # Repetition detection (if user repeats the same question)
        query_lower = query.lower()
        recent_queries = [entry["query"].lower() for entry in self.history[-3:]] if len(self.history) >= 3 else []
        repeated_question = any(self._similarity(query_lower, prev_query) > 0.7 for prev_query in recent_queries)

        # Check for explicit escalation keywords
        explicit_escalation = any(keyword in query_lower for keyword in escalation_keywords)

        # Check for frustration patterns
        import re
        frustration_detected = any(re.search(pattern, query) for pattern in frustration_patterns)

        # Determine if escalation is needed
        escalation_needed = explicit_escalation or frustration_detected or repeated_question or conversation_too_long

        # If we detect an email in the query after escalation was requested
        if self.escalation_requested and ("@" in query and "." in query.split("@")[1]):
            # Extract the email address
            import re
            email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
            email_matches = re.findall(email_pattern, query)

            if email_matches:
                email = email_matches[0]
                # Send email notification via EmailJS directly from the backend
                email_sent = self._send_escalation_email(email, query)

                if email_sent:
                    response_data[
                        "response"] = f"Thank you! A team member will contact you at {email} shortly. Your conversation has been forwarded to our support team."
                else:
                    response_data[
                        "response"] = f"Thank you for providing your email address ({email}). However, there was an issue sending the notification. A team member will review this conversation and contact you as soon as possible."

                # Reset escalation flag
                self.escalation_requested = False
            else:
                response_data[
                    "response"] = "I couldn't detect a valid email address. Could you please provide your email address so our team can contact you? For example: yourname@example.com"

        # If escalation is needed but not yet requested, add escalation message
        elif escalation_needed and not self.escalation_requested:
            # Different escalation messages based on the trigger
            if conversation_too_long:
                escalation_message = "\n\nI notice we've been talking for a while. Would you like me to connect you with a team member who might be able to help further? If so, please provide your email address, and someone will reach out to you directly."
            elif repeated_question:
                escalation_message = "\n\nI notice I may not be addressing your question adequately. Would you like to speak with a team member who can help you more directly? If so, please share your email address, and someone will contact you soon."
            elif explicit_escalation:
                escalation_message = "\n\nI'd be happy to connect you with a team member. Please provide your email address, and someone will contact you shortly."
            else:  # frustration detected
                escalation_message = "\n\nI understand this might be frustrating. Would you like to speak with a team member directly? If so, please provide your email address, and someone will contact you soon."

            # Enhance the response with the appropriate escalation offer
            response_data["response"] += escalation_message
            self.escalation_requested = True

        return response_data

    def _similarity(self, text1: str, text2: str) -> float:
        """Calculate similarity between two texts (simple method)"""
        # This is a basic implementation - could be improved with better NLP techniques
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())

        if not words1 or not words2:
            return 0.0

        intersection = words1.intersection(words2)
        union = words1.union(words2)

        return len(intersection) / len(union)

    def _send_escalation_email(self, user_email: str, last_query: str) -> bool:
        """Send an escalation email with the conversation history using EmailJS"""
        try:
            logger.info(f"Sending escalation email for user: {user_email}")

            # Prepare the conversation history
            conversation = "\n\n".join([
                f"User: {entry['query']}\nChatbot: {entry['response']}"
                for entry in self.history
            ])

            # Prepare the request data for EmailJS
            template_params = {
                "website_url": self.website_url,
                "user_email": user_email,
                "user_query": last_query,
                "conversation": conversation,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
            }

            # Prepare the full request body
            request_data = {
                "service_id": EMAILJS_SERVICE_ID,
                "template_id": EMAILJS_TEMPLATE_ID,
                "user_id": EMAILJS_PUBLIC_KEY,
                "template_params": template_params
            }

            # Make the HTTP request to EmailJS
            try:
                import requests

                logger.info(f"Sending EmailJS request to {EMAILJS_URL}")

                # Log the template parameters being sent
                logger.info(f"Email template params: {json.dumps({
                    'website_url': self.website_url,
                    'user_email': user_email,
                    'conversation_length': len(self.history),
                    'timestamp': time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
                })}")

                headers = {
                    'Content-Type': 'application/json'
                }

                response = requests.post(
                    EMAILJS_URL,
                    headers=headers,
                    json=request_data
                )

                if response.status_code == 200:
                    logger.info(f"Successfully sent escalation email to {user_email}")
                    return True
                else:
                    logger.error(
                        f"Failed to send email: Status code {response.status_code}, Response: {response.text}")
                    return False

            except Exception as request_error:
                logger.error(f"Error making EmailJS request: {request_error}")
                return False

        except Exception as e:
            logger.error(f"Error preparing escalation email: {e}")
            return False

    def _analyze_user_sentiment(self, query: str) -> str:
        """
        Analyze the user's message to detect sentiment and adapt response style.
        Returns one of: "neutral", "frustrated", "curious", "happy", "confused", "urgent"
        """
        query_lower = query.lower()

        # Check for urgent language
        urgent_indicators = ["asap", "urgent", "immediately", "emergency", "right now", "hurry", "quickly"]
        if any(indicator in query_lower for indicator in urgent_indicators):
            return "urgent"

        # Check for frustrated language
        frustrated_indicators = ["not working", "doesn't work", "doesn't help", "unhelpful", "frustrated",
                                 "annoying", "useless", "waste", "terrible", "awful", "stupid"]
        if any(indicator in query_lower for indicator in frustrated_indicators) or "!" in query:
            return "frustrated"

        # Check for confused language
        confused_indicators = ["don't understand", "confused", "unclear", "what do you mean", "how does", "explain"]
        if any(indicator in query_lower for indicator in confused_indicators) or "?" in query:
            return "confused"

        # Check for happy/satisfied language
        happy_indicators = ["thanks", "thank you", "great", "awesome", "excellent", "helpful", "good"]
        if any(indicator in query_lower for indicator in happy_indicators):
            return "happy"

        # Check for curious language (questions, asking for more information)
        curious_indicators = ["how", "what", "where", "when", "why", "who", "can you", "is there", "tell me"]
        if any(query_lower.startswith(indicator) for indicator in curious_indicators):
            return "curious"

        # Default sentiment
        return "neutral"

    def _generate_ai_response(self, query: str) -> Dict[str, Any]:
        """Generate a response using Google Gemini based on the context prompt with enhanced human-like qualities"""
        try:
            # Basic error checking
            if not self.context_prompt:
                return {
                    "response": "I don't have enough information about this website yet. Please try again in a moment.",
                    "source": self.website_url
                }

            # Call Gemini API with error handling
            try:
                import google.generativeai as genai
                from google.generativeai.types import HarmCategory, HarmBlockThreshold

                # Configure the Gemini API
                genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

                # Analyze user sentiment to adjust response tone
                sentiment = self._analyze_user_sentiment(query)

                # Adjust response parameters based on sentiment
                temperature = 0.7  # Default temperature for natural responses

                if sentiment == "frustrated":
                    # More careful and empathetic for frustrated users
                    temperature = 0.4  # Lower temperature for more controlled responses
                elif sentiment == "curious":
                    # More detailed and thorough for curious users
                    temperature = 0.5
                elif sentiment == "urgent":
                    # More direct and concise for urgent queries
                    temperature = 0.3  # Lower temperature for more focused responses

                # Set up the model
                generation_config = {
                    "temperature": temperature,
                    "top_p": 0.95,
                    "top_k": 40,
                    "max_output_tokens": 800,
                }

                # Set up safety settings
                safety_settings = [
                    {
                        "category": HarmCategory.HARM_CATEGORY_HARASSMENT,
                        "threshold": HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE
                    },
                    {
                        "category": HarmCategory.HARM_CATEGORY_HATE_SPEECH,
                        "threshold": HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE
                    },
                    {
                        "category": HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
                        "threshold": HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE
                    },
                    {
                        "category": HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
                        "threshold": HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE
                    },
                ]

                # Get the generative model
                model = genai.GenerativeModel(
                    model_name="gemini-2.0-flash",
                    generation_config=generation_config,
                    safety_settings=safety_settings,
                )

                # Build conversation history for context
                chat_history = []

                # Include recent conversation history for continuity
                # This helps the AI maintain context across multiple messages
                history_to_include = min(5, len(self.history))  # Include up to 5 previous exchanges

                for i in range(max(0, len(self.history) - history_to_include), len(self.history)):
                    chat_history.append({"role": "user", "parts": [self.history[i]["query"]]})
                    chat_history.append({"role": "model", "parts": [self.history[i]["response"]]})

                # Enhance the context prompt for robust, human-like responses
                enhanced_context = self.context_prompt + "\n\n"
                enhanced_context += "Additional instructions:\n"
                enhanced_context += "1. Be conversational and helpful like a human customer service agent.\n"
                enhanced_context += "2. Show empathy when users express frustration or confusion.\n"
                enhanced_context += "3. Use natural language that's professional but not overly formal.\n"
                enhanced_context += "4. If you can't help with a specific request, suggest what the user might do next.\n"
                enhanced_context += "5. Avoid saying 'As an AI' or referring to yourself as a bot or AI.\n"
                enhanced_context += f"6. The user's sentiment appears to be: {sentiment}. Adjust your tone accordingly.\n"

                # Start a chat session with history if available
                if chat_history:
                    chat = model.start_chat(history=chat_history)
                else:
                    chat = model.start_chat(history=[])

                # Send the system prompt first
                system_message = f"System: {enhanced_context}"
                chat.send_message(system_message)

                # Send the user's query
                response = chat.send_message(query)

                # Get the response text
                response_text = response.text

                return {
                    "response": response_text,
                    "source": f"Information from {self.website_url}"
                }

            except ImportError:
                logger.error("Google Generative AI package not installed. Run: pip install google-generativeai")
                return {
                    "response": "I'm having trouble connecting to my knowledge base. The Google Generative AI package is not installed.",
                    "source": f"Error from {self.website_url}"
                }
            except Exception as api_error:
                logger.error(f"Gemini API error: {api_error}")
                # Fallback response that doesn't rely on Gemini
                return {
                    "response": "I'm having trouble accessing my knowledge base right now. For specific questions, please try again in a moment or ask to speak with a team member for immediate assistance.",
                    "source": f"Limited information from {self.website_url}"
                }

        except Exception as e:
            logger.error(f"Error generating response: {e}")
            return {
                "response": "Sorry, I encountered an error while generating a response. Please try again or ask to speak with a team member.",
                "source": self.website_url
            }


# Initialize chatbot manager with the hard-coded website URL
chatbot_manager = ChatbotManager(WEBSITE_URL)


class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, client_id: str):
        await websocket.accept()
        self.active_connections[client_id] = websocket

    def disconnect(self, client_id: str):
        if client_id in self.active_connections:
            del self.active_connections[client_id]

    async def send_message(self, message: str, client_id: str):
        if client_id in self.active_connections:
            await self.active_connections[client_id].send_text(message)


manager = ConnectionManager()


@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    await manager.connect(websocket, client_id)
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)

            if message.get("type") == "query":
                query = message.get("query")
                result = chatbot_manager.get_response(query)
                await manager.send_message(json.dumps(result), client_id)

    except WebSocketDisconnect:
        manager.disconnect(client_id)


# REST API endpoints
@app.post("/api/query")
async def api_query(query: Query):
    """Process a query from the user and get a response from the chatbot"""
    try:
        # Log the incoming query
        logger.info(f"Received query: {query.query}")

        # Get response from chatbot
        result = chatbot_manager.get_response(query.query)

        # Log response summary
        logger.info(
            f"Response length: {len(result.get('response', ''))} chars, source: {result.get('source', 'unknown')}")

        return result
    except Exception as e:
        logger.error(f"Error processing query: {e}")
        return {
            "response": "I apologize, but I encountered an unexpected error. Please try again with your question.",
            "source": "Error handler"
        }


# Basic health check
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "website": WEBSITE_URL,
        "context_last_updated": time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(
            chatbot_manager.last_scan_time)) if chatbot_manager.last_scan_time else None
    }


if __name__ == "__main__":
    # Get port from environment variable (for Railway deployment)
    port = int(os.environ.get("PORT", 8000))

    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=port,
        log_level="info"
    )