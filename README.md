<div align="center">

# Ctx AI

_A personal, organic agentic framework that grows and learns with you_

[![Website](https://img.shields.io/badge/Website-agent--zero.ai-0A2020?style=flat&logo=v)](https://ctxai.ai)
[![Discord](https://img.shields.io/badge/Discord-Join-5865F2?style=flat&logo=discord)](https://discord.gg/B8KZKNsPpj)
[![X](https://img.shields.io/badge/Follow-000000?style=flat&logo=x)](https://x.com/KhulnaSoft)
[![YouTube](https://img.shields.io/badge/Subscribe-red?style=flat&logo=youtube)](https://www.youtube.com/@CtxAiFW)
[![GitHub Sponsors](https://img.shields.io/badge/Sponsor-FF69B4?style=flat&logo=githubsponsors)](https://github.com/sponsors/ctxos)

---

> **Ctx AI Skills System** — portable, structured agent capabilities using the open `SKILL.md` standard (compatible with Claude Code, Codex and more).
> 
> Plus: Git-based Projects with authentication for public/private repositories.

[Get Started](./docs/setup/installation.md) • [Usage Guide](./docs/guides/usage.md) • [Development](./docs/setup/dev-setup.md) • [Update](./docs/setup/installation.md#how-to-update-ctxai)

</div>

---

## Why Ctx AI?

Ctx AI is not a predefined agentic framework. It's designed to be **dynamic, organically growing, and learning** as you use it.

- Fully transparent, readable, and customizable
- Uses the computer as a tool to accomplish your tasks
- Multi-agent cooperation with hierarchical task delegation

![Ctx AI Working](/docs/res/ui_screen2.png)

---

## Quick Start

```bash
# Pull and run with Docker
docker pull ctxos/ctxai
docker run -p 50001:80 ctxos/ctxai

# Visit http://localhost:50001 to start
```

[Installation Guide](./docs/setup/installation.md) — Windows, macOS, and Linux

---

## Key Features

### 🤖 General-purpose Assistant
Give Ctx AI any task and it will gather information, execute commands, write code, and cooperate with other agents to accomplish it. It has persistent memory to learn from previous solutions.

### 🔧 Computer as a Tool
- No single-purpose tools pre-programmed
- Creates its own tools as needed using code and terminal
- **Default tools:** knowledge search, code execution, communication
- **Skills (SKILL.md):** Dynamic contextual expertise — compatible with Claude Code, Cursor, Goose, OpenAI Codex CLI, and GitHub Copilot

### 👥 Multi-agent Cooperation
- Every agent has a superior giving tasks and instructions
- Agents can create subordinates to break down complex tasks
- Keeps context clean and focused

### ✏️ Completely Customizable
- Everything defined in **prompts/** folder — change the system prompt, change the framework
- Default tools in **backend/tools/** can be extended or replaced
- Configure via `CTX_SET_` environment variables

### 💬 Communication is Key
- Real-time interactive terminal — intervene at any time
- Agents report back, ask questions, and delegate subtasks
- Point-scoring systems, permission workflows, result verification — all customizable

---

## Real-world Use Cases

| Use Case | Example |
|----------|---------|
| **Financial Analysis** | "Find last month's Bitcoin/USD price trend, correlate with news, generate annotated chart" |
| **Excel Automation** | "Scan directory for spreadsheets, validate data, consolidate, generate executive reports" |
| **API Integration** | "Use this Gemini API snippet to generate product images, remember for future use" |
| **Server Monitoring** | "Check server every 30 min: CPU, disk, memory. Alert if thresholds exceeded" |
| **Client Isolation** | Separate projects with isolated memory, custom instructions, and dedicated secrets |

---

## Dockerized with Speech

![Settings](docs/res/settings-page-ui1.png)

- Clean, colorful, interactive Web UI — nothing hidden
- Load/save chats directly in the browser
- Session logs auto-saved to HTML in **logs/** folder
- Real-time streaming — read along and intervene anytime
- Works reliably with small models

---

## ⚠️ Important

1. **Ctx AI Can Be Dangerous** — With the right instructions, it can perform potentially dangerous actions. Always run in an isolated environment (like Docker) and be careful what you wish for.

2. **Prompt-based Framework** — The entire behavior is guided by the **prompts/** folder. Agent guidelines, tool instructions, messages, and utility functions are all there.

---

## Documentation

| Guide | Description |
|-------|-------------|
| [Installation](./docs/setup/installation.md) | Setup, configuration, and updates |
| [Usage](./docs/guides/usage.md) | Basic and advanced usage |
| [Projects](./docs/guides/projects.md) | Git-based project management |
| [Guides](./docs/guides/) | API integration, MCP, A2A setup |
| [Development](./docs/setup/dev-setup.md) | Dev environment and customization |
| [WebSocket Infra](./docs/developer/websockets.md) | Real-time handlers and client APIs |
| [Extensions](./docs/developer/extensions.md) | Extending Ctx AI |
| [Architecture](./docs/developer/architecture.md) | System design |
| [Contributing](./docs/guides/contribution.md) | How to contribute |
| [Troubleshooting](./docs/guides/troubleshooting.md) | Common issues |

---

<div align="center">

_Built by [GitHub](https://github.com/ctxos)

</div>
