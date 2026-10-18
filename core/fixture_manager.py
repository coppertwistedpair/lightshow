import json
import os


class Fixture:
    CHANNELS = 6  # Ch1=R, Ch2=G, Ch3=B, Ch4=A, Ch5=W, Ch6=UV/Purple

    def __init__(self, name, start_address):
        self.name = name
        self.start_address = start_address

    def to_dict(self):
        return {'name': self.name, 'start_address': self.start_address}

    @staticmethod
    def from_dict(d):
        return Fixture(d['name'], d['start_address'])


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

    def add_fixture(self, name, start_address=None):
        start = self.next_start_address() if start_address is None else int(start_address)
        if start is None:
            raise ValueError("No DMX addresses left (universe max 512 channels).")
        self._validate_address(start)
        fixture = Fixture(name, start)
        self.fixtures.append(fixture)
        self._save()
        return fixture

    def set_start_address(self, index, start_address):
        fixture = self.fixtures[index]
        start = int(start_address)
        self._validate_address(start, ignore=fixture)
        fixture.start_address = start
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
