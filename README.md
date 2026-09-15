# Gedit AI Web Research & Markdown Copilot (100% C / Vala Architecture)

A native, high-performance Gedit side-panel plugin written in **Vala & C** providing **Live Markdown Preview** and an **AI Web Research Copilot**, powered by a native **C Daemon** with **Intel OpenVINO Execution Provider** hardware acceleration for Intel integrated graphics (**iGPU**).

---

## 🌟 Key Features

1. **100% Pure C & Vala Core**: Zero Python overhead or Python runtime dependencies. Extremely fast startup and minimal memory footprint.
2. **Intel OpenVINO iGPU Hardware Acceleration**: Utilizes ONNX Runtime accelerated by Intel OpenVINO EP on integrated graphics (`GPU` / `GPU.0` device) with automatic OpenCL kernel warm-up on launch.
3. **Automated First-Launch Model Fetching**: Automatically fetches `Qwen-2.5-0.5B` INT4 ONNX models from **Hugging Face**, with automated fallbacks to **GitHub Releases** and **HF-Mirror**.
4. **Debian Packaging (`.deb`)**: Package generation script for seamless Linux distribution and system-wide installation.
5. **Native Gedit IPC**: Asynchronous non-blocking HTTP IPC via `LibSoup 3` between Vala plugin (`libresearch_copilot.so`) and C daemon (`service/bin/daemon` on port `5055`).

---

## 🏗️ Architecture

```text
┌─────────────────────────────────────────────────────────────────────────┐
│                          Gedit Host Process                             │
│                                                                         │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │                        Gedit Side Panel                           │  │
│  │   [ Tab 1: Live MD Preview ]       [ Tab 2: AI Web Copilot ]      │  │
│  └─────────────────────────────────┬─────────────────────────────────┘  │
│                                    │                                    │
│             Native Vala Plugin (libresearch_copilot.so)                 │
└────────────────────────────────────┼────────────────────────────────────┘
                                     │ Async HTTP / LibSoup 3
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                Native C AI Research Daemon (Port 5055)                  │
│                (libxml2 + cmark + LibSoup 3 HTTP Server)                │
│                                                                         │
│  1. First Launch Handler: Auto-fetch Qwen 2.5 INT4 ONNX from            │
│     Hugging Face -> Fallback to GitHub Release -> Fallback to HF-Mirror.  │
│  2. Intel OpenVINO iGPU Execution Provider ("GPU" device).              │
│  3. Warm-up Sync: Waits until OpenVINO iGPU kernel compilation finishes │
│     before serving live inference requests.                             │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 🚀 Quick Start

### Option 1: Install via Debian Package (`.deb`)

```bash
# Build the Debian package
make deb

# Install system-wide
sudo dpkg -i knowitall.deb
```

### Option 2: Build & Install Locally

```bash
# Compile native C daemon and Vala plugin
make build-daemon
make build-plugin

# Download Qwen-2.5-0.5B INT4 ONNX model weights
make download-model

# Install Vala plugin locally
make install-plugin
```

### Enable in Gedit

1. Open **Gedit**.
2. Navigate to **Preferences** -> **Plugins**.
3. Enable **AI Web Research & Markdown Copilot**.
4. Press `F9` to toggle the Gedit side panel.

---

## 🛠️ Build & Tooling Targets

| Makefile Target | Description |
| :--- | :--- |
| `make build-daemon` | Compiles native C daemon binary (`service/bin/daemon`). |
| `make build-plugin` | Compiles Vala plugin into native shared object (`libresearch_copilot.so`). |
| `make download-model` | Auto-fetches Qwen-2.5 INT4 ONNX model with Hugging Face & GitHub Release fallbacks. |
| `make install-plugin` | Installs plugin files into `~/.local/share/gedit/plugins/`. |
| `make deb` | Builds Debian binary distribution package (`knowitall.deb`). |
| `make test` | Compiles and runs native C daemon unit test suite (`service/tests/test_daemon.c`). |
| `make clean` | Purges compiled binaries, intermediate objects, and package build directories. |

---

## 📄 License

Distributed under the GNU General Public License v3. See [LICENSE](LICENSE) for details.