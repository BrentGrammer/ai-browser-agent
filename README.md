# AI Agents

## Browser-Use Library (Python)
 
### Setup
- create a virtual environment (i.e. `conda create -n browseruse python=3.12`)
- `conda activate browseruse` (or whatever env you created locally)
- `uv pip install -r requirements.txt`
- `uvx browser-use install` (one time install for chromium)
- update the `.env` files with the target url, username, password to login, and llm api key (Open AI is used in this project)
  - adjust the model or type of LLM (Gemini, Open AI etc.) if needed in browser_agent.py

### Run the program

- `python browser_agent.py`
