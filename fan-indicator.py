import gi
import os
import configparser

gi.require_version('Gtk', '3.0')
gi.require_version('AppIndicator3', '0.1')

from gi.repository import Gtk, AppIndicator3, GLib

# Configuration file path
CONFIG_FILE_PATH = os.path.join(os.path.expanduser('~/.config'), 'fan_indicator_config')

# Default temperature unit (True -> Celsius, False -> Fahrenheit)
DEFAULT_TEMPERATURE_UNIT_CELSIUS = True


# ------------------------- Configuration Handling -------------------------

# Function to load configuration
def load_configuration():
    config = configparser.ConfigParser()
    if not os.path.exists(CONFIG_FILE_PATH):
        # If the config file doesn't exist, create it with default values
        config['Preferences'] = {'TemperatureUnit': 'True'}  # Default to Celsius
        save_configuration(config)
    else:
        config.read(CONFIG_FILE_PATH)
    return config


# Function to save configuration
def save_configuration(config):
    with open(CONFIG_FILE_PATH, 'w') as configfile:
        config.write(configfile)


# ------------------------- Hardware Information -------------------------

# Function to find the directory containing CPU temperature sensor
def find_cpu_temp_sensor_directory():
    hwmon_base_path = '/sys/devices/platform/coretemp.0/hwmon/'
    cpu_temp_sensor_directory = None

    # Iterate over subdirectories to find the one with 'temp1_input'
    for directory in os.listdir(hwmon_base_path):
        if os.path.exists(os.path.join(hwmon_base_path, directory, 'temp1_input')):
            cpu_temp_sensor_directory = os.path.join(hwmon_base_path, directory)
            break

    if cpu_temp_sensor_directory is None:
        raise FileNotFoundError("Could not find the directory with 'temp1_input'")

    return cpu_temp_sensor_directory


# Function to find the directory containing fan speed sensor
def find_fan_speed_sensor_directory():
    fan_base_path = '/sys/devices/platform/clevofan/hwmon/'
    fan_speed_sensor_directory = None

    # Iterate over subdirectories to find the one with 'fan1_input'
    for directory in os.listdir(fan_base_path):
        if os.path.exists(os.path.join(fan_base_path, directory, 'fan1_input')):
            fan_speed_sensor_directory = os.path.join(fan_base_path, directory)
            break

    if fan_speed_sensor_directory is None:
        raise FileNotFoundError("Could not find the directory with 'fan1_input'")

    return fan_speed_sensor_directory


# ------------------------- Temperature Conversion -------------------------

# Function to convert Celsius to Fahrenheit
def convert_celsius_to_fahrenheit(celsius):
    return (celsius * 9 / 5) + 32


# ------------------------- Application Management -------------------------

# Function to handle quitting the application
def quit_application(source):
    Gtk.main_quit()


# ------------------------- Tray Indicator Class -------------------------

# Class for the tray indicator
class FanTrayIndicator:
    def __init__(self):
        # Load configuration
        self.config = load_configuration()
        self.cpu_temp_sensor_path = find_cpu_temp_sensor_directory() + '/temp1_input'

        # Retrieve temperature unit preference from configuration
        self.is_temp_unit_celsius = self.config.getboolean('Preferences', 'TemperatureUnit', fallback=True)

        # Initialize the indicator
        self.APP_NAME = 'Fan Indicator'
        self.ICON_PATH = 'temperature-symbolic'  # icon in tray
        self.fan1_speed_rpm_path = find_fan_speed_sensor_directory() + '/fan1_input'
        self.fan1_speed_pwm_path = find_fan_speed_sensor_directory() + '/pwm1'
        self.max_fan_speed = 255  # maximum fan speed
        self.gpu_fan_speed_rpm_path = find_fan_speed_sensor_directory() + '/fan2_input'
        self.gpu_fan_speed_pwm_path = find_fan_speed_sensor_directory() + '/pwm2'
        self.fan2_exists = os.path.exists(self.gpu_fan_speed_rpm_path) and os.path.exists(self.gpu_fan_speed_pwm_path)

        self.indicator = AppIndicator3.Indicator.new(
            self.APP_NAME,
            self.ICON_PATH,
            AppIndicator3.IndicatorCategory.APPLICATION_STATUS)
        self.indicator.set_status(AppIndicator3.IndicatorStatus.ACTIVE)
        self.indicator.set_menu(self.build_menu())

        # Update the tooltip and menu periodically
        GLib.timeout_add_seconds(5, self.update_cpu_temp_tooltip)
        GLib.timeout_add_seconds(5, self.update_fan_speed_menu)

    # Function to build the menu
    def build_menu(self):
        menu = Gtk.Menu()

        # Add a menu item to display CPU temperature and RPM
        self.item_fan_speed_cpu = Gtk.MenuItem(label="")
        menu.append(self.item_fan_speed_cpu)

        if self.fan2_exists:
            # Add a menu item to display GPU temperature and RPM
            self.item_fan_speed_gpu = Gtk.MenuItem(label="")
            menu.append(self.item_fan_speed_gpu)

        # Add a menu item to toggle temperature unit
        item_toggle_temp_unit = Gtk.MenuItem(label="Toggle Temperature Unit")
        item_toggle_temp_unit.connect('activate', self.toggle_temperature_unit)
        menu.append(item_toggle_temp_unit)

        # Add a quit option to the menu
        item_quit = Gtk.MenuItem(label='Quit')
        item_quit.connect('activate', quit_application)
        menu.append(item_quit)

        menu.show_all()
        return menu

    # Function to update the tooltip
    def update_cpu_temp_tooltip(self):
        try:
            with open(self.cpu_temp_sensor_path, 'r') as file:
                value = file.read().strip()
                cpu_temp_celsius = float(value) / 1000
                # Parse the temperature value and format it
                if not self.is_temp_unit_celsius:
                    cpu_temp_fahrenheit = convert_celsius_to_fahrenheit(cpu_temp_celsius)
                    temperature = "{:.0f}°F".format(cpu_temp_fahrenheit)
                else:
                    temperature = "{:.0f}°C".format(cpu_temp_celsius)

                # Display formatted temperature value as label
                self.indicator.set_label(" " + temperature, self.APP_NAME)
        except FileNotFoundError:
            self.indicator.set_label('File not found', self.APP_NAME)

        # Returning True ensures the function is called again after the specified interval
        return True

    # Function to update the menu
    def update_fan_speed_menu(self):
        with open(self.fan1_speed_pwm_path, 'r') as f1, open(self.fan1_speed_rpm_path, 'r') as f2:
            cpu_pwm_value = f1.read().strip()
            cpu_rpm_value = f2.read().strip()
            # Calculate percentage
            cpu_speed_percentage = "{:.0f}".format((float(cpu_pwm_value) / self.max_fan_speed) * 100)
            # Format the label with CPU temperature and RPM
            menu_label_cpu = "CPU FAN: {}% | {} RPM".format(cpu_speed_percentage, cpu_rpm_value)
            # Update the label of the CPU fan menu item
            self.item_fan_speed_cpu.set_label(menu_label_cpu)

        if self.fan2_exists:
            with open(self.gpu_fan_speed_pwm_path, 'r') as f1, open(self.gpu_fan_speed_rpm_path, 'r') as f2:
                gpu_pwm_value = f1.read().strip()
                gpu_rpm_value = f2.read().strip()
                # Calculate percentage
                gpu_speed_percentage = "{:.0f}".format((float(gpu_pwm_value) / self.max_fan_speed) * 100)
                # Format the label with GPU temperature and RPM
                menu_label_gpu = "GPU FAN: {}% | {} RPM".format(gpu_speed_percentage, gpu_rpm_value)
                # Update the label of the GPU fan menu item
                self.item_fan_speed_gpu.set_label(menu_label_gpu)

        return True


    # Function to toggle temperature unit
    def toggle_temperature_unit(self, source):
        self.is_temp_unit_celsius = not self.is_temp_unit_celsius
        # Save updated preference to configuration
        self.config['Preferences']['TemperatureUnit'] = str(self.is_temp_unit_celsius)
        save_configuration(self.config)
        # Call update_cpu_temp_tooltip to reflect the change immediately
        self.update_cpu_temp_tooltip()


# ------------------------- Main -------------------------

# Main function
def main():
    Gtk.init([])
    indicator = FanTrayIndicator()
    Gtk.main()


# Entry point of the script
if __name__ == "__main__":
    main()