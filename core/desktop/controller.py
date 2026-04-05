import pyautogui
import time
from typing import Tuple, Optional

class DesktopController:
    """
    Arvis's OS-level interaction engine.
    Uses PyAutoGUI to provide full desktop control (mouse, keyboard, screenshots).
    Designed for 24/7 autonomous operation on a dedicated Linux desktop.
    """
    def __init__(self):
        # Fail-safe: moving mouse to corner aborts PyAutoGUI
        pyautogui.FAILSAFE = True

    def click_at(self, x: int, y: int, double: bool = False):
        """Moves to (x, y) and clicks."""
        if double:
            pyautogui.doubleClick(x, y)
        else:
            pyautogui.click(x, y)

    def type_text(self, text: str, interval: float = 0.05):
        """Types string with a realistic interval between strokes."""
        pyautogui.write(text, interval=interval)

    def press_key(self, key: str):
        """Presses a single key (e.g., 'enter', 'tab', 'esc')."""
        pyautogui.press(key)

    def capture_screen(self, region: Optional[Tuple[int, int, int, int]] = None) -> str:
        """Captures a screenshot for Arvis to 'see' the desktop status."""
        timestamp = int(time.time())
        filename = f"arvis_data/screenshots/screen_{timestamp}.png"
        os.makedirs("arvis_data/screenshots", exist_ok=True)
        
        screenshot = pyautogui.screenshot(region=region)
        screenshot.save(filename)
        return filename

    def locate_on_screen(self, image_path: str, confidence: float = 0.9):
        """Finds an image on screen (e.g., a specific icon or button)."""
        return pyautogui.locateOnScreen(image_path, confidence=confidence)

if __name__ == "__main__":
    controller = DesktopController()
    # Mock usage: Click 'Start' menu if it was at (20, 1060)
    # controller.click_at(20, 1060)
