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

## Running Sandboxed in Docker (recommended)

Runs the LangGraph agent in a locked-down container: Chromium's own sandbox stays on
(no `--no-sandbox`), the agent's only network route is an egress proxy that
default-denies all but an allowlist of domains, and the container is read-only,
non-root, with all capabilities dropped. See `docs/sandboxing.md` for the full
threat model and design.

### Prerequisites

- Docker with the Compose plugin installed on the host

### Setup

1. Copy `env.template` to `.env` in the repo root and set `PROXY_ALLOWED_DOMAINS`
   to a comma-separated list of hosts the agent may reach (your target app's domain
   plus the LLM API, e.g. `yourapp.com,api.openai.com`). Subdomains are included
   automatically.
2. Create `langgraph/.env` from `langgraph/env.template` as usual (target url,
   login credentials, LLM API key). Optionally set `ALLOWED_NAV_DOMAINS` for extra
   domains the agent may navigate to (the `TARGET_URL` host is always allowed).

### Run

```shell
docker compose up --build
```

This starts three services:

- `agent` — the LangGraph agent + Chromium, on an internal-only network
- `proxy` — the egress allowlist proxy (the agent's only way out)
- `viewer` — noVNC, so you can watch the browser live

### Watching the browser live

The compose default is headed mode (`HEADLESS: "false"`): the browser runs on a
virtual display inside the container and is streamed via VNC. Open
`http://<host-ip>:6080/vnc.html` in a browser to watch.

The viewer has no auth or TLS, so on a remote host port 6080 must not be publicly
reachable. On the EC2 box from
[ai-coding-agent-workbench](https://github.com/BrentGrammer/ai-coding-agent-workbench)
this is already handled: its security group has zero inbound rules, blocking all
public traffic. Tailscale still gets through because it tunnels over an *outbound*
WireGuard connection — which also encrypts the HTTP stream, so no HTTPS is needed.

To view: install Tailscale on your laptop and join the same tailnet as the box,
then open `http://<box-tailscale-ip>:6080/vnc.html` (run `tailscale ip -4` on the
box to get the IP).

For unwatched background runs, set `HEADLESS: "true"` in `docker-compose.yml`.

### Where output goes

- Screenshots: `./langgraph/screenshots/` (bind-mounted from the container)
- Learned knowledge: the `knowledge` named volume (`agent_knowledge.json`)
- Browser profile (cookies/session): the `profile` named volume — persists across
  runs, so logins stick; `docker volume rm` it for a fresh session