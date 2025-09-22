#!/usr/bin/env python3

import gi
gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
from gi.repository import Gtk, GLib, Gio, Gdk
import locale
import os
import queue
import sys
import pyperclip
import importlib.util
from datetime import datetime

# Load the VoxtarixEngine from voxtarix.py
voxtarix_path = os.path.join(os.path.dirname(__file__), "voxtarix.py")
spec = importlib.util.spec_from_file_location("voxtarix", voxtarix_path)
voxtarix_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(voxtarix_module)
VoxtarixEngine = voxtarix_module.VoxtarixEngine
ClipboardStateChangedEvent = voxtarix_module.ClipboardStateChangedEvent
TypingStateChangedEvent = voxtarix_module.TypingStateChangedEvent
EngineTerminatedEvent = voxtarix_module.EngineTerminatedEvent
TextRecognizedEvent = voxtarix_module.TextRecognizedEvent

class VoxtarixWaylandApplet:
    def __init__(self):
        # Create a simple window instead of using AppIndicator
        self.window = Gtk.Window()
        self.window.set_title("Voxtarix")
        self.window.set_default_size(220, 600)
        self.window.set_skip_taskbar_hint(True)
        self.window.set_skip_pager_hint(True)
        self.window.connect("delete-event", self.on_window_close)
        
        # Create main container
        vbox = Gtk.VBox(spacing=10)
        vbox.set_border_width(10)
        self.window.add(vbox)
        
        # Status label
        self.status_label = Gtk.Label()
        self.status_label.set_markup("<b>Voxtarix Status</b>")
        vbox.pack_start(self.status_label, False, False, 0)
        
        # Mute toggle
        self.mute_toggle = Gtk.CheckButton(label="Mute")
        self.mute_toggle.connect("toggled", self.on_mute_toggled)
        vbox.pack_start(self.mute_toggle, False, False, 0)
        
        # Clipboard toggle
        self.clipboard_toggle = Gtk.CheckButton(label="Clipboard")
        self.clipboard_toggle.connect("toggled", self.on_clipboard_toggled)
        vbox.pack_start(self.clipboard_toggle, False, False, 0)
        

        
        # History section
        history_label = Gtk.Label()
        history_label.set_markup("<b>Recent Transcriptions:</b>")
        vbox.pack_start(history_label, False, False, 0)
        
        # Scrolled window for history
        self.scrolled_window = Gtk.ScrolledWindow()
        self.scrolled_window.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        self.scrolled_window.set_size_request(-1, 200)
        
        # Create list box for clickable history items
        self.history_listbox = Gtk.ListBox()
        self.history_listbox.set_selection_mode(Gtk.SelectionMode.NONE)
        
        # Create a box to control alignment and margins
        list_container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        list_container.set_margin_start(0)
        list_container.set_margin_end(0)
        list_container.pack_start(self.history_listbox, True, True, 0)
        
        self.scrolled_window.add(list_container)
        vbox.pack_start(self.scrolled_window, True, True, 0)
        

        
        self.window.show_all()
        
        # Initialize engine
        self.event_queue = queue.Queue()
        self.engine = None
        self.history = []
        self.muted = False
        
        try:
            current_locale, _ = locale.getlocale(locale.LC_MESSAGES)
            if current_locale:
                language = current_locale.split('_')[0]
            else:
                language = "en"
        except Exception as e:
            print(f"Failed to detect GNOME language: {e}, falling back to 'en'", file=sys.stderr)
            language = "en"

        print(f"Detected GNOME language: {language}", file=sys.stderr)

        try:
            self.engine = VoxtarixEngine(language=language, event_queue=self.event_queue)
            self.engine.start()
            GLib.timeout_add(100, self.process_events)
            self.update_status("Running")
        except Exception as e:
            print(f"Failed to start VoxtarixEngine: {e}", file=sys.stderr)
            self.update_status("Error")
        print("Applet initialized", file=sys.stderr)

    def update_status(self, status):
        if self.muted:
            self.status_label.set_markup(f"<b>Voxtarix Status: {status} (Muted)</b>")
        else:
            self.status_label.set_markup(f"<b>Voxtarix Status: {status}</b>")

    def on_window_close(self, widget, event):
        # Use the same quit function as voice command
        self.quit(None)
        return False

    def on_mute_toggled(self, widget):
        self.muted = widget.get_active()
        if self.engine:
            self.engine.muted = self.muted
        print(f"Mute {'enabled' if self.muted else 'disabled'}", file=sys.stderr)
        self.update_status("Running")

    def on_clipboard_toggled(self, widget):
        if self.engine:
            self.engine.use_clipboard = widget.get_active()
            print(f"Clipboard {'enabled' if self.engine.use_clipboard else 'disabled'}", file=sys.stderr)



    def add_to_history(self, text):
        if not isinstance(text, str) or not text.strip():
            return
        
        text = text.strip()
        
        # Add to beginning of list (newest first)
        self.history.insert(0, text)
        
        # Clear existing items
        for child in self.history_listbox.get_children():
            self.history_listbox.remove(child)
        
        # Add new items (newest first)
        for item_text in self.history:
            self.create_history_item(item_text)
        
        # Show all items and scroll to top
        self.history_listbox.show_all()
        
        # Scroll to top
        adjustment = self.scrolled_window.get_vadjustment()
        adjustment.set_value(0)

    def create_history_item(self, text):
        # Create a clickable button instead of ListBoxRow for better click handling
        button = Gtk.Button()
        button.set_relief(Gtk.ReliefStyle.NONE)
        
        # Create label with text wrapping
        label = Gtk.Label()
        label.set_text(text)
        label.set_line_wrap(True)
        label.set_line_wrap_mode(2)  # PANGO_WRAP_WORD
        label.set_max_width_chars(50)
        label.set_halign(Gtk.Align.START)
        label.set_valign(Gtk.Align.START)
        label.set_xalign(0.0)  # Force left alignment
        label.set_margin_start(3)
        label.set_margin_end(3)
        label.set_margin_top(5)
        label.set_margin_bottom(5)
        
        # Add label to button and ensure button alignment
        button.add(label)
        button.set_halign(Gtk.Align.FILL)
        
        # Connect click event
        button.connect("clicked", lambda btn, text=text: self.on_history_item_clicked(text))
        
        # Create a ListBoxRow and add the button to it
        row = Gtk.ListBoxRow()
        row.set_activatable(False)
        row.add(button)
        
        # Add row to listbox
        self.history_listbox.add(row)

    def on_history_item_clicked(self, text):
        print(f"Button clicked with text: {text}", file=sys.stderr)
        try:
            self.copy_to_clipboard(text)
            print(f"Successfully copied to clipboard: {text[:50]}...", file=sys.stderr)
        except Exception as e:
            print(f"Failed to copy to clipboard: {e}", file=sys.stderr)

    def copy_to_clipboard(self, text):
        clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
        clipboard.set_text(text, -1)
        clipboard.store()

    def quit(self, source):
        if self.engine and not self.engine.should_terminate:
            self.engine.should_terminate = True
        Gtk.main_quit()

    def process_events(self):
        try:
            while True:
                event = self.event_queue.get_nowait()
                if isinstance(event, EngineTerminatedEvent):
                    print("Engine terminated via voice command, stopping applet...", file=sys.stderr)
                    self.quit(None)
                    return False
                elif isinstance(event, ClipboardStateChangedEvent):
                    self.clipboard_toggle.set_active(event.enabled)
                    print(f"Clipboard state updated: {'enabled' if event.enabled else 'disabled'}", file=sys.stderr)

                elif isinstance(event, TextRecognizedEvent):
                    self.add_to_history(event.text)
        except queue.Empty:
            pass
        return True

    def show_window(self):
        self.window.present()

if __name__ == "__main__":
    app = VoxtarixWaylandApplet()
    
    # Create a simple keyboard shortcut to show the window
    # User can press Alt+F2 and type 'pkill -USR1 python' to show window
    import signal
    signal.signal(signal.SIGUSR1, lambda sig, frame: app.show_window())
    
    Gtk.main()