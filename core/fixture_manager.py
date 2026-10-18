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

    def _next_start_address(self):
        if not self.fixtures:
            return 1
        last = self.fixtures[-1]
        return last.start_address + Fixture.CHANNELS

    def add_fixture(self, name):
        start = self._next_start_address()
        if start + Fixture.CHANNELS - 1 > 512:
            raise ValueError("No DMX addresses left (universe max 512 channels).")
        fixture = Fixture(name, start)
        self.fixtures.append(fixture)
        self._save()
        return fixture

    def remove_fixture(self, index):
        if 0 <= index < len(self.fixtures):
            self.fixtures.pop(index)
            self._reassign_addresses()
            self._save()

    def _reassign_addresses(self):
        addr = 1
        for f in self.fixtures:
            f.start_address = addr
            addr += Fixture.CHANNELS

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
