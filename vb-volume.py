import voicemeeterlib
import keyboard
import pystray
from PIL import Image, ImageDraw
import threading
import time
import sys
import os
import json

KIND_ID = 'banana'
STRIP_INDEX = 3

# Numpad scan codes (Windows)
NUMPAD_SCAN_CODES = {
    82: '0',  # Numpad 0
    79: '1',  # Numpad 1
    80: '2',  # Numpad 2
    81: '3',  # Numpad 3
    75: '4',  # Numpad 4
    76: '5',  # Numpad 5
    77: '6',  # Numpad 6
    71: '7',  # Numpad 7
    72: '8',  # Numpad 8
    73: '9',  # Numpad 9
}


def resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


def get_settings_path():
    """Get path for settings file in user directory"""
    # Use user's home directory for persistent storage
    home_dir = os.path.expanduser("~")
    settings_dir = os.path.join(home_dir, ".voicemeeter-controller")
    
    # Create directory if it doesn't exist
    if not os.path.exists(settings_dir):
        os.makedirs(settings_dir)
    
    return os.path.join(settings_dir, "settings.json")


class VoiceMeeterTray:
    def __init__(self):
        self.vm = None
        self.icon = None
        self.running = True
        self.icon_theme = ""  # "" for regular icons, "1" for white icons
        self.settings_file = get_settings_path()
        self.load_settings()
        
    def load_settings(self):
        """Load settings from JSON file"""
        try:
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r') as f:
                    settings = json.load(f)
                    self.icon_theme = settings.get('icon_theme', '')
                    print(f"Loaded settings: icon_theme = {'white' if self.icon_theme == '1' else 'regular'}")
            else:
                print("No settings file found, using default settings")
        except Exception as e:
            print(f"Error loading settings: {e}")
            self.icon_theme = ""  # Default to regular icons
    
    def save_settings(self):
        """Save settings to JSON file"""
        try:
            settings = {
                'icon_theme': self.icon_theme
            }
            with open(self.settings_file, 'w') as f:
                json.dump(settings, f, indent=2)
            print(f"Settings saved to: {self.settings_file}")
        except Exception as e:
            print(f"Error saving settings: {e}")

    def create_icon_image(self, muted=False):
        """Create a context-aware icon using custom PNG files"""
        try:
            # Get current bus states
            a1_active = self.is_bus_active('A1')  # Headset
            a2_active = self.is_bus_active('A2')  # Speakers
            
            if muted:
                # When muted, show muted.png
                icon_name = f"muted{self.icon_theme}.png"
            elif a1_active and a2_active:
                # Both active - show unmute.png
                icon_name = f"unmute{self.icon_theme}.png"
            elif a1_active and not a2_active:
                # Only headset (A2 toggled off) - show headset.png
                icon_name = f"headset{self.icon_theme}.png"
            elif a2_active and not a1_active:
                # Only speakers (A1 toggled off) - show speakers.png
                icon_name = f"speakers{self.icon_theme}.png"
            else:
                # Neither active - fallback to muted.png
                icon_name = f"muted{self.icon_theme}.png"
            
            # Load the appropriate icon from icons folder
            icon_path = resource_path(os.path.join("icons", icon_name))
            image = Image.open(icon_path)
            
            # Ensure it's the right size
            if image.size != (64, 64):
                image = image.resize((64, 64), Image.Resampling.LANCZOS)
            
            # Keep transparency - don't convert to RGB
            return image
            
        except Exception as e:
            print(f"Error loading icon {icon_path}: {e}")
            # Fallback to simple programmatic icon
            return self.create_fallback_icon(muted)

    def create_fallback_icon(self, muted=False):
        """Fallback icon if PNG files are not found"""
        image = Image.new('RGB', (64, 64), color='white')
        draw = ImageDraw.Draw(image)
        
        bg_color = 'red' if muted else 'green'
        draw.ellipse([4, 4, 60, 60], fill=bg_color, outline='black', width=2)
        
        if muted:
            draw.text((32, 32), "M", fill='white', anchor="mm")
        else:
            draw.text((32, 32), "♪", fill='white', anchor="mm")
        
        return image

    def get_tooltip(self):
        """Generate tooltip with current status"""
        if not self.vm:
            return "VoiceMeeter Controller"
        
        try:
            strip = self.vm.strip[STRIP_INDEX]
            mute_status = "MUTED" if strip.mute else "UNMUTED"
            gain = strip.gain
            a1_status = "ON" if strip.A1 else "OFF"
            a2_status = "ON" if strip.A2 else "OFF"
            
            return f"Strip {STRIP_INDEX}: {mute_status}\nGain: {gain:.1f}dB\nA1: {a1_status}, A2: {a2_status}"
        except:
            return "VoiceMeeter Controller"

    def toggle_mute(self, item=None):
        """Toggle mute and update icon"""
        if self.vm:
            current = self.vm.strip[STRIP_INDEX].mute
            new_state = not current
            self.vm.strip[STRIP_INDEX].mute = new_state
            print(f"Toggled Strip[{STRIP_INDEX}].mute from {current} to {new_state}")
            self.update_icon()

    def toggle_bus(self, bus: str):
        """Toggle bus routing"""
        if self.vm:
            current = getattr(self.vm.strip[STRIP_INDEX], bus)
            new_state = not current
            setattr(self.vm.strip[STRIP_INDEX], bus, new_state)
            print(f"Toggled Strip[{STRIP_INDEX}].{bus} from {current} to {new_state}")

    def change_gain(self, delta: float):
        """Change gain by delta amount"""
        if self.vm:
            current = self.vm.strip[STRIP_INDEX].gain
            new_gain = max(min(current + delta, 0.0), -60.0)
            self.vm.strip[STRIP_INDEX].gain = new_gain
            print(f"Changed gain Strip[{STRIP_INDEX}] from {current:.2f} to {new_gain:.2f} dB")

    def set_gain(self, value: float):
        """Set gain to specific value"""
        if self.vm:
            current = self.vm.strip[STRIP_INDEX].gain
            clamped_value = max(min(value, 0.0), -60.0)
            self.vm.strip[STRIP_INDEX].gain = clamped_value
            print(f"Set gain Strip[{STRIP_INDEX}] from {current:.1f} to {clamped_value:.1f} dB")

    def get_current_gain(self):
        """Get current gain value"""
        if self.vm:
            return self.vm.strip[STRIP_INDEX].gain
        return 0.0

    def is_muted(self):
        """Check if currently muted"""
        if self.vm:
            return self.vm.strip[STRIP_INDEX].mute
        return False

    def is_bus_active(self, bus: str):
        """Check if bus is active"""
        if self.vm:
            return getattr(self.vm.strip[STRIP_INDEX], bus)
        return False

    def update_icon(self):
        """Update the tray icon and tooltip"""
        if self.icon:
            muted = self.is_muted()
            self.icon.icon = self.create_icon_image(muted)
            self.icon.title = self.get_tooltip()

    def set_icon_theme(self, theme_suffix):
        """Set the icon theme ('' for regular, '1' for white)"""
        self.icon_theme = theme_suffix
        self.save_settings()  # Save immediately when changed
        print(f"Switched to {'white' if theme_suffix == '1' else 'regular'} icons")
        self.update_icon()

    def create_menu(self):
        """Create the context menu"""
        current_gain = self.get_current_gain()
        
        return pystray.Menu(
            pystray.MenuItem("Mute", self.toggle_mute, checked=lambda item: self.is_muted(), default=True),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Bus A1", lambda item: self.toggle_bus('A1'), checked=lambda item: self.is_bus_active('A1')),
            pystray.MenuItem("Bus A2", lambda item: self.toggle_bus('A2'), checked=lambda item: self.is_bus_active('A2')),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(f"Gain Control (Current: {current_gain:.1f}dB)", pystray.Menu(
                pystray.MenuItem("Set to 0dB", lambda item: self.set_gain(0.0)),
                pystray.MenuItem("Set to -6dB", lambda item: self.set_gain(-6.0)),
                pystray.MenuItem("Set to -12dB", lambda item: self.set_gain(-12.0)),
                pystray.MenuItem("Set to -20dB", lambda item: self.set_gain(-20.0)),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("Increase (+2dB)", lambda item: self.change_gain(2.0)),
                pystray.MenuItem("Increase (+4dB)", lambda item: self.change_gain(4.0)),
                pystray.MenuItem("Decrease (-4dB)", lambda item: self.change_gain(-4.0)),
                pystray.MenuItem("Decrease (-2dB)", lambda item: self.change_gain(-2.0)),
            )),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Icon Theme", pystray.Menu(
                pystray.MenuItem("Regular Icons", lambda item: self.set_icon_theme(""), checked=lambda item: self.icon_theme == ""),
                pystray.MenuItem("White Icons", lambda item: self.set_icon_theme("1"), checked=lambda item: self.icon_theme == "1"),
            )),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Exit", self.quit_application)
        )

    def quit_application(self):
        """Properly quit the application"""
        self.running = False
        if self.icon:
            self.icon.stop()

    def menu_update_loop(self):
        """Background thread to periodically update the menu and icon"""
        while self.running:
            if self.icon and self.vm:
                try:
                    # Update the menu
                    self.icon.menu = self.create_menu()
                    # Update icon and tooltip
                    self.update_icon()
                except:
                    pass
            time.sleep(0.5)  # Update every 500ms

    def setup_numpad_hotkeys(self):
        """Set up numpad-specific hotkeys using scan codes"""
        def on_key_event(event):
            # Only process key down events
            if event.event_type != keyboard.KEY_DOWN:
                return
            
            # Check if Alt is pressed
            if not keyboard.is_pressed('alt'):
                return
            
            # Check if it's a numpad key we care about
            if event.scan_code in NUMPAD_SCAN_CODES:
                numpad_key = NUMPAD_SCAN_CODES[event.scan_code]
                
                if numpad_key == '0':
                    self.toggle_mute()
                    print("Numpad hotkey: Alt+Numpad 0 - Toggle Mute")
                    return False  # Suppress the event
                elif numpad_key == '1':
                    self.toggle_bus('A1')
                    print("Numpad hotkey: Alt+Numpad 1 - Toggle A1")
                    return False  # Suppress the event
                elif numpad_key == '2':
                    self.toggle_bus('A2')
                    print("Numpad hotkey: Alt+Numpad 2 - Toggle A2")
                    return False  # Suppress the event
                elif numpad_key == '3':
                    self.change_gain(-2.0)
                    print("Numpad hotkey: Alt+Numpad 3 - Decrease Gain")
                    return False  # Suppress the event
                elif numpad_key == '6':
                    self.change_gain(2.0)
                    print("Numpad hotkey: Alt+Numpad 6 - Increase Gain")
                    return False  # Suppress the event
        
        # Hook into keyboard events with suppression enabled
        keyboard.hook(on_key_event, suppress=False)

    def run(self):
        """Main run method"""
        # Enable parameter dirty tracking for real-time updates
        with voicemeeterlib.api(KIND_ID, pdirty=True) as vm:
            self.vm = vm
            
            print(f"VoiceMeeter connected! Version: {KIND_ID}")
            print(f"Initial Strip[{STRIP_INDEX}] state:")
            print(f"  Mute: {vm.strip[STRIP_INDEX].mute}")
            print(f"  A1: {vm.strip[STRIP_INDEX].A1}")
            print(f"  A2: {vm.strip[STRIP_INDEX].A2}")
            print(f"  Gain: {vm.strip[STRIP_INDEX].gain:.1f}dB")
            
            # Set up numpad-specific hotkeys using scan codes
            self.setup_numpad_hotkeys()

            # Create tray icon using MenuItem with default=True for left-click
            initial_icon = self.create_icon_image(self.is_muted())
            self.icon = pystray.Icon(
                "VoiceMeeter Controller",
                initial_icon,
                title=self.get_tooltip(),
                menu=self.create_menu()
            )
            
            # Start the menu update thread
            update_thread = threading.Thread(target=self.menu_update_loop, daemon=True)
            update_thread.start()
            
            print("VoiceMeeter Tray Controller started!")
            print("Hotkeys: Alt+Numpad 0/1/2/3/6 (numpad keys only)")
            print("Left-click tray icon to toggle mute")
            print("Right-click for menu")
            
            # Run the tray icon (this blocks)
            self.icon.run()


def main():
    controller = VoiceMeeterTray()
    controller.run()


if __name__ == '__main__':
    main()
