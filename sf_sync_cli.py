"""
================================================================================
FILE: sf_sync_cli.py
VERSION: 1.0.4
DATE: 2026-04-27
DESCRIPTION: Professional Salesforce Report Sync Tool.
             UPDATED: Uses Absolute Paths to ensure local config persistence
             when launched via terminal aliases.
================================================================================
"""

import os
import json
import subprocess
import requests
import csv

# --- VERSION TRACKING ---
VERSION = "1.0.4"
ORG_ALIAS = "akamai_sf"

# --- PATH LOCKING ---
# This ensures the config file is always in the same folder as this script
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, "reports_config.json")
OUTPUT_FOLDER = os.path.join(BASE_DIR, "downloads")

def load_report_config():
    """Loads reports from local JSON. Returns empty dict if file missing."""
    if not os.path.exists(CONFIG_FILE):
        return {}
    with open(CONFIG_FILE, 'r') as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}

def save_report_config(config_dict):
    """Saves the current report configuration to JSON."""
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config_dict, f, indent=4)

def get_sf_connection():
    """Authenticates using the SF CLI."""
    try:
        result = subprocess.run(["sf", "org", "display", "--json", "-o", ORG_ALIAS], 
                                capture_output=True, text=True, check=True)
        data = json.loads(result.stdout)
        return {"token": data["result"]["accessToken"], "url": data["result"]["instanceUrl"]}
    except Exception:
        return None

def sync_details_master(report_id, report_name, conn):
    """Flattens and extracts Matrix reports to CSV with overwrite."""
    headers = {"Authorization": f"Bearer {conn['token']}", "Content-Type": "application/json"}
    
    # 1. Describe
    res = requests.get(f"{conn['url']}/services/data/v60.0/analytics/reports/{report_id}/describe", headers=headers)
    if res.status_code != 200: return False

    metadata = res.json()["reportMetadata"]
    group_fields = [g["name"] for g in metadata.get("groupingsDown", [])] + \
                   [g["name"] for g in metadata.get("groupingsAcross", [])]
    
    current_cols = metadata.get("detailColumns", [])
    for field in reversed(group_fields):
        if field not in current_cols: current_cols.insert(0, field)
    
    metadata["groupingsDown"], metadata["groupingsAcross"] = [], []
    metadata["detailColumns"] = current_cols

    # 2. Run
    run_res = requests.post(f"{conn['url']}/services/data/v60.0/analytics/reports/{report_id}?includeDetails=true", 
                            headers=headers, json={"reportMetadata": metadata})

    if run_res.status_code == 200:
        data = run_res.json()
        col_info = data["reportExtendedMetadata"]["detailColumnInfo"]
        headers_list = [col_info[c]["label"] for c in current_cols]
        rows = data.get("factMap", {}).get("T!T", {}).get("rows", [])
        
        if not rows: return False

        if not os.path.exists(OUTPUT_FOLDER): os.makedirs(OUTPUT_FOLDER)
        file_path = os.path.join(OUTPUT_FOLDER, f"{report_name}.csv")
        with open(file_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(headers_list)
            for r in rows: writer.writerow([cell["label"] for cell in r["dataCells"]])
        return True
    return False