import os
import jsonlines
from fuzzywuzzy import process


class FuzzyReverseIndex:
    def __init__(self, filepath):
        self.index = {}
        self.filepath = filepath
        try:
            with jsonlines.open(filepath) as reader:
                for obj in reader:
                    for key in obj['keys']:
                        if key not in self.index:
                            self.index[key] = []
                        self.index[key].append(obj['value'])
        except FileNotFoundError:
            # File doesn't exist, create an empty index
            directory = os.path.dirname(filepath)
            if directory:
                os.makedirs(directory, exist_ok=True)
            with open(filepath, 'w') as file:
                pass

    def index_document(self, keys: list[str], value: str):
        with jsonlines.open(self.filepath, mode='a') as writer:
            writer.write({'keys': keys, 'value': value})
            for key in keys:
                if key not in self.index:
                    self.index[key] = []
                self.index[key].append(value)

    def query(self, search_terms: list[str], threshold: int = 80):
        results = []
        for term in search_terms:
            matches = process.extractBests(
                term, self.index.keys(), score_cutoff=threshold)
            for key, _ in matches:
                # Yes, this is O(n^2), the data sets are expected to be small
                for item in self.index[key]:
                    if item not in results:
                        results.append(item)
        return results
