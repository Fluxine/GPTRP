import json
from fuzzywuzzy import fuzz, process


class FuzzyDict:
    def __init__(self):
        self._store = {}

    def _find_key(self, key, threshold=80):
        """Helper method to find the best matching key based on fuzzy matching."""
        if not self._store:
            return None
        matches = process.extractBests(key, self._store.keys(
        ), scorer=fuzz.token_sort_ratio, score_cutoff=threshold)
        if matches:
            return matches[0][0]  # Return the best match
        return None

    def getOrInsert(self, key: str, default, threshold: int = 80):
        matched_key = self._find_key(key, threshold)
        if matched_key:
            return self._store[matched_key]
        else:
            self._store[key] = default
            return default

    def contains(self, key: str, threshold: int = 80) -> bool:
        return self._find_key(key, threshold) is not None

    def remove(self, key: str, threshold: int = 80):
        matched_key = self._find_key(key, threshold)
        if matched_key:
            del self._store[matched_key]

    def items(self):
        return self._store.items()

    def values(self):
        return self._store.values()

    def keys(self):
        return self._store.keys()

    def toJSON(self):
        return json.dumps(self._store)

    @classmethod
    def fromJSON(cls, json_str):
        obj = cls()
        obj._store = json.loads(json_str)
        return obj
