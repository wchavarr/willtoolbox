import streamlit as st
import pandas as pd
import requests
import json
import io

# --- 1. CONFIGURACIÓN DE PÁGINA Y ESTADO ---
st.set_page_config(page_title="MSL5 Bulk Suite v13.4", layout="wide")

if "file_uploader_key" not in st.session_state: st.session_state.file_uploader_key = 0
if "editor_df" not in st.session_state: st.session_state.editor_df = None
if "master_inventory" not in st.session_state: st.session_state.master_inventory = None

def clear_all_data():
    """Reseteo total de la aplicación"""
    st.session_state.editor_df = None
    st.session_state.master_inventory = None
    st.session_state.file_uploader_key += 1
    st.toast("| Sweep complete! 🧹")

# --- 2. FUNCIONES DE APOYO (API WRAPPERS) ---

def get_origin_stats(token, askey):
    """
    Motor Central v13.4:
    1. Genera el mapa determinístico para nombres -> IDs.
    2. Cuenta cuántos streams existen en Akamai para validar carga.
    """
    headers = {"Authorization": f"Bearer {token}"}
    o_url = "https://gateway.mslapis.net/api/v1/origins"
    s_url = "https://gateway.mslapis.net/api/v1/streams"
    if askey:
        o_url += f"?accountSwitchKey={askey}"
        s_url += f"?accountSwitchKey={askey}"
    
    try:
        o_res = requests.get(o_url, headers=headers)
        s_res = requests.get(s_url, headers=headers)
        
        if o_res.status_code == 200 and s_res.status_code == 200:
            o_map = {}
            for o in o_res.json():
                o_id = str(o.get('id') or o.get('origin_id'))
                h_name = str(o.get('host_name')).lower().strip()
                c_id = str(o.get('contract_id')).upper().strip()
                ingest = str(o.get('ingest_location')).upper().strip()
                
                # Fingerprint Logic: CONTRATO|INGEST|SHORTNAME
                try:
                    parts = h_name.split('.')
                    main_part = parts[0]
                    short = main_part.split('-')[-1] if '-' in main_part else main_part
                except:
                    short = h_name.split('.')[0]
                
                o_map[f"{c_id}|{ingest}|{short}"] = o_id
                o_map[h_name] = o_id # Soporte para FQDN

            # Conteo de carga real
            origin_counts = {}
            for s in s_res.json():
                oid = str(s.get('origin_id'))
                origin_counts[oid] = origin_counts.get(oid, 0) + 1
            
            return o_map, origin_counts
        return None, None
    except:
        return None, None

# --- 3. BARRA LATERAL ---
with st.sidebar:
    st.header("🔑 Authentication")
    token_input = st.text_input("JWT Token", type="password")
    askey_input = st.text_input("Account Switch Key", placeholder="1-XXXX:1-YYYY")
    st.divider()
    st.button("🧹 Clear All Data", on_click=clear_all_data, use_container_width=True)
    st.caption("v13.4 | Precision & Search Enabled")

# --- 4. UI PRINCIPAL ---
st.title("🚀 Automated MSL5 Tools")
t1, t2, t3, t4, t5 = st.tabs([
    "🚀 Bulk Stream Creator", 
    "🏗️ Bulk Origin Creator", 
    "✏️ Stream Editor", 
    "🔍 OrigintoStream Explorer", 
    "📂 Bulk CSV Sync"
])

# ==========================================
# TAB 1: BULK STREAM CREATOR
# ==========================================
with t1:
    st.subheader("🚀 Bulk Stream Creator")
    st.caption("Step 1: Validate Capacity -> Step 2: Push to Akamai")
    
    up_file = st.file_uploader("Upload Stream CSV", type=["csv"], key=f"up_st_{st.session_state.file_uploader_key}")
    
    if up_file:
        cdf = pd.read_csv(up_file)
        st.dataframe(cdf, use_container_width=True)
        
        # --- PASO 1: VALIDACIÓN ---
        st.write("### 🔍 Step 1: Pre-Flight Check")
        if st.button("Validate IDs & Origin Load Factor", use_container_width=True):
            tk = token_input.replace("Bearer ", "").strip()
            ak = askey_input.strip()
            
            if not tk:
                st.error("Missing JWT Token in Sidebar.")
            else:
                with st.spinner("Analyzing Akamai Infrastructure..."):
                    o_map, current_counts = get_origin_stats(tk, ak)
                
                if o_map:
                    batch_counts = {}
                    id_to_name = {}
                    for _, row in cdf.iterrows():
                        raw_o = str(row['origin_id']).strip().lower()
                        c_id = str(row['contract_id']).upper().strip()
                        ing = str(row['ingest_loc']).upper().strip()
                        
                        res_id = raw_o if raw_o.isdigit() else o_map.get(f"{c_id}|{ing}|{raw_o}", o_map.get(raw_o))
                        if res_id:
                            batch_counts[res_id] = batch_counts.get(res_id, 0) + 1
                            id_to_name[res_id] = raw_o
                    
                    st.divider()
                    has_critical = False
                    for oid, b_count in batch_counts.items():
                        total = current_counts.get(oid, 0) + b_count
                        if total > 10:
                            st.error(f"🚨 **CRITICAL OVERLOAD:** Origin `{id_to_name.get(oid)}` (ID: {oid}) will have **{total}** streams.")
                            has_critical = True
                        elif total > 8:
                            st.warning(f"⚠️ **HIGH LOAD:** Origin `{id_to_name.get(oid)}` (ID: {oid}) will reach **{total}** streams.")
                    
                    if not has_critical: st.success("✅ All target origins are within safe limits.")

                    st.write("#### 📊 Mapping Summary")
                    summary = [{"Origin Name": id_to_name.get(oid), "ID": oid, "In Akamai": current_counts.get(oid,0), "In CSV": b_count, "Total": current_counts.get(oid,0)+b_count, "Status": "❌ OVERLOAD" if (current_counts.get(oid,0)+b_count) > 10 else "✅ OK"} for oid, b_count in batch_counts.items()]
                    st.table(summary)
                else: st.error("Verification failed. Check your Token/SwitchKey.")

        # --- PASO 2: EJECUCIÓN ---
        st.divider()
        st.write("### 🚀 Step 2: Push to Akamai")
        st.info("The Run button will enable once you acknowledge the load report.")
        proceed_safety = st.checkbox("I verify that the IDs and Load Factors are correct.")
        
        if st.button("▶️ Run Bulk Stream Creation", type="primary", use_container_width=True, disabled=not proceed_safety):
            tk, ak = token_input.replace("Bearer ", "").strip(), askey_input.strip()
            o_map, _ = get_origin_stats(tk, ak)
            
            log_win = st.container(height=400)
            for idx, row in cdf.iterrows():
                raw_o = str(row['origin_id']).strip().lower()
                c_id = str(row['contract_id']).upper().strip()
                ing = str(row['ingest_loc']).upper().strip()
                res_id = raw_o if raw_o.isdigit() else o_map.get(f"{c_id}|{ing}|{raw_o}", o_map.get(raw_o))

                if not res_id:
                    log_win.error(f"❌ Skipped '{row['stream_name']}': Origin ID not found.")
                    continue

                payload = {
                    "description": str(row['stream_name']).strip().lower(),
                    "format": str(row['format']).strip().upper(),
                    "contract_id": c_id,
                    "group_id": str(row['group_id']).strip(),
                    "cptag": str(row['cp_tag']).strip(),
                    "ingest_location": ing,
                    "origin_id": res_id,
                    "encoder_version": str(row.get('encoder_ver', 'GENERIC')).upper(),
                    "ingest_auth": "AKAMAI_SSO" if str(row.get('ingest_auth', 'OFF')).upper() == 'OFF' else str(row['ingest_auth']).upper(),
                    "allowed_ips": [] if str(row.get('allowed_ips','ALL')).upper() in ['ALL',''] else [i.strip() for i in str(row['allowed_ips']).split(',')],
                    "archiving": {"automatic_purge": {"retention_days": int(row.get('archive_ret', 0))}, "no_archive": False if int(row.get('archive_ret', 0)) > 0 else True}
                }
                if 'backup_ingest_loc' in row and pd.notna(row['backup_ingest_loc']):
                    payload["backup_ingest_location"] = str(row['backup_ingest_loc']).strip().upper()

                url = f"https://gateway.mslapis.net/api/v1/streams" + (f"?accountSwitchKey={ak}" if ak else "")
                try:
                    r = requests.post(url, json=payload, headers={"Authorization": f"Bearer {tk}", "Content-Type": "application/json"})
                    if r.status_code < 300: log_win.success(f"✅ Created: {payload['description']}")
                    else: log_win.error(f"❌ Error {r.status_code} on {payload['description']}")
                except: log_win.error(f"⚠️ Request Failed for {row['stream_name']}")

# ==========================================
# TAB 2: BULK ORIGIN CREATOR
# ==========================================
with t2:
    up_orig = st.file_uploader("Upload Origin CSV", type=["csv"], key="up_orig_csv")
    if up_orig:
        odf = pd.read_csv(up_orig)
        st.dataframe(odf, use_container_width=True)
        if st.button("🔥 Create Origins", type="primary", use_container_width=True):
            tk, ak = token_input.replace("Bearer ", "").strip(), askey_input.strip()
            log_o = st.container(height=300)
            for idx, row in odf.iterrows():
                raw_h, loc = str(row['host_name']).strip().lower(), str(row['ingest_location']).upper()
                fn_h = f"{loc.replace('_','-').lower()}-{raw_h}.mslorigin.net" if ".mslorigin.net" not in raw_h else raw_h
                payload = {"contract_id": str(row['contract_id']), "cptag": str(row['cptag']), "group_id": str(row['group_id']), "host_name": fn_h, "ingest_location": loc, "backup_ingest_location": str(row['backup_ingest_location']).upper()}
                url = "https://gateway.mslapis.net/api/v1/origins"
                if ak: url += f"?accountSwitchKey={ak}"
                r = requests.post(url, json=payload, headers={"Authorization": f"Bearer {tk}", "Content-Type": "application/json"})
                if r.status_code < 300: log_o.success(f"✅ Created: {fn_h}")
                else: log_o.error(f"❌ Failed {fn_h}: {r.text}")

# ==========================================
# TAB 3: STREAM EDITOR
# ==========================================
with t3:
    if st.button("📡 Fetch Data", use_container_width=True):
        tk, ak = token_input.replace("Bearer ", "").strip(), askey_input.strip()
        url = "https://gateway.mslapis.net/api/v1/streams"
        if ak: url += f"?accountSwitchKey={ak}"
        res = requests.get(url, headers={"Authorization": f"Bearer {tk}"})
        if res.status_code == 200:
            flat = [{"stream_id": s['stream_id'], "stream_name": s['description'], "format": s['format'], "cp_tag": s['cptag'], "contract_id": s['contract_id'], "ingest_loc": s['ingest_location'], "allowed_ips": "ALL" if not s.get('allowed_ips') else ",".join(s['allowed_ips']), "retention": s.get('archiving', {}).get('automatic_purge', {}).get('retention_days', 0), "no_archive": s.get('archiving', {}).get('no_archive', True)} for s in res.json()]
            st.session_state.editor_df = pd.DataFrame(flat)
            st.rerun()
    if st.session_state.editor_df is not None:
        cfg = {"stream_id": st.column_config.TextColumn("ID", width=280), "stream_name": st.column_config.TextColumn("Name", width=None)}
        edt = st.data_editor(st.session_state.editor_df, use_container_width=True, hide_index=True, column_config=cfg, key="edt_w")
        if st.button("⬆️ Push Changes", type="primary", use_container_width=True):
            tk, ak = token_input.replace("Bearer ", "").strip(), askey_input.strip()
            ch = st.session_state.edt_w.get("edited_rows", {})
            for i_str, r_ch in ch.items():
                row = edt.iloc[int(i_str)]
                ips = [] if str(row['allowed_ips']).upper() in ["ALL", ""] else [x.strip() for x in str(row['allowed_ips']).split(",") if x.strip()]
                payload = {"description": str(row['stream_name']).lower(), "format": str(row['format']).upper(), "allowed_ips": ips, "archiving": {"automatic_purge": {"retention_days": int(row['retention'])}, "no_archive": bool(row['no_archive'])}}
                u = f"https://gateway.mslapis.net/api/v1/streams/{row['stream_id']}"
                if ak: u += f"?accountSwitchKey={ak}"
                requests.put(u, json=payload, headers={"Authorization": f"Bearer {tk}", "Content-Type": "application/json"})
            st.success("✅ Sync OK")

# ==========================================
# TAB 4: OrigintoStream Explorer
# ==========================================
with t4:
    st.subheader("🔍 Origin-to-Stream Inventory")
    st.caption("v13.4 | Search across Origins and Streams")
    
    if st.button("📊 Load / Refresh Mapping Report", use_container_width=True):
        tk, ak = token_input.replace("Bearer ", "").strip(), askey_input.strip()
        if not tk:
            st.error("JWT Token Required in Sidebar")
        else:
            headers = {"Authorization": f"Bearer {tk}"}
            ou, su = "https://gateway.mslapis.net/api/v1/origins", "https://gateway.mslapis.net/api/v1/streams"
            if ak: 
                ou += f"?accountSwitchKey={ak}"
                su += f"?accountSwitchKey={ak}"
            with st.spinner("Building Origin-to-Stream Map..."):
                o_res, s_res = requests.get(ou, headers=headers), requests.get(su, headers=headers)
                if o_res.status_code == 200 and s_res.status_code == 200:
                    origins, streams, inv = o_res.json(), s_res.json(), []
                    for o in origins:
                        o_id = str(o.get('id') or o.get('origin_id'))
                        tied = [s for s in streams if str(s.get('origin_id')) == o_id]
                        for s in tied:
                            inv.append({
                                "Origin Name": o.get('host_name'),
                                "Origin ID": o_id,
                                "Primary": o.get('ingest_location'),
                                "Stream Name": s.get('description'),
                                "Stream ID": str(s.get('stream_id'))
                            })
                    st.session_state.master_inventory = pd.DataFrame(inv)
                    st.success(f"Successfully mapped {len(inv)} active streams.")
                else: st.error("Failed to fetch data.")

    if st.session_state.master_inventory is not None:
        st.divider()
        search_query = st.text_input("🎯 Filter Report", placeholder="Search by Name, ID, Hostname...")
        df_display = st.session_state.master_inventory.copy()
        if search_query:
            mask = df_display.apply(lambda row: row.astype(str).str.contains(search_query, case=False).any(), axis=1)
            df_display = df_display[mask]
        explorer_cfg = {
            "Origin ID": st.column_config.TextColumn("Origin ID", width=250),
            "Stream ID": st.column_config.TextColumn("Stream ID", width=250),
            "Origin Name": st.column_config.TextColumn("Origin Hostname", width=None),
            "Stream Name": st.column_config.TextColumn("Stream Name", width=None)
        }
        st.dataframe(df_display, use_container_width=True, hide_index=True, column_config=explorer_cfg)
        csv_data = df_display.to_csv(index=False).encode('utf-8')
        st.download_button(label="📥 Export Current View to CSV", data=csv_data, file_name="akamai_origintostream_report.csv", mime="text/csv", use_container_width=True)

# ==========================================
# TAB 5: BULK CSV SYNC
# ==========================================
with t5:
    st.subheader("📂 Bulk Stream CSV Sync")
    up_sync = st.file_uploader("Upload CSV for Bulk Sync", type=["csv"], key="up_sync_csv")
    if up_sync:
        sdf = pd.read_csv(up_sync)
        st.dataframe(sdf, use_container_width=True, hide_index=True)
        if st.button("🔥 Start Bulk Sync", type="primary", use_container_width=True):
            tk, ak = token_input.replace("Bearer ", "").strip(), askey_input.strip()
            log_s = st.container(height=350)
            for i, row in sdf.iterrows():
                ips = str(row.get('allowed_ips', 'ALL')).strip().upper()
                ip_list = [] if ips in ['ALL', ''] else [x.strip() for x in ips.split(',') if x.strip()]
                payload = {
                    "description": str(row['stream_name']).strip().lower(),
                    "format": str(row['format']).upper(),
                    "allowed_ips": ip_list,
                    "archiving": {"automatic_purge": {"retention_days": int(row.get('retention', 0))}, "no_archive": bool(row.get('no_archive', False))}
                }
                url = f"https://gateway.mslapis.net/api/v1/streams/{str(row['stream_id']).strip()}" + (f"?accountSwitchKey={ak}" if ak else "")
                r = requests.put(url, json=payload, headers={"Authorization": f"Bearer {tk}", "Content-Type": "application/json"})
                if r.status_code < 300: log_s.success(f"✅ Updated: {payload['description']}")
                else: log_s.error(f"❌ Failed {payload['description']}: {r.status_code}")
            st.success("🏁 Bulk CSV Sync Finished!")