import voicemeeterlib
import keyboard
import pystray
from PIL import Image, ImageDraw
import threading
import time

KIND_ID = 'banana'
STRIP_INDEX = 3


class VoiceMeeterTray:
    def __init__(self):
        self.vm = None
        self.icon = None
        self.running = True
        
    def create_icon_image(self, muted=False):
        """Create a simple icon - red when muted, green when unmuted"""
        image = Image.new('RGB', (64, 64), color='white')
        draw = ImageDraw.Draw(image)
        
        color = 'red' if muted else 'green'
        draw.ellipse([8, 8, 56, 56], fill=color, outline='black', width=2)
        
        # Add "M" for muted
        if muted:
            draw.text((24, 20), "M", fill='white', anchor="mm")
        
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

    def create_menu(self):
        """Create the context menu"""
        current_gain = self.get_current_gain()
        
        return pystray.Menu(
            pystray.MenuItem("Left-Click-Mute", self.toggle_mute, default=True),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Mute", self.toggle_mute, checked=lambda item: self.is_muted()),
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
            
            # Set up hotkeys
            keyboard.add_hotkey('alt+num 0', lambda: self.toggle_mute(), suppress=True)
            keyboard.add_hotkey('alt+num 1', lambda: self.toggle_bus('A1'), suppress=True)
            keyboard.add_hotkey('alt+num 2', lambda: self.toggle_bus('A2'), suppress=True)
            keyboard.add_hotkey('alt+num 3', lambda: self.change_gain(-2.0), suppress=True)
            keyboard.add_hotkey('alt+num 6', lambda: self.change_gain(2.0), suppress=True)

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
            print("Hotkeys: Alt+Numpad 0/1/2/3/6")
            print("Left-click tray icon to toggle mute")
            print("Right-click for menu")
            
            # Run the tray icon (this blocks)
            self.icon.run()


def main():
    controller = VoiceMeeterTray()
    controller.run()


if __name__ == '__main__':
    main()
