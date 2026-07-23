# Know-It-All: Semi-AI NLP Webcrawler (Panel Widget)

Know-It-All is a native, localized "Semi-AI" panel widget. It bypasses the need for heavy LLMs (like Gemini or Copilot) by leveraging classical Natural Language Processing (NLP) to parse user intent, performing intelligent web crawling via DuckDuckGo, and presenting a localized extractive summary inside a beautiful, Dark-Copilot themed UI.

## Architecture

The project is structured with a powerful background Python D-Bus service and multiple lightweight, native panel widget frontends tailored to different Desktop Environments.

1.  **Python D-Bus Backend (`org.knowitall.CrawlerService`)**
    *   Listens for conversational queries over the D-Bus session bus.
    *   Uses `nltk` for keyword extraction and query intent.
    *   Scrapes DuckDuckGo (HTML version) with `beautifulsoup4`.
    *   Summarizes text and renders a Copilot-styled HTML response using `Jinja2`.
2.  **Native Panel Frontends**
    *   **XFCE:** Python/GTK3 PyGObject panel plugin.
    *   **KDE Plasma:** QML Plasmoid widget.

## Build and Installation

### Prerequisites

Ensure you have the necessary system libraries installed:
```bash
sudo apt update
sudo apt install python3 python3-venv python3-gi gir1.2-gtk-3.0 gir1.2-xfcepanel-2.0
```

### Packaging via GitHub Actions or Script

This repository uses automated scripts to build a Debian package (`.deb`) containing the Python backend and native C++/Python plugins, as well as a standalone `.plasmoid` file for KDE.

To build the Debian package locally:
```bash
./packaging/build_deb.sh
```

To build the KDE Plasmoid locally:
```bash
./packaging/build_plasmoid.sh
```

### Running the Backend Manually

If you'd like to test the backend crawler service locally before installing the plugins:
```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python3 crawler_service.py
```
You can then test it using `dbus-send` or `qdbus`.