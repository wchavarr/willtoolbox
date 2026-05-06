import streamlit as st
import pandas as pd
import requests
from akamai.edgegrid import EdgeGridAuth, EdgeRc
from urllib.parse import urljoin
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import os
import time
import re

# --- VERSION INFO ---
VERSION = "30.6"

# --- HELPER: GET HOST ---
def get_host_from_edgerc(section_name):
    try:
        edgerc = EdgeRc(os.path.expanduser("~/.edgerc"))
        return edgerc.get(section_name, 'host')
    except:
        return "akab-x6dk72mqodpsifbf-7lp2db7eatl5c5at.luna.akamaiapis.net" # Fallback to your working host

# --- RATE LIMIT HANDLER ---
def handle_429(response):
    wait_time = 25  
    try:
        error_data = response.json()
        detail = error_data.get("detail", "")
        match = re.search(r'after: (\d+)', detail)
        if match:
            wait_time = int(match.group(1)) + 3 
    except: pass
    st.toast(f"🛑 API Limit Reached. Waiting {wait_time}s...", icon="🚨")
    time.sleep(wait_time)
    return True

# --- CORE FETCH ENGINE (from 30.3) ---
def fetch_akamai_data(path, s_key, section):
    host = get_host_from_edgerc(section)
    base_url = f"https://{host}/"
    url = urljoin(base_url, path)
    params = {'accountSwitchKey': s_key.strip()} if s_key and s_key.strip() else {}
    
    for attempt in range(2):
        try:
            auth = EdgeGridAuth.from_edgerc("~/.edgerc", section)
            response = requests.get(url, auth=auth, params=params, timeout=15)
            if response.status_code == 429:
                handle_429(response)
                continue
            return response.json() if response.status_code == 200 else None
        except: return None
    return None

def force_list(data):
    if isinstance(data, list): return data
    if isinstance(data, dict):
        for key in ['streams', 'origins', 'items', 'content']:
            if key in data and isinstance(data[key], list): return data[key]
    return []

# --- SIDEBAR: SAFE SEARCH ---
st.sidebar.title("🔍 Account Search")
section_name = st.sidebar.text_input("Edgerc Section", value="default")

with st.sidebar.form("msl4_search"):
    account_query = st.text_input("Type Account Name:", placeholder="e.g. NBA")
    submit_search = st.form_submit_button("🔍 Find Account")

if submit_search and account_query:
    if len(account_query) >= 3:
        path = f"/identity-management/v3/api-clients/self/account-switch-keys?search={account_query}"
        data = fetch_akamai_data(path, "", section_name)
        if data:
            st.session_state['msl4_results'] = {item.get('accountName'): item.get('accountSwitchKey') for item in data}
        else:
            st.sidebar.error("No accounts found.")

selected_name = None
switch_key = ""
if 'msl4_results' in st.session_state and st.session_state['msl4_results']:
    res = st.session_state['msl4_results']
    selected_name = st.sidebar.selectbox("Match Found:", list(res.keys()))
    switch_key = res[selected_name]
else:
    switch_key = st.sidebar.text_input("Manual Switch Key:", value="")

# --- UI CONTENT ---
st.title("📊 Akamai MSL4 Mapping Dashboard")
display_account = selected_name if selected_name else ("Primary Account" if not switch_key else switch_key)
st.markdown(f"#### 🏢 {display_account}")
st.caption(f"Account Key: {switch_key if switch_key else 'Primary'} | v{VERSION}")

# Reset logic
if "active_msl4_key" not in st.session_state: st.session_state["active_msl4_key"] = ""
if switch_key != st.session_state["active_msl4_key"]:
    st.session_state["active_msl4_key"] = switch_key
    if "master_df" in st.session_state: del st.session_state["master_df"]

sync_button = st.button("🔄 Sync Master MSL4 Audit", type="primary")

if sync_button:
    with st.spinner(f"Analyzing Architecture..."):
        with ThreadPoolExecutor(max_workers=3) as executor:
            f_s = executor.submit(fetch_akamai_data, "/config-media-live/v2/msl-origin/streams", switch_key, section_name)
            f_o = executor.submit(fetch_akamai_data, "/config-media-live/v2/msl-origin/origins", switch_key, section_name)
            f_m = executor.submit(fetch_akamai_data, "/config-media-live/v2/msl-origin/streams/migrate", switch_key, section_name)
            
            streams = force_list(f_s.result())
            origins_summary = force_list(f_o.result())
            migrations = force_list(f_m.result())

        if streams:
            mig_map = {str(m.get('id') or m.get('streamId', '')).strip(): {
                "type": m.get('migrationType', 'N/A'),
                "status": (m.get('migrationDetail') or {}).get('status', 'PENDING')
            } for m in migrations}

            host_to_id = {str(o.get('hostName') or o.get('primaryHostname', '')).strip().lower(): str(o.get('id', '')) 
                          for o in origins_summary if o.get('hostName') or o.get('primaryHostname')}

            target_ids = {str(s.get('originId') or host_to_id.get(str(s.get('originHostName', '')).strip().lower())) 
                          for s in streams if s.get('originId') or s.get('originHostName')}
            target_ids.discard('None')

            def get_origin_details(oid):
                detail = fetch_akamai_data(f"/config-media-live/v2/msl-origin/origins/{oid}", switch_key, section_name)
                if detail and isinstance(detail, dict):
                    p_names = [p.get('propertyName') for p in detail.get('amdProperties', []) if p.get('propertyName')]
                    return str(oid), {"host": detail.get('hostName', 'N/A'), "prop": ", ".join(p_names) if p_names else "N/A"}
                return oid, None

            with ThreadPoolExecutor(max_workers=10) as executor:
                results = list(executor.map(get_origin_details, target_ids))
                origin_cache = {oid: data for oid, data in results if data}

            rows = []
            for s in streams:
                sid = str(s.get('streamId') or s.get('id', '')).strip()
                shost_raw = s.get('originHostName', '')
                oid = str(s.get('originId') or host_to_id.get(shost_raw.strip().lower()) or 'N/A')
                det = origin_cache.get(oid, {"host": shost_raw or "N/A", "prop": "N/A"})
                mig = mig_map.get(sid, {"type": "None", "status": "In MSL4"})
                
                rows.append({
                    "Stream Name": s.get('streamName') or s.get('name') or "Unknown",
                    "Stream ID": sid,
                    "Origin ID": oid,
                    "Origin Hostname": det['host'],
                    "Akamai Property (AMD)": det['prop'],
                    "Migration Status": mig['status'],
                    "Type": mig['type']
                })
            st.session_state.master_df = pd.DataFrame(rows)
            st.rerun()

# --- DISPLAY ---
if "master_df" in st.session_state:
    df = st.session_state.master_df
    st.metric("Total Streams", len(df))
    st.dataframe(df, use_container_width=True, hide_index=True)