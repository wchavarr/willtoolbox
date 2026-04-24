import streamlit as st
import pandas as pd
import requests
from akamai.edgegrid import EdgeGridAuth
from urllib.parse import urljoin
from concurrent.futures import ThreadPoolExecutor

# --- VERSION INFO ---
# FILENAME: apiusersv2.py
# VERSION: 7.2
# STATUS: LOCKED / PRODUCTION
# DESCRIPTION: 
#    - Integrated Reverse Account Lookup (Search by Name).
#    - Tab 1: Detailed Permission Audit via /api-clients/{clientId}?apiAccess=true.
#    - Tab 2: Stable Credential Metadata (Status/Expiration).
# ---------------------

# --- API INITIALIZATION ---
BASE_URL = "https://akab-x6dk72mqodpsifbf-7lp2db7eatl5c5at.luna.akamaiapis.net/"
MAX_WORKERS = 15

session = requests.Session()
session.auth = EdgeGridAuth.from_edgerc("~/.edgerc", section="default")

# --- NEW: REVERSE LOOKUP LOGIC ---
@st.cache_data(ttl=3600)
def search_accounts(query):
    """Hits the Identity API to find accounts matching a name string."""
    if not query or len(query) < 3: return {}
    path = "/identity-management/v3/api-clients/self/account-switch-keys"
    url = urljoin(BASE_URL, path)
    try:
        # Use the same session to ensure auth carries over
        response = session.get(url, params={'search': query}, timeout=10)
        if response.status_code == 200:
            data = response.json()
            return {item.get('accountName'): item.get('accountSwitchKey') for item in data}
    except: return {}
    return {}

# --- SIDEBAR CONFIGURATION ---
st.sidebar.title("⚙️ Connection Settings")

# 1. Added Search UI
st.sidebar.subheader("🔍 Account Lookup")
acc_query = st.sidebar.text_input("Search Account Name:", placeholder="e.g. NBA or Canadian")
found_accounts = search_accounts(acc_query)

if found_accounts:
    selected_name = st.sidebar.selectbox("Matches Found:", list(found_accounts.keys()))
    derived_key = found_accounts[selected_name]
    st.sidebar.success(f"Linked: {selected_name}")
else:
    derived_key = "1-VJVV:1-2RBL" # Your previous default

# 2. Existing Switch Key Input (Now powered by the search)
switch_key = st.sidebar.text_input(
    "Account Switch Key", 
    value=derived_key, 
    help="Leave blank for primary account access."
)

# --- CORE UTILITY FUNCTIONS ---
def get_data(endpoint, params_override=None):
    params = {}
    if switch_key.strip():
        params['accountSwitchKey'] = switch_key.strip()
    if params_override:
        params.update(params_override)
        
    url = urljoin(BASE_URL, endpoint)
    result = session.get(url, params=params)
    result.raise_for_status()
    return result.json()

# --- DATA FETCHING: PERMISSIONS AUDIT ---
def fetch_audit_row(client):
    client_name = client.get('clientName', 'N/A')
    client_id = client.get('clientId', 'N/A')
    auth_users = client.get('authorizedUsers', [])
    primary_user = auth_users[0] if auth_users else 'N/A'
    link = f"https://control.akamai.com/apps/identity-management/#/tabs/users/list/api-client/{client_id}/details"
    
    try:
        data = get_data(f"/identity-management/v3/api-clients/{client_id}", params_override={"apiAccess": "true"})
        api_access_list = data.get('apiAccess', {}).get('apis', [])
        rows = []
        
        if not api_access_list:
            rows.append({
                'API Client': client_name, 'Portal Link': link, 'Username': primary_user, 
                'API Name': 'NONE / NO ACCESS', 'Access Level': 'N/A'
            })
        else:
            for api in api_access_list:
                rows.append({
                    'API Client': client_name, 
                    'Portal Link': link, 
                    'Username': primary_user, 
                    'API Name': api.get('apiName', 'N/A'), 
                    'Access Level': api.get('accessLevel', 'N/A')
                })
        return rows
    except Exception:
        return [{'API Client': client_name, 'Portal Link': link, 'Username': primary_user, 'API Name': 'ERROR', 'Access Level': 'ERROR'}]

# --- DATA FETCHING: CREDENTIAL METADATA ---
def fetch_credential_row(client):
    client_name = client.get('clientName', 'N/A')
    client_id = client.get('clientId', 'N/A')
    client_desc = client.get('clientDescription') or "[No Description]"
    link = f"https://control.akamai.com/apps/identity-management/#/tabs/users/list/api-client/{client_id}/details"
    
    try:
        creds = get_data(f"/identity-management/v3/api-clients/{client_id}/credentials")
        rows = []
        if not creds:
            rows.append({'API Client': client_name, 'Portal Link': link, 'Status': 'NO CREDS', 'Created On': 'N/A', 'Expires On': 'N/A', 'Description': client_desc})
        else:
            for c in creds:
                rows.append({
                    'API Client': client_name, 'Portal Link': link,
                    'Status': str(c.get('status', 'UNKNOWN')).upper(),
                    'Created On': c.get('createdOn', 'N/A'),
                    'Expires On': c.get('expiresOn', 'N/A'),
                    'Description': client_desc
                })
        return rows
    except:
        return [{'API Client': client_name, 'Portal Link': link, 'Status': 'ERR', 'Created On': 'ERR', 'Expires On': 'ERR', 'Description': client_desc}]

# --- UI CONTENT ---
st.title("🛡️ Akamai Identity Control Center")
display_acc = switch_key if switch_key.strip() else "Primary Account"
st.caption(f"Target Account: {display_acc} | v7.2 Production Build")

# State Management to prevent data mixing on account switch
if "last_switch_key" not in st.session_state: st.session_state.last_switch_key = switch_key
if st.session_state.last_switch_key != switch_key:
    st.session_state.last_switch_key = switch_key
    if 'audit_df' in st.session_state: del st.session_state['audit_df']
    if 'cred_df' in st.session_state: del st.session_state['cred_df']

if st.button('🔄 Refresh All Data', type="primary"):
    with st.spinner(f'Syncing data for {display_acc}...'):
        try:
            clients = get_data("/identity-management/v3/api-clients")
            a_res, c_res = [], []
            
            with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
                audit_f = list(ex.map(fetch_audit_row, clients))
                cred_f = list(ex.map(fetch_credential_row, clients))
                for r in audit_f: a_res.extend(r)
                for r in cred_f: c_res.extend(r)
                
            st.session_state['audit_df'] = pd.DataFrame(a_res)
            
            temp_cred_df = pd.DataFrame(c_res)
            if not temp_cred_df.empty:
                temp_cred_df['Status'] = temp_cred_df['Status'].astype(str).str.upper()
                temp_cred_df['sort_p'] = temp_cred_df['Status'].map({'ACTIVE': 0, 'INACTIVE': 1, 'NO CREDS': 2, 'ERR': 3}).fillna(4)
                temp_cred_df = temp_cred_df.sort_values(by=['API Client', 'sort_p']).drop_duplicates(subset=['API Client'], keep='first').drop(columns=['sort_p'])
            st.session_state['cred_df'] = temp_cred_df
            st.success("Synchronization Successful.")
        except Exception as e:
            st.error(f"Error accessing {display_acc}: {e}")

tab1, tab2 = st.tabs(["🔑 Permissions Audit", "📜 Credential Metadata"])

with tab1:
    if 'audit_df' in st.session_state:
        df1 = st.session_state['audit_df'].copy()
        s1 = st.text_input("🔍 Search API Name, Client, User, or Level:", placeholder="e.g. Property Manager", key="s1")
        if s1:
            search_cols = ['API Client', 'Username', 'API Name', 'Access Level']
            f1 = df1[df1[search_cols].apply(lambda row: row.astype(str).str.contains(s1, case=False).any(), axis=1)]
        else: f1 = df1

        m1, m2, m3 = st.columns(3)
        m1.metric("Visible Clients", len(f1['API Client'].unique()))
        m2.metric("Visible Permissions", len(f1))
        m3.metric("Visible RW Keys", len(f1[f1['Access Level'] == 'READ-WRITE']))
        st.divider()

        def styler_p(v): return 'color: #FF8F00; font-weight: bold' if v == 'READ-WRITE' else ''
        st.dataframe(
            f1.style.map(styler_p, subset=['Access Level']) if hasattr(f1.style, 'map') else f1.style.applymap(styler_p, subset=['Access Level']),
            use_container_width=True, hide_index=True,
            column_config={"Portal Link": st.column_config.LinkColumn(display_text="Open in Akamai")}
        )
        st.download_button(label="📥 Download Filtered Audit", data=f1.to_csv(index=False), file_name=f"audit_{display_acc}.csv", mime="text/csv")
    else: st.info("Click Refresh Data to begin.")

with tab2:
    if 'cred_df' in st.session_state:
        df2 = st.session_state['cred_df'].copy()
        s2 = st.text_input("🔍 Search Metadata:", placeholder="Search status or client name...", key="s2")
        f2 = df2[df2.apply(lambda r: s2.lower() in r.astype(str).str.lower().values, axis=1)] if s2 else df2
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Visible Clients", len(f2))
        c2.metric("Active", len(f2[f2['Status'] == 'ACTIVE']))
        c3.metric("Inactive/Missing", len(f2[f2['Status'] != 'ACTIVE']), delta_color="inverse")
        st.divider()

        def styler_s(v):
            if v == 'ACTIVE': return 'color: #28a745; font-weight: bold'
            if v in ['INACTIVE', 'ERR', 'NO CREDS']: return 'color: #dc3545;'
            return ''
            
        st.dataframe(
            f2.style.map(styler_s, subset=['Status']) if hasattr(f2.style, 'map') else f2.style.applymap(styler_s, subset=['Status']),
            use_container_width=True, hide_index=True,
            column_config={"Portal Link": st.column_config.LinkColumn(display_text="Open in Akamai")}
        )
        st.download_button(label="📥 Download Filtered Metadata", data=f2.to_csv(index=False), file_name=f"metadata_{display_acc}.csv", mime="text/csv")
    else: st.info("Click Refresh Data to begin.")