using Gtk;
using Peas;
using Soup;

[CCode (cheader_filename = "gtk/gtk.h")]
extern Gtk.Widget gedit_window_get_side_panel (Gtk.Window window);

[CCode (cheader_filename = "gtk/gtk.h")]
extern void tepl_panel_add (GLib.Object panel, Gtk.Widget widget, string name, string title, string? icon_name);

namespace ResearchCopilot {

    public class Plugin : GLib.Object, Peas.Activatable {
        [CCode (no_accessor_method = true)]
        public GLib.Object object { owned get; construct; }

        private Gtk.Notebook panel_widget;
        private Gtk.TextView preview_view;
        private Gtk.Entry url_entry;
        private Gtk.Entry query_entry;
        private Gtk.TextView summary_text_view;
        private Gtk.Label status_label;
        private Gtk.Spinner spinner;
        private Soup.Session soup_session;

        public void activate () {
            var window = object as Gtk.Window;
            if (window == null) return;

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

            var side_panel = gedit_window_get_side_panel (window);
            if (side_panel != null) {
                tepl_panel_add (side_panel, panel_widget, "ResearchCopilot", "AI Web & Copilot", "system-search");
            }
        }

        public void deactivate () {
            var window = object as Gtk.Window;
            if (window != null && panel_widget != null) {
                var side_panel = gedit_window_get_side_panel (window);
                if (side_panel != null && side_panel is Gtk.Container) {
                    ((Gtk.Container) side_panel).remove (panel_widget);
                }
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
    obj_module.register_extension_type (typeof (Peas.Activatable), typeof (ResearchCopilot.Plugin));
}
