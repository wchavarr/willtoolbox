import streamlit as st
import pandas as pd
import requests
import time
import io

# --- App Configuration ---
# st.set_page_config(page_title="Automated MSL5 Tools", page_icon="🚀", layout="wide")

# --- 1. SESSION STATE & CALLBACKS ---
if "file_uploader_key" not in st.session_state:
    st.session_state.file_uploader_key = 0
if "confirm_push" not in st.session_state:
    st.session_state.confirm_push = False
if "editor_results" not in st.session_state:
    st.session_state.editor_results = []
if "editor_df" not in st.session_state:
    st.session_state.editor_df = None
if "master_inventory" not in st.session_state:
    st.session_state.master_inventory = None

def clear_all_data():
    """Complete Reset of App State"""
    keys_to_clear = ["editor_df", "editor_results", "confirm_push", "master_inventory"]
    for key in keys_to_clear:
        if key in st.session_state:
            st.session_state[key] = [] if "results" in key else None
    st.session_state.file_uploader_key += 1
    st.session_state.confirm_push = False
    st.toast("🧹 All data cleared!")

def fetch_data():
    """Live Fetch from Akamai API"""
    token = st.session_state.get('token', '').replace("Bearer ", "").strip()
    if not token:
        st.error("JWT Token required in sidebar.")
        return
    url = "https://gateway.mslapis.net/api/v1/streams"
    askey = st.session_state.get('askey', '')
    if askey: url += f"?accountSwitchKey={askey}"
    headers = {"Authorization": f"Bearer {token}"}
    with st.spinner("Fetching live data from Akamai..."):
        try:
            res = requests.get(url, headers=headers)
            if res.status_code == 200:
                raw = res.json()
                flat = []
                for s in raw:
                    ips = s.get("allowed_ips", [])
                    flat.append({
                        "stream_id": s.get("stream_id"),
                        "stream_name": s.get("description"),
                        "format": s.get("format"),
                        "contract_id": s.get("contract_id"),
                        "group_id": s.get("group_id"),
                        "ingest_loc": s.get("ingest_location"),
                        "ingest_auth": s.get("ingest_auth"),
                        "allowed_ips": "ALL" if not ips else ",".join(ips),
                        "retention": s.get("archiving", {}).get("automatic_purge", {}).get("retention_days", 0),
                        "no_archive": s.get("archiving", {}).get("no_archive", True)
                    })
                st.session_state.editor_df = pd.DataFrame(flat)
                st.success(f"Fetched {len(flat)} streams.")
            else: st.error(f"Fetch Failed: {res.status_code}")
        except Exception as e: st.error(f"Error: {e}")

# --- 2. GLOBAL UI ELEMENTS ---
st.title("🚀 Automated MSL5 Tools")

with st.expander("⚖️ Legal Disclaimer & Terms of Use", expanded=False):
    st.markdown("""
    This tool is provided "as-is" solely for the purpose of assisting with configuration within the MSL5 ecosystem. 
    It is **not** an official Akamai product and is not covered by standard Akamai Support (SLA). 
    """)

col_consent, col_clear = st.columns([4, 1])
with col_consent:
    consent = st.checkbox("I have read and agree to the Legal Disclaimer and Terms of Use.")
with col_clear:
    st.button("🧹 Clear All Data", on_click=clear_all_data, use_container_width=True)

st.error("**🛑 CRITICAL SECURITY NOTICE:** Run LOCALLY only. DO NOT use the 'Deploy' button.")

# --- 3. SIDEBAR ---
with st.sidebar:
    st.header("🔑 Authentication")
    st.session_state.token = st.text_input("JWT Token", type="password")
    st.session_state.askey = st.text_input("Account Switch Key", placeholder="1-XXXX:1-YYYY")
    st.divider()
    st.caption("v11.6 | Production Locked")

# --- 4. TABS ---
tab_create, tab_edit, tab_explorer, tab_csv = st.tabs([
    "🚀 Bulk Creator", 
    "✏️ Stream Editor", 
    "🔍 Origin Explorer", 
    "📂 Bulk Stream CSV Editor"
])

# ==========================================
# TAB 1: BULK CREATOR
# ==========================================
with tab_create:
    if consent:
        col_doc1, col_doc2, col_doc3 = st.columns(3)
        with col_doc1:
            with st.expander("📖 Creator Reference (1)"):
                st.markdown("* **stream_name**: Lowercase.\n* **format**: HLS, DASH, CMAF.\n* **contract_id**: e.g. 1-ABC12.")
        with col_doc2:
            with st.expander("📖 Creator Reference (2)"):
                st.markdown("* **archive_ret**: Days (0=Off).\n* **origin_id**: UUID/Numeric.\n* **ingest_auth**: OFF/SIGNATURE.")
        with col_doc3:
            with st.expander("📍 Locations"):
                st.markdown("* Chicago: `us_ord`\n* London: `gb_lon`\n* Tokyo: `jp_tyo_3`.")

        st.divider()
        up_file = st.file_uploader("Upload Creator CSV", type=["csv"], key=f"up_{st.session_state.file_uploader_key}")
        
        if up_file:
            cdf = pd.read_csv(up_file)
            st.dataframe(cdf, use_container_width=True)
            if st.button("▶️ Run Bulk Creation", use_container_width=True):
                token = st.session_state.get('token', '').replace("Bearer ", "").strip()
                if not token: st.error("Token Required.")
                else:
                    log_win = st.container(height=300)
                    for idx, row in cdf.iterrows():
                        ret_val = str(row.get('archive_ret', 0))
                        no_archive, retention = (True, 1) if ret_val in ['0', 'nan', ''] else (False, int(float(ret_val)))
                        payload = {
                            "description": str(row['stream_name']).strip().lower(),
                            "format": str(row['format']).strip().upper(),
                            "contract_id": str(row['contract_id']).strip(),
                            "group_id": str(row['group_id']).strip(),
                            "cptag": str(row['cp_tag']).strip(),
                            "ingest_location": str(row['ingest_loc']).strip().upper(),
                            "origin_id": str(row['origin_id']).strip(),
                            "encoder_version": str(row['encoder_ver']).strip().upper(),
                            "ingest_auth": str(row['ingest_auth']).strip().upper(),
                            "allowed_ips": [] if str(row.get('allowed_ips', '')).upper() in ['ALL', ''] else [str(row['allowed_ips'])],
                            "archiving": {"automatic_purge": {"retention_days": retention}, "no_archive": no_archive}
                        }
                        url = "https://gateway.mslapis.net/api/v1/streams"
                        if st.session_state.askey: url += f"?accountSwitchKey={st.session_state.askey}"
                        try:
                            r = requests.post(url, json=payload, headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
                            if r.status_code in [201, 202]: log_win.success(f"Created: {row['stream_name']}")
                            else: log_win.error(f"Failed: {row['stream_name']} ({r.status_code})")
                        except Exception as e: log_win.error(f"Error: {e}")
                    st.success("🏁 Creation Complete.")

# ==========================================
# TAB 2: STREAM EDITOR (LOCKED)
# ==========================================
with tab_edit:
    if consent:
        st.subheader("✏️ Stream Editor")
        col_ed1, col_ed2, col_ed3 = st.columns(3)
        with col_ed1:
            with st.expander("📖 Editor Info"):
                st.markdown("1. Fetch live data.\n2. Edit values.\n3. Locked: ID, Contract, Format.")
        
        st.divider()
        btn_col1, btn_col2 = st.columns([2, 1])
        with btn_col1:
            if st.button("📡 Fetch Data from Akamai", use_container_width=True):
                st.session_state.editor_results = [] 
                fetch_data()
        with btn_col2:
            if st.session_state.editor_df is not None:
                st.download_button(label="📥 Download CSV", data=st.session_state.editor_df.to_csv(index=False).encode('utf-8'), file_name="streams.csv", mime="text/csv", use_container_width=True)

        if st.session_state.editor_df is not None:
            if st.session_state.editor_results:
                st.text_area("Logs", value="\n".join(st.session_state.editor_results), height=150)
            
            edited_df = st.data_editor(
                st.session_state.editor_df,
                use_container_width=True, hide_index=True,
                disabled=["stream_id", "contract_id", "ingest_loc", "format"],
                key="msl_editor_widget"
            )

            edit_state = st.session_state.get("msl_editor_widget", {})
            edited_rows = edit_state.get("edited_rows", {})
            if len(edited_rows) > 0:
                st.warning(f"⚠️ {len(edited_rows)} modified.")
                if not st.session_state.get('confirm_push', False):
                    if st.button("⬆️ Push Changes", type="primary", use_container_width=True):
                        st.session_state.confirm_push = True
                        st.rerun()
                
                if st.session_state.get('confirm_push', False):
                    st.subheader("Confirm update?")
                    c1, c2 = st.columns(2)
                    with c1:
                        if st.button("✅ Yes, Sync Now", type="primary", use_container_width=True):
                            token = st.session_state.token.replace("Bearer ", "").strip()
                            st.session_state.editor_results = []
                            for idx_str in edited_rows.keys():
                                row = edited_df.iloc[int(idx_str)]
                                payload = {
                                    "description": str(row['stream_name']).strip().lower(),
                                    "format": str(row['format']).upper(),
                                    "contract_id": str(row['contract_id']),
                                    "group_id": str(row['group_id']),
                                    "ingest_location": str(row['ingest_loc']).upper(),
                                    "ingest_auth": str(row['ingest_auth']).upper(),
                                    "allowed_ips": [] if str(row['allowed_ips']).upper() in ["ALL", ""] else [x.strip() for x in str(row['allowed_ips']).split(",")],
                                    "archiving": {"automatic_purge": {"retention_days": int(row['retention'])}, "no_archive": bool(row['no_archive'])}
                                }
                                url = f"https://gateway.mslapis.net/api/v1/streams/{row['stream_id']}"
                                if st.session_state.askey: url += f"?accountSwitchKey={st.session_state.askey}"
                                try:
                                    r = requests.put(url, json=payload, headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
                                    st.session_state.editor_results.append(f"{'✅' if r.status_code < 300 else '❌'} {row['stream_name']}")
                                except Exception as e: st.session_state.editor_results.append(f"ERR: {e}")
                            st.session_state.confirm_push = False
                            fetch_data()
                            st.rerun()
                    with c2:
                        if st.button("❌ No, Cancel", use_container_width=True):
                            st.session_state.confirm_push = False
                            st.rerun()

# ==========================================
# TAB 3: ORIGIN EXPLORER
# ==========================================
with tab_explorer:
    if consent:
        st.subheader("🔍 Origin & Stream Inventory")
        if st.button("📊 Generate Mapping Report", type="primary", use_container_width=True):
            token = st.session_state.get('token', '').replace("Bearer ", "").strip()
            headers = {"Authorization": f"Bearer {token}"}
            with st.spinner("Fetching..."):
                try:
                    orig_url = "https://gateway.mslapis.net/api/v1/origins"
                    strm_url = "https://gateway.mslapis.net/api/v1/streams"
                    if st.session_state.askey:
                        orig_url += f"?accountSwitchKey={st.session_state.askey}"
                        strm_url += f"?accountSwitchKey={st.session_state.askey}"
                    o_res, s_res = requests.get(orig_url, headers=headers), requests.get(strm_url, headers=headers)
                    if o_res.status_code == 200 and s_res.status_code == 200:
                        origins = o_res.json()
                        streams = s_res.json()
                        inv = []
                        for o in origins:
                            o_id = str(o.get("id") or o.get("origin_id", "")).strip()
                            o_name = o.get("host_name") or o.get("name") or "Unnamed"
                            tied = [s for s in streams if str(s.get("origin_id", "")).strip() == o_id]
                            stream_count = len(tied) # RE-ADDED COUNT
                            if not tied: inv.append({"Origin Host Name": o_name, "Origin ID": o_id, "Stream Count": 0, "Stream Name": "--- EMPTY ---", "Stream ID": "N/A"})
                            else:
                                for s in tied: inv.append({"Origin Host Name": o_name, "Origin ID": o_id, "Stream Count": stream_count, "Stream Name": s.get("description"), "Stream ID": s.get("stream_id")})
                        st.session_state.master_inventory = pd.DataFrame(inv)
                except Exception as e: st.error(f"Error: {e}")

        if st.session_state.get("master_inventory") is not None:
            q = st.text_input("🎯 Filter by Origin Name:", key="origin_filter")
            df = st.session_state.master_inventory
            if q: df = df[df['Origin Host Name'].str.contains(q, case=False, na=False)]
            st.dataframe(df, use_container_width=True, hide_index=True)

# ==========================================
# TAB 4: 📂 BULK STREAM CSV EDITOR (LOCKED)
# ==========================================
with tab_csv:
    if consent:
        st.subheader("📂 Bulk Stream CSV Editor")
        
        # --- RED SAFETY NOTE ---
        st.error("⚠️ **CRITICAL:** For best performance and safety, please upload a CSV containing **ONLY** the specific rows that require updates.")
        
        st.markdown("1. Fetch/Download from **Stream Editor**. 2. Edit Excel. 3. Upload here.")
        up = st.file_uploader("Upload Edited CSV", type="csv", key="csv_sync_uploader")
        
        if up:
            udf = pd.read_csv(up)
            if 'stream_id' not in udf.columns: 
                st.error("❌ Missing 'stream_id'")
            else:
                st.dataframe(udf, use_container_width=True, hide_index=True)
                
                if st.button("🔥 Start Bulk Sync", type="primary", use_container_width=True):
                    token = st.session_state.get('token', '').replace("Bearer ", "").strip()
                    askey = st.session_state.get('askey', '')
                    
                    # --- LIVE UI ELEMENTS ---
                    bar = st.progress(0)
                    status_text = st.empty()
                    log_display = st.empty() 
                    live_logs = ""
                    
                    for i, row in udf.iterrows():
                        status_text.text(f"Processing {i+1} of {len(udf)}: {row['stream_name']}...")
                        
                        payload = {
                            "description": str(row['stream_name']).strip().lower(),
                            "format": str(row['format']).upper(),
                            "contract_id": str(row['contract_id']),
                            "group_id": str(row['group_id']),
                            "ingest_location": str(row['ingest_loc']).upper(),
                            "ingest_auth": str(row['ingest_auth']).upper(),
                            "allowed_ips": [] if str(row.get('allowed_ips', 'ALL')).upper() in ["ALL", ""] else [x.strip() for x in str(row['allowed_ips']).split(",")],
                            "archiving": {
                                "automatic_purge": {"retention_days": int(row.get('retention', 0))}, 
                                "no_archive": bool(row.get('no_archive', False))
                            }
                        }
                        
                        url = f"https://gateway.mslapis.net/api/v1/streams/{row['stream_id']}"
                        if askey: url += f"?accountSwitchKey={askey}"
                        
                        try:
                            r = requests.put(url, json=payload, headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
                            if r.status_code < 300:
                                live_logs += f"✅ SUCCESS: {row['stream_name']}\n"
                            else:
                                live_logs += f"❌ FAILED: {row['stream_name']} (Error {r.status_code})\n"
                        except Exception as e:
                            live_logs += f"⚠️ ERROR: {row['stream_id']} - {e}\n"
                        
                        # Update UI
                        log_display.text_area("Live Sync Report", value=live_logs, height=300)
                        bar.progress((i + 1) / len(udf))
                        
                    st.success("🏁 Bulk Sync Task Finished!")
                    status_text.empty()