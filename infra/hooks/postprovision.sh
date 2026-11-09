#!/bin/sh
set -eu

echo "Writing local development settings..."
uv run --locked python infra/setup-env.py

echo "Creating the shared Search indexes and the HR agent knowledge base..."
uv run --locked python infra/create-search-indexes.py

if [ "${ENABLE_FABRIC_ITEMS:-false}" = "true" ]; then
    if [ -z "${FABRIC_CAPACITY_ID:-}" ] && [ -z "${FABRIC_WORKSPACE_ID:-}" ]; then
        echo "ENABLE_FABRIC_ITEMS is true but neither FABRIC_CAPACITY_ID nor FABRIC_WORKSPACE_ID is set." >&2
        echo "Set ENABLE_FABRIC_CAPACITY=true to create a capacity, or set FABRIC_WORKSPACE_ID to use an existing workspace." >&2
        exit 1
    fi

    echo "Creating the optional Fabric lakehouse and ontology..."
    uv run --locked python infra/create-lakehouse.py

    echo "Creating the Fabric product review graph..."
    uv run --locked python infra/create-fabric-graph.py

    echo "Creating the web analytics lakehouse..."
    uv run --locked python infra/create-web-analytics-lakehouse.py

    echo "Creating the web analytics semantic model..."
    uv run --locked python infra/create-semantic-model.py

    echo "Creating the web analytics Power BI report..."
    uv run --locked python infra/create-web-analytics-report.py

    echo "Creating the Fabric data agent..."
    uv run --locked python infra/create-fabric-data-agent.py
fi

if [ "${ENABLE_WORK_IQ:-false}" = "true" ]; then
    echo "Creating the Work IQ Entra application..."
    uv run --locked python infra/create-workiq-entra.py --apply
    echo "Creating the direct Work IQ MCP OAuth connection..."
    uv run --locked python infra/create-workiq-mcp.py --apply
fi

echo "Postprovision setup complete."
