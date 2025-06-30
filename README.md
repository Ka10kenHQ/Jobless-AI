# 🔍 MCP Job Search Server

An intelligent job search system that uses an MCP (Model Context Protocol) server with a chatbox interface to find jobs matching your specific requirements.

## ✨ Features

- **Intelligent Job Matching**: Uses AI to understand your job requirements from natural language
- **Multi-Source Scraping**: Searches across LinkedIn, Indeed, and Glassdoor
- **Real-time Chat Interface**: Interactive chatbox for job search conversations
- **Smart Filtering**: Matches jobs based on title, location, skills, and experience level
- **WebSocket Support**: Real-time updates and responses
- **RESTful API**: Programmatic access to job search functionality
- **Custom Model Training**: Train your own specialized job search model

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

**Note**: You'll also need Chrome browser installed for Selenium-based scraping.

### 2. Choose Your Model Approach

#### Option A: Use Pre-trained Model (Quick Start)
```bash
python scripts/serve.py
```

#### Option B: Train Your Own Model (Recommended)

**Unified Training (Auto-detects your GPU):**
```bash
# Auto-optimized training for your hardware
python scripts/train.py

# Quick test (3-5 minutes) 
python scripts/train.py --quick-test

# Georgian + English multilingual training
python scripts/train.py --languages georgian english

# Start server with trained model
python scripts/serve_trained.py
```

**Supported GPUs:**
- RTX 4050/4060 (6-8GB): Auto-optimized with BF16, 4-bit quantization
- RTX 3060/4070 (8-12GB): Enhanced settings with larger batches  
- RTX 4080/4090 (16-24GB): Full performance mode

### 3. Access the Chatbox

- **General Model**: http://localhost:8000/chatbox
- **Trained Model**: http://localhost:8000/chatbox (when using serve_trained.py)

## 💬 How to Use the Chatbox

Simply describe what job you're looking for in natural language:

**Examples:**
- "I'm looking for a senior Python developer job in New York with React experience"
- "Find me remote React developer positions" 
- "I want a data scientist role with machine learning experience"
- "Looking for entry-level software engineer jobs in San Francisco"

The system will:
1. Extract your requirements from your message
2. Search multiple job sites
3. Match and rank results based on your criteria
4. Present the best matches with explanations

## 🎯 GPU Auto-Optimization & Georgian Support

**Hardware Support:**
- **Any NVIDIA GPU** with CUDA support (auto-detected)
- 16GB+ RAM (recommended)
- 10GB free disk space

**Auto-Optimizations by GPU:**
- **RTX 4050/4060**: BF16, batch size 1, 4-bit quantization, gradient checkpointing
- **RTX 3060/4070**: BF16, batch size 2-4, selective optimizations
- **RTX 4080/4090**: Full performance with large batches and models

**Multilingual Features:**
- **Georgian language support** via mGPT model (1.3B params)
- **Job site scrapers** for hr.ge and jobs.ge
- **Auto-model selection** based on language needs and GPU capability

**Training Options:**
```bash
# Auto-optimized training (detects your GPU)
python scripts/train.py

# Quick test (3-5 minutes, optimal sample size)  
python scripts/train.py --quick-test

# Georgian + English multilingual
python scripts/train.py --languages georgian english

# Monitor your specific GPU
watch -n 1 nvidia-smi
```

**Memory Management:**
- System **automatically detects** your GPU and applies optimal settings
- **No manual configuration** needed for different GPU models
- Training automatically saves checkpoints and resumes on interruption

## 🔧 API Usage

### WebSocket Connection

```javascript
const ws = new WebSocket('ws://localhost:8000/ws/your_user_id');

ws.send(JSON.stringify({
    message: "Looking for Python developer jobs in NYC",
    timestamp: new Date().toISOString()
}));
```

### REST API

```bash
curl -X POST "http://localhost:8000/search_jobs" \
     -H "Content-Type: application/json" \
     -d '{
       "message": "Looking for Python developer jobs in NYC",
       "user_id": "user123"
     }'
```

## 📋 Response Format

The system returns structured data including:

```json
{
  "response": "Natural language response about the search",
  "jobs": [...],  // All found jobs
  "matched_jobs": [...],  // Jobs that match your criteria
  "requirements_extracted": {
    "keywords": "python developer",
    "location": "nyc", 
    "skills": ["python"],
    "experience_level": "any"
  },
  "total_jobs_found": 25,
  "total_matched_jobs": 12
}
```

## 🎯 Job Matching Algorithm

The system uses a sophisticated matching algorithm that considers:

- **Title/Keywords (40% weight)**: How well the job title matches your requirements
- **Location (20% weight)**: Geographic matching with support for remote work
- **Skills (25% weight)**: Technical skills and related technologies  
- **Experience Level (15% weight)**: Entry, mid-level, or senior positions

Each job gets a match score from 0-1, and only jobs above 0.3 threshold are shown.

## 🛠 Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Chatbox UI    │◄──►│  MCP Server     │◄──►│  Job Scrapers   │
│   (WebSocket)   │    │  (FastAPI)      │    │  (Multi-source) │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                        ┌─────────────────┐
                        │  Job Matcher    │
                        │  (AI Scoring)   │
                        └─────────────────┘
```

### Key Components

- **`inference/server.py`**: Main MCP server with WebSocket and REST APIs
- **`data_collection/scraper_hr_ge.py`**: Multi-source job scraping
- **`inference/job_matcher.py`**: Intelligent job matching and scoring
- **`scripts/serve.py`**: Server startup script

## 🔍 Supported Job Sites

- **LinkedIn**: Job search with recent postings
- **Indeed**: Comprehensive job listings  
- **Glassdoor**: Company insights and positions

## 🤖 AI Features

- **Requirement Extraction**: Uses the OpenChat model to understand natural language job descriptions
- **Fuzzy Matching**: Handles similar terms and typos in job titles
- **Skill Recognition**: Recognizes related technologies and skills
- **Context Awareness**: Maintains conversation context for follow-up questions

## 🎓 Training Your Own Model

### Why Train a Custom Model?

Training a job search-specific model provides:
- **Better requirement extraction** from natural language
- **More accurate job matching** responses
- **Domain-specific understanding** of job search conversations
- **Improved performance** on job-related tasks

### Training Process

```bash
# Quick test training (5 minutes)
python scripts/train.py --quick-test

# Full training with synthetic data
python scripts/train.py --synthetic-samples 5000

# Training with real job data collection
python scripts/train.py --synthetic-samples 3000

# Custom training with specific config
python training/trainer.py --num-synthetic 10000 --no-real-data
```

### Training Components

1. **Dataset Preparation**: Generates synthetic job search conversations
2. **LoRA Fine-tuning**: Efficient training using Low-Rank Adaptation
3. **Multi-task Learning**: Trains on requirement extraction + conversation
4. **Real Data Integration**: Optionally incorporates scraped job data

### Training Configuration

Edit `config/hyperparameters.py` to customize:

- **Base Model**: Default is `microsoft/DialoGPT-medium`
- **LoRA Parameters**: Rank, alpha, dropout for efficient training
- **Training Args**: Epochs, batch size, learning rate
- **Dataset Size**: Number of synthetic examples to generate

## ⚙️ Configuration

The system supports two modes:

### Pre-trained Model Mode
- Uses OpenChat for general conversation
- Basic requirement extraction
- Fast setup, good general performance

### Trained Model Mode  
- Uses your custom-trained model
- Specialized for job search tasks
- Better accuracy, domain-specific responses

**Customization Options:**
- **Model**: Change base model in `config/hyperparameters.py`
- **Scraping Limits**: Adjust `limit_per_source` in scraping calls
- **Match Threshold**: Modify the 0.3 threshold in `job_matcher.py`
- **Training Data**: Add your own job search conversations

## 🔒 Notes on Web Scraping

This tool scrapes publicly available job postings for research and personal use. Please:
- Use responsibly and respect rate limits
- Check each site's robots.txt and terms of service
- Consider using official APIs when available
- Don't use for commercial purposes without permission

## 🐛 Troubleshooting

**Common Issues:**

1. **Chrome/Selenium Issues**: Install Chrome browser and ensure chromedriver is in PATH
2. **Model Loading**: Ensure you have enough GPU memory for the language model
3. **Network Issues**: Some sites may block requests; use VPN if needed
4. **Rate Limiting**: The scraper includes delays to avoid overwhelming servers

**RTX 4050 Specific:**

5. **Out of Memory**: Try `--ultra-light` mode or close other GPU applications
6. **Slow Training**: Use `--quick-test` for faster iteration
7. **Model Not Loading**: Check VRAM usage with `nvidia-smi`

## 📈 Future Enhancements

- [ ] More job sites (Stack Overflow, AngelList, etc.)
- [ ] Salary information extraction and filtering
- [ ] Email alerts for new matching jobs
- [ ] Resume matching against job requirements
- [ ] Company research and insights
- [ ] Application tracking

## 📄 License

MIT License - see LICENSE file for details.

---

**Happy Job Hunting! 🎯** 