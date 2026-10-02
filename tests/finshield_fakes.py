from copy import deepcopy
from threading import RLock


class MemoryStore:
    """Tests only. Never a production storage fallback."""
    def __init__(self):
        self.docs, self.lock = {}, RLock()

    def read(self, key):
        with self.lock:
            return deepcopy(self.docs.get(key))

    def atomic(self, keys, reduce):
        with self.lock:
            writes = reduce({key: deepcopy(self.docs.get(key)) for key in keys})
            assert set(writes) <= set(keys)
            self.docs.update(deepcopy(writes))
            return deepcopy(writes)
