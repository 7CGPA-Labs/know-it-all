import gi
gi.require_version('Gtk', '3.0')
gi.require_version('XfcePanelPlugin', '2.0')
from gi.repository import Gtk, XfcePanelPlugin
from pydbus import SessionBus

def on_button_clicked(widget, plugin):
    bus = SessionBus()
    try:
        service = bus.get('org.knowitall.CrawlerService')
        html = service.AskQuestion("Tell me about Semi-AI")
        # Pop up a dialog with the result
        dialog = Gtk.MessageDialog(
            parent=None,
            flags=0,
            message_type=Gtk.MessageType.INFO,
            buttons=Gtk.ButtonsType.OK,
            text="Know-It-All Result"
        )
        dialog.format_secondary_text(html)
        dialog.run()
        dialog.destroy()
    except Exception as e:
        print(f"Error calling D-Bus service: {e}")

def create_plugin(plugin):
    button = Gtk.Button(label="Know-It-All")
    button.connect("clicked", on_button_clicked, plugin)
    plugin.add(button)
    plugin.show_all()

XfcePanelPlugin.register(create_plugin)
