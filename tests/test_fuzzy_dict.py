import unittest
from fuzzywuzzy import fuzz
from fuzzywuzzy import process
# Replace 'your_module' with the actual module name where FuzzyDict is located
from gptrp.fuzzy_dict import FuzzyDict


class TestFuzzyDict(unittest.TestCase):

    def setUp(self):
        self.fdict = FuzzyDict()

    def test_insert_and_retrieve_exact_key(self):
        self.fdict.getOrInsert('Test', 'Value')
        self.assertEqual(self.fdict.getOrInsert('Test', 'Default'), 'Value')

    def test_fuzzy_retrieve_key(self):
        self.fdict.getOrInsert('TestKey', 'Value')
        self.assertEqual(self.fdict.getOrInsert(
            'testkey', 'Default', threshold=80), 'Value')

    def test_case_insensitivity(self):
        self.fdict.getOrInsert('TestKey', 'Value')
        self.assertTrue(self.fdict.contains('testkey', threshold=100))
        self.assertEqual(self.fdict.getOrInsert(
            'TESTKEY', 'Default', threshold=100), 'Value')

    def test_insert_default_if_no_match(self):
        result = self.fdict.getOrInsert('TestKey', 'Default', threshold=80)
        self.assertEqual(result, 'Default')
        self.assertEqual(self.fdict.getOrInsert(
            'TestKey', 'Value', threshold=80), 'Default')

    def test_contains(self):
        self.fdict.getOrInsert('TestKey', 'Value')
        self.assertTrue(self.fdict.contains('TestKey'))
        self.assertTrue(self.fdict.contains('testkey', threshold=80))
        self.assertFalse(self.fdict.contains('AnotherKey', threshold=80))

    def test_remove_existing_key(self):
        self.fdict.getOrInsert('TestKey', 'Value')
        self.assertTrue(self.fdict.contains('TestKey'))
        self.fdict.remove('TestKey', threshold=80)
        self.assertFalse(self.fdict.contains('TestKey'))

    def test_remove_non_existing_key(self):
        self.fdict.getOrInsert('TestKey', 'Value')
        # Should not raise an exception
        self.fdict.remove('AnotherKey', threshold=80)
        self.assertTrue(self.fdict.contains('TestKey'))

    def test_items(self):
        self.fdict.getOrInsert('Key1', 'Value1')
        self.fdict.getOrInsert('Key2', 'Value2')
        items = list(self.fdict.items())
        self.assertIn(('Key1', 'Value1'), items)
        self.assertIn(('Key2', 'Value2'), items)

    def test_values(self):
        self.fdict.getOrInsert('Key1', 'Value1')
        self.fdict.getOrInsert('Key2', 'Value2')
        values = list(self.fdict.values())
        self.assertIn('Value1', values)
        self.assertIn('Value2', values)

    def test_keys(self):
        self.fdict.getOrInsert('Key1', 'Value1')
        self.fdict.getOrInsert('Key2', 'Value2')
        keys = list(self.fdict.keys())
        self.assertIn('Key1', keys)
        self.assertIn('Key2', keys)

    def test_json_serialization(self):
        self.fdict.getOrInsert('Key1', 'Value1')
        self.fdict.getOrInsert('Key2', 'Value2')
        json_str = self.fdict.toJSON()
        new_fdict = FuzzyDict.fromJSON(json_str)
        self.assertEqual(self.fdict.getOrInsert('Key1', 'Default'),
                         new_fdict.getOrInsert('Key1', 'Default'))
        self.assertEqual(self.fdict.getOrInsert('Key2', 'Default'),
                         new_fdict.getOrInsert('Key2', 'Default'))

    def test_fuzzy_threshold(self):
        self.fdict.getOrInsert('HelloWorld', 'Value')
        # Exact match, threshold ignored
        self.assertEqual(self.fdict.getOrInsert(
            'HelloWorld', 'Default', threshold=90), 'Value')
        # Fuzzy match with lower threshold
        self.assertEqual(self.fdict.getOrInsert(
            'HelloWrold', 'Default', threshold=80), 'Value')
        # No match with higher threshold
        self.assertEqual(self.fdict.getOrInsert(
            'HelloWrold', 'Default', threshold=95), 'Default')


if __name__ == '__main__':
    unittest.main()
