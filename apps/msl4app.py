import streamlit as st
import pandas as pd
import requests
from akamai.edgegrid import EdgeGridAuth
from urllib.parse import urljoin
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

# --- VERSION INFO ---
VERSION = "30.3"

# --- SIDEBAR: DYNAMIC ACCOUNT SEARCH ---
st.sidebar.title("🔍 Account Search")
section_name = st.sidebar.text_input("Edgerc Section", value="default")

# 1. Reverse Name Lookup Engine
@st.cache_data(ttl=3600)
def search_accounts_by_name(query, section):
    if len(query) < 3: return {}
    BASE_URL = "https://akab-x6dk72mqodpsifbf-7lp2db7eatl5c5at.luna.akamaiapis.net"
    try:
        auth = EdgeGridAuth.from_edgerc("~/.edgerc", section)
        path = f"/identity-management/v3/api-clients/self/account-switch-keys?search={query}"
        response = requests.get(f"{BASE_URL}{path}", auth=auth, timeout=10)
        if response.status_code == 200:
            return {item.get('accountName'): item.get('accountSwitchKey') for item in response.json()}
    except: return {}
    return {}

account_query = st.sidebar.text_input("Type Account Name:", placeholder="e.g. NBA or CIBC")
found_accounts = search_accounts_by_name(account_query, section_name) if account_query else {}

if found_accounts:
    selected_name = st.sidebar.selectbox("Match Found:", list(found_accounts.keys()))
    switch_key = found_accounts[selected_name]
    st.sidebar.success(f"Linked: `{switch_key}`")
else:
    # Use text_input for manual entry, defaults to empty for Primary Account
    switch_key = st.sidebar.text_input("Manual Switch Key:", value="")
    if not account_query:
        st.sidebar.info("💡 Leave blank to audit the **Primary Account**.")

# --- PARAMETER GUARD ---
if "active_msl4_key" not in st.session_state: st.session_state["active_msl4_key"] = ""
if switch_key != st.session_state["active_msl4_key"]:
    st.session_state["active_msl4_key"] = switch_key
    if "master_df" in st.session_state: del st.session_state["master_df"]

# --- UTILITY FUNCTIONS ---
def fetch_akamai_data(path, s_key, section):
    try:
        auth = EdgeGridAuth.from_edgerc("~/.edgerc", section)
        base_url = "https://akab-x6dk72mqodpsifbf-7lp2db7eatl5c5at.luna.akamaiapis.net/"
        url = urljoin(base_url, path)
        # Safely handle empty switch_key
        params = {'accountSwitchKey': s_key.strip()} if s_key and s_key.strip() else {}
        response = requests.get(url, auth=auth, params=params, timeout=15)
        return response.json() if response.status_code == 200 else None
    except: return None

def force_list(data):
    if isinstance(data, list): return data
    if isinstance(data, dict):
        for key in ['streams', 'origins', 'items', 'content']:
            if key in data and isinstance(data[key], list): return data[key]
    return []

# --- UI CONTENT ---
st.title("📊 Akamai MSL4 Mapping Dashboard")
# Updated display name logic for Primary Account
display_account = selected_name if 'selected_name' in locals() else ("Primary Account" if not switch_key else switch_key)
st.markdown(f"#### 🏢 {display_account}")
st.caption(f"Account Key: {switch_key if switch_key else 'Primary (None)'} | Build v{VERSION}")

# REMOVED: disabled=not switch_key to allow Primary Account sync
sync_button = st.button("🔄 Sync Master MSL4 Audit", type="primary")

if sync_button:
    with st.spinner(f"Analyzing MSL4 Architecture for {display_account}..."):
        # 1. Fetch Top-Level Metadata
        with ThreadPoolExecutor(max_workers=3) as executor:
            f_s = executor.submit(fetch_akamai_data, "/config-media-live/v2/msl-origin/streams", switch_key, section_name)
            f_o = executor.submit(fetch_akamai_data, "/config-media-live/v2/msl-origin/origins", switch_key, section_name)
            f_m = executor.submit(fetch_akamai_data, "/config-media-live/v2/msl-origin/streams/migrate", switch_key, section_name)
            
            streams = force_list(f_s.result())
            origins_summary = force_list(f_o.result())
            migrations = force_list(f_m.result())

        if streams:
            # 2. Map migration status
            mig_map = {str(m.get('id') or m.get('streamId', '')).strip(): {
                "type": m.get('migrationType', 'N/A'),
                "status": (m.get('migrationDetail') or {}).get('status', 'PENDING')
            } for m in migrations}

            # 3. Map hostnames to IDs
            host_to_id = {str(o.get('hostName') or o.get('primaryHostname', '')).strip().lower(): str(o.get('id', '')) 
                          for o in origins_summary if o.get('hostName') or o.get('primaryHostname')}

            # 4. Resolve Origin Details (AMD Properties)
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

            # 5. Build Final Rows
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

# --- UI DISPLAY ---
if "master_df" in st.session_state and not st.session_state.master_df.empty:
    st.divider()
    df_show = st.session_state.master_df.copy()
    c1, c2, c3 = st.columns(3)
    c1.metric("Total MSL4 Streams", len(df_show))
    migrating = len(df_show[df_show["Migration Status"] != "In MSL4"])
    c2.metric("Active Migrations", migrating)
    c3.metric("Mapped Properties", len(df_show[df_show["Akamai Property (AMD)"] != "N/A"]))

    search_q = st.text_input("🔍 Filter MSL4 Inventory:", placeholder="Search by Stream, Hostname, or Property...")
    if search_q:
        mask = df_show.astype(str).apply(lambda x: x.str.contains(search_q, case=False)).any(axis=1)
        df_show = df_show[mask]
    
    def style_status(row):
        color = ''
        if row['Migration Status'] == 'PENDING': color = 'background-color: #ff8f00; color: white;'
        elif row['Migration Status'] == 'FAILED': color = 'background-color: #ff4b4b; color: white;'
        return [color] * len(row)

    st.dataframe(df_show.style.apply(style_status, axis=1), use_container_width=True, hide_index=True, height=1000)
    st.download_button("📥 Export MSL4 Audit CSV", df_show.to_csv(index=False), f"MSL4_Audit_{display_account}.csv", "text/csv")
else:
    st.info(f"Ready. Click 'Sync Master MSL4 Audit' to analyze mapping for {display_account}.")