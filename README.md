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

Copy `.env.template` to `.env` in the repo root and fill in `TARGET_URL`,
`LLM_MODEL`, `LLM_API_DOMAIN`, and `LLM_API_KEY` — the template documents each.
No login credentials needed; the proxy allowlist and the langchain provider
package are both derived from these. Switching providers is an `.env` edit
plus `./agent start`.

### Commands

Everything runs through the `./agent` wrapper:

```shell
./agent start        # start the sandbox — runs nothing on its own
./agent login        # open the browser to log in by hand (first time only)
./agent run          # run the agent against the task in langgraph_agent.py
./agent screenshots  # copy screenshots out to langgraph/screenshots/
./agent stop         # stop the sandbox, keeping the login session
./agent reset        # stop and erase the login session and learned knowledge
```

`start` brings up three services and leaves them idle: `agent` (Chromium on a
virtual display), `proxy` (the egress allowlist, its only way out), and `viewer`
(noVNC). Log in once via `login` — the saved session is reused by every later
`run`. To change what the agent does, edit the `task` string in
`langgraph/langgraph_agent.py`.

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

Named volumes, so no host directory needs container-writable permissions:

- Screenshots — `./agent screenshots` copies them to `./langgraph/screenshots/`
- Learned knowledge (`agent_knowledge.json`)
- Browser profile — logins stick across runs; `./agent reset` clears it

## Running LangGraph locally (unsandboxed, for development)

- Python 3.12 in a virtual environment
  - Example: `conda create -n langgraphagent python=3.12`
    - `conda activate langgraphagent`
    - Make sure the right Python Interpreter is selected in the IDE (i.e for VS Code `CMD + SHFT + P` -> `Python: Select Interpreter`)
- Install dependencies

```shell
pip install -r langgraph/requirements.txt
# plus the langchain-<provider> package for your LLM_MODEL, e.g. langchain-openai
playwright install chromium
```

- Uses the same root `.env` as the Docker setup
- Run with `python langgraph_agent.py` from the `langgraph` folder

## Experimental: Browser-Use library (unsupported)

> **Warning:** this is an unsandboxed experiment kept around for tinkering only.
> It runs directly on the host (none of the Docker/proxy protections apply) and
> it passes `LOGIN_USERNAME` / `LOGIN_PASSWORD` from its env file straight into
> the LLM prompt — so the credentials leave your machine and reach the LLM
> provider. Use a dedicated test account with a unique password and minimal
> permissions, never a real account. The sandboxed LangGraph setup above is the
> supported path.

### Setup

- create a virtual environment (i.e. `conda create -n browseruse python=3.12`)
- `conda activate browseruse` (or whatever env you created locally)
- `uv pip install -r requirements.txt`
- `uvx browser-use install` (one time install for chromium)
- Create a `.env` in `browser-use/` based off of `browser-use/.env.template` with the target url, test-account login, and llm api key
  - adjust the model or type of LLM (Gemini, Open AI etc.) if needed in browser_agent.py

### Run the program

- `python browser_agent.py`

### What the agent does:

- Attempts to login to a url (you will need to update the instructions under task= in browser_agent.py to your liking for your site)
- After logging in, navigates through pages of the app
- Takes a screenshot and saves it to a folder
