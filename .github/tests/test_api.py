"""Exercise location decoding and bounded radius expansion without network access."""

import asyncio
import importlib.util
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import AsyncMock

# The parser can run in the fast CI suite without installing Home Assistant.
ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / "custom_components" / "cigarette_vending_finder"
sys.modules.setdefault("custom_components", types.ModuleType("custom_components"))
pkg = types.ModuleType("custom_components.cigarette_vending_finder")
pkg.__path__ = [str(PACKAGE)]
sys.modules.setdefault("custom_components.cigarette_vending_finder", pkg)
spec = importlib.util.spec_from_file_location(
    "custom_components.cigarette_vending_finder.api", PACKAGE / "api.py"
)
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)


class FinderTests(unittest.TestCase):
    def test_details_image_and_way_center(self):
        point = {
            "type": "way", "id": 42, "center": {"lat": 50.0, "lon": 8.0},
            "tags": {"amenity": "vending_machine", "vending": "drinks;cigarettes",
                     "location": "behind the station", "wikimedia_commons": "File:Machine front.jpg"},
        }
        machine = module.parse_machine(point, (50.0, 8.0))
        self.assertEqual(machine.details["location"], "behind the station")
        self.assertEqual(machine.image_url,
                         "https://commons.wikimedia.org/wiki/Special:FilePath/Machine%20front.jpg")
        self.assertEqual(machine.as_dict()["osm_url"], "https://www.openstreetmap.org/way/42")
        self.assertIsNone(module.parse_machine({**point, "tags": {"vending": "cigarettes"}}, (50, 8)))

    def test_search_deduplicates_and_respects_radius(self):
        async def check():
            finder = module.OverpassFinder(None)
            finder._query = AsyncMock(side_effect=[
                [{"type": "node", "id": 1, "lat": 50.0, "lon": 8.0,
                  "tags": {"amenity": "vending_machine", "vending": "cigarettes"}}],
                [{"type": "node", "id": 1, "lat": 50.0, "lon": 8.0,
                  "tags": {"amenity": "vending_machine", "vending": "cigarettes"}},
                 {"type": "node", "id": 2, "lat": 50.01, "lon": 8.0,
                  "tags": {"amenity": "vending_machine", "vending": "cigarettes"}},
                 {"type": "node", "id": 3, "lat": 51, "lon": 8,
                  "tags": {"amenity": "vending_machine", "vending": "cigarettes"}}],
            ])
            machines = await finder.search(50, 8, 2, 2)
            self.assertEqual([machine.osm_id for machine in machines], [1, 2])
            self.assertEqual(finder._query.await_count, 2)
        asyncio.run(check())
