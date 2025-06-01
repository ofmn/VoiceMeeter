import voicemeeterlib
import keyboard

KIND_ID = 'banana'
STRIP_INDEX = 3


def toggle_bus(vm, bus: str):
    current = getattr(vm.strip[STRIP_INDEX], bus)
    setattr(vm.strip[STRIP_INDEX], bus, not current)
    print(f"Toggled Strip[{STRIP_INDEX}].{bus} to {not current}")


def toggle_mute(vm):
    current = vm.strip[STRIP_INDEX].mute
    vm.strip[STRIP_INDEX].mute = not current
    print(f"Toggled Strip[{STRIP_INDEX}].mute to {not current}")


def change_gain(vm, delta: float):
    current = vm.strip[STRIP_INDEX].gain
    new_gain = max(min(current + delta, 0.0), -60.0)
    vm.strip[STRIP_INDEX].gain = new_gain
    print(f"Changed gain Strip[{STRIP_INDEX}] from {current:.2f} to {new_gain:.2f} dB")


def main():
    with voicemeeterlib.api(KIND_ID) as vm:
        keyboard.add_hotkey('alt+num 0', lambda: toggle_mute(vm), suppress=True)
        keyboard.add_hotkey('alt+num 1', lambda: toggle_bus(vm, 'A1'), suppress=True)
        keyboard.add_hotkey('alt+num 2', lambda: toggle_bus(vm, 'A2'), suppress=True)
        keyboard.add_hotkey('alt+num 3', lambda: change_gain(vm, -2.0), suppress=True)
        keyboard.add_hotkey('alt+num 6', lambda: change_gain(vm, 2.0), suppress=True)


        print("Hotkeys ready: Alt+Numpad 0/1/2/3/6")
        keyboard.wait()  # Waits forever until manually closed


if __name__ == '__main__':
    main()
