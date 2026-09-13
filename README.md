# Gedit AI Web Research & Markdown Copilot

A native Gedit side-panel plugin providing **Live Markdown Preview** and an **AI Web Research Copilot** (`trafilatura` + `Qwen-2.5-0.5B-Instruct` via `onnxruntime-genai`) running inside an isolated containerized service.

---

## 🌟 Key Features

1. **Live Markdown Preview**: Real-time rendering of your active Gedit Markdown document via WebKit2GTK in the side panel, debounced to guarantee zero UI lag.
2. **AI Web Research Copilot**: Ingests web URLs via `trafilatura` clean DOM extraction, applies a tailored **Agent Role Prompt**, synthesizes research notes using `Qwen-2.5-0.5B-Instruct` ONNX LLM, and allows 1-click **Insert at Cursor** into your document.
3. **Container-Isolated Micro-Daemon**: Runs as an isolated service via Docker/Podman (or local Python venv) communicating over HTTP API on port `5055`.
4. **Automated CI/CD**:
   - `publish-models.yml`: Automated model packaging and GitHub Release assets.
   - `build-plugin.yml`: Continuous Integration for container daemon builds and plugin packaging.

---

## 🏗️ Architecture

```text
┌─────────────────────────────────────────────────────────────┐
│                       Gedit Desktop Host                    │
│                                                             │
│   ┌─────────────────────────────────────────────────────┐   │
│   │                 Gedit Side Panel                    │   │
│   │  [ Tab 1: MD Preview ]   [ Tab 2: AI Copilot ]      │   │
│   └──────────────────────────┬──────────────────────────┘   │
└──────────────────────────────┼──────────────────────────────┘
                               │ IPC (HTTP / JSON)
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                 Container / Subprocess Daemon               │
│                 (Docker / Podman / Local Venv)              │
│                                                             │
│  FastAPI (Port 5055)                                        │
│  ├── /render-md (Markdown -> GTK Styled HTML)               │
│  └── /scrape-and-summarize (Trafilatura + Qwen-2.5-0.5B)    │
└─────────────────────────────────────────────────────────────┘
```

---

## 🚀 Quick Start

### 1. Download Model & Build Container Daemon

```bash
# Download Qwen-2.5-0.5B ONNX Model weights
make download-model

# Build Docker / Podman daemon container image
make build-container

# Start the AI Research Daemon service
./service/run_daemon.sh
```

The daemon will start listening on `http://localhost:5055`.

### 2. Install the Gedit Plugin

```bash
make install-plugin
```

This copies `research_copilot.plugin` and `research_copilot.py` to `~/.local/share/gedit/plugins/`.

### 3. Enable in Gedit

1. Open **Gedit**.
2. Go to **Preferences** -> **Plugins**.
3. Check the box for **AI Web Research & Markdown Copilot**.
4. Press `F9` (or View -> Side Panel) to show the side panel.

---

## 🛠️ Development & Tooling

| Makefile Target | Description |
| :--- | :--- |
| `make build-container` | Builds `gedit-research-daemon:latest` Docker/Podman image. |
| `make download-model` | Downloads Qwen 2.5 0.5B ONNX model weights via `download_model.py`. |
| `make install-plugin` | Installs plugin files to `~/.local/share/gedit/plugins/`. |
| `make clean-legacy` | Purges legacy standalone application artifacts. |
| `make test` | Executes unit tests via `pytest`. |

---

## 📄 License

Distributed under the GNU General Public License v3. See [LICENSE](LICENSE) for details.