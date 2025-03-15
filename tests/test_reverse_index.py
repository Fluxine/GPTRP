import os
import unittest

from gptrp.reverse_index import FuzzyReverseIndex


class TestFuzzyReverseIndex(unittest.TestCase):
    def setUp(self):
        self.index = FuzzyReverseIndex('test_index.jsonl')
        self.index.index_document(['apple', 'banana'], {
                                  'id': 1, 'text': 'Fruit basket'})
        self.index.index_document(['banana', 'orange'], {
                                  'id': 2, 'text': 'Tropical fruits'})

    def test_query_single(self):
        result = self.index.query(['apple'])
        self.assertIn({'id': 1, 'text': 'Fruit basket'}, result)

    def test_query_fuzzy(self):
        # Lower similarity to see fuzzy matching
        result = self.index.query(['appel'], threshold=80)
        self.assertIn({'id': 1, 'text': 'Fruit basket'}, result)

    def test_query_no_match(self):
        result = self.index.query(['grape'])
        self.assertEqual(len(result), 0)

    def test_multiple_matches(self):
        result = self.index.query(['banana'])
        self.assertEqual(len(result), 2)
        self.assertIn({'id': 1, 'text': 'Fruit basket'}, result)
        self.assertIn({'id': 2, 'text': 'Tropical fruits'}, result)

    def test_no_duplicates_in_results(self):
        self.index.index_document(
            ['mango', 'peach'], {'id': 3, 'text': 'Summer fruits'})
        self.index.index_document(
            ['peach', 'plum'], {'id': 4, 'text': 'Stone fruits'})

        result = self.index.query(['peach', 'mango'])

        result_tuples = [tuple(sorted(item.items())) for item in result]

        self.assertEqual(len(result), len(set(result_tuples)),
                         "Query results contain duplicates")

    def tearDown(self):
        os.remove('test_index.jsonl')


if __name__ == '__main__':
    unittest.main()
