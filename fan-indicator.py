import gi
import os

gi.require_version('Gtk', '3.0')
gi.require_version('AppIndicator3', '0.1')

from gi.repository import Gtk, AppIndicator3, GLib


class TrayIndicator:
    def __init__(self):
        self.app = 'My Indicator'
        print(os.getcwd())
        self.icon_path = 'generic-fan-symbolic'  # Change 'icon1' to your actual icon file path
        self.file_path = 'test-file'  # Change 'test-file-1' to your first file path

        self.indicator = AppIndicator3.Indicator.new(self.app, self.icon_path,
                                                     AppIndicator3.IndicatorCategory.APPLICATION_STATUS)
        self.indicator.set_status(AppIndicator3.IndicatorStatus.ACTIVE)
        self.indicator.set_menu(self.build_menu())

        # Keep track of the state for alternating between two sets of values
        self.current_state = 0

        # Update the tooltip periodically
        GLib.timeout_add_seconds(5, self.update_tooltip)

    def build_menu(self):
        menu = Gtk.Menu()

        # Add a quit option to the menu
        item_quit = Gtk.MenuItem(label='Quit')
        item_quit.connect('activate', self.quit)
        menu.append(item_quit)

        menu.show_all()
        return menu

    def update_tooltip(self):
        try:
            with open(self.file_path, 'r') as file:
                value = file.read().strip()
                self.indicator.set_icon_full(self.icon_path, self.app)
                self.indicator.set_label(value, self.app)
        except FileNotFoundError:
            self.indicator.set_label('File not found', self.app)

        # Returning True ensures the function is called again after the specified interval
        return True

    def quit(self, source):
        Gtk.main_quit()


def main():
    Gtk.init([])
    indicator = TrayIndicator()
    Gtk.main()


if __name__ == "__main__":
    main()
