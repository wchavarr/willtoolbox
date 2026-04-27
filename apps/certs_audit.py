import streamlit as st
import pandas as pd
import requests
from akamai.edgegrid import EdgeGridAuth, EdgeRc
from datetime import datetime
import urllib.parse
import os
import time
import re

# --- VERSION INFO ---
VERSION = "1.4.8"

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
    """Parses the Akamai 429 response and waits the requested time."""
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

# --- API HELPERS ---
def akamai_request(method, path, switch_key, section_name, accept="application/json"):
    """Unified request handler with built-in 429 management."""
    host = get_host_from_edgerc(section_name)
    if not host: return 500, None
    
    base_url = f"https://{host}"
    connector = "&" if "?" in path else "?"
    url = f"{base_url}/{path.lstrip('/')}"
    
    if switch_key and switch_key.strip():
        url += f"{connector}accountSwitchKey={switch_key.strip()}"
    
    headers = {"Accept": accept}
    if "papi" in path: headers["PAPI-Use-Prefixes"] = "false"

    for attempt in range(3):
        try:
            auth = EdgeGridAuth.from_edgerc("~/.edgerc", section_name)
            res = requests.request(method, url, auth=auth, headers=headers, timeout=25)
            
            if res.status_code == 429:
                handle_429(res)
                continue 
            
            return res.status_code, res.json() if res.status_code == 200 else None
        except:
            return 500, None
    return 429, None

# --- SIDEBAR: SEARCH FORM ---
st.sidebar.title("🔍 Account Search")
section = st.sidebar.text_input("Edgerc Section", value="default")

# We use a form to prevent API calls while typing
with st.sidebar.form("search_tool"):
    query_input = st.text_input("Account Name:", placeholder="e.g. NBA")
    submit_search = st.form_submit_button("🔍 Find Account")

# Logic to handle the search only when button is clicked
if submit_search and query_input:
    if len(query_input) < 3:
        st.sidebar.warning("Type at least 3 characters.")
    else:
        with st.sidebar.status("Searching Akamai...", expanded=False):
            path = f"identity-management/v3/api-clients/self/account-switch-keys?search={query_input}"
            status, data = akamai_request("GET", path, "", section)
            if status == 200:
                # Save results to session state so they persist through selections
                st.session_state['search_results'] = {
                    item.get('accountName'): item.get('accountSwitchKey') for item in data
                }
            else:
                st.sidebar.error(f"Search failed (Error {status})")

# Selection logic based on saved search results
selected_name = None
switch_key = ""

if 'search_results' in st.session_state and st.session_state['search_results']:
    found = st.session_state['search_results']
    selected_name = st.sidebar.selectbox("Match Found:", list(found.keys()))
    switch_key = found[selected_name]
    st.sidebar.success(f"Linked Key: `{switch_key}`")
else:
    # If no search has been done, allow manual entry or primary account
    switch_key = st.sidebar.text_input("OR Manual Switch Key:", value="")
    if not query_input:
        st.sidebar.info("💡 Search above or leave blank for Primary Account.")

# --- UI LOGIC ---
st.title("📜 Account-Wide CPS Audit")
display_name = selected_name if selected_name else (f"Key: {switch_key}" if switch_key else "Primary Account")
st.markdown(f"#### 🏢 {display_name}")
st.caption(f"Account Key: `{switch_key if switch_key else 'Primary'}` | v{VERSION}")

# State Reset on Key Change
if "active_key" not in st.session_state: 
    st.session_state["active_key"] = switch_key

if switch_key != st.session_state["active_key"]:
    st.session_state["active_key"] = switch_key
    for k in ['master_audit_df', 'contract_summary', 'audit_errors']:
        if k in st.session_state: del st.session_state[k]
    st.rerun()

# --- RUN AUDIT ---
if st.button("🚀 Run Master Account Audit", type="primary"):
    with st.spinner(f"Auditing {display_name}..."):
        status, data = akamai_request("GET", "papi/v1/contracts", switch_key, section)
        
        if status != 200:
            st.error(f"❌ Could not retrieve contract list. Error {status}")
        else:
            contracts = [c.get('contractId') for c in data.get("contracts", {}).get("items", [])]
            all_certs, summary, errors = [], {}, []
            p_bar = st.progress(0)
            
            for i, cid in enumerate(contracts):
                st.toast(f"Checking: {cid}", icon="🔍")
                path = f"cps/v2/active-certificates?contractId={cid}"
                c_status, c_raw = akamai_request("GET", path, switch_key, section, 
                                                 accept="application/vnd.akamai.cps.active-certificates.v2+json")
                
                if c_status == 200 and c_raw and "enrollments" in c_raw:
                    for e in c_raw.get('enrollments', []):
                        prod = e.get('production')
                        if not prod: continue
                        cert = prod.get('primaryCertificate')
                        if not cert or not cert.get('expiry'): continue
                        
                        expiry_dt = pd.to_datetime(cert.get('expiry'))
                        all_certs.append({
                            "Common Name": e.get('csr', {}).get('cn', 'N/A'),
                            "Expiry Date": expiry_dt.strftime('%Y-%m-%d'),
                            "Days Left": (expiry_dt.date() - datetime.now().date()).days,
                            "Contract ID": cid,
                            "Slot(s)": ", ".join(map(str, e.get('productionSlots', []))),
                            "ID": e.get('id')
                        })
                elif c_status == 403:
                    errors.append(f"🚫 {cid}: Access Denied")
                
                p_bar.progress((i + 1) / len(contracts))
                time.sleep(1.2) 

            p_bar.empty()
            st.session_state['master_audit_df'] = pd.DataFrame(all_certs)
            st.session_state['audit_errors'] = errors
            st.rerun()

# --- DISPLAY RESULTS ---
if 'master_audit_df' in st.session_state:
    df = st.session_state['master_audit_df']
    if not df.empty:
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Certs", len(df))
        crit = len(df[df['Days Left'] < 30])
        c2.metric("Critical", crit)
        c3.metric("Warning", len(df[(df['Days Left'] >= 30) & (df['Days Left'] < 90)]))

        def style_rows(row):
            if row['Days Left'] < 30: return ['background-color: #ff4b4b; color: white'] * len(row)
            if row['Days Left'] < 90: return ['background-color: #ff8f00; color: white'] * len(row)
            return [''] * len(row)

        st.dataframe(df.style.apply(style_rows, axis=1), use_container_width=True, hide_index=True)
    else: st.warning("No production certificates found.")