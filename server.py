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
    import pandas as pd
    import networkx as nx
    from pyvis.network import Network
    import os

    # Load the data
    if filepath.endswith('.csv'):
        df = pd.read_csv(filepath)
    else:
        df = pd.read_excell(filepath)

    required_columns = ["UserID", "First Name", "Last Name", "Manager Name", "Manager UserID"]
    missing_cols = set(required_columns) - set(df.columns)
    if missing_cols:
        raise ValueError(f"Missing columns infile: {missing_cols}")
    
    G = nx.DiGraph()

    # Add nodes
    for _, row in df.iterrows():
        user_id = row["UserID"]
        manager_id = row["Manager UserID"]
        G.add_node(user_id,
                   first_name=row["First Name"],
                   last_name=row["Last Name"],
                   manager_name=row["Manager Name"],
                   manager_user_id=manager_id)
        # Add edges if manager_id exists and is not blank
        if pd.notna(manager_id) and manager_id != "" and manager_id != user_id:
            G.add_edge(manager_id, user_id, relation="reports_to")

    # Detect cycles
    try:
        cycles = list(nx.find_cycle(G, orientation="original"))
        if cycles:
            print(f"Warning: Detected management cycle(s): {cycles}")
    except nx.exception.NetworkXNoCycle:
        cycles = []

    # Detect broken references
    all_ids = set(df["UserID"])
    broken_managers = set(df["Manager UserID"]) - all_ids - {None, ""}
    if broken_managers:
        print(f"Warning: Manager IDs not found in data: {broken_managers}")

    # Create interactive visualization
    net = Network(directed=True, notebook=False)
    for node, data in G.nodes(data=True):
        net.add_node(node,
                     label=f'{data["first_name"]} {data["last_name"]}',
                     title=f"UserID: {node}\nManager: {data['manager_name']} ({data['manager_user_id']})")
    
    for source, target, data in G.edges(data=True):
        net.add_edge(source, target, label=data["relation"])

    # Save HTML
    output_html = os.path.splitext(filepath)[0] + "org_chart.html"
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