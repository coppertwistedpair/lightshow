import threading
import time
import math


def _lerp(a, b, t):
    return a + (b - a) * t


def _interpolate_color(color_a, color_b, t, sinusoidal=True):
    if sinusoidal:
        t = (1 - math.cos(t * math.pi)) / 2
    return tuple(int(_lerp(a, b, t)) for a, b in zip(color_a, color_b))


class ColorCycleMode:
    def __init__(self, dmx_output, fixture_manager):
        self.dmx = dmx_output
        self.fixtures = fixture_manager
        self.colors = [(255, 0, 0, 0, 0, 0), (0, 0, 255, 0, 0, 0)]
        self.fade_time = 3.0
        self.hold_time = 0.0
        self.chase_mode = False
        self._running = False
        self._thread = None

    def set_colors(self, colors):
        self.colors = list(colors) if len(colors) >= 2 else list(colors) + [(0, 0, 0, 0, 0, 0)]

    def set_fade_time(self, seconds):
        self.fade_time = max(0.0, float(seconds))

    def set_hold_time(self, seconds):
        self.hold_time = max(0.0, float(seconds))

    def set_chase_mode(self, enabled):
        self.chase_mode = bool(enabled)

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=1)
        self.dmx.blackout()

    def _loop(self):
        if self.chase_mode:
            self._loop_chase()
        else:
            self._loop_standard()

    def _loop_standard(self):
        start_time = time.time()
        while self._running:
            colors = self.colors
            fade_time = self.fade_time
            hold_time = self.hold_time
            n = len(colors)
            step_time = max(fade_time + hold_time, 0.01)

            elapsed = time.time() - start_time
            t_in_cycle = elapsed % (step_time * n)
            step_idx = int(t_in_cycle / step_time) % n
            t_in_step = t_in_cycle - step_idx * step_time

            if t_in_step < hold_time:
                color = colors[step_idx]
            elif fade_time > 0:
                t = max(0.0, min(1.0, (t_in_step - hold_time) / fade_time))
                color = _interpolate_color(colors[step_idx], colors[(step_idx + 1) % n], t)
            else:
                color = colors[step_idx]

            self._apply_color_all(color)
            time.sleep(0.025)

    def _loop_chase(self):
        # Each fixture holds a different color; all advance one slot every step_time.
        # If colors > fixtures, extra colors act as phantom slots keeping animation rhythm.
        start_time = time.time()
        while self._running:
            colors = self.colors
            fade_time = self.fade_time
            hold_time = self.hold_time
            n = len(colors)
            step_time = max(fade_time + hold_time, 0.01)
            fixtures = list(self.fixtures.fixtures)

            elapsed = time.time() - start_time
            global_step = elapsed / step_time  # continuous position advancing through color ring

            for i, fixture in enumerate(fixtures):
                pos = (i + global_step) % n
                step_idx = int(pos) % n
                t_in_step = (pos - int(pos)) * step_time

                if t_in_step < hold_time:
                    color = colors[step_idx]
                elif fade_time > 0:
                    t = max(0.0, min(1.0, (t_in_step - hold_time) / fade_time))
                    color = _interpolate_color(colors[step_idx], colors[(step_idx + 1) % n], t)
                else:
                    color = colors[step_idx]

                self._apply_color_to_fixture(fixture, color)

            time.sleep(0.025)

    def _apply_color_to_fixture(self, fixture, color):
        # color is (r, g, b, a, w, uv); the fixture maps it to its own channel order
        fixture.apply(self.dmx, color)

    def _apply_color_all(self, rgb):
        for fixture in list(self.fixtures.fixtures):
            self._apply_color_to_fixture(fixture, rgb)
