import serial
import serial.tools.list_ports
import threading
import time

ENTTEC_START = 0x7E
ENTTEC_END = 0xE7
ENTTEC_LABEL_DMX = 6
DMX_UNIVERSE_SIZE = 512


def list_com_ports():
    ports = serial.tools.list_ports.comports()
    return [p.device for p in ports]


class DMXOutput:
    def __init__(self):
        self._universe = bytearray(DMX_UNIVERSE_SIZE)
        self._lock = threading.Lock()
        self._port = None
        self._running = False
        self._thread = None

    def connect(self, port_name):
        # write_timeout stops a stuck USB write from hanging the send thread forever
        self._port = serial.Serial(port=port_name, baudrate=57600, timeout=1, write_timeout=1)
        self._running = True
        self._thread = threading.Thread(target=self._send_loop, args=(self._port,), daemon=True)
        self._thread.start()

    def disconnect(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)  # longer than write_timeout so the thread is done writing
        self._thread = None
        if self._port and self._port.is_open:
            # The Enttec keeps repeating the last frame it got, so send an explicit
            # blackout before closing or the lights stay frozen on their last color.
            try:
                self._port.write(self._build_packet(bytearray(DMX_UNIVERSE_SIZE)))
                self._port.flush()
            except Exception:
                pass
            self._port.close()
        self._port = None

    def set_channel(self, channel, value):
        if 1 <= channel <= DMX_UNIVERSE_SIZE:
            with self._lock:
                self._universe[channel - 1] = max(0, min(255, int(value)))

    def set_channels(self, start_channel, values):
        with self._lock:
            for i, v in enumerate(values):
                idx = start_channel - 1 + i
                if 0 <= idx < DMX_UNIVERSE_SIZE:
                    self._universe[idx] = max(0, min(255, int(v)))

    def blackout(self):
        with self._lock:
            self._universe = bytearray(DMX_UNIVERSE_SIZE)

    def is_connected(self):
        return self._port is not None and self._port.is_open

    def _build_packet(self, universe):
        data = bytes([0x00]) + bytes(universe)
        length = len(data)
        return bytes([ENTTEC_START, ENTTEC_LABEL_DMX, length & 0xFF, (length >> 8) & 0xFF]) + data + bytes([ENTTEC_END])

    def _send_loop(self, port):
        while self._running:
            try:
                with self._lock:
                    snapshot = bytearray(self._universe)
                port.write(self._build_packet(snapshot))
            except Exception:
                # Interface unplugged or write failed: close the port so
                # is_connected() reports False and the GUI can show it.
                self._running = False
                try:
                    port.close()
                except Exception:
                    pass
                break
            time.sleep(0.025)  # ~40 Hz
