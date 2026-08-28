# EDA Studio

React frontend + FastAPI backend. Load a CSV, walk a seven-step EDA path, then ask an open LLM (Groq GPT-OSS / Qwen, or Ollama) for insights.

Repo: [github.com/Vekri/EDA-AI](https://github.com/Vekri/EDA-AI)

## Run locally

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
cd frontend && npm install && npm run build && cd ..
uvicorn server:app --host 127.0.0.1 --port 8787
```

Open http://127.0.0.1:8787

## Deploy

Vercel builds the React app, then hosts FastAPI (`server.py`) as a function. Set `GROQ_API_KEY` in the Vercel project environment variables.

## LLM

Put `GROQ_API_KEY` in `.env` locally (see `.env.example`). Insights uses `openai/gpt-oss-20b` on Groq by default.
