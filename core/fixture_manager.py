import json
import os

# Colors throughout the app are 6-tuples in this order:
COLOR_FIELDS = ('r', 'g', 'b', 'a', 'w', 'uv')  # red, green, blue, amber, white, UV/purple

# Supported lights (6-channel DMX mode). 'channels' lists which color field
# goes on Ch1, Ch2, ... for that model.
FIXTURE_TYPES = {
    'rockwedge': {
        'label': 'Rockville Rockwedge',
        'channels': ('r', 'g', 'b', 'a', 'w', 'uv'),  # from the Rockwedge GDTF profile
    },
    'bestpar50': {
        'label': 'Rockville BestPar 50',
        'channels': ('r', 'g', 'b', 'w', 'a', 'uv'),  # manual: R, G, B, White, Amber, Purple
    },
}
DEFAULT_FIXTURE_TYPE = 'rockwedge'  # configs saved before types existed were all Rockwedges


class Fixture:
    CHANNELS = 6  # every supported type uses 6 channels

    def __init__(self, name, start_address, fixture_type=DEFAULT_FIXTURE_TYPE):
        if fixture_type not in FIXTURE_TYPES:
            raise ValueError(f"Unknown fixture type '{fixture_type}'.")
        self.name = name
        self.start_address = start_address
        self.fixture_type = fixture_type

    @property
    def type_label(self):
        return FIXTURE_TYPES[self.fixture_type]['label']

    def channel_values(self, color):
        """Map a (r, g, b, a, w, uv) color to this fixture's DMX channel order."""
        by_field = {f: (color[i] if i < len(color) else 0) for i, f in enumerate(COLOR_FIELDS)}
        return [by_field[f] for f in FIXTURE_TYPES[self.fixture_type]['channels']]

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

    MAX_START = 512 - Fixture.CHANNELS + 1  # last start address that still fits in the universe

    def _overlaps(self, start, ignore=None):
        """Return the fixture whose channels overlap a fixture starting at `start`, or None."""
        end = start + Fixture.CHANNELS - 1
        for f in self.fixtures:
            if f is ignore:
                continue
            if start <= f.start_address + Fixture.CHANNELS - 1 and f.start_address <= end:
                return f
        return None

    def _validate_address(self, start, ignore=None):
        if not 1 <= start <= self.MAX_START:
            raise ValueError(f"Start address must be between 1 and {self.MAX_START} "
                             f"(each light uses {Fixture.CHANNELS} channels).")
        clash = self._overlaps(start, ignore)
        if clash:
            raise ValueError(
                f"Channels {start}–{start + Fixture.CHANNELS - 1} overlap '{clash.name}' "
                f"(ch {clash.start_address}–{clash.start_address + Fixture.CHANNELS - 1}).")

    def next_start_address(self):
        """Suggest an address: right after the highest fixture, else the first free gap."""
        if not self.fixtures:
            return 1
        after_last = max(f.start_address for f in self.fixtures) + Fixture.CHANNELS
        if after_last <= self.MAX_START and not self._overlaps(after_last):
            return after_last
        for start in range(1, self.MAX_START + 1):
            if not self._overlaps(start):
                return start
        return None

    def add_fixture(self, name, start_address=None, fixture_type=DEFAULT_FIXTURE_TYPE):
        start = self.next_start_address() if start_address is None else int(start_address)
        if start is None:
            raise ValueError("No DMX addresses left (universe max 512 channels).")
        self._validate_address(start)
        fixture = Fixture(name, start, fixture_type)
        self.fixtures.append(fixture)
        self._save()
        return fixture

    def update_fixture(self, index, start_address, fixture_type):
        fixture = self.fixtures[index]
        start = int(start_address)
        if fixture_type not in FIXTURE_TYPES:
            raise ValueError(f"Unknown fixture type '{fixture_type}'.")
        self._validate_address(start, ignore=fixture)
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
