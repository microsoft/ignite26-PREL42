# Data

Sample data used by the setup scripts, notebooks, and agents:

| Folder | Contents |
| --- | --- |
| `ai-search-data/` | HR and health documents for the Foundry IQ notebooks |
| `index-data/` | Exported Azure AI Search index definitions and pre-vectorized documents, restored by `infra/create-search-indexes.py` |
| `lakehouse-data/` | Contoso DIY products and stores, loaded into the Fabric lakehouse by `infra/create-lakehouse.py` (from the [Zava DIY dataset](https://github.com/microsoft/ai-tour-26-zava-diy-dataset-plus-mcp)) |
| `ontologies/contoso-diy/` | TMDL definition of the Contoso DIY Fabric IQ ontology |
| `semantic-models/web-analytics/` | TMDL definition of the Direct Lake web analytics semantic model |
| `reports/web-analytics/` | PBIR definition of the web analytics Power BI report |
| `workiq-fixtures/` | Sample emails for Work IQ, sent to the lab mailbox by `infra/seed-emails.ps1` |
