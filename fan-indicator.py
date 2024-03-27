import gi
import os
import configparser

gi.require_version('Gtk', '3.0')
gi.require_version('AppIndicator3', '0.1')

from gi.repository import Gtk, AppIndicator3, GLib

print(os.path.expanduser('~'))
CONFIG_FILE = os.path.join(os.path.expanduser('~'), '.fan_indicator_config')
temp_toggle = True  # True -> C | False -> F


# Function to load configuration
def load_config():
    config = configparser.ConfigParser()
    if not os.path.exists(CONFIG_FILE):
        # If the config file doesn't exist, create it with default values
        config['Preferences'] = {'TemperatureUnit': 'True'}  # Default to Celsius
        save_config(config)
    else:
        config.read(CONFIG_FILE)
    return config


# Function to save configuration
def save_config(config):
    with open(CONFIG_FILE, 'w') as configfile:
        config.write(configfile)


def find_hwmon_directory():
    hwmon_base_path = '/sys/devices/platform/coretemp.0/hwmon/'
    hwmon_directory = None

    # Iterate over subdirectories to find the one with 'temp1_input'
    for directory in os.listdir(hwmon_base_path):
        if os.path.exists(os.path.join(hwmon_base_path, directory, 'temp1_input')):
            hwmon_directory = os.path.join(hwmon_base_path, directory)
            break

    if hwmon_directory is None:
        raise FileNotFoundError("Could not find the directory with 'temp1_input'")

    return hwmon_directory


def find_fan_directory():
    fan_base_path = '/sys/devices/platform/clevofan/hwmon/'
    fan_directory = None

    # Iterate over subdirectories to find the one with 'fan1_input'
    for directory in os.listdir(fan_base_path):
        if os.path.exists(os.path.join(fan_base_path, directory, 'fan1_input')):
            fan_directory = os.path.join(fan_base_path, directory)
            break

    if fan_directory is None:
        raise FileNotFoundError("Could not find the directory with 'fan1_input'")

    return fan_directory


def celsius_to_fahrenheit(celsius):
    return (celsius * 9 / 5) + 32


def quit(source):
    Gtk.main_quit()


class TrayIndicator:
    def __init__(self):
        # Load configuration
        self.config = load_config()
        self.file_path = find_hwmon_directory() + '/temp1_input'

        # Retrieve temperature unit preference from configuration
        self.temp_toggle = self.config.getboolean('Preferences', 'TemperatureUnit', fallback=True)

        # Initialize the indicator before referencing it
        self.app = 'My Indicator'
        self.ICON_PATH = '/usr/share/icons/hicolor/symbolic/generic-fan-symbolic.svg'  # icon in tray
        self.rpm_file_path = find_fan_directory() + '/fan1_input'
        self.max_fan_speed = 5270  # maximum fan speed

        self.indicator = AppIndicator3.Indicator.new(
            self.app,
            self.ICON_PATH,
            AppIndicator3.IndicatorCategory.APPLICATION_STATUS)
        self.indicator.set_status(AppIndicator3.IndicatorStatus.ACTIVE)
        self.indicator.set_menu(self.build_menu())

        # Keep track of the state for alternating between two sets of values
        self.current_state = 0

        # Update the tooltip periodically
        GLib.timeout_add_seconds(5, self.update_tooltip)
        GLib.timeout_add_seconds(5, self.update_menu)

    def build_menu(self):
        menu = Gtk.Menu()

        # Add a menu item to display CPU temperature and RPM
        self.item_fan_speed = Gtk.MenuItem(label="")
        menu.append(self.item_fan_speed)

        item_toggle_temp_unit = Gtk.MenuItem(label="Toggle Temperature Unit")
        item_toggle_temp_unit.connect('activate', self.toggle_temperature_unit)
        menu.append(item_toggle_temp_unit)

        # Add a quit option to the menu
        item_quit = Gtk.MenuItem(label='Quit')
        item_quit.connect('activate', quit)
        menu.append(item_quit)

        menu.show_all()
        return menu

    def update_tooltip(self):
        try:
            with open(self.file_path, 'r') as file:
                value = file.read().strip()
                celsius_temp = float(value) / 1000
                # Parse the temperature value and format it
                if not self.temp_toggle:  # Assuming self.temp_toggle is the attribute indicating the temperature unit
                    fahrenheit_temp = celsius_to_fahrenheit(celsius_temp)
                    temperature = "{:.0f}°F".format(fahrenheit_temp)
                else:
                    temperature = "{:.0f}°C".format(celsius_temp)

                # Display formatted temperature value as label
                self.indicator.set_label(" " + temperature, self.app)
        except FileNotFoundError:
            self.indicator.set_label('File not found', self.app)

        # Returning True ensures the function is called again after the specified interval
        return True

    def update_menu(self):
        with open(self.rpm_file_path, 'r') as file:
            rpm_value = file.read().strip()
            # Calculate RPM percentage
            rpm_percentage = "{:.0f}".format((float(rpm_value) / self.max_fan_speed) * 100)
            # Format the label with CPU temperature and RPM
            menu_label = "CPU: {}% | {} RPM".format(rpm_percentage, rpm_value)
            # Update the label of the menu item
            self.item_fan_speed.set_label(menu_label)
        return True

    def toggle_temperature_unit(self, source):
        self.temp_toggle = not self.temp_toggle
        # Save updated preference to configuration
        self.config['Preferences']['TemperatureUnit'] = str(self.temp_toggle)
        save_config(self.config)
        # Call update_tooltip to reflect the change immediately
        self.update_tooltip()


def main():
    Gtk.init([])
    indicator = TrayIndicator()
    Gtk.main()


if __name__ == "__main__":
    main()
