#!/usr/bin/env python3

import gi
gi.require_version("Gtk", "3.0")
gi.require_version("AppIndicator3", "0.1")
from gi.repository import Gtk, AppIndicator3, GLib
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

class VoxtarixApplet:
    def __init__(self):
        self.indicator = AppIndicator3.Indicator.new(
            "voxtarix-applet",
            os.path.abspath(os.path.join(os.path.dirname(__file__), "icon/voxtarix-white.png")),
            AppIndicator3.IndicatorCategory.APPLICATION_STATUS
        )
        self.indicator.set_status(AppIndicator3.IndicatorStatus.ACTIVE)
        self.indicator.set_menu(self.build_menu())

        self.event_queue = queue.Queue()
        self.engine = None
        self.history = []
        self.muted = False
        self.icon_unmuted = os.path.abspath(os.path.join(os.path.dirname(__file__), "icon/voxtarix-white.png"))
        self.icon_muted = os.path.abspath(os.path.join(os.path.dirname(__file__), "icon/voxtarix-white-muted.png"))

        try:
            self.engine = VoxtarixEngine(language="de", event_queue=self.event_queue)
            self.engine.start()
            GLib.timeout_add(100, self.process_events)
        except Exception as e:
            print(f"Failed to start VoxtarixEngine: {e}", file=sys.stderr)
        print("Applet initialized", file=sys.stderr)

    def build_menu(self):
        self.menu = Gtk.Menu()

        self.mute_toggle = Gtk.CheckMenuItem(label="Mute")
        self.mute_toggle.set_active(False)
        self.mute_toggle.connect("toggled", self.on_mute_toggled)
        self.menu.append(self.mute_toggle) 

        self.clipboard_toggle = Gtk.CheckMenuItem(label="Clipboard")
        self.clipboard_toggle.set_active(False)
        self.clipboard_toggle.connect("toggled", self.on_clipboard_toggled)
        self.menu.append(self.clipboard_toggle)

        self.typing_toggle = Gtk.CheckMenuItem(label="Typing")
        self.typing_toggle.set_active(False)
        self.typing_toggle.connect("toggled", self.on_typing_toggled)
        self.menu.append(self.typing_toggle)

        self.menu.append(Gtk.SeparatorMenuItem())

        self.history_items = []

        item_quit = Gtk.MenuItem(label="Quit")
        item_quit.connect("activate", self.quit)
        self.menu.append(Gtk.SeparatorMenuItem())
        self.menu.append(item_quit)

        self.menu.show_all()
        return self.menu

    def on_mute_toggled(self, widget):
        self.muted = widget.get_active()
        self.engine.muted = self.muted
        print(f"Mute {'enabled' if self.muted else 'disabled'}", file=sys.stderr)
        self.indicator.set_icon_full(
            self.icon_muted if self.muted else self.icon_unmuted,
            "Voxtarix Applet"
        )

    def on_clipboard_toggled(self, widget):
        if self.engine:
            self.engine.use_clipboard = widget.get_active()
            print(f"Clipboard {'enabled' if self.engine.use_clipboard else 'disabled'}", file=sys.stderr)

    def on_typing_toggled(self, widget):
        if self.engine:
            self.engine.use_typing = widget.get_active()
            print(f"Typing {'enabled' if self.engine.use_typing else 'disabled'}", file=sys.stderr)

    def add_to_history(self, text):
        if not isinstance(text, str) or not text.strip():
            return
        self.history.append(text.strip())
        self.update_history_menu()

    def copy_to_clipboard(self, text):
        pyperclip.copy(text)

    def update_history_menu(self):
        for item in self.history_items:
            self.menu.remove(item)
        self.history_items.clear()

        for text in self.history[-5:]:
            display_text = text[:20] + "..." if len(text) > 20 else text
            item = Gtk.MenuItem(label=display_text)
            item.connect("activate", lambda w, t=text: self.copy_to_clipboard(t))
            self.history_items.append(item)
            self.menu.insert(item, len(self.menu.get_children()) - 2)

        self.menu.show_all()

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
                    return False  # Stop the timeout and don't process further events
                elif isinstance(event, ClipboardStateChangedEvent):
                    self.clipboard_toggle.set_active(event.enabled)
                    print(f"Clipboard state updated: {'enabled' if event.enabled else 'disabled'}", file=sys.stderr)
                elif isinstance(event, TypingStateChangedEvent):
                    self.typing_toggle.set_active(event.enabled)
                    print(f"Typing state updated: {'enabled' if event.enabled else 'disabled'}", file=sys.stderr)
                elif isinstance(event, TextRecognizedEvent):
                    self.add_to_history(event.text)
        except queue.Empty:
            pass
        return True

if __name__ == "__main__":
    indicator = VoxtarixApplet()
    Gtk.main()