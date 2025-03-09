# Context-Aware Website Chatbot

A smart chatbot that scans and understands website content to provide context-aware responses to user inquiries. The chatbot uses natural language processing to analyze website content and generate human-like responses based on the website's context.

## Features

- **Automatic Website Scanning**: Recursively scans websites to extract and process content
- **Context-Aware Responses**: Generates responses based on website content and context
- **Natural Language Processing**: Uses NLP to understand user queries and website content
- **Sentiment Analysis**: Detects user sentiment to adapt response tone
- **Human Escalation**: Offers to connect users with human support when appropriate
- **WebSocket Support**: Real-time chat functionality via WebSockets
- **Email Notifications**: Sends emails for customer support escalations
- **FastAPI Backend**: Fast, modern API framework with automatic OpenAPI documentation

## Tech Stack

- **Backend**: Python 3.9+, FastAPI
- **NLP**: NLTK, scikit-learn
- **AI**: Google Gemini API
- **Web Scraping**: BeautifulSoup4, Requests
- **Database**: In-memory caching (can be extended to persistent storage)
- **Real-time Communication**: WebSockets
- **Email Integration**: EmailJS

## Getting Started

### Prerequisites

- Python 3.9+
- Google Gemini API Key

### Installation

1. Clone the repository
   ```bash
   git clone https://github.com/yourusername/context-aware-chatbot.git
   cd context-aware-chatbot