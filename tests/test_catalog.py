import json
from pathlib import Path
import sys
import tempfile
import unittest

from telegram_integration.catalog import CatalogUnavailable, CodexProjectCatalog


class CatalogContractTests(unittest.TestCase):
    def test_consumer_obtains_known_destination_from_paginated_catalog(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'projects.json'
            source.write_text(json.dumps([
                [{'id': 'server-nika', 'name': 'nika', 'roots': [{'path': '/work/nika'}]}],
                [{'id': 'server-help', 'name': 'help', 'roots': [{'path': '/work/help'}]}],
            ]))
            catalog = CodexProjectCatalog(command=[sys.executable, str(Path(__file__).parent / 'fixtures/catalog_server.py'), str(source)])
            self.assertEqual(catalog.destination('server-help'), Path('/work/help'))
            source.write_text(json.dumps([[{'id': 'server-help', 'name': 'Renamed', 'roots': [{'path': '/work/new-help'}]}]]))
            self.assertEqual(catalog.destination('server-help'), Path('/work/new-help'))
            source.write_text('[[]]')
            with self.assertRaises(CatalogUnavailable):
                catalog.destination('server-help')

    def test_incomplete_project_metadata_is_not_exposed_as_a_catalog(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'projects.json'
            source.write_text(json.dumps([[{'id': '', 'name': 'help', 'roots': [{'path': 'relative'}]}]]))
            catalog = CodexProjectCatalog(command=[sys.executable, str(Path(__file__).parent / 'fixtures/catalog_server.py'), str(source)])
            with self.assertRaises(CatalogUnavailable):
                catalog.refresh()


if __name__ == '__main__':
    unittest.main()
