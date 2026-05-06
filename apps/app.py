import streamlit as st
import pandas as pd
import requests
import time
import io

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
    st.toast("UI Cleared 🧹")

def fetch_data():
    """Live Fetch from Akamai API for Editor"""
    token = st.session_state.get('token', '').replace("Bearer ", "").strip()
    if not token:
        st.error("JWT Token required in sidebar.")
        return
    url = "https://gateway.mslapis.net/api/v1/streams"
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
                        "cp_tag": s.get("cptag", "N/A"),
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

col_consent, col_clear = st.columns([4, 1])
with col_consent:
    consent = st.checkbox("I have read and agree to the Legal Disclaimer and Terms of Use.")
with col_clear:
    st.button("🧹 Clear All Data", on_click=clear_all_data, use_container_width=True)

# --- 3. SIDEBAR ---
with st.sidebar:
    st.header("🔑 Authentication")
    st.session_state.token = st.text_input("JWT Token", type="password")
    st.divider()
    st.caption("v12.2 | Wide-ID Optimized")

# --- 4. TABS ---
tab_create, tab_origin, tab_edit, tab_explorer, tab_csv = st.tabs([
    "🚀 Bulk Stream Creator", 
    "🏗️ Bulk Origin Creator", 
    "✏️ Stream Editor", 
    "🔍 Origin Explorer", 
    "📂 Bulk CSV Sync"
])

# ==========================================
# TAB 1: BULK STREAM CREATOR
# ==========================================
with tab_create:
    if consent:
        st.subheader("🚀 Bulk Stream Creator")
        up_file = st.file_uploader("Upload Stream Creator CSV", type=["csv"], key=f"up_st_{st.session_state.file_uploader_key}")
        if up_file:
            cdf = pd.read_csv(up_file)
            st.dataframe(cdf, use_container_width=True)
            if st.button("▶️ Run Bulk Stream Creation", use_container_width=True):
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
                        try:
                            r = requests.post(url, json=payload, headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
                            if r.status_code in [201, 202]: log_win.success(f"Created: {row['stream_name']}")
                            else: log_win.error(f"Failed: {row['stream_name']} ({r.status_code})")
                        except Exception as e: log_win.error(f"Error: {e}")

# ==========================================
# TAB 2: BULK ORIGIN CREATOR
# ==========================================
with tab_origin:
    if consent:
        st.subheader("🏗️ Bulk Origin Creator")
        up_orig = st.file_uploader("Upload Origin CSV", type=["csv"], key="up_origin_csv")
        if up_orig:
            odf = pd.read_csv(up_orig)
            st.dataframe(odf, use_container_width=True)
            if st.button("🔥 Start Bulk Origin Creation", type="primary", use_container_width=True):
                token = st.session_state.get('token', '').replace("Bearer ", "").strip()
                if not token: st.error("JWT Token Required.")
                else:
                    log_orig = st.container(height=300)
                    for idx, row in odf.iterrows():
                        payload = {
                            "contract_id": str(row['contract_id']).strip(),
                            "cptag": str(row['cptag']).strip(),
                            "group_id": str(row['group_id']).strip(),
                            "host_name": str(row['host_name']).strip(),
                            "ingest_location": str(row['ingest_location']).strip().upper(),
                            "backup_ingest_location": str(row['backup_ingest_location']).strip().upper()
                        }
                        url = "https://gateway.mslapis.net/api/v1/origins"
                        try:
                            r = requests.post(url, json=payload, headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
                            if r.status_code in [200, 201, 202]: log_orig.success(f"✅ Created Origin: {row['host_name']}")
                            else: log_orig.error(f"❌ Failed: {row['host_name']} ({r.status_code})")
                        except Exception as e: log_orig.error(f"⚠️ Error: {e}")

# ==========================================
# TAB 3: STREAM EDITOR (ADJUSTED WIDTHS)
# ==========================================
with tab_edit:
    if consent:
        st.subheader("✏️ Stream Editor")
        if st.button("📡 Fetch Data from Akamai", use_container_width=True):
            st.session_state.editor_results = [] 
            fetch_data()

        if st.session_state.editor_df is not None:
            # CONFIGURACIÓN PARA SOPORTAR UUIDs LARGOS
            editor_config = {
                "stream_id": st.column_config.TextColumn("ID", width=300), # Espacio para UUID
                "stream_name": st.column_config.TextColumn("Stream Name", width=None), # Flexible
                "format": st.column_config.TextColumn("Format", width=80),
                "cp_tag": st.column_config.TextColumn("CP Tag 🔒", width=100),
                "contract_id": st.column_config.TextColumn("Contract", width=110),
                "ingest_loc": st.column_config.TextColumn("Loc", width=90),
                "retention": st.column_config.NumberColumn("Days", width=70),
            }
            
            edited_df = st.data_editor(
                st.session_state.editor_df,
                use_container_width=True, hide_index=True,
                disabled=["stream_id", "contract_id", "ingest_loc", "format", "cp_tag"],
                column_config=editor_config,
                key="msl_editor_widget"
            )

            edit_state = st.session_state.get("msl_editor_widget", {})
            edited_rows = edit_state.get("edited_rows", {})
            if len(edited_rows) > 0:
                st.warning(f"⚠️ {len(edited_rows)} modified.")
                if st.button("⬆️ Push Changes", type="primary", use_container_width=True):
                    token = st.session_state.token.replace("Bearer ", "").strip()
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
                        requests.put(url, json=payload, headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
                    st.success("Changes pushed. Re-fetching...")
                    fetch_data()
                    st.rerun()

# ==========================================
# TAB 4: ORIGIN EXPLORER (WIDE-ID FIX)
# ==========================================
with tab_explorer:
    if consent:
        st.subheader("🔍 Origin & Stream Inventory")
        if st.button("📊 Generate Mapping Report", type="primary", use_container_width=True):
            token = st.session_state.get('token', '').replace("Bearer ", "").strip()
            headers = {"Authorization": f"Bearer {token}"}
            with st.spinner("Analyzing Origin Infrastructure..."):
                try:
                    orig_url, strm_url = "https://gateway.mslapis.net/api/v1/origins", "https://gateway.mslapis.net/api/v1/streams"
                    o_res, s_res = requests.get(orig_url, headers=headers), requests.get(strm_url, headers=headers)
                    if o_res.status_code == 200 and s_res.status_code == 200:
                        origins, streams, inv = o_res.json(), s_res.json(), []
                        for o in origins:
                            o_id, o_name = str(o.get("id") or o.get("origin_id", "")).strip(), o.get("host_name") or o.get("name") or "Unnamed"
                            p_loc, b_loc = o.get("ingest_location") or "N/A", o.get("backup_ingest_location") or "N/A"
                            tied = [s for s in streams if str(s.get("origin_id", "")).strip() == o_id]
                            if not tied:
                                inv.append({"Origin Name": o_name, "Origin ID": o_id, "Primary Ingest": p_loc, "Backup Ingest": b_loc, "Stream Count": 0, "Stream Name": "--- EMPTY ---", "Stream ID": "N/A"})
                            else:
                                for s in tied:
                                    inv.append({"Origin Name": o_name, "Origin ID": o_id, "Primary Ingest": p_loc, "Backup Ingest": b_loc, "Stream Count": len(tied), "Stream Name": s.get("description"), "Stream ID": s.get("stream_id")})
                        st.session_state.master_inventory = pd.DataFrame(inv)
                except Exception as e: st.error(f"Error: {e}")

        if st.session_state.get("master_inventory") is not None:
            # CONFIGURACIÓN OPTIMIZADA PARA UUIDs Y NOMBRES
            exp_config = {
                "Origin Name": st.column_config.TextColumn(width=None), # Flexible
                "Origin ID": st.column_config.TextColumn(width=280),   # UUID Ancho
                "Primary Ingest": st.column_config.TextColumn(width=100), # Squeezed
                "Backup Ingest": st.column_config.TextColumn(width=100),  # Squeezed
                "Stream Count": st.column_config.NumberColumn(width=70),  # Squeezed
                "Stream Name": st.column_config.TextColumn(width=None), # Flexible
                "Stream ID": st.column_config.TextColumn(width=280),   # UUID Ancho
            }
            df = st.session_state.master_inventory
            q = st.text_input("🎯 Filter Report:", placeholder="Search...")
            if q: df = df[df.apply(lambda row: row.astype(str).str.contains(q, case=False).any(), axis=1)]
            st.dataframe(df, use_container_width=True, hide_index=True, column_config=exp_config)

# ==========================================
# TAB 5: BULK CSV SYNC
# ==========================================
with tab_csv:
    if consent:
        st.subheader("📂 Bulk Stream CSV Editor")
        up = st.file_uploader("Upload Edited CSV", type="csv", key="csv_sync_uploader")
        if up:
            udf = pd.read_csv(up)
            st.dataframe(udf, use_container_width=True, hide_index=True)
            if st.button("🔥 Start Bulk Sync", type="primary", use_container_width=True):
                token = st.session_state.get('token', '').replace("Bearer ", "").strip()
                log_display, live_logs = st.empty(), ""
                for i, row in udf.iterrows():
                    payload = {
                        "description": str(row['stream_name']).strip().lower(),
                        "format": str(row['format']).upper(),
                        "contract_id": str(row['contract_id']),
                        "group_id": str(row['group_id']),
                        "ingest_location": str(row['ingest_loc']).upper(),
                        "ingest_auth": str(row['ingest_auth']).upper(),
                        "allowed_ips": [] if str(row.get('allowed_ips', 'ALL')).upper() in ["ALL", ""] else [x.strip() for x in str(row['allowed_ips']).split(",")],
                        "archiving": {"automatic_purge": {"retention_days": int(row.get('retention', 0))}, "no_archive": bool(row.get('no_archive', False))}
                    }
                    url = f"https://gateway.mslapis.net/api/v1/streams/{row['stream_id']}"
                    requests.put(url, json=payload, headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
                    live_logs += f"✅ Processed: {row['stream_name']}\n"
                    log_display.text_area("Live Sync Report", value=live_logs, height=300)
                st.success("🏁 Bulk Sync Task Finished!")