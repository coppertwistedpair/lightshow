import sys
import os
from PyQt6.QtWidgets import QApplication

from core.dmx_output import DMXOutput
from core.fixture_manager import FixtureManager
from core.mode_cycle import ColorCycleMode
from core.animations import RainbowMode, StrobeMode, CandleMode, PoliceMode, FireworksMode
from gui.main_window import MainWindow

if getattr(sys, 'frozen', False):
    # Packaged .exe: keep config.json next to the exe, not in the temp unpack folder
    PROJECT_DIR = os.path.dirname(sys.executable)
else:
    PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(PROJECT_DIR, 'config.json')


def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')

    dmx = DMXOutput()
    fixtures = FixtureManager(config_path=CONFIG_PATH)
    cycle     = ColorCycleMode(dmx, fixtures)
    rainbow   = RainbowMode(dmx, fixtures)
    strobe    = StrobeMode(dmx, fixtures)
    candle    = CandleMode(dmx, fixtures)
    police    = PoliceMode(dmx, fixtures)
    fireworks = FireworksMode(dmx, fixtures)

    window = MainWindow(dmx, fixtures, cycle, rainbow, strobe, candle, police, fireworks)
    window.show()

    sys.exit(app.exec())


if __name__ == '__main__':
    main()
