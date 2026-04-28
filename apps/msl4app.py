import streamlit as st
import pandas as pd
import requests
from akamai.edgegrid import EdgeGridAuth, EdgeRc
import os
import time
import re

# --- VERSION INFO ---
VERSION = "30.4"

# --- HELPER: GET HOST FROM EDGERC ---
def get_host_from_edgerc(section_name):
    try:
        edgerc = EdgeRc(os.path.expanduser("~/.edgerc"))
        return edgerc.get(section_name, 'host')
    except Exception as e:
        st.error(f"Error reading .edgerc section [{section_name}]: {e}")
        return None

# --- RATE LIMIT HANDLER ---
def handle_429(response):
    wait_time = 25  
    try:
        error_data = response.json()
        detail = error_data.get("detail", "")
        match = re.search(r'after: (\d+)', detail)
        if match:
            wait_time = int(match.group(1)) + 3 
    except:
        pass
    
    msg = f"🛑 API Limit Reached. Akamai says wait {wait_time}s. Pausing..."
    st.toast(msg, icon="🚨")
    with st.status(msg, expanded=False):
        time.sleep(wait_time)
    return True

# --- UNIFIED API ENGINE ---
def akamai_request(method, path, switch_key, section_name):
    host = get_host_from_edgerc(section_name)
    if not host: return 500, None
    
    base_url = f"https://{host}"
    connector = "&" if "?" in path else "?"
    url = f"{base_url}/{path.lstrip('/')}"
    
    if switch_key and switch_key.strip():
        url += f"{connector}accountSwitchKey={switch_key.strip()}"
    
    for attempt in range(3):
        try:
            auth = EdgeGridAuth.from_edgerc("~/.edgerc", section_name)
            res = requests.request(method, url, auth=auth, timeout=25)
            
            if res.status_code == 429:
                handle_429(res)
                continue 
            
            return res.status_code, res.json() if res.status_code == 200 else None
        except:
            return 500, None
    return 429, None

# --- SIDEBAR: SEARCH FORM ---
st.sidebar.title("🔍 MSL4 Search")
section = st.sidebar.text_input("Edgerc Section", value="default")

with st.sidebar.form("msl4_account_search"):
    query_input = st.text_input("Account Name:", placeholder="Search for customer...")
    submit_search = st.form_submit_button("🔍 Find Account")

if submit_search and query_input:
    if len(query_input) < 3:
        st.sidebar.warning("Type at least 3 characters.")
    else:
        with st.sidebar.status("Searching...", expanded=False):
            path = f"identity-management/v3/api-clients/self/account-switch-keys?search={query_input}"
            status, data = akamai_request("GET", path, "", section)
            if status == 200:
                st.session_state['msl4_search_results'] = {
                    item.get('accountName'): item.get('accountSwitchKey') for item in data
                }
            else:
                st.sidebar.error(f"Search failed (Error {status})")

# Selection logic
selected_name = None
switch_key = ""

if 'msl4_search_results' in st.session_state and st.session_state['msl4_search_results']:
    found = st.session_state['msl4_search_results']
    selected_name = st.sidebar.selectbox("Select Account:", list(found.keys()))
    switch_key = found[selected_name]
else:
    switch_key = st.sidebar.text_input("OR Manual Switch Key:", value="")

# --- MAIN UI ---
st.title("📊 MSL4 Mapping Dashboard")
display_name = selected_name if selected_name else (f"Key: {switch_key}" if switch_key else "Primary Account")
st.markdown(f"#### 🏢 {display_name}")
st.caption(f"Account Key: `{switch_key if switch_key else 'Primary'}` | v{VERSION}")

# State Reset on Key Change
if "msl4_active_key" not in st.session_state: 
    st.session_state["msl4_active_key"] = switch_key

if switch_key != st.session_state["msl4_active_key"]:
    st.session_state["msl4_active_key"] = switch_key
    if 'msl4_data' in st.session_state: del st.session_state['msl4_data']
    st.rerun()

# --- MSL4 LOGIC (Locked Version) ---
if st.button("🚀 Fetch MSL4 Mappings", type="primary"):
    with st.spinner(f"Querying MSL4 for {display_name}..."):
        # Note: Replace this path with your specific locked MSL4 reporting path
        path = "msl-reporting/v1/mappings" 
        status, data = akamai_request("GET", path, switch_key, section)
        
        if status == 200:
            st.session_state['msl4_data'] = data
            st.success("Data retrieved successfully.")
        else:
            st.error(f"Error {status}: Could not fetch MSL4 data.")

if 'msl4_data' in st.session_state:
    st.write("### Mapping Results")
    st.json(st.session_state['msl4_data'])