# ╔══════════════════════════════════════════════════════════════════╗
# ║   NutriBot — AI Nutrition Agent                                  ║
# ║   Powered by IBM Watsonx.ai (Granite Models)                     ║
# ╚══════════════════════════════════════════════════════════════════╝

## Overview

NutriBot is a full-stack AI-powered Nutrition Agent web application built with:
- **Backend**: Python Flask + IBM Watsonx.ai (Granite-13b-chat-v2)
- **Frontend**: Bootstrap 5, vanilla JS, dark mode, mobile responsive
- **Features**: Chat UI, Nutrition Dashboard, Meal Plan Generator, BMI Calculator, Family Diet Planner

---

## Project Structure

```
nutrition-agent/
├── app.py                  # Flask backend — routes & API endpoints
├── agent.py                # IBM Watsonx.ai agent + AGENT_INSTRUCTIONS
├── requirements.txt        # Python dependencies
├── env.txt                 # Rename to .env before running
├── templates/
│   └── index.html          # Single-page HTML frontend
└── static/
    ├── css/
    │   ├── style.css       # Main stylesheet (dark mode, animations)
    │   └── extras.css      # Additional utility styles
    └── js/
        └── app.js          # Frontend logic (chat, BMI, meal plan, family)
```

---

## Quick Start

### 1. Prerequisites
- Python 3.9 or higher
- IBM Cloud account with Watsonx.ai access
- Valid IBM API Key and Project ID

### 2. Set Up Environment

```bash
# Clone / copy the project folder
cd nutrition-agent

# Create virtual environment
python -m venv venv

# Activate (Windows)
venv\Scripts\activate

# Activate (Mac/Linux)
source venv/bin/activate
```

### 3. Create `.env` File

```bash
# Copy env.txt to .env
copy env.txt .env          # Windows
cp env.txt .env            # Mac/Linux
```

Your `.env` should contain:
```
IBM_API_KEY=your_ibm_api_key_here
IBM_PROJECT_ID=8de9fb00-0119-4bb9-aafb-4d28a2503209
IBM_WATSONX_URL=https://us-south.ml.cloud.ibm.com
FLASK_SECRET_KEY=nutrition-agent-super-secret-key-2024
FLASK_ENV=development
FLASK_DEBUG=True
APP_PORT=5000
APP_HOST=0.0.0.0
```

### 4. Install Dependencies

```bash
pip install -r requirements.txt
```

> **Note**: If `ibm-watsonx-ai` fails to install, try:
> ```bash
> pip install ibm-watsonx-ai --upgrade --no-cache-dir
> ```

### 5. Run the Application

```bash
python app.py
```

Open your browser at: **http://localhost:5000**

---

## Customising the AI Agent

Open `agent.py` and find the `AGENT_INSTRUCTIONS` block:

```python
AGENT_INSTRUCTIONS = """
You are NutriBot, an expert AI nutritionist...
"""
```

You can customise:
| Section | What to Edit |
|---|---|
| **PERSONA & TONE** | Change personality, warmth level, formality |
| **SPECIALISATIONS** | Add/remove diet types (keto, paleo, ayurvedic…) |
| **INDIAN FOOD PREFERENCES** | Add regional foods, spices, seasonal items |
| **RESPONSE FORMAT** | Change output structure, length, emoji usage |
| **SAFETY RULES** | Update disclaimers, calorie limits, medical referrals |
| **CAPABILITIES** | Add new features (e.g. supplement guidance, workout plans) |

### Change the Model
In `agent.py`, edit:
```python
model_id: str = "ibm/granite-13b-chat-v2"
```

Available Granite models on Watsonx.ai:
- `ibm/granite-13b-chat-v2` (recommended — best for dialogue)
- `ibm/granite-3-8b-instruct` (faster, lighter)
- `ibm/granite-20b-multilingual` (multilingual support)

### Tune Generation Parameters
In `agent.py`:
```python
GENERATE_PARAMS = {
    "decoding_method": "greedy",   # or "sample"
    "max_new_tokens": 1024,        # increase for longer responses
    "temperature": 0.7,            # 0.0 = deterministic, 1.0 = creative
    "repetition_penalty": 1.1,
}
```

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Main web application |
| `POST` | `/api/chat` | Send a chat message |
| `POST` | `/api/chat/clear` | Clear conversation history |
| `POST` | `/api/nutrition/analyze` | Analyze meal nutrition |
| `POST` | `/api/mealplan/generate` | Generate a meal plan |
| `POST` | `/api/bmi/calculate` | Calculate BMI + advice |
| `POST` | `/api/family/plan` | Generate family nutrition plan |
| `GET` | `/api/health/tips` | Get daily nutrition tips |
| `GET` | `/api/health/status` | Check agent status |

### Example: Chat API
```bash
curl -X POST http://localhost:5000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Give me a high-protein Indian breakfast"}'
```

### Example: Meal Plan API
```bash
curl -X POST http://localhost:5000/api/mealplan/generate \
  -H "Content-Type: application/json" \
  -d '{"calories": 1800, "dietary_preference": "Vegetarian", "cuisine": "South Indian", "duration": 7}'
```

---

## Production Deployment

### Option 1: Gunicorn (Linux/Mac)
```bash
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

### Option 2: Docker

Create `Dockerfile`:
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 5000
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "app:app"]
```

Build and run:
```bash
docker build -t nutribot .
docker run -p 5000:5000 --env-file .env nutribot
```

### Option 3: IBM Code Engine / Cloud Foundry
```bash
ibmcloud login
ibmcloud target --cf
ibmcloud cf push nutribot -m 512M
```

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| `ibm-watsonx-ai` import error | Run `pip install ibm-watsonx-ai --upgrade` |
| 401 Unauthorized from Watsonx | Check your `IBM_API_KEY` in `.env` |
| App shows "Demo Mode" | Watsonx SDK loaded but API call failed — check Project ID and URL |
| Port already in use | Change `APP_PORT=5001` in `.env` |
| Slow first response | First call initialises the model (lazy loading) — subsequent calls are faster |

---

## Security Notes

- ⚠️ **Never commit `.env` to version control** — it contains your API key
- The `env.txt` file is a safe template (no real credentials in tracked form)
- In production, use environment variables or IBM Secrets Manager
- Session data is stored server-side (Flask sessions with secret key)

---

## Features Checklist

- ✅ AI Chat with multi-turn conversation memory
- ✅ User profile context (age, gender, weight, goals)
- ✅ Quick prompt shortcuts
- ✅ Meal nutrition analyzer with calorie extraction
- ✅ 7-day / 14-day meal plan generator
- ✅ BMI calculator with visual needle indicator
- ✅ Family nutrition planner (multiple members)
- ✅ Daily health tips
- ✅ Dark mode with system preference detection
- ✅ Fully responsive mobile design
- ✅ Loading overlay with status messages
- ✅ Toast notification system
- ✅ Markdown rendering in AI responses
- ✅ AGENT_INSTRUCTIONS customisation block
- ✅ Demo mode fallback when Watsonx offline

---

## License

MIT License — Free to use, modify, and distribute.

---

*Made with ❤️ using IBM Watsonx.ai · Flask · Bootstrap 5*
