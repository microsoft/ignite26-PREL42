$ErrorActionPreference = "Stop"

Write-Host "Writing local development settings..."
uv run --locked python infra/setup-env.py

Write-Host "Creating the shared Search indexes and the HR agent knowledge base..."
uv run --locked python infra/create-search-indexes.py

if ($env:ENABLE_FABRIC_ITEMS -eq "true") {
    if (-not $env:FABRIC_CAPACITY_ID -and -not $env:FABRIC_WORKSPACE_ID) {
        Write-Error "ENABLE_FABRIC_ITEMS is true but neither FABRIC_CAPACITY_ID nor FABRIC_WORKSPACE_ID is set. Set ENABLE_FABRIC_CAPACITY=true to create a capacity, or set FABRIC_WORKSPACE_ID to use an existing workspace."
    }

    Write-Host "Creating the optional Fabric lakehouse and ontology..."
    uv run --locked python infra/create-lakehouse.py

    Write-Host "Creating the Fabric product review graph..."
    uv run --locked python infra/create-fabric-graph.py

    Write-Host "Creating the web analytics lakehouse..."
    uv run --locked python infra/create-web-analytics-lakehouse.py

    Write-Host "Creating the web analytics semantic model..."
    uv run --locked python infra/create-semantic-model.py

    Write-Host "Creating the web analytics Power BI report..."
    uv run --locked python infra/create-web-analytics-report.py

    Write-Host "Creating the Fabric data agent..."
    uv run --locked python infra/create-fabric-data-agent.py
}

if ($env:ENABLE_WORK_IQ -eq "true") {
    Write-Host "Creating the Work IQ Entra application..."
    uv run --locked python infra/create-workiq-entra.py --apply
    Write-Host "Creating the direct Work IQ MCP OAuth connection..."
    uv run --locked python infra/create-workiq-mcp.py --apply
}

Write-Host "Postprovision setup complete."
