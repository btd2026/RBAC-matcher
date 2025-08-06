import os
from dotenv import load_dotenv
from typing import Any
import logging

import httpx

from fastmcp import FastMCP

load_dotenv()

# Initialize MCP
mcp = FastMCP("Multi-MCP", port=3000)

@mcp.tool("csv_to_org_chart")
def csv_to_graph_tool(filepath: str) -> str:
    import os
    import pandas as pd
    import networkx as nx
    from pyvis.network import Network

    # Load the data
    if filepath.endswith(".csv"):
        df = pd.read_csv(filepath)
    else:
        df = pd.read_excel(filepath)

    # Normalize column names to simplify lookups
    normalized = {c.lower(): c for c in df.columns}
    required = {"employee_id", "reports_to_manager_id"}
    missing = required - set(normalized)
    if missing:
        raise ValueError(f"Missing columns in file: {missing}")

    id_col = normalized["employee_id"]
    manager_col = normalized["reports_to_manager_id"]

    G = nx.DiGraph()

    for _, row in df.iterrows():
        node_id = row[id_col]
        manager_id = row[manager_col]

        # Use all headers as node attributes
        attributes = row.to_dict()
        # Explicit manager reference for convenience
        attributes["reports_to_manager_id"] = manager_id
        G.add_node(node_id, **attributes)

        if pd.notna(manager_id) and manager_id != "" and manager_id != node_id:
            G.add_edge(manager_id, node_id, relation="reports_to")

    # Detect cycles
    try:
        cycles = list(nx.find_cycle(G, orientation="original"))
        if cycles:
            print(f"Warning: Detected management cycle(s): {cycles}")
    except nx.exception.NetworkXNoCycle:
        cycles = []

    # Detect broken references
    all_ids = set(df[id_col])
    broken_managers = set(df[manager_col]) - all_ids - {None, ""}
    if broken_managers:
        print(f"Warning: Manager IDs not found in data: {broken_managers}")

    # Create interactive visualization
    net = Network(directed=True, notebook=False)
    for node, data in G.nodes(data=True):
        first = data.get("first_name") or data.get("First Name") or ""
        last = data.get("last_name") or data.get("Last Name") or ""
        label = f"{first} {last}".strip() or str(node)
        title = "\n".join(f"{k}: {v}" for k, v in data.items())
        net.add_node(node, label=label, title=title)

    for source, target, data in G.edges(data=True):
        net.add_edge(source, target, label=data["relation"])

    output_html = os.path.splitext(filepath)[0] + "_org_chart.html"
    net.show(output_html)
    return output_html




if __name__ == "__main__":
    try:
        logging.basicConfig(level=logging.INFO)
        logger = logging.getLogger(__name__)

        logger.info("Starting FastMCP server")
        mcp.run(transport="http", host="0.0.0.0")
    except KeyboardInterrupt:
        logger.info("Quitting...")
        quit()

