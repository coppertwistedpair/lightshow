import json
import os

# Colors throughout the app are 6-tuples in this order:
COLOR_FIELDS = ('r', 'g', 'b', 'a', 'w', 'uv')  # red, green, blue, amber, white, UV/purple

# Supported lights. 'channels' lists what goes on Ch1, Ch2, ... for that model:
# a color field name, or a fixed number sent unchanged (dimmer, strobe, macros).
FIXTURE_TYPES = {
    'rockwedge': {
        'label': 'Rockville Rockwedge (6-ch)',
        # From the Rockville manual: R, G, B, White, Amber, Purple.
        # (The GDTF profile in profiles/ swaps White/Amber; the manual is correct.)
        'channels': ('r', 'g', 'b', 'w', 'a', 'uv'),
    },
    'bestpar50': {
        'label': 'Rockville BestPar 50 (6-ch)',
        'channels': ('r', 'g', 'b', 'w', 'a', 'uv'),  # manual: R, G, B, White, Amber, Purple
    },
    'bestpar50_10ch': {
        'label': 'Rockville BestPar 50 (10-ch)',
        # manual: Dimmer, R, G, B, White, Amber, Purple, Strobe, Function, Function speed.
        # Dimmer held at full; strobe off; function 0 = "Close" (no built-in program).
        'channels': (255, 'r', 'g', 'b', 'w', 'a', 'uv', 0, 0, 0),
    },
}
DEFAULT_FIXTURE_TYPE = 'rockwedge'  # configs saved before types existed were all Rockwedges
DMX_CHANNELS = 512


def channel_count(fixture_type):
    return len(FIXTURE_TYPES[fixture_type]['channels'])


def max_start_address(fixture_type):
    """Last start address where a fixture of this type still fits in the universe."""
    return DMX_CHANNELS - channel_count(fixture_type) + 1


class Fixture:
    def __init__(self, name, start_address, fixture_type=DEFAULT_FIXTURE_TYPE):
        if fixture_type not in FIXTURE_TYPES:
            raise ValueError(f"Unknown fixture type '{fixture_type}'.")
        self.name = name
        self.start_address = start_address
        self.fixture_type = fixture_type

    @property
    def type_label(self):
        return FIXTURE_TYPES[self.fixture_type]['label']

    @property
    def channel_count(self):
        return channel_count(self.fixture_type)

    @property
    def end_address(self):
        return self.start_address + self.channel_count - 1

    def channel_values(self, color):
        """Map a (r, g, b, a, w, uv) color to this fixture's DMX channel values."""
        by_field = {f: (color[i] if i < len(color) else 0) for i, f in enumerate(COLOR_FIELDS)}
        return [by_field[c] if isinstance(c, str) else c
                for c in FIXTURE_TYPES[self.fixture_type]['channels']]

    def apply(self, dmx, color):
        dmx.set_channels(self.start_address, self.channel_values(color))

    def to_dict(self):
        return {'name': self.name, 'start_address': self.start_address, 'type': self.fixture_type}

    @staticmethod
    def from_dict(d):
        return Fixture(d['name'], d['start_address'], d.get('type', DEFAULT_FIXTURE_TYPE))


class FixtureManager:
    def __init__(self, config_path):
        self.config_path = config_path
        self.fixtures = []
        self._load()

    def _overlaps(self, start, count, ignore=None):
        """Return the fixture whose channels overlap channels start..start+count-1, or None."""
        end = start + count - 1
        for f in self.fixtures:
            if f is ignore:
                continue
            if start <= f.end_address and f.start_address <= end:
                return f
        return None

    def _validate_address(self, start, fixture_type, ignore=None):
        count = channel_count(fixture_type)
        max_start = max_start_address(fixture_type)
        if not 1 <= start <= max_start:
            raise ValueError(f"Start address must be between 1 and {max_start} "
                             f"(this light uses {count} channels).")
        clash = self._overlaps(start, count, ignore)
        if clash:
            raise ValueError(
                f"Channels {start}–{start + count - 1} overlap '{clash.name}' "
                f"(ch {clash.start_address}–{clash.end_address}).")

    def next_start_address(self, fixture_type=DEFAULT_FIXTURE_TYPE):
        """Suggest an address: right after the highest fixture, else the first free gap."""
        count = channel_count(fixture_type)
        max_start = max_start_address(fixture_type)
        if not self.fixtures:
            return 1
        after_last = max(f.end_address for f in self.fixtures) + 1
        if after_last <= max_start and not self._overlaps(after_last, count):
            return after_last
        for start in range(1, max_start + 1):
            if not self._overlaps(start, count):
                return start
        return None

    def add_fixture(self, name, start_address=None, fixture_type=DEFAULT_FIXTURE_TYPE):
        if fixture_type not in FIXTURE_TYPES:
            raise ValueError(f"Unknown fixture type '{fixture_type}'.")
        start = (self.next_start_address(fixture_type) if start_address is None
                 else int(start_address))
        if start is None:
            raise ValueError("No DMX addresses left (universe max 512 channels).")
        self._validate_address(start, fixture_type)
        fixture = Fixture(name, start, fixture_type)
        self.fixtures.append(fixture)
        self._save()
        return fixture

    def update_fixture(self, index, start_address, fixture_type):
        fixture = self.fixtures[index]
        start = int(start_address)
        if fixture_type not in FIXTURE_TYPES:
            raise ValueError(f"Unknown fixture type '{fixture_type}'.")
        self._validate_address(start, fixture_type, ignore=fixture)
        fixture.start_address = start
        fixture.fixture_type = fixture_type
        self._save()

    def remove_fixture(self, index):
        # Other fixtures keep their addresses: they match what is set on the physical lights.
        if 0 <= index < len(self.fixtures):
            self.fixtures.pop(index)
            self._save()

    def _save(self):
        data = {'fixtures': [f.to_dict() for f in self.fixtures]}
        with open(self.config_path, 'w') as fp:
            json.dump(data, fp, indent=2)

    def _load(self):
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r') as fp:
                    data = json.load(fp)
                self.fixtures = [Fixture.from_dict(d) for d in data.get('fixtures', [])]
            except Exception:
                self.fixtures = []
        else:
            self.fixtures = []
