import json
import urllib.request
import urllib.error
import threading
import gi

gi.require_version('Gtk', '3.0')
gi.require_version('Gedit', '3.0')

HAS_WEBKIT = False
try:
    gi.require_version('WebKit2', '4.0')
    from gi.repository import WebKit2
    HAS_WEBKIT = True
except Exception:
    try:
        gi.require_version('WebKit2', '4.1')
        from gi.repository import WebKit2
        HAS_WEBKIT = True
    except Exception:
        HAS_WEBKIT = False

from gi.repository import GObject, Gtk, Gedit, GLib

DAEMON_URL = "http://localhost:5055"

class ResearchCopilotPlugin(GObject.Object, Gedit.WindowActivatable):
    __gtype_name__ = "ResearchCopilotPlugin"

    window = GObject.Property(type=Gedit.Window)

    def __init__(self):
        GObject.Object.__init__(self)
        self.panel_widget = None
        self.preview_view = None
        self.summary_text_view = None
        self.url_entry = None
        self.query_entry = None
        self.spinner = None
        self.status_label = None
        self.update_timeout_id = None
        self.active_doc_handler = None
        self.current_doc = None

    def do_activate(self):
        self.panel_widget = Gtk.Notebook()

        # Tab 1: Live Markdown Preview
        preview_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        if HAS_WEBKIT:
            self.preview_view = WebKit2.WebView()
            scrolled = Gtk.ScrolledWindow()
            scrolled.add(self.preview_view)
            preview_box.pack_start(scrolled, True, True, 0)
        else:
            scrolled = Gtk.ScrolledWindow()
            self.preview_view = Gtk.TextView()
            self.preview_view.set_editable(False)
            self.preview_view.set_wrap_mode(Gtk.WrapMode.WORD)
            scrolled.add(self.preview_view)
            preview_box.pack_start(scrolled, True, True, 0)

        preview_label = Gtk.Label(label="MD Preview")
        self.panel_widget.append_page(preview_box, preview_label)

        # Tab 2: AI Web Research Copilot
        copilot_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        copilot_box.set_border_width(8)

        url_label = Gtk.Label(label="Target Web URL:", xalign=0)
        self.url_entry = Gtk.Entry()
        self.url_entry.set_placeholder_text("https://example.com/article")

        query_label = Gtk.Label(label="Research Focus / Query:", xalign=0)
        self.query_entry = Gtk.Entry()
        self.query_entry.set_placeholder_text("Summarize key findings...")

        fetch_btn = Gtk.Button(label="Fetch & Summarize")
        fetch_btn.connect("clicked", self.on_fetch_clicked)

        self.spinner = Gtk.Spinner()
        self.status_label = Gtk.Label(label="", xalign=0)

        status_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        status_box.pack_start(self.spinner, False, False, 0)
        status_box.pack_start(self.status_label, True, True, 0)

        output_scrolled = Gtk.ScrolledWindow()
        self.summary_text_view = Gtk.TextView()
        self.summary_text_view.set_wrap_mode(Gtk.WrapMode.WORD)
        output_scrolled.add(self.summary_text_view)

        insert_btn = Gtk.Button(label="Insert at Cursor")
        insert_btn.connect("clicked", self.on_insert_clicked)

        copilot_box.pack_start(url_label, False, False, 0)
        copilot_box.pack_start(self.url_entry, False, False, 0)
        copilot_box.pack_start(query_label, False, False, 0)
        copilot_box.pack_start(self.query_entry, False, False, 0)
        copilot_box.pack_start(fetch_btn, False, False, 0)
        copilot_box.pack_start(status_box, False, False, 0)
        copilot_box.pack_start(output_scrolled, True, True, 0)
        copilot_box.pack_start(insert_btn, False, False, 0)

        copilot_tab_label = Gtk.Label(label="AI Copilot")
        self.panel_widget.append_page(copilot_box, copilot_tab_label)

        self.panel_widget.show_all()

        side_panel = self.window.get_side_panel()
        side_panel.add_titled(self.panel_widget, "ResearchCopilot", "AI Web & Copilot")

        # Connect to active tab signals
        self.window.connect("active-tab-changed", self.on_active_tab_changed)
        self.on_active_tab_changed(self.window, self.window.get_active_tab())

    def do_deactivate(self):
        if self.current_doc and self.active_doc_handler:
            self.current_doc.disconnect(self.active_doc_handler)
            self.active_doc_handler = None

        side_panel = self.window.get_side_panel()
        if self.panel_widget and side_panel:
            side_panel.remove(self.panel_widget)
            self.panel_widget = None

    def do_update_state(self):
        pass

    def on_active_tab_changed(self, window, tab):
        if self.current_doc and self.active_doc_handler:
            self.current_doc.disconnect(self.active_doc_handler)
            self.active_doc_handler = None

        if tab:
            doc = tab.get_document()
            if doc:
                self.current_doc = doc
                self.active_doc_handler = doc.connect("changed", self.on_document_changed)
                self.trigger_preview_update()

    def on_document_changed(self, doc):
        if self.update_timeout_id:
            GLib.source_remove(self.update_timeout_id)
        self.update_timeout_id = GLib.timeout_add(300, self.trigger_preview_update)

    def trigger_preview_update(self):
        self.update_timeout_id = None
        doc = self.window.get_active_document()
        if not doc:
            return False

        start, end = doc.get_bounds()
        text = doc.get_text(start, end, True)

        def worker():
            try:
                data = json.dumps({"markdown": text}).encode("utf-8")
                req = urllib.request.Request(
                    f"{DAEMON_URL}/render-md",
                    data=data,
                    headers={"Content-Type": "application/json"}
                )
                with urllib.request.urlopen(req, timeout=3) as resp:
                    result = json.loads(resp.read().decode("utf-8"))
                    html = result.get("html", "")
                    GLib.idle_add(self.update_preview_ui, html)
            except Exception as e:
                pass

        threading.Thread(target=worker, daemon=True).start()
        return False

    def update_preview_ui(self, html):
        if HAS_WEBKIT and isinstance(self.preview_view, WebKit2.WebView):
            self.preview_view.load_html(html, "http://localhost")
        else:
            buf = self.preview_view.get_buffer()
            buf.set_text(html)

    def on_fetch_clicked(self, button):
        url = self.url_entry.get_text().strip()
        query = self.query_entry.get_text().strip() or "Summarize key points"

        if not url:
            self.status_label.set_text("Error: Please enter a valid URL.")
            return

        self.spinner.start()
        self.status_label.set_text("Fetching and summarizing...")

        def worker():
            try:
                payload = json.dumps({"url": url, "query": query}).encode("utf-8")
                req = urllib.request.Request(
                    f"{DAEMON_URL}/scrape-and-summarize",
                    data=payload,
                    headers={"Content-Type": "application/json"}
                )
                with urllib.request.urlopen(req, timeout=30) as resp:
                    result = json.loads(resp.read().decode("utf-8"))
                    summary = result.get("summary", "")
                    GLib.idle_add(self.on_fetch_success, summary)
            except Exception as e:
                GLib.idle_add(self.on_fetch_error, str(e))

        threading.Thread(target=worker, daemon=True).start()

    def on_fetch_success(self, summary):
        self.spinner.stop()
        self.status_label.set_text("Summary generated successfully!")
        buf = self.summary_text_view.get_buffer()
        buf.set_text(summary)

    def on_fetch_error(self, err_msg):
        self.spinner.stop()
        self.status_label.set_text(f"Error: {err_msg}")

    def on_insert_clicked(self, button):
        buf = self.summary_text_view.get_buffer()
        start, end = buf.get_bounds()
        text = buf.get_text(start, end, True)

        if text and self.window:
            doc = self.window.get_active_document()
            if doc:
                doc.insert_at_cursor(text)
