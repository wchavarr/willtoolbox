import streamlit as st
import pandas as pd
import requests
from akamai.edgegrid import EdgeGridAuth, EdgeRc
import os
import time
import re

# --- VERSION INFO ---
VERSION = "2.3"

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
        # Busca el tiempo de espera sugerido por Akamai
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
def akamai_request(method, path, section_name):
    """Unified request handler with built-in 429 management."""
    host = get_host_from_edgerc(section_name)
    if not host: return 500, None
    
    url = f"https://{host}/{path.lstrip('/')}"
    
    for attempt in range(3):
        try:
            auth = EdgeGridAuth.from_edgerc("~/.edgerc", section_name)
            res = requests.request(method, url, auth=auth, timeout=20)
            
            if res.status_code == 429:
                handle_429(res)
                continue 
            
            return res.status_code, res.json() if res.status_code == 200 else None
        except Exception as e:
            return 500, None
    return 429, None

# --- UI ---
st.title("🔍 Account Switch Finder")
st.markdown("Search for Akamai accounts to retrieve their **Account Switch Keys**.")

# --- SIDEBAR SEARCH FORM (SAFE MODE) ---
st.sidebar.title("Settings")
section = st.sidebar.text_input("Edgerc Section", value="default")

with st.sidebar.form("finder_form"):
    search_query = st.text_input("Account Name or ID:", placeholder="e.g. NBA")
    submit_search = st.form_submit_button("🔍 Search Accounts")

# --- SEARCH LOGIC ---
if submit_search and search_query:
    if len(search_query) < 3:
        st.warning("Please enter at least 3 characters to search.")
    else:
        with st.spinner(f"Searching for '{search_query}'..."):
            path = f"identity-management/v3/api-clients/self/account-switch-keys?search={search_query}"
            status, data = akamai_request("GET", path, section)
            
            if status == 200:
                st.session_state['finder_results'] = data
            elif status == 429:
                st.error("Rate limit exceeded. Please try again in a few seconds.")
            else:
                st.error(f"Search failed with error code: {status}")

# --- DISPLAY RESULTS ---
if 'finder_results' in st.session_state:
    results = st.session_state['finder_results']
    
    if results:
        st.write(f"### Found {len(results)} matches:")
        
        # DataFrame para visualización tabular
        df = pd.DataFrame(results)
        df = df.rename(columns={
            'accountName': 'Account Name',
            'accountSwitchKey': 'Switch Key'
        })
        
        st.dataframe(df[['Account Name', 'Switch Key']], use_container_width=True, hide_index=True)
        
        # Lista de copiado rápido
        st.divider()
        st.write("#### Quick Copy List")
        for item in results:
            col1, col2 = st.columns([2, 3])
            col1.write(f"**{item['accountName']}**")
            col2.code(item['accountSwitchKey'], language="text")
            
        if st.button("Clear Results"):
            if 'finder_results' in st.session_state:
                del st.session_state['finder_results']
            st.rerun()
    else:
        st.info("No accounts found matching that query.")

st.caption(f"v{VERSION} | Unified Akamai Identity Engine")