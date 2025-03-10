# Context-Aware Website Chatbot

![Python Version](https://img.shields.io/badge/python-3.9%2B-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.95%2B-green)
![Google Gemini](https://img.shields.io/badge/AI-Google%20Gemini-orange)

A smart chatbot that scans and understands website content to provide context-aware responses to user inquiries. Built with Google Gemini AI and advanced NLP techniques, this chatbot delivers human-like responses that are specifically tailored to your website's content.


## 🌟 Features

- **Intelligent Website Scanning**: Automatically crawls and indexes your website content, extracting relevant information for generating responses
- **Context-Aware AI**: Uses Google Gemini AI to understand both user queries and website content
- **Natural Language Processing**: Employs advanced NLP techniques for content understanding and processing
- **Sentiment Analysis**: Detects user emotions and adapts response tone accordingly
- **Human Escalation**: Intelligently identifies when to offer human support options
- **Real-time Communication**: Supports WebSockets for smooth, real-time conversations
- **WordPress Integration**: Includes a ready-to-use WordPress plugin for easy deployment
- **Analytics Dashboard**: Provides conversation statistics and insights (WordPress plugin)
- **Developer-Friendly**: Well-documented codebase with clean API endpoints
- **Customizable UI**: Adaptable front-end design with configurable colors and position

## 🚀 Getting Started

### Prerequisites

- Python 3.9+
- Google Gemini API Key (Get one from [Google AI Studio](https://makersuite.google.com/app/apikey))
- Hosting environment with HTTP/HTTPS support

### Installation

1. Clone the repository
   ```bash
   git clone https://github.com/yourusername/context-aware-chatbot.git
   cd context-aware-chatbot
   ```

2. Create and activate a virtual environment
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies
   ```bash
   pip install -r requirements.txt
   ```

4. Create a `.env` file with your API key
   ```bash
   echo "GEMINI_API_KEY=your-Gemini-Api-Key" > .env
   ```

5. Start the server
   ```bash
   uvicorn app:app --host 0.0.0.0 --port 8000
   ```

6. Test the chatbot
   ```bash
   python test_client.py
   ```

## 📋 Configuration Options

### FastAPI Backend

The `.env` file supports these configuration variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `GEMINI_API_KEY` | Your Google Gemini API key | (Required) |
| `WEBSITE_URL` | Target website URL for scanning | Set in app.py |
| `MAX_SCAN_DEPTH` | Maximum recursive scan depth | 3 |
| `MAX_SCAN_PAGES` | Maximum pages to scan | 200 |

### WordPress Plugin

The plugin admin panel provides these options:

- **Chatbot Name**: Customizable name displayed in the header
- **Welcome Message**: Initial greeting message
- **Position**: Bottom-left or bottom-right screen placement
- **Primary Color**: Main theme color for the chatbot
- **Secondary Color**: Text color on primary color backgrounds

## 🔧 Technical Architecture

<p align="center">
  <img src="https://github.com/TERRA26/context-aware-chatbot/raw/main/docs/architecture.png" alt="Architecture Diagram" width="700">
</p>

The system comprises these key components:

1. **FastAPI Backend**: Handles web requests, website scanning, and AI integration
2. **Website Scanner**: Extracts and processes website content
3. **NLP Processing Pipeline**: Analyzes and structures text data
4. **Google Gemini Integration**: Provides AI-powered responses
5. **WordPress Plugin**: Client-side interface with chat functionality
6. **Analytics Dashboard**: Visualizes conversation statistics

## 💻 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/query` | POST | Send a user query, get AI response |
| `/ws/{client_id}` | WebSocket | Real-time bidirectional communication |
| `/health` | GET | Server health check and status |
| `/api/send-email` | POST | Human escalation email trigger |

## 🔌 WordPress Integration

The included WordPress plugin provides a complete front-end solution:

1. Upload the `chatbot-plugin` directory to your WordPress plugins folder
2. Activate the "Luxe Customer Support Chatbot" plugin
3. Configure appearance in Settings → Luxe Chatbot
4. Access analytics in the admin menu under "Chatbot Stats"

<p align="center">
  <img src="https://github.com/TERRA26/context-aware-chatbot/raw/main/docs/wordpress-dashboard.png" alt="WordPress Dashboard" width="700">
</p>

## 🛠️ Development and Testing

### Local Testing

```bash
# Run the server
uvicorn app:app --reload

# Test with the provided client
python test_client.py --server http://localhost:8000
```

## 📊 Analytics and Insights

The WordPress plugin includes a comprehensive dashboard showing:

- Total conversations and average message count
- Conversations over time (chart)
- Common user queries
- Recent conversation history
- Shareable public dashboard link

## 🔄 Roadmap

- [ ] Persistent database storage option
- [ ] Multi-language support
- [ ] Voice input/output capabilities 
- [ ] Customizable conversation flows
- [ ] Knowledge base integration
- [ ] E-commerce product recommendations
- [ ] File upload/download support

## 🚀 Deployment Options

### Railway Deployment

Railway offers a simple deployment process:

1. Create a Railway account and new project
2. Connect your GitHub repository or use Railway's CLI
3. Add your `GEMINI_API_KEY` as an environment variable
4. Deploy the application
5. Railway will automatically recognize the Procfile and requirements.txt

```bash
# Using Railway CLI
railway login
railway init
railway up
```

### AWS Deployment

Deploy to AWS Elastic Beanstalk:

1. Create an Elastic Beanstalk environment with Python platform
2. Prepare your application:
   ```bash
   pip install awsebcli
   eb init -p python-3.9 context-aware-chatbot
   ```
3. Create a `.ebextensions/01_env.config` file:
   ```yaml
   option_settings:
     aws:elasticbeanstalk:application:environment:
       GEMINI_API_KEY: your-Gemini-Api-Key
   ```
4. Deploy:
   ```bash
   eb create context-aware-chatbot-env
   ```

### Custom Server Deployment

For standard VPS or dedicated server:

1. Clone the repository
   ```bash
   git clone https://github.com/yourusername/context-aware-chatbot.git
   cd context-aware-chatbot
   ```
2. Install dependencies
   ```bash
   pip install -r requirements.txt
   ```
3. Set up environment variables
   ```bash
   export GEMINI_API_KEY=your-Gemini-Api-Key
   ```
4. Run with Gunicorn (production server)
   ```bash
   gunicorn -w 4 -k uvicorn.workers.UvicornWorker app:app
   ```
5. Set up a reverse proxy (Nginx/Apache) to forward requests
