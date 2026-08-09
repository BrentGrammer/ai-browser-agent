# AI Agents

LLM-driven browser automation. The supported path is the LangGraph agent run
sandboxed in Docker (below). A separate Browser-Use experiment lives in
`browser-use/` — see the warning at the bottom before touching it.

## LangGraph (from LangChain) with Playwright

- Could be a bit more predictable than leveraging Browser-Use
- More programmatic control via Playwright
- LangGraph can store memory to remember how to do things in the application

### What the agent does:

- Attempts to learn patterns of app usage (for example logging into the website)
- Patterns are stored in memory from agent tasks run defined in the python script

## Running Sandboxed in Docker (recommended)

Runs the LangGraph agent in a locked-down container: Chromium's own sandbox stays on
(no `--no-sandbox`), the agent's only network route is an egress proxy that
default-denies all but an allowlist of domains, and the container is read-only,
non-root, with all capabilities dropped. See `docs/sandboxing.md` for the full
threat model and design.

### Prerequisites

- Docker with the Compose plugin installed on the host

### Setup

Copy `.env.template` to `.env` in the repo root and set `TARGET_URL`,
`LLM_API_DOMAIN` (your LLM provider's API host, e.g. `api.openai.com` or
`api.anthropic.com`), and the LLM API key — no login credentials needed. That's
the whole config: the egress proxy's allowlist is derived from it (the target
app's domain plus the LLM API host, subdomains included). The optional variables
in the template cover extra navigation domains or extra proxy-allowed hosts
(e.g. the app's CDN).

### First-time login

```shell
LOGIN_MODE=true docker compose up --build
```

Open the viewer (URL below), log in to the site by hand, then Ctrl+C. The session
is saved in the browser profile volume and reused by the agent. Repeat whenever
the session expires. This works on any site — no selectors or credentials in config.

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
then open `http://agent-workbench:6080/vnc.html` (the box's MagicDNS name — bookmarkable,
survives rebuilds). If MagicDNS is disabled on your tailnet, use the box's stable
Tailscale IP instead (`tailscale ip -4` on the box).

For unwatched background runs, set `HEADLESS: "true"` in `docker-compose.yml`.

### Where output goes

- Screenshots: `./langgraph/screenshots/` (bind-mounted from the container)
- Learned knowledge: the `knowledge` named volume (`agent_knowledge.json`)
- Browser profile (cookies/session): the `profile` named volume — persists across
  runs, so logins stick; `docker volume rm` it for a fresh session

## Running LangGraph locally (unsandboxed, for development)

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

- Uses the same root `.env` as the Docker setup
- Run with `python langgraph_agent.py` from the `langgraph` folder

## Experimental: Browser-Use library (unsupported)

> **Warning:** this is an unsandboxed experiment kept around for tinkering only.
> It runs directly on the host (none of the Docker/proxy protections apply) and
> it passes `LOGIN_USERNAME` / `LOGIN_PASSWORD` from its env file straight into
> the LLM prompt. Only ever point it at a throwaway account on a test app —
> never real credentials. The sandboxed LangGraph setup above is the supported
> path.

### Setup

- create a virtual environment (i.e. `conda create -n browseruse python=3.12`)
- `conda activate browseruse` (or whatever env you created locally)
- `uv pip install -r requirements.txt`
- `uvx browser-use install` (one time install for chromium)
- Create a `.env` in `browser-use/` based off of `browser-use/.env.template` with the target url, throwaway login, and llm api key
  - adjust the model or type of LLM (Gemini, Open AI etc.) if needed in browser_agent.py

### Run the program

- `python browser_agent.py`

### What the agent does:

- Attempts to login to a url (you will need to update the instructions under task= in browser_agent.py to your liking for your site)
- After logging in, navigates through pages of the app
- Takes a screenshot and saves it to a folder
