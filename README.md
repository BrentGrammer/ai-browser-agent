# AI Browser Agent

An LLM drives a real browser through your web app: it navigates, clicks, fills
forms, takes screenshots, and saves what it learned for the next run.

The supported setup is the LangGraph + Playwright agent running sandboxed in
Docker. An unsandboxed Browser-Use experiment lives in `browser-use/` — read the
warning at the bottom before using it.

## Quick start

Requires Docker with the Compose plugin.

**1. Configure.** Copy `.env.template` to `.env` in the repo root and fill in the
four values it documents: `TARGET_URL`, `LLM_MODEL`, `LLM_API_DOMAIN`,
`LLM_API_KEY`. No login credentials — you log in by hand in step 3.

**2. Start the sandbox.**

```shell
./agent start
```

**3. Log in once.** Open the viewer (see below), then:

```shell
./agent login
```

The browser opens your app. Log in through the viewer, then Ctrl+C. The session
is saved and reused by every later run; repeat this only when it expires.

**4. Run the agent.**

```shell
./agent run
```

Watch it work in the viewer. It follows the `task` written in
`langgraph/langgraph_agent.py` — edit that text to change what it does, then run
again.

## Commands

| Command | What it does |
| --- | --- |
| `./agent start` | Start the sandbox. Runs nothing on its own. |
| `./agent login` | Open the browser so you can log in by hand. |
| `./agent run` | Run the agent against the task in `langgraph_agent.py`. |
| `./agent screenshots` | Copy screenshots out to `langgraph/screenshots/`. |
| `./agent logs` | Follow container logs. |
| `./agent stop` | Stop the sandbox, keeping the login session. |
| `./agent reset` | Stop and erase the login session and learned knowledge. |

## Watching the browser live

The browser runs on a virtual display inside the container and is streamed to
your browser over VNC.

- **On this box:** `http://agent-workbench:6080/vnc.html`
- **Anywhere else:** `http://<host-ip>:6080/vnc.html`

The viewer has no password or TLS, so port 6080 must never be publicly
reachable. On the EC2 box from
[ai-coding-agent-workbench](https://github.com/BrentGrammer/ai-coding-agent-workbench)
that is already true: its security group has no inbound rules at all, and you
reach the viewer over Tailscale, which tunnels outbound and encrypts the stream.

For unwatched background runs, set `HEADLESS: "true"` in `docker-compose.yml`.

## Where output goes

Everything lives in Docker volumes, so no host directory needs to be writable by
the container:

- **Screenshots** — `./agent screenshots` copies them to `langgraph/screenshots/`
- **Learned knowledge** — `agent_knowledge.json`, fed back in on the next run
- **Browser profile** — your login session; `./agent reset` clears it

## How it is sandboxed

Chromium's own sandbox stays on (no `--no-sandbox`), the container is read-only,
non-root, and has every capability dropped, and its only route to the network is
a proxy that denies every domain except your app and the LLM API. See
[docs/sandboxing.md](docs/sandboxing.md) for the threat model and design.

## Running locally without Docker (development)

No sandbox — for iterating on the agent code.

```shell
conda create -n langgraphagent python=3.12 && conda activate langgraphagent
pip install -r langgraph/requirements.txt
pip install langchain-openai   # the package matching your LLM_MODEL
playwright install chromium
cd langgraph && python langgraph_agent.py
```

Uses the same root `.env` as the Docker setup.

## Experimental: Browser-Use library (unsupported)

> **Warning:** an unsandboxed experiment kept for tinkering. It runs directly on
> the host — none of the Docker or proxy protections apply — and it passes
> `LOGIN_USERNAME` / `LOGIN_PASSWORD` straight into the LLM prompt, so those
> credentials leave your machine and reach the LLM provider. Use a dedicated test
> account with a unique password and minimal permissions, never a real account.

```shell
conda create -n browseruse python=3.12 && conda activate browseruse
uv pip install -r requirements.txt
uvx browser-use install
cd browser-use && python browser_agent.py
```

Create `browser-use/.env` from `browser-use/.env.template` first. The task lives
under `task=` in `browser_agent.py`; the model is set in that file too.
