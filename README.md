# AI Agents

## Option 1: Browser-Use Library (Python)

### Setup

- create a virtual environment (i.e. `conda create -n browseruse python=3.12`)
- `conda activate browseruse` (or whatever env you created locally)
- `uv pip install -r requirements.txt`
- `uvx browser-use install` (one time install for chromium)
- Create a `.env` based off of `template.env` with the target url, username, password to login, and llm api key (Open AI is used in this project)
  - adjust the model or type of LLM (Gemini, Open AI etc.) if needed in browser_agent.py
  - The API key could be for any LLM service even though it is currently named after the OPEN AI service. (update as needed)

### Run the program

- `python browser_agent.py`

### What the agent does:

- Attempts to login to a url (you will need to update the instructions under task= in browser_agent.py to your liking for your site)
- After logging in, navigates through pages of the app
- Takes a screenshot and saves it to a folder

## Option 2: LangGraph (from LangChain) with Playwright

- Could be a bit more predictable than leveraging Browser-Use
- More programmatic control via Playwright
- LangGraph can store memory to remember how to do things in the application

### Pre-requisites and Setup

- Python 3.12 in a virtual environment
  - Example: `conda create -n langgraphagent python=3.12`
    - `conda activate langgraphagent`
    - Make sure the right Python Interpreter is selected in the IDE (i.e for VS Code `CMD + SHFT + P` -> `Python: Select Interpreter`)
- Install dependencies

```shell
pip install langgraph langchain-openai playwright python-dotenv
# or pip install -r requirements.txt in the langgraph folder
playwright install chromium
```

### What the agent does:

- Attempts to learn patterns of app usage (for example logging into the website)
- Patterns are stored in memory from agent tasks run defined in the python script

### Running the agent:

- `python run langgraph_agent.py`