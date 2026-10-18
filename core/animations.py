import threading
import time
import random
import colorsys


def _apply(dmx, fixture, color):
    r  = color[0] if len(color) > 0 else 0
    g  = color[1] if len(color) > 1 else 0
    b  = color[2] if len(color) > 2 else 0
    a  = color[3] if len(color) > 3 else 0
    w  = color[4] if len(color) > 4 else 0
    uv = color[5] if len(color) > 5 else 0
    sa = fixture.start_address
    # Fixed 6-channel mapping (Rockwedge GDTF): Ch1=R Ch2=G Ch3=B Ch4=A Ch5=W Ch6=UV
    dmx.set_channel(sa + 0, r)
    dmx.set_channel(sa + 1, g)
    dmx.set_channel(sa + 2, b)
    dmx.set_channel(sa + 3, w)
    dmx.set_channel(sa + 4, a)
    dmx.set_channel(sa + 5, uv)


class _BaseMode:
    def __init__(self, dmx, fixtures):
        self.dmx = dmx
        self.fixtures = fixtures
        self._running = False
        self._thread = None

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
        pass

    def _apply_all(self, color):
        for f in list(self.fixtures.fixtures):
            _apply(self.dmx, f, color)


def _sync_states(states, count, make_state):
    """Grow/shrink per-fixture state list when fixtures are added or removed mid-animation."""
    while len(states) < count:
        states.append(make_state())
    del states[count:]


class RainbowMode(_BaseMode):
    """Smooth HSV rainbow sweep. Each fixture offset in hue so the rig fans a full rainbow."""

    def __init__(self, dmx, fixtures):
        super().__init__(dmx, fixtures)
        self.cycle_seconds = 8.0

    def set_cycle_seconds(self, s):
        self.cycle_seconds = max(0.3, float(s))

    def _loop(self):
        start = time.time()
        while self._running:
            fixtures = list(self.fixtures.fixtures)
            n = max(len(fixtures), 1)
            base_hue = ((time.time() - start) / self.cycle_seconds) % 1.0
            for i, f in enumerate(fixtures):
                hue = (base_hue + i / n) % 1.0
                r, g, b = colorsys.hsv_to_rgb(hue, 1.0, 1.0)
                _apply(self.dmx, f, (int(r * 255), int(g * 255), int(b * 255), 0, 0, 0))
            time.sleep(0.025)


class StrobeMode(_BaseMode):
    """Sparkle strobe — each fixture fires independently at random times."""

    def __init__(self, dmx, fixtures):
        super().__init__(dmx, fixtures)
        self.rate = 8.0
        self.color = (255, 255, 255, 0, 0, 0)

    def set_rate(self, hz):
        self.rate = max(0.5, min(30.0, float(hz)))

    def set_color(self, color):
        self.color = color

    def _loop(self):
        BLACK = (0, 0, 0, 0, 0, 0)
        # Each fixture: is it on, and when does it next change state?
        new_state = lambda: {'lit': False, 'next': time.time() + random.uniform(0, 1.0)}
        states = []

        while self._running:
            fixtures = list(self.fixtures.fixtures)
            _sync_states(states, len(fixtures), new_state)
            now = time.time()
            rate = self.rate
            for i, f in enumerate(fixtures):
                s = states[i]
                if now >= s['next']:
                    if s['lit']:
                        _apply(self.dmx, f, BLACK)
                        s['lit'] = False
                        # Random gap before next flash — shorter at higher rate
                        s['next'] = now + random.uniform(0.1, 1.2) / rate
                    else:
                        _apply(self.dmx, f, self.color)
                        s['lit'] = True
                        # Short flash, but at least ~2 DMX frames (25 ms each) so it is actually sent
                        s['next'] = now + random.uniform(0.05, 0.08)
            time.sleep(0.005)


class CandleMode(_BaseMode):
    """Warm flame flicker. Each fixture flickers independently. Uses amber LED for realistic warmth."""

    def _loop(self):
        new_state = lambda: {'bri': 1.0, 'target': random.uniform(0.7, 1.0), 'speed': random.uniform(3.0, 9.0),
                             'amber_bias': random.uniform(0.6, 1.0)}  # per-fixture amber vs red balance
        states = []
        last = time.time()
        while self._running:
            fixtures = list(self.fixtures.fixtures)
            _sync_states(states, len(fixtures), new_state)
            now = time.time()
            dt = min(now - last, 0.05)
            last = now
            for i, f in enumerate(fixtures):
                s = states[i]
                s['bri'] += (s['target'] - s['bri']) * s['speed'] * dt
                if abs(s['target'] - s['bri']) < 0.02:
                    s['target'] = random.uniform(0.40, 1.0)
                    s['speed'] = random.uniform(2.0, 14.0)
                    s['amber_bias'] = random.uniform(0.5, 1.0)
                bri = max(0.0, min(1.0, s['bri']))
                ab = s['amber_bias']
                # Flame: full red, low green, heavy amber, tiny blue
                r  = int(255 * bri)
                g  = int(30 * bri * bri)
                b  = int(3 * bri)
                a  = int(220 * bri * ab)       # amber carries the warm golden glow
                w  = 0
                uv = 0
                _apply(self.dmx, f, (r, g, b, a, w, uv))
            time.sleep(0.02)


class FireworksMode(_BaseMode):
    """Per-fixture fireworks: random color pops up instantly, decays slowly to black. Fully unsynced."""

    _COLORS = [
        (255, 0,   0,   0, 0, 0),  # red
        (255, 100, 0,   0, 0, 0),  # orange
        (255, 200, 0,   0, 0, 0),  # gold
        (255, 255, 0,   0, 0, 0),  # yellow
        (0,   255, 80,  0, 0, 0),  # spring green
        (0,   100, 255, 0, 0, 0),  # blue
        (140, 0,   255, 0, 0, 0),  # purple
        (255, 0,   180, 0, 0, 0),  # magenta
        (0,   220, 255, 0, 0, 0),  # cyan
        (255, 255, 255, 0, 0, 0),  # white
    ]

    def _loop(self):
        # r,g,b,a are floats for smooth decay; next_fire = when to launch next burst
        new_state = lambda: {
            'r': 0.0, 'g': 0.0, 'b': 0.0, 'a': 0.0,
            'half_life': 1.5,
            'next_fire': time.time() + random.uniform(0.0, 2.5)
        }
        states = []

        last = time.time()
        while self._running:
            fixtures = list(self.fixtures.fixtures)
            _sync_states(states, len(fixtures), new_state)
            now = time.time()
            dt = min(now - last, 0.05)
            last = now

            for i, f in enumerate(fixtures):
                s = states[i]

                # Launch burst when dark enough and timer expired
                brightness = max(s['r'], s['g'], s['b'])
                if now >= s['next_fire'] and brightness < 8:
                    c = random.choice(self._COLORS)
                    s['r'], s['g'], s['b'], s['a'] = float(c[0]), float(c[1]), float(c[2]), float(c[3])
                    s['half_life'] = random.uniform(0.6, 2.0)
                    s['next_fire'] = now + 99999  # re-armed when dark again

                # Exponential decay to black
                decay = 0.5 ** (dt / s['half_life'])
                s['r'] *= decay
                s['g'] *= decay
                s['b'] *= decay
                s['a'] *= decay

                # Re-arm when nearly dark
                if max(s['r'], s['g'], s['b']) < 4 and s['next_fire'] > now + 100:
                    s['next_fire'] = now + random.uniform(0.3, 3.0)

                _apply(self.dmx, f, (int(s['r']), int(s['g']), int(s['b']), int(s['a']), 0, 0))

            time.sleep(0.02)


class PoliceMode(_BaseMode):
    """Cop-car strobe: all lights burst red, then all lights burst blue, repeat."""

    def __init__(self, dmx, fixtures):
        super().__init__(dmx, fixtures)
        self.rate = 5.0  # burst-pairs per second

    def set_rate(self, hz):
        self.rate = max(1.0, min(20.0, float(hz)))

    def _burst(self, color, on, off, count):
        BLACK = (0, 0, 0, 0, 0, 0)
        for _ in range(count):
            if not self._running:
                return
            self._apply_all(color)
            time.sleep(on)
            self._apply_all(BLACK)
            time.sleep(off)

    def _loop(self):
        RED  = (255, 0,   0,   0, 0, 0)
        BLUE = (0,   0,   255, 0, 0, 0)
        while self._running:
            beat  = 1.0 / self.rate
            on    = beat * 0.30
            off   = beat * 0.15
            pause = beat * 0.30

            self._burst(RED,  on, off, 3)
            if not self._running: return
            time.sleep(pause)
            self._burst(BLUE, on, off, 3)
            if not self._running: return
            time.sleep(pause)


# ── Holiday preset definitions ────────────────────────────────────────────────
# Each entry: list of (r,g,b,a,w,uv) tuples + fade/hold seconds for cycle mode.

HOLIDAY_PRESETS = [
    # (name, colors_or_None, fade_s, hold_s)
    # colors=None means a special animation mode is launched instead of cycle mode.
    ('Christmas',     [(255,0,0,0,0,0), (0,200,0,0,0,0), (255,255,255,0,0,0)],    2, 2),
    ('Halloween',     [(130,0,180,0,0,0), (255,80,0,0,0,0), (0,200,20,0,0,0)],    3, 2),
    ('July 4th',      [(255,0,0,0,0,0), (255,255,255,0,0,0), (0,0,220,0,0,0)],    1, 2),
    ("Valentine's",   [(255,20,80,0,0,0),(200,0,40,0,0,0),(255,160,180,0,0,0),(255,255,255,0,0,0)], 3, 2),
    ("St. Patrick's", [(0,200,0,0,0,0), (210,200,0,0,0,0)],                        2, 1),
    ('Hanukkah',      [(255,255,255,0,0,0), (0,80,220,0,0,0)],                     2, 3),
    ('New Year',      None, None, None),  # triggers FireworksMode
    ('Mardi Gras',    [(0,180,0,0,0,0), (160,0,200,0,0,0), (220,190,0,0,0,0)],    2, 1),
]
