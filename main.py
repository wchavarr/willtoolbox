"""
================================================================================
FILE: main.py
VERSION: 1.8.8
DATE: 2026-04-27
DESCRIPTION: Will Toolbox - Unified Management Platform.
             Integrated Salesforce management with absolute path persistence.
================================================================================
"""

import streamlit as st
import os
import subprocess

# --- VERSION TRACKING ---
VERSION = "1.8.8"

# Import Sync Logic
try:
    from sf_sync_cli import (
        get_sf_connection, sync_details_master, load_report_config, save_report_config
    )
except ImportError:
    st.error("🚨 CRITICAL: sf_sync_cli.py not found in the root directory.")

# --- AUTO-UPDATER LOGIC ---
def check_for_updates():
    try:
        subprocess.run(['git', 'fetch'], check=True, capture_output=True)
        local_hash = subprocess.check_output(['git', 'rev-parse', 'HEAD']).decode().strip()
        remote_hash = subprocess.check_output(['git', 'rev-parse', 'origin/main']).decode().strip()
        
        if local_hash != remote_hash:
            st.sidebar.warning("🚀 **Update Available!**")
            if st.sidebar.button("Update & Restart Toolbox", use_container_width=True):
                st.sidebar.info("Pulling latest changes...")
                subprocess.run(['git', 'pull', 'origin', 'main'], check=True)
                st.rerun()
    except Exception:
        pass

# --- SF SYNC WRAPPER ---
def run_manual_sync():
    reports = load_report_config()
    with st.sidebar.status("🔄 Syncing Salesforce...", expanded=True) as status:
        conn = get_sf_connection()
        if conn:
            for rid, rname in reports.items():
                st.write(f"Downloading {rname}...")
                sync_details_master(rid, rname, conn)
            status.update(label="Sync Complete!", state="complete", expanded=False)
            st.sidebar.success("Reports Updated")
            st.rerun()
        else:
            status.update(label="Sync Failed", state="error")
            st.sidebar.error("CLI Authentication Failed. Check README.")

# 1. GLOBAL CONFIGURATION
st.set_page_config(page_title="Will Toolbox", page_icon="🛡️", layout="wide")
check_for_updates()

# 2. BRANDING
st.logo("https://www.akamai.com/content/dam/site/en/images/logo/akamai-logo.svg")

# 3. DEFINE PAGES
pages = {
    "Identity & Access": [
        st.Page("apps/apiusersv2.py", title="Identity Control (v7.2)", icon="🛡️"),
        st.Page("apps/account_finder.py", title="Account Switch Finder (v2.2)", icon="🔍"),
    ],
    "Certificates": [
        st.Page("apps/certs_audit.py", title="Master Certs Audit (v1.4.8)", icon="📜"),
    ],
    "Media Services Live": [
        st.Page("apps/app.py", title="MSL5 Bulk Tools (v11.6)", icon="🚀"),
        # UPDATED MSL4 VERSION HERE
        st.Page("apps/msl4app.py", title="MSL4 Mapping Dashboard (v30.4)", icon="📊"),
    ],
    "Project Tracking": [
        st.Page("apps/tcreport.py", title="TC Report Dashboard (v1.8.6)", icon="📈"),
    ]
}

# 4. INITIALIZE NAVIGATION
pg = st.navigation(pages)

# 5. SIDEBAR BRANDING
st.sidebar.markdown(f"# 🚀 Will Toolbox v{VERSION}")
st.sidebar.caption("Unified Management Platform")
st.sidebar.caption("Created by wchavarr@akamai.com")
st.sidebar.divider()

# --- CONTEXTUAL SALESFORCE TOOLS ---
if pg.title == "TC Report Dashboard (v1.8.6)":
    st.sidebar.subheader("Salesforce Integration")
    reports = load_report_config()

    if not reports:
        st.sidebar.warning("⚠️ No reports configured.")
    else:
        if st.sidebar.button("🔄 Sync Reports Now", use_container_width=True):
            run_manual_sync()

    with st.sidebar.expander("⚙️ Manage Report IDs", expanded=not reports):
        st.markdown("### Add Report")
        new_name = st.text_input("Name", placeholder="e.g. NBA_Reports")
        new_id = st.text_input("Report ID", placeholder="18-character ID")
        
        if st.button("➕ Add to Local Config", use_container_width=True):
            if new_name and new_id:
                clean_name = "".join([c if c.isalnum() else "_" for c in new_name])
                reports[new_id] = clean_name
                save_report_config(reports)
                st.rerun()

        if reports:
            st.divider()
            for rid, rname in list(reports.items()):
                c1, c2 = st.columns([4, 1])
                c1.caption(f"**{rname}**\n{rid}")
                if c2.button("🗑️", key=rid):
                    del reports[rid]
                    save_report_config(reports)
                    st.rerun()
    st.sidebar.divider()

# 6. RUN THE SELECTED PAGE
pg.run()