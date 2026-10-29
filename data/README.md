# Data

Sample data used by the setup scripts, notebooks, and agents:

| Folder | Contents |
| --- | --- |
| `ai-search-data/` | HR and health documents for the Foundry IQ notebooks |
| `index-data/` | Exported Azure AI Search index definitions and documents, restored by `infra/create-search-indexes.py`; unchanged documents are pre-vectorized, while the revised company overview is embedded during restore |
| `lakehouse-data/` | Contoso DIY products and stores, loaded into the Fabric lakehouse by `infra/create-lakehouse.py` (from the [Zava DIY dataset](https://github.com/microsoft/ai-tour-26-zava-diy-dataset-plus-mcp)) |
| `ontologies/contoso-diy/` | TMDL definition of the Contoso DIY Fabric IQ ontology |
| `semantic-models/web-analytics/` | TMDL definition of the Direct Lake web analytics semantic model |
| `reports/web-analytics/` | PBIR definition of the web analytics Power BI report |
| `workiq-fixtures/` | Sample emails for Work IQ, sent to the lab mailbox by `infra/seed-emails.ps1` |

The shared scenario is **Contoso DIY**, a home improvement retailer with seven
Washington retail stores and an online store. The Zava dataset link above records
the original source; the local store names and Work IQ scenario use Contoso.
Northwind remains the health insurance provider in the benefits documents.

The generated inventory matches the Work IQ emails for Professional Claw Hammer
16oz (`HTHM001600`): Seattle has zero stock, Bellevue has 24 available units, and
Redmond has 18. Other product/store combinations retain their deterministic
generated inventory.

The company overview source is `ai-search-data/hrdocs/Contoso_DIY_Company_Overview.md`.
Its two exported chunks deliberately omit `snippet_vector`: restoring the index
generates fresh `text-embedding-3-large` vectors from the updated text using the
deployment's Azure OpenAI endpoint and setup identity. Existing document IDs,
other vectors, resource names, and product SKUs are preserved.

These changes apply when the sample data is loaded. Existing lab mailboxes are
not rewritten, and `create-search-indexes.py` skips index uploads when the shared
knowledge base already exists. Use a fresh lab deployment to get the complete
updated scenario; no running environments are migrated automatically.
