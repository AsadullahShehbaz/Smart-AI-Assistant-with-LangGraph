# 🤖 LangGraph Chatbot

Simple chatbot with memory using LangGraph and Qdrant.

## Features
- 🧠 Long-term memory
- 🛠️ Multiple tools (calculator, YouTube, stocks, web search)
- 💬 Multiple conversations
- 💾 Auto-save conversations

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Create `.env` file:
```python
OPENROUTER_API_KEY=your_key
QDRANT_URL=your_url
QDRANT_API_KEY=your_key
STOCK_API_KEY=your_key
```
3. Run:
```bash
streamlit run app.py
```

## Project Structure
├── config.py      # Settings
├── memory.py      # Memory functions
├── tools.py       # AI tools
├── agent.py       # Agent logic
└── app.py         # UI and logic

## Made by [Ali Asadullah Shehbaz]

# 🎯 Migration Steps (Copy-Paste!)

## 1.Create new folder:
```bash
mkdir langgraph-chatbot-simple
cd langgraph-chatbot-simple
```
## 2.Copy your .env file into this folder
## 3.Create all 5 Python files (copy code from above):

* config.py
* memory.py
* tools.py
* agent.py
* app.py


## 4.Create data folder:
`mkdir data`

## 5.Create supporting files:

- .gitignore
- requirements.txt
- README.md
## 6.Run it:
`streamlit run app.py`
