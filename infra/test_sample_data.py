"""Offline regression checks for the shared Contoso DIY sample scenario."""

import importlib.util
import json
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

ROOT = Path(__file__).resolve().parents[1]


def load_script(name):
    spec = importlib.util.spec_from_file_location(name.replace("-", "_"), ROOT / "infra" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


lakehouse = load_script("create-lakehouse")
search = load_script("create-search-indexes")


class RetailScenarioTests(unittest.TestCase):
    def test_normalization_updates_nested_store_keys_and_values(self):
        original = {
            "stores": {"Zava Retail Seattle": {"weight": 30}},
            "locations": ["Zava Retail Online", "Professional Claw Hammer 16oz"],
        }
        normalized = lakehouse.normalize_company_locations(original)
        self.assertEqual(normalized["stores"], {"Contoso Retail Seattle": {"weight": 30}})
        self.assertEqual(normalized["locations"], ["Contoso Retail Online", "Professional Claw Hammer 16oz"])
        self.assertIn("Zava Retail Seattle", original["stores"])

    def test_hammer_inventory_matches_the_seeded_stockout_and_transfer_request(self):
        products = lakehouse.flatten_products(lakehouse.load_json("product_data.json"))
        stores = lakehouse.flatten_stores(lakehouse.load_json("reference_data.json"))
        inventory = lakehouse.generate_inventory(products, stores)
        hammer = {row["store_id"]: row for row in inventory if row["sku"] == "HTHM001600"}
        self.assertTrue(all(store["store_name"].startswith("Contoso Retail ") for store in stores))
        for store_id, available in {"STORE-SEA": 0, "STORE-BEL": 24, "STORE-RED": 18}.items():
            with self.subTest(store_id=store_id):
                self.assertEqual(hammer[store_id]["available_quantity"], available)
                self.assertEqual(hammer[store_id]["quantity_on_hand"], available)
                self.assertEqual(hammer[store_id]["quantity_reserved"], 0)
        self.assertGreaterEqual(hammer["STORE-TAC"]["available_quantity"], 5)
        self.assertGreaterEqual(hammer["STORE-ONL"]["available_quantity"], 5)
        self.assertEqual(inventory, lakehouse.generate_inventory(products, stores))
        for row in inventory:
            self.assertEqual(row["available_quantity"], row["quantity_on_hand"] - row["quantity_reserved"])
            self.assertGreaterEqual(row["available_quantity"], 0)

    def test_indexed_overview_chunks_come_from_the_updated_source_without_stale_vectors(self):
        source = (ROOT / "data/ai-search-data/hrdocs/Contoso_DIY_Company_Overview.md").read_text(encoding="utf-8")
        records = [
            json.loads(line)
            for line in (ROOT / "data/index-data/hrdocs-exported.jsonl").read_text(encoding="utf-8").splitlines()
        ]
        overview = [row for row in records if row["blob_path"] == "/hrdocs/Contoso_DIY_Company_Overview.md"]
        self.assertEqual(len(overview), 2)
        for row in overview:
            self.assertIn(row["snippet"], source)
            self.assertNotIn("snippet_vector", row)
        self.assertIn("home improvement retailer", overview[0]["snippet"])
        for row in records:
            if row not in overview:
                self.assertEqual(len(row["snippet_vector"]), 3072)
            self.assertNotIn("consumer electronics", row["snippet"].lower())


class SearchEmbeddingTests(unittest.IsolatedAsyncioTestCase):
    async def test_only_revised_documents_are_embedded_in_response_index_order(self):
        documents = [
            {"snippet": "Existing policy", "snippet_vector": [0.1, 0.2]},
            {"snippet": "Contoso DIY overview"},
            {"snippet": "Contoso DIY careers"},
        ]
        credential = SimpleNamespace(get_token=AsyncMock(return_value=SimpleNamespace(token="test-token")))
        response = Mock()
        response.json.return_value = {
            "data": [{"index": 1, "embedding": [0.5, 0.6]}, {"index": 0, "embedding": [0.3, 0.4]}]
        }
        with patch.object(search.requests, "post", return_value=response) as post:
            await search.populate_missing_embeddings(
                documents, credential, "https://example.openai.azure.com/", "embed", 2
            )
        self.assertEqual(post.call_args.kwargs["json"], {
            "input": ["Contoso DIY overview", "Contoso DIY careers"], "dimensions": 2,
        })
        self.assertEqual([document["snippet_vector"] for document in documents], [[0.1, 0.2], [0.3, 0.4], [0.5, 0.6]])
        response.raise_for_status.assert_called_once()

    async def test_prevectorized_documents_do_not_require_embedding_access(self):
        credential = SimpleNamespace(get_token=AsyncMock())
        with patch.object(search.requests, "post") as post:
            await search.populate_missing_embeddings([{"snippet_vector": [0.1, 0.2]}], credential, "", "embed", 2)
        credential.get_token.assert_not_called()
        post.assert_not_called()

    async def test_missing_endpoint_or_invalid_response_fails_before_upload(self):
        credential = SimpleNamespace(get_token=AsyncMock(return_value=SimpleNamespace(token="test-token")))
        with self.assertRaisesRegex(ValueError, "AZURE_OPENAI_ENDPOINT"):
            await search.populate_missing_embeddings([{"snippet": "New overview"}], credential, "", "embed", 2)
        for data in ([], [{"index": 0, "embedding": [0.1]}], [{"index": 1, "embedding": [0.1, 0.2]}]):
            response = Mock()
            response.json.return_value = {"data": data}
            document = {"snippet": "New overview"}
            with self.subTest(data=data), patch.object(search.requests, "post", return_value=response):
                with self.assertRaisesRegex(ValueError, "Embedding response"):
                    await search.populate_missing_embeddings([document], credential, "https://example", "embed", 2)
                self.assertNotIn("snippet_vector", document)


if __name__ == "__main__":
    unittest.main()
