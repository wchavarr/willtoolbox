import streamlit as st
import pandas as pd
import requests
from akamai.edgegrid import EdgeGridAuth
from urllib.parse import urljoin

# --- VERSION INFO ---
VERSION = "2.2"

# --- UTILITY FUNCTIONS ---
def fetch_akamai_data(path, section, params=None):
    """Base fetcher for Identity API calls."""
    try:
        auth = EdgeGridAuth.from_edgerc("~/.edgerc", section)
        base_url = "https://akab-x6dk72mqodpsifbf-7lp2db7eatl5c5at.luna.akamaiapis.net/"
        url = urljoin(base_url, path)
        response = requests.get(url, auth=auth, params=params, timeout=12)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"API Error: {e}")
        return None

@st.cache_data(ttl=3600)
def get_account_matches(query, section):
    """Dynamic search logic with caching to prevent redundant API hits."""
    if len(query) < 3: return []
    path = "/identity-management/v3/api-clients/self/account-switch-keys"
    results = fetch_akamai_data(path, section, params={'search': query})
    
    if isinstance(results, list): return results
    if isinstance(results, dict) and 'accountSwitchKeys' in results:
        return results['accountSwitchKeys']
    return []

# --- UI SETUP ---
st.title("🔍 Account Switch Finder")
st.caption(f"Identity Discovery Engine v{VERSION}")

with st.sidebar:
    st.header("Search Settings")
    section_name = st.sidebar.text_input("Edgerc Section", value="default")
    st.divider()
    st.info("💡 Type at least 3 characters to trigger the lookup.")

# --- DYNAMIC SEARCH LOGIC ---
acc_search_input = st.text_input(
    "Enter Account Name (or portion):", 
    placeholder="e.g. Canadian, NBA, Iberdrola...",
    help="The tool will search for matches as you type (3+ chars)."
)

if acc_search_input:
    with st.spinner(f"Searching for '{acc_search_input}'..."):
        accounts = get_account_matches(acc_search_input, section_name)
        
        if accounts:
            st.success(f"Found {len(accounts)} matching accounts.")
            
            # Convert to DataFrame for the main view
            df = pd.DataFrame(accounts)
            
            # Create a selection dropdown for detail view
            account_names = df['accountName'].tolist()
            selected_acc = st.selectbox("🎯 Select an account to view details:", ["-- Select One --"] + account_names)
            
            if selected_acc != "-- Select One --":
                # Get specific data for selected account
                row = df[df['accountName'] == selected_acc].iloc[0]
                
                st.divider()
                c1, c2 = st.columns(2)
                with c1:
                    st.text_input("Full Account Name", value=row['accountName'], disabled=True)
                with c2:
                    # Clearer display for the Switch Key
                    st.text_input("Account Switch Key (ASK)", value=row['accountSwitchKey'], help="Copy this for use in other tools.")
                
                st.info("ℹ️ Copy the key above to use in the Master Certs Audit or MSL4 Mapping tools.")
                st.divider()

            # Display the full table for bulk browsing
            st.subheader("📚 All Matches")
            display_cols = [c for c in ["accountName", "accountSwitchKey"] if c in df.columns]
            st.dataframe(df[display_cols], use_container_width=True, hide_index=True)
            
            st.download_button(
                "📥 Export Match List", 
                df[display_cols].to_csv(index=False), 
                f"Account_Search_{acc_search_input}.csv", 
                "text/csv"
            )
        else:
            if len(acc_search_input) >= 3:
                st.warning("No matching accounts found. Try a different keyword.")
else:
    st.info("Start typing an account name above to discover Switch Keys.")

# --- SHARED FOOTER ---
st.sidebar.markdown("---")
st.sidebar.caption(f"Finder Build: {VERSION}")