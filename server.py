import os
import stat
import sys
import logging
from dotenv import load_dotenv
from fastmcp import FastMCP
import pandas as pd
from pyvis.network import Network
import networkx as nx

def print_file_permissions(filepath):
    st = os.stat(filepath)
    mode = st.st_mode
    permissions = stat.filemode(mode)
    print(f"Permissions for {filepath}: {permissions}")
    print(f"Numeric mode: {oct(mode)}")

# Example usage
print_file_permissions("/data/Workday_Data_Sample.xlsx")

# Load environment variables
load_dotenv()

# Initialize logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastMCP with necessary dependencies to support Excel formats
mcp = FastMCP("Multi-MCP", dependencies=["openpyxl", "xlrd"], port=3000)


@mcp.tool("xlsx_to_org_chart")
def xlsx_to_org_chart(filename: str) -> str:
    """
    Converts an Excel HR dataset file into an organizational chart visualization.
    Supports files in mounted directories, checks for existence, and handles possible errors.
    """
    try:
        # Define potential file paths for accessibility within containers
        possible_paths = [
            filename,
            os.path.join("/data", filename),
            os.path.join("/app", filename)
        ]

        # Locate the actual file
        filepath = None
        for path in possible_paths:
            if os.path.exists(path):
                filepath = path
                break

        if not filepath:
            return f"❌ File not found: {filename}"

        # Read Excel file with explicit engine
        try:
            df = pd.read_excel(filepath, engine='openpyxl')
        except:
            df = pd.read_excel(filepath, engine='xlrd')

        # Normalize column names for flexible lookup
        normalized_cols = {c.lower(): c for c in df.columns}
        required_cols = {"associate id", "reports to manager id"}

        missing_cols = required_cols - set(normalized_cols)
        if missing_cols:
            return f"❌ Missing required columns: {', '.join(missing_cols)}"

        associate_id_col = normalized_cols["associate id"]
        manager_id_col = normalized_cols["reports to manager id"]

        # Build directed graph representing hierarchy
        G = nx.DiGraph()

        for _, row in df.iterrows():
            node_id = row[associate_id_col]
            manager_id = row[manager_id_col]

            # Convert row to dict for attributes, store manager reference
            attributes = row.to_dict()
            attributes["reports to manager id"] = manager_id

            G.add_node(node_id, **attributes)

            if pd.notna(manager_id) and manager_id != "" and manager_id != node_id:
                G.add_edge(manager_id, node_id, relation="reports_to")

        # Detect management cycles
        try:
            cycles = list(nx.find_cycle(G, orientation="original"))
            if cycles:
                logger.warning(f"Management cycle(s) detected: {cycles}")
        except nx.exception.NetworkXNoCycle:
            pass

        # Identify broken references (managers not present)
        all_ids = set(df[associate_id_col])
        broken_managers = set(df[manager_id_col]) - all_ids - {None, ""}
        if broken_managers:
            logger.warning(f"Manager IDs not found in data: {broken_managers}")

        # Generate interactive network visualization
        net = Network(directed=True, notebook=False)

        for node, data in G.nodes(data=True):
            first_name = data.get("legal first name") or data.get("Legal First Name") or ""
            last_name = data.get("legal last name") or data.get("Legal Last Name") or ""
            label = f"{first_name} {last_name}".strip() or str(node)
            title = "\n".join(f"{k}: {v}" for k, v in data.items())
            net.add_node(node, label=label, title=title)

        for source, target, data in G.edges(data=True):
            net.add_edge(source, target, label=data.get("relation", ""))

        # Save HTML visualization
        output_html = os.path.splitext(filepath)[0] + "_org_chart.html"
        net.write_html(output_html)

        return f"✅ Chart created successfully! See {output_html}"

    except Exception as e:
        logger.exception("Error generating organization chart")
        return f"❌ Error: {str(e)}"


if __name__ == "__main__":
    try:
        logger.info("Starting FastMCP server")
        mcp.run(transport="http", host="0.0.0.0")
    except KeyboardInterrupt:
        logger.info("Server shutting down.")
        sys.exit()

