import streamlit as st
import pandas as pd
import requests
from akamai.edgegrid import EdgeGridAuth
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
import urllib.parse

# --- VERSION INFO ---
VERSION = "1.3.8"

# --- SIDEBAR: DYNAMIC ACCOUNT SEARCH ---
st.sidebar.title("🔍 Account Search")
section = st.sidebar.text_input("Edgerc Section", value="default")

@st.cache_data(ttl=3600)
def search_accounts_by_name(query, section_name):
    if len(query) < 3: return {}
    BASE_URL = "https://akab-x6dk72mqodpsifbf-7lp2db7eatl5c5at.luna.akamaiapis.net"
    try:
        auth = EdgeGridAuth.from_edgerc("~/.edgerc", section_name)
        path = f"/identity-management/v3/api-clients/self/account-switch-keys?search={query}"
        response = requests.get(f"{BASE_URL}{path}", auth=auth, timeout=10)
        if response.status_code == 200:
            return {item.get('accountName'): item.get('accountSwitchKey') for item in response.json()}
    except: return {}
    return {}

account_query = st.sidebar.text_input("Type Account Name:", placeholder="e.g. NBA or Canadian")
found_accounts = search_accounts_by_name(account_query, section) if account_query else {}

if found_accounts:
    selected_name = st.sidebar.selectbox("Match Found:", list(found_accounts.keys()))
    switch_key = found_accounts[selected_name]
    st.sidebar.success(f"Linked: `{switch_key}`")
else:
    # Use text_input for manual entry, defaults to empty for Primary Account
    switch_key = st.sidebar.text_input("OR Manual Switch Key:", value="")
    if not account_query:
        st.sidebar.info("💡 Leave blank to audit the **Primary Account**.")

# --- API HELPERS ---
BASE_URL = "https://akab-x6dk72mqodpsifbf-7lp2db7eatl5c5at.luna.akamaiapis.net"

def get_detailed_data(path, switch_key, section_name, accept_header="application/json"):
    connector = "&" if "?" in path else "?"
    url = f"{BASE_URL}/{path.lstrip('/')}"
    # Only append switch key if it's not empty
    if switch_key and switch_key.strip():
        url += f"{connector}accountSwitchKey={switch_key.strip()}"
    
    headers = {"Accept": accept_header}
    try:
        auth = EdgeGridAuth.from_edgerc("~/.edgerc", section_name)
        response = requests.get(url, auth=auth, headers=headers, timeout=15)
        return response.status_code, response.json() if response.status_code == 200 else None
    except:
        return 500, None

def get_contract_list(switch_key, section_name):
    papi_headers = {"PAPI-Use-Prefixes": "false"}
    url = f"{BASE_URL}/papi/v1/contracts"
    if switch_key and switch_key.strip():
        url += f"?accountSwitchKey={switch_key.strip()}"
        
    try:
        auth = EdgeGridAuth.from_edgerc("~/.edgerc", section_name)
        res = requests.get(url, auth=auth, headers=papi_headers, timeout=10)
        if res.status_code == 200:
            data = res.json()
            return [c.get('contractId') for c in data.get("contracts", {}).get("items", [])]
    except: pass
    return []

# --- AUDIT WORKER ---
def audit_single_contract(cid, s_key, s_name):
    header = "application/vnd.akamai.cps.active-certificates.v2+json"
    path = f"cps/v2/active-certificates?contractId={cid}"
    status, raw = get_detailed_data(path, s_key, s_name, accept_header=header)
    
    results = []
    error = None
    
    if status == 403:
        error = f"🚫 {cid}: Access Denied (Scope Issue)"
    elif status == 400:
        pass 
    elif status != 200:
        error = f"⚠️ {cid}: API Error ({status})"
    elif raw and "enrollments" in raw:
        for e in raw.get('enrollments', []):
            prod = e.get('production')
            if not prod: continue
            
            cert = prod.get('primaryCertificate')
            if not cert or not cert.get('expiry'): continue
            
            expiry_dt = pd.to_datetime(cert.get('expiry'))
            results.append({
                "Common Name": e.get('csr', {}).get('cn', 'N/A'),
                "Expiry Date": expiry_dt.strftime('%Y-%m-%d'),
                "Days Left": (expiry_dt.date() - datetime.now().date()).days,
                "Contract ID": cid,
                "Slot(s)": ", ".join(map(str, e.get('productionSlots', []))),
                "ID": e.get('id'),
                "SANs": ", ".join(e.get('csr', {}).get('sans', [])) if e.get('csr', {}).get('sans') else "None"
            })
    return results, error

# --- OUTLOOK MAILTO ---
def generate_outlook_mailto(df, account_name):
    triage_df = df[df['Days Left'] <= 30].sort_values('Days Left', ascending=True)
    if triage_df.empty: return None

    subject = f"Heads-up: Akamai Certificates Expiring Soon - {account_name}"
    body = (
        f"Hello,\n\n"
        f"Our audit for '{account_name}' shows the following certificates "
        f"are scheduled to expire in 30 days or less:\n\n"
    )
    for _, row in triage_df.iterrows():
        body += (
            f"• {row['Common Name']}\n"
            f"  Expiry: {row['Expiry Date']} ({row['Days Left']} days left)\n"
            f"  Slot/ID: {row['Slot(s)']} | {row['ID']}\n\n"
        )
    body += "If you need any technical help from Akamai, just let us know.\n\nBest regards,\n[Your Name]"
    return f"mailto:?subject={urllib.parse.quote(subject)}&body={urllib.parse.quote(body)}"

# --- UI LOGIC ---
st.title("📜 Account-Wide CPS Audit")
# Updated display name logic to show "Primary Account" if no Switch Key is used
display_name = selected_name if 'selected_name' in locals() else ("Primary Account" if not switch_key else switch_key)
st.markdown(f"#### 🏢 {display_name}")
st.caption(f"Account Key: {switch_key if switch_key else 'Primary (None)'} | v{VERSION}")

if switch_key != st.session_state.get("active_key", ""):
    st.session_state["active_key"] = switch_key
    if 'master_audit_df' in st.session_state: del st.session_state['master_audit_df']

# REMOVED: disabled=not switch_key to allow Primary Account audit
if st.button("🚀 Run Master Account Audit", type="primary"):
    with st.spinner(f"Scanning contracts for {display_name}..."):
        contracts = get_contract_list(switch_key, section)
        if not contracts:
            st.error("No contracts found. Check your API permissions or Edgerc section.")
        else:
            all_certs, summary, errors = [], {}, []
            p_bar = st.progress(0)
            with ThreadPoolExecutor(max_workers=8) as ex:
                futures = {ex.submit(audit_single_contract, cid, switch_key, section): cid for cid in contracts}
                for i, f in enumerate(futures):
                    res, err = f.result()
                    if res: all_certs.extend(res)
                    if err: errors.append(err)
                    summary[futures[f]] = len(res)
                    p_bar.progress((i + 1) / len(contracts))
            p_bar.empty()
            
            master_df = pd.DataFrame(all_certs)
            if not master_df.empty:
                master_df = master_df.sort_values(by="Days Left", ascending=True)
                
            st.session_state['master_audit_df'] = master_df
            st.session_state['contract_summary'] = summary
            st.session_state['audit_errors'] = errors
            st.rerun()

# --- RESULTS ---
if 'master_audit_df' in st.session_state:
    df = st.session_state['master_audit_df']
    errors = st.session_state.get('audit_errors', [])
    if errors:
        with st.expander("⚠️ Access Warnings"):
            for e in errors: st.write(e)

    active_summary = {cid: count for cid, count in st.session_state['contract_summary'].items() if count > 0}
    if active_summary:
        st.markdown("---")
        for cid, count in active_summary.items():
            st.markdown(f"▫️ Contract `{cid}`: **{count}** certificates")
        st.markdown("---")

    if not df.empty:
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Items", len(df))
        crit = len(df[df['Days Left'] < 30])
        c2.metric("Critical (Red)", crit)
        c3.metric("Warning (Orange)", len(df[(df['Days Left'] >= 30) & (df['Days Left'] < 90)]))

        col_text, col_btn = st.columns([3, 1])
        with col_btn:
            mailto = generate_outlook_mailto(df, display_name)
            if mailto: st.link_button("📧 Triage in Outlook", mailto, type="primary", use_container_width=True)

        st.divider()
        search = st.text_input("🔍 Search Domain, Slot, or Contract:")
        df_show = df.copy()
        if search:
            df_show = df_show[df_show.astype(str).apply(lambda x: x.str.contains(search, case=False)).any(axis=1)]
        
        def style_rows(row):
            color = ''
            if row['Days Left'] < 30: color = 'background-color: #ff4b4b; color: white;'
            elif row['Days Left'] < 90: color = 'background-color: #ff8f00; color: white;'
            return [color] * len(row)

        st.dataframe(df_show.style.apply(style_rows, axis=1), use_container_width=True, hide_index=True, height=1000)
        st.download_button(f"📥 Export Sorted CSV", df_show.to_csv(index=False), f"Audit_{display_name}.csv", "text/csv")
    else:
        st.warning(f"No production certificates found for {display_name}.")