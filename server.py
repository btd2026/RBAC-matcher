

































import os
import json
import logging
import sys
import pandas as pd
from dotenv import load_dotenv
from fastmcp import FastMCP
from pyvis.network import Network
import networkx as nx
from rapidfuzz import process, fuzz
import webbrowser

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

mcp = FastMCP("RBAC-matcher", dependencies=["openpyxl", "xlrd", "rapidfuzz"], port=3000)


SUGGESTION_MEMORY = {}

def find_matching_file(file_reference, files, session_id="default", proceed=None):
    data_dir = "/data"
    if proceed and proceed.lower() == "yes" and session_id in SUGGESTION_MEMORY:
        return SUGGESTION_MEMORY.pop(session_id)
    elif file_reference and os.path.exists(os.path.join(data_dir, file_reference)):
        return os.path.join(data_dir, file_reference)
    elif file_reference and files:
        fname, score, _ = process.extractOne(file_reference, files, scorer=fuzz.partial_ratio)
        if score > 60:
            matched_file = os.path.join(data_dir, fname)
            SUGGESTION_MEMORY[session_id] = matched_file
            return f"Did you mean '{fname}'? Reply with proceed=yes to continue."
        else:
            return f"No matching file found for '{file_reference}'. Available files: {files}"
    else:
        return f"No file reference provided. Available files: {files}"

def build_graph_from_df(df, associate_id_col, manager_id_col):
    G = nx.DiGraph()
    for _, row in df.iterrows():
        node_id = row[associate_id_col]
        manager_id = row[manager_id_col]
        attributes = row.to_dict()
        attributes["reports to manager id"] = manager_id
        G.add_node(node_id, **attributes)
        if pd.notna(manager_id) and manager_id != "" and manager_id != node_id:
            G.add_edge(manager_id, node_id, relation="reports_to")
    return G

def save_network_html(G, filepath, suffix="_org_chart", options=None):
    net = Network(directed=True, notebook=False)
    if not options:
        options = {
            "layout": {
                "hierarchical": {
                    "enabled": True,
                    "direction": "UD",
                    "sortMethod": "directed",
                    "levelSeparation": 250,
                    "nodeSpacing": 300
                }
            },
            "physics": {
                "enabled": False
            }
        }
    net.set_options(json.dumps(options))
    for node, data in G.nodes(data=True):
        first_name = data.get("legal first name") or data.get("Legal First Name") or ""
        last_name = data.get("legal last name") or data.get("Legal Last Name") or ""
        job_title = data.get("Job Title", "")
        cost_center = data.get("Cost Center Name", "")
        label = (
            f"{first_name} {last_name}\n"
            f"{job_title}\n"
            f"Cost Center: {cost_center}"
        ).strip()
        title = "\n".join(f"{k}: {v}" for k, v in data.items())
        net.add_node(
            node,
            label=label,
            title=title,
            color="lightgreen" if data.get("Job Title") == "Manager" else "lightblue",
            shape="box",
            font={"size": 18, "color": "black"}
        )
    for source, target, data in G.edges(data=True):
        net.add_edge(source, target, label=data.get("relation", ""))


    output_dir = "output"
    os.makedirs(output_dir, exist_ok=True)
    base_filename = os.path.splitext(os.path.basename(filepath))[0] + f"{suffix}.html"
    output_html = os.path.join(output_dir, base_filename)
    net.write_html(output_html)

    abs_path = os.path.abspath(output_html)
    try:

        webbrowser.open_new_tab(f"file://{abs_path}")
    except Exception as e:
        logger.warning(f"Could not open browser automatically: {e}")

    return output_html

@mcp.tool("xlsx_to_org_chart")
def xlsx_to_org_chart(
    file_reference: str = None,
    proceed: str = None,
    session_id: str = "default",
    filter: str = None
) -> str:






    data_dir = "/data"
    files = [f for f in os.listdir(data_dir) if f.lower().endswith((".xlsx", ".csv"))]


    match_result = find_matching_file(file_reference, files, session_id, proceed)
    if not match_result or (isinstance(match_result, str) and not os.path.exists(match_result)):
        return match_result
    matched_file = match_result
    try:
        try:
            df = pd.read_excel(matched_file, engine="openpyxl")
        except Exception:
            df = pd.read_csv(matched_file)


        if filter:
            normalized_cols = {c.lower().strip(): c for c in df.columns}
            filters = [kv.split("=", 1) for kv in filter.split(",") if "=" in kv]
            for key, value in filters:
                key = key.strip().lower()
                value = value.strip()
                colname = normalized_cols.get(key)
                if colname:
                    df = df[df[colname].astype(str).str.lower().eq(value.lower())]
                else:
                    return (
                        f"Filter column '{key}' not found. "
                        f"Available columns are: {', '.join(df.columns)}"
                    )

        normalized_cols = {c.lower(): c for c in df.columns}
        required_cols = {"associate id", "reports to manager id"}
        missing = required_cols - set(normalized_cols)
        if missing:
            return f"Missing required columns: {', '.join(missing)}"
        associate_id_col = normalized_cols["associate id"]
        manager_id_col = normalized_cols["reports to manager id"]

        G = build_graph_from_df(df, associate_id_col, manager_id_col)
        out_html = save_network_html(G, matched_file, suffix="_org_chart")
        return f"Chart created: {out_html}"
    except Exception as e:
        logger.exception("Error generating organization chart")
        return f"Error processing file: {str(e)}"

@mcp.tool("list_cost_centers")
def list_cost_centers(
    file_reference: str = None,
    proceed: str = None,
    session_id: str = "default",
) -> str:




    data_dir = "/data"
    files = [f for f in os.listdir(data_dir) if f.lower().endswith((".xlsx", ".csv"))]


    match_result = find_matching_file(file_reference, files, session_id, proceed)
    if not match_result or (isinstance(match_result, str) and not os.path.exists(match_result)):
        return match_result
    matched_file = match_result
    try:
        try:
            df = pd.read_excel(matched_file, engine="openpyxl")
        except Exception:
            df = pd.read_csv(matched_file)
        col_candidates = [c for c in df.columns if c.lower().replace(" ", "") == "costcentername"]
        if not col_candidates:
            return f"Could not find 'Cost Center Name' column. Available columns: {list(df.columns)}"
        col = col_candidates[0]
        unique_centers = df[col].dropna().unique()
        if not unique_centers.any():
            return "No cost centers found in this file."
        centers_list = "\n".join(f"- {name}" for name in sorted(map(str, unique_centers)))
        return f"Available Cost Centers:\n{centers_list}"
    except Exception as e:
        logger.exception("Error listing cost centers")
        return f"Error processing file: {str(e)}"

if __name__ == "__main__":
    try:
        logger.info("Starting FastMCP server")
        mcp.run(transport="http", host="0.0.0.0")
    except KeyboardInterrupt:
        logger.info("Server shutting down.")
        sys.exit()