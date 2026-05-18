import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import re

# --- VERSIONING ---
VERSION = "2.0.6"

# --- SIDEBAR: PROJECT CONFIGURATION ---
st.sidebar.title(f"TC Report Tool v{VERSION}")
st.sidebar.header("📋 Project Settings")

uploaded_file = st.sidebar.file_uploader("Upload Salesforce Report (Excel or CSV)", type=["csv", "xlsx"])

if 'start_date' not in st.session_state:
    st.session_state.start_date = datetime(2026, 4, 1).date()
if 'end_date' not in st.session_state:
    st.session_state.end_date = datetime(2026, 6, 30).date()

budget_input = st.sidebar.number_input("Project Budgeted Hours", min_value=1, value=120, step=10)
start_date_input = st.sidebar.date_input("Project Start Date", value=st.session_state.start_date)
end_date_input = st.sidebar.date_input("Project End Date", value=st.session_state.end_date)

st.session_state.start_date = start_date_input
st.session_state.end_date = end_date_input

# --- CATEGORIZATION SETTINGS ---
SECURITY_FULL_NAMES = [
    'Cesar Castro', 'Mario Alvarado', 'David Pereira', 
    'Austin Thornburg', 'Valeria Mora', 'Justin Rummel', 'Ericka Ramirez'
]

ACTIVITY_MAP = {
    'Datastream': ['datastream', r'\bds\b'],
    'Meetings & Syncs': ['meeting', 'call', 'sync', 'touch-base', 'iat', 'huddle', 'discussion', 'review', 'standup'],
    'WAF, Bot & Rate Control': ['waf', 'rate control', 'bot', 'bmp', 'spike', 'hits', 'attack', 'scr', 'cl', 'client list', 'match targets'],
    'Config review/change': ['amd', 'dai', 'cm ', 're-integration', 'config', 'properties review', 'token'],
    'ULL & Prefetching': ['ull', 'prefetching', 'breadcrumbs'],
    'mTLS & Identity': ['mtls', 'identity', 'tls'],
    'Support, Admin & Tracking': ['case', 'ticket', 'tracking', 'kanban', 'prep', 'investigation', 'planning'],
    'Hotlinking & MP4': ['hotlink', 'mp4'],
    'Synamedia & Piracy': ['synamedia', 'watermarking', 'piracy'],
    'TrafficPeak & Reporting': ['trafficpeak', 'reporting', 'trends'],
    'Peer Review': ['peer review', 'pr ', 'pr:']
}

def get_team(owner):
    o = str(owner).lower()
    for sec_name in SECURITY_FULL_NAMES:
        if sec_name.lower() in o:
            return 'Security'
    return 'Delivery'

def get_activities(notes, owner):
    n = str(notes).lower()
    team = get_team(owner)
    parts = re.split(r'[,|]', n)
    found_categories = set()
    for part in parts:
        part = part.strip()
        if not part or part == '-': continue
        if any(k in part for k in ['peer review', 'pr ', 'pr:']):
            found_categories.add('Peer Review')
            continue
        if any(re.search(k, part) for k in ['datastream', r'\bds\b']):
            found_categories.add('Datastream')
            continue
        waf_k = ['waf', 'rate control', 'bot', 'bmp', 'spike', 'hits', 'attack', 'scr', 'cl', 'client list', 'match targets']
        if any(k in part for k in waf_k) or (team == 'Security' and 'review' in part):
            found_categories.add('WAF, Bot & Rate Control')
            continue
        conf_k = ['amd', 'dai', 'cm ', 're-integration', 'config', 'properties review', 'token']
        if any(k in part for k in conf_k) or (team == 'Delivery' and 'review' in part):
            found_categories.add('Config review/change')
            continue
        if any(k in part for k in ['meeting', 'call', 'sync', 'touch-base', 'iat', 'huddle', 'discussion', 'standup']):
            found_categories.add('Meetings & Syncs')
        elif any(k in part for k in ['ull', 'prefetching', 'breadcrumbs']):
            found_categories.add('ULL & Prefetching')
        elif any(k in part for k in ['mtls', 'identity', 'tls']):
            found_categories.add('mTLS & Identity')
        elif any(k in part for k in ['case', 'ticket', 'tracking', 'kanban', 'prep', 'investigation', 'planning']):
            found_categories.add('Support, Admin & Tracking')
        elif any(k in part for k in ['hotlink', 'mp4']):
            found_categories.add('Hotlinking & MP4')
        elif any(k in part for k in ['synamedia', 'watermarking', 'piracy']):
            found_categories.add('Synamedia & Piracy')
        elif any(k in part for k in ['trafficpeak', 'reporting', 'trends']):
            found_categories.add('TrafficPeak & Reporting')
    return list(found_categories) if found_categories else ['General / Uncategorized']

if uploaded_file:
    try:
        df_raw = pd.read_excel(uploaded_file, header=None) if uploaded_file.name.endswith('.xlsx') else pd.read_csv(uploaded_file, header=None)
        is_tabular = False
        header_row = 0
        for r in range(min(20, len(df_raw))):
            row_str = " ".join([str(x) for x in df_raw.iloc[r].tolist()])
            if any(k in row_str for k in ["Total Hours", "Timecard Id", "Owner Name"]):
                header_row = r; is_tabular = True; break
        
        if is_tabular:
            df = df_raw.copy()
            df.columns = [str(c).strip() for c in df.iloc[header_row]]
            df = df[header_row + 1:].reset_index(drop=True)
            df['Total Hours'] = pd.to_numeric(df['Total Hours'], errors='coerce').fillna(0)
            df['Date'] = pd.to_datetime(df['End Date'], errors='coerce')
            df = df.rename(columns={'Timecard: Owner Name': 'Owner', 'Milestone: Milestone Name': 'Milestone'})
            note_cols = [c for c in df.columns if 'Notes' in str(c)]
            df['Notes'] = df[note_cols].fillna('').agg(' | '.join, axis=1)
            processed_df = df[['Date', 'Owner', 'Milestone', 'Total Hours', 'Notes']].dropna(subset=['Date'])
            processed_df['Team'] = processed_df['Owner'].apply(get_team)

            # Calculations
            today = datetime.now().date()
            project_total_used = processed_df['Total Hours'].sum()
            total_project_days = max((end_date_input - start_date_input).days, 1)
            total_working_days = len(pd.bdate_range(start=today + timedelta(days=1), end=end_date_input)) if today < end_date_input else 0
            weeks_rem_decimal = max(total_working_days / 5, 0.1)
            days_passed_hist = max(((processed_df['Date'].max().date() if not processed_df.empty else today) - start_date_input).days, 1)
            ongoing_burn_rate = project_total_used / (days_passed_hist / 7)
            hours_remaining = budget_input - project_total_used
            required_weekly_rate = max(hours_remaining / weeks_rem_decimal, 0.0)
            projected_total = ongoing_burn_rate * (total_project_days / 7)

            # --- UI HEADER & KPI CARDS ---
            st.title(f"📊 Project Dashboard")
            usage_pct = (project_total_used / budget_input) * 100
            
            if usage_pct >= 100:
                st.error(f"🛑 **Project in overages:** {usage_pct:.1f}% of budget consumed.")
            elif usage_pct >= 80:
                st.error(f"⚠️ **Possible overages:** {usage_pct:.1f}% of budget consumed.")
            else:
                st.success(f"✅ **Budget Healthy:** {usage_pct:.1f}% of budget consumed.")
            
            if total_working_days > 0:
                st.info(f"🗓️ **Time Remaining:** {total_working_days} Business Days ({total_working_days // 5} weeks left)")
            
            ci1, ci2 = st.columns(2)
            ci1.info(f"**Actual Usage:** {project_total_used:.2f} / {budget_input} Hours")
            ci2.warning(f"**Target Burn:** {required_weekly_rate:.2f} hrs/week required to stay on budget")
            
            kpi1, kpi2, kpi3, kpi4 = st.columns(4)
            kpi1.metric("Project Total Used", f"{project_total_used:.2f} hrs")
            kpi2.metric("Hours Left", f"{hours_remaining:.2f}")
            kpi3.metric("Burn Rate", f"{ongoing_burn_rate:.2f} /wk")
            kpi4.metric("Projected Total", f"{projected_total:.1f}", f"{projected_total - budget_input:+.1f}")
            st.markdown("---")

            # Team Filter
            all_owners = sorted(processed_df['Owner'].unique())
            selected_owners = st.sidebar.multiselect("Filter Individuals:", options=all_owners, default=all_owners)
            filtered_df = processed_df[processed_df['Owner'].isin(selected_owners)].copy()

            # --- TABS ---
            tab1, tab2, tab3, tab4 = st.tabs(["🔥 Burn Rate Analysis", "📊 Distribution", "🛡️ Security vs Delivery", "📝 Activity Log"])
            
            with tab1:
                chart_df = filtered_df.groupby('Date')['Total Hours'].sum().reset_index().sort_values('Date')
                chart_df['Cumulative'] = chart_df['Total Hours'].cumsum()
                fig = go.Figure()
                fig.add_trace(go.Scatter(x=chart_df['Date'], y=chart_df['Cumulative'], name='Ongoing Usage', line=dict(color='red', width=4)))
                fig.add_trace(go.Scatter(x=[start_date_input, end_date_input], y=[0, budget_input], name='Budget Target', line=dict(color='gray', dash='dash')))
                st.plotly_chart(fig, use_container_width=True)

            with tab2:
                col1, col2 = st.columns(2)
                col1.plotly_chart(px.bar(filtered_df.groupby('Owner')['Total Hours'].sum().reset_index(), x='Total Hours', y='Owner', orientation='h', title="Hours by Individual"), use_container_width=True)
                col2.plotly_chart(px.pie(filtered_df.groupby('Milestone')['Total Hours'].sum().reset_index(), values='Total Hours', names='Milestone', title="Hours by Milestone"), use_container_width=True)

            with tab3:
                st.subheader("🛡️ Security vs Delivery Analysis")
                ana_rows = []
                for _, row in filtered_df.iterrows():
                    acts = get_activities(row['Notes'], row['Owner'])
                    share = row['Total Hours'] / len(acts)
                    for a in acts:
                        ana_rows.append({'Owner': row['Owner'], 'Team': row['Team'], 'Activity': a, 'Hours': share})
                ana_df = pd.DataFrame(ana_rows)
                pivot_df = ana_df.pivot_table(index='Activity', columns='Team', values='Hours', aggfunc='sum', fill_value=0)
                for col in ['Security', 'Delivery']:
                    if col not in pivot_df.columns: pivot_df[col] = 0.0
                pivot_df['Total'] = pivot_df['Security'] + pivot_df['Delivery']
                pivot_df = pivot_df.round(2)
                names_ser = ana_df.groupby('Activity')['Owner'].apply(lambda x: ', '.join(sorted(x.unique())))
                pivot_df.insert(0, 'Team Members', names_ser)
                sorted_pivot = pivot_df.sort_values('Total', ascending=False)
                total_row = pd.DataFrame({'Team Members': '---', 'Security': round(sorted_pivot['Security'].sum(), 2), 'Delivery': round(sorted_pivot['Delivery'].sum(), 2), 'Total': round(sorted_pivot['Total'].sum(), 2)}, index=['TOTAL'])
                st.dataframe(pd.concat([sorted_pivot, total_row[sorted_pivot.columns]]), use_container_width=True)
                st.plotly_chart(px.bar(ana_df.groupby(['Team', 'Activity'])['Hours'].sum().reset_index().round(2), x='Hours', y='Activity', color='Team', orientation='h', barmode='group'), use_container_width=True)

            with tab4:
                st.subheader("Timecard Logs & Notes")
                
                # RESTORED: Date Filter logic inside the Activity Log Tab
                all_weeks = sorted(filtered_df['Date'].dt.strftime('%Y-%m-%d').unique(), reverse=True)
                selected_week = st.selectbox("Filter Log by Week Ending:", options=["All Weeks"] + all_weeks)
                
                log_display = filtered_df.copy()
                if selected_week != "All Weeks":
                    log_display = log_display[log_display['Date'].dt.strftime('%Y-%m-%d') == selected_week]
                
                # Format Date strings cleanly for the DataFrame view
                log_display['Date'] = log_display['Date'].dt.strftime('%Y-%m-%d')
                log_display['Total Hours'] = log_display['Total Hours'].round(2)
                
                st.dataframe(log_display[['Date', 'Owner', 'Team', 'Milestone', 'Total Hours', 'Notes']].sort_values(['Date', 'Owner'], ascending=[False, True]), use_container_width=True)

    except Exception as e:
        st.error(f"Error processing report: {e}")
else:
    st.info("👋 Upload a Salesforce report to begin.")