using Gtk;
using Peas;
using Soup;

namespace Gedit {
    [CCode (cheader_filename = "gedit/gedit-window.h", has_type_id = true)]
    public interface WindowActivatable : GLib.Object {
        public abstract Gedit.Window window { get; construct; }
        public abstract void activate ();
        public abstract void deactivate ();
        public abstract void update_state ();
    }

    [CCode (cheader_filename = "gedit/gedit-window.h")]
    public class Window : Gtk.Window {
        public extern Gtk.Widget get_side_panel ();
        public extern Gtk.Widget get_active_document ();
    }
}

namespace ResearchCopilot {

    public class Plugin : GLib.Object, Gedit.WindowActivatable {
        public Gedit.Window window { get; construct; }

        private Gtk.Notebook panel_widget;
        private Gtk.TextView preview_view;
        private Gtk.Entry url_entry;
        private Gtk.Entry query_entry;
        private Gtk.TextView summary_text_view;
        private Gtk.Label status_label;
        private Gtk.Spinner spinner;
        private Soup.Session soup_session;

        public void activate () {
            panel_widget = new Gtk.Notebook ();
            soup_session = new Soup.Session ();

            // Tab 1: Live MD Preview
            var preview_box = new Gtk.Box (Gtk.Orientation.VERTICAL, 4);
            var scrolled_preview = new Gtk.ScrolledWindow (null, null);
            preview_view = new Gtk.TextView ();
            preview_view.editable = false;
            preview_view.wrap_mode = Gtk.WrapMode.WORD;
            scrolled_preview.add (preview_view);
            preview_box.pack_start (scrolled_preview, true, true, 0);

            var preview_label = new Gtk.Label ("MD Preview");
            panel_widget.append_page (preview_box, preview_label);

            // Tab 2: AI Web Research Copilot
            var copilot_box = new Gtk.Box (Gtk.Orientation.VERTICAL, 6);
            copilot_box.border_width = 8;

            var url_lbl = new Gtk.Label ("Target Web URL:");
            url_lbl.halign = Gtk.Align.START;
            url_entry = new Gtk.Entry ();
            url_entry.placeholder_text = "https://example.com/article";

            var query_lbl = new Gtk.Label ("Research Focus / Query:");
            query_lbl.halign = Gtk.Align.START;
            query_entry = new Gtk.Entry ();
            query_entry.placeholder_text = "Summarize key findings...";

            var fetch_btn = new Gtk.Button.with_label ("Fetch & Summarize");
            fetch_btn.clicked.connect (on_fetch_clicked);

            spinner = new Gtk.Spinner ();
            status_label = new Gtk.Label ("");
            status_label.halign = Gtk.Align.START;

            var status_box = new Gtk.Box (Gtk.Orientation.HORIZONTAL, 6);
            status_box.pack_start (spinner, false, false, 0);
            status_box.pack_start (status_label, true, true, 0);

            var output_scrolled = new Gtk.ScrolledWindow (null, null);
            summary_text_view = new Gtk.TextView ();
            summary_text_view.wrap_mode = Gtk.WrapMode.WORD;
            output_scrolled.add (summary_text_view);

            var insert_btn = new Gtk.Button.with_label ("Insert at Cursor");

            copilot_box.pack_start (url_lbl, false, false, 0);
            copilot_box.pack_start (url_entry, false, false, 0);
            copilot_box.pack_start (query_lbl, false, false, 0);
            copilot_box.pack_start (query_entry, false, false, 0);
            copilot_box.pack_start (fetch_btn, false, false, 0);
            copilot_box.pack_start (status_box, false, false, 0);
            copilot_box.pack_start (output_scrolled, true, true, 0);
            copilot_box.pack_start (insert_btn, false, false, 0);

            var copilot_tab_label = new Gtk.Label ("AI Copilot");
            panel_widget.append_page (copilot_box, copilot_tab_label);

            panel_widget.show_all ();

            var side_panel = window.get_side_panel ();
            if (side_panel != null) {
                GLib.Signal.emit_by_name (side_panel, "add-titled", panel_widget, "ResearchCopilot", "AI Web & Copilot");
            }
        }

        public void deactivate () {
            var side_panel = window.get_side_panel ();
            if (side_panel != null && panel_widget != null) {
                ((Gtk.Container) side_panel).remove (panel_widget);
                panel_widget = null;
            }
        }

        public void update_state () {
        }

        private void on_fetch_clicked () {
            string url = url_entry.text.strip ();
            string query = query_entry.text.strip ();
            if (query == "") query = "Summarize key findings";

            if (url == "") {
                status_label.set_text ("Error: Please enter a valid URL.");
                return;
            }

            spinner.start ();
            status_label.set_text ("Fetching and summarizing...");

            var message = new Soup.Message ("POST", "http://127.0.0.1:5055/scrape-and-summarize");
            string payload = "{\"url\": \"%s\", \"query\": \"%s\"}".printf (url, query);
            message.set_request_body_from_bytes ("application/json", new Bytes (payload.data));

            soup_session.send_and_read_async.begin (message, GLib.Priority.DEFAULT, null, (obj, res) => {
                try {
                    var bytes = soup_session.send_and_read_async.end (res);
                    string response_text = (string) bytes.get_data ();
                    spinner.stop ();
                    status_label.set_text ("Summary generated successfully!");
                    summary_text_view.buffer.text = response_text;
                } catch (Error e) {
                    spinner.stop ();
                    status_label.set_text ("Error: %s".printf (e.message));
                }
            });
        }
    }
}

[ModuleInit]
public void peas_register_types (Peas.ObjectModule module) {
    var obj_module = (Peas.ObjectModule) module;
    obj_module.register_extension_type (typeof (Gedit.WindowActivatable), typeof (ResearchCopilot.Plugin));
}
