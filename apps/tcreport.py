import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import calendar
import re
import subprocess
import json

# --- VERSIONING ---
VERSION = "2.1.8-DailySplit"

# --- SIDEBAR: PROJECT CONFIGURATION ---
st.sidebar.title(f"TC Report Tool v{VERSION}")
st.sidebar.header("📋 Project Settings")

uploaded_file = st.sidebar.file_uploader("Upload Salesforce Report (Excel or CSV)", type=["csv", "xlsx"])

# Set safe baseline parameters inside application state memory
if 'start_date' not in st.session_state:
    st.session_state.start_date = datetime(2026, 5, 1).date()
if 'end_date' not in st.session_state:
    st.session_state.end_date = datetime(2026, 7, 31).date()
if 'budget_hours_state' not in st.session_state:
    st.session_state.budget_hours_state = 120.0  # Safe initial baseline fallback

calculated_start = st.session_state.start_date
calculated_end = st.session_state.end_date

# ==============================================================================
# 🛰️ ISOLATED SALESFORCE AUTOMATION HOOK (Hidden Background Calculator)
# ==============================================================================
def pull_salesforce_hours(project_name_string):
    """Hits Salesforce CLI using the exact cell text to calculate target hours."""
    api_hours = "pse__Planned_Hours__c"
    api_months = "Months_from_Start_to_End_Date_New__c"
    escaped_name = str(project_name_string).replace("'", "\\'")
    
    soql = f"SELECT {api_hours}, {api_months} FROM pse__Proj__c WHERE Name = '{escaped_name}' LIMIT 1"
    cmd = ["sf", "data", "query", "--query", soql, "--target-org", "akamai_sf", "--json"]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        records = json.loads(res.stdout).get("result", {}).get("records", [])
        if records:
            rec = records[0]
            hrs = float(rec.get(api_hours, 0) or 0)
            mns = float(rec.get(api_months, 0) or 0)
            if mns > 0:
                return round((hrs / mns) * 3, 2)
    except Exception:
        pass
    return None

# --- SNEAK PEEK FOR AUTO-TIMELINE & SALESFORCE SYNC ---
if uploaded_file:
    try:
        uploaded_file.seek(0)
        df_peek = pd.read_excel(uploaded_file) if uploaded_file.name.endswith('.xlsx') else pd.read_csv(uploaded_file)
        df_peek.columns = [str(c).strip() for c in df_peek.columns]
        
        # 1. Handle Automatic Date Bound Extraction
        date_col = None
        for col in df_peek.columns:
            if "Created Date" in col or col == "Date" or "End Date" in col:
                date_col = col
                break
        
        if date_col:
            peek_dates = pd.to_datetime(df_peek[date_col], errors='coerce').dropna()
            if not peek_dates.empty:
                min_date = peek_dates.min()
                
                # SNEAK PEEK DATE OVERHANG SAFEGUARD
                # If the earliest date belongs to a trailing month-end tail (day 26 or later),
                # we roll the start date cleanly forward to the 1st day of the true target month.
                if min_date.day >= 26:
                    if min_date.month == 12:
                        calculated_start = datetime(min_date.year + 1, 1, 1).date()
                    else:
                        calculated_start = datetime(min_date.year, min_date.month + 1, 1).date()
                else:
                    calculated_start = datetime(min_date.year, min_date.month, 1).date()
                
                end_month = calculated_start.month + 2
                end_year = calculated_start.year
                if end_month > 12:
                    end_month -= 12
                    end_year += 1
                
                last_day_of_month = calendar.monthrange(end_year, end_month)[1]
                calculated_end = datetime(end_year, end_month, last_day_of_month).date()

                # --- CORRECTED SMART INCREMENTAL ROLLING ENGINE ---
                # Safely advances in precise 3-month blocks based on the exact base window
                today_date = datetime.now().date()
                
                while today_date > calculated_end:
                    # Advance the start month by exactly 3 months
                    start_m = calculated_start.month + 3
                    start_y = calculated_start.year
                    if start_m > 12:
                        start_m -= 12
                        start_y += 1
                    calculated_start = datetime(start_y, start_m, 1).date()
                    
                    # Align the end month precisely to 2 months after the newly updated start month
                    end_m = calculated_start.month + 2
                    end_y = calculated_start.year
                    if end_m > 12:
                        end_m -= 12
                        end_y += 1
                    last_day = calendar.monthrange(end_y, end_m)[1]
                    calculated_end = datetime(end_y, end_m, last_day).date()

        # 2. Handle Background Salesforce Allocation Sync Upfront
        if 'Project' in df_peek.columns and not df_peek['Project'].empty:
            raw_file_project_name = str(df_peek['Project'].iloc[0]).strip()
            
            # Check if this is a newly uploaded file context to avoid refresh loop spikes
            if "last_checked_project" not in st.session_state or st.session_state.last_checked_project != raw_file_project_name:
                st.session_state.last_checked_project = raw_file_project_name
                sf_hours = pull_salesforce_hours(raw_file_project_name)
                if sf_hours is not None:
                    st.session_state.budget_hours_state = float(sf_hours)

        uploaded_file.seek(0)
    except Exception:
        try: uploaded_file.seek(0)
        except: pass

# Sidebar widgets - initialized natively using our smart memory sync pipeline
budget_input = st.sidebar.number_input(
    "Project Budgeted Hours", 
    min_value=1, 
    value=int(st.session_state.budget_hours_state), 
    step=10
)
start_date_input = st.sidebar.date_input("Project Start Date", value=calculated_start)
end_date_input = st.sidebar.date_input("Project End Date", value=calculated_end)

st.session_state.start_date = start_date_input
st.session_state.end_date = end_date_input
st.session_state.budget_hours_state = float(budget_input)  # Retain user overrides cleanly

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

# --- CORE PARS ENGINE ---
if uploaded_file:
    try:
        df = pd.read_excel(uploaded_file) if uploaded_file.name.endswith('.xlsx') else pd.read_csv(uploaded_file)
        df.columns = [str(c).strip() for c in df.columns]
        
        # Dynamic targeting for the Date index column key header
        active_date_col = None
        for col in df.columns:
            if "Created Date" in col or col == "Date" or "End Date" in col:
                active_date_col = col
                break
                
        if not active_date_col:
            st.error("Could not find a valid Date column in the uploaded file.")
            st.stop()
            
        # Map fields matching raw spreadsheet columns safely
        df = df.rename(columns={'Timecard: Owner Name': 'Owner', 'Milestone: Milestone Name': 'Milestone'})
        if 'Owner' not in df.columns and 'Timecard: Owner Name' in df.columns:
            df = df.rename(columns={'Timecard: Owner Name': 'Owner'})
        if 'Milestone' not in df.columns and 'Milestone: Milestone Name' in df.columns:
            df = df.rename(columns={'Milestone: Milestone Name': 'Milestone'})

        # Group by unique timecards to clear out the repeated week-rows noise
        if 'Timecard: Timecard Id' in df.columns:
            unique_timecards = df.drop_duplicates(subset=['Timecard: Timecard Id'])
        else:
            unique_timecards = df

        # --- GRANULAR DAILY UNPIVOT ENGINE ---
        # Expands horizontal multi-day columns vertically into separate logs with correct dates
        expanded_rows = []
        for idx, row in unique_timecards.iterrows():
            base_date = pd.to_datetime(row[active_date_col], errors='coerce')
            if pd.isna(base_date):
                continue
            
            # Find Monday of that specific entry's week to act as our temporal baseline anchor
            monday = base_date - timedelta(days=base_date.weekday())
            
            for day_idx, day_name in enumerate(['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']):
                hrs_col = f'{day_name} Hours'
                notes_col = f'{day_name} Notes'
                if hrs_col in row and notes_col in row:
                    hrs = pd.to_numeric(row[hrs_col], errors='coerce')
                    if pd.notna(hrs) and hrs > 0:
                        day_date = monday + timedelta(days=day_idx)
                        expanded_rows.append({
                            'Date': day_date,
                            'Owner': row['Owner'],
                            'Milestone': row['Milestone'],
                            'Hours': hrs,
                            'Notes': str(row[notes_col]).strip() if pd.notna(row[notes_col]) else ''
                        })

        if expanded_rows:
            processed_df = pd.DataFrame(expanded_rows)
        else:
            processed_df = pd.DataFrame(columns=['Date', 'Owner', 'Milestone', 'Hours', 'Notes'])

        processed_df['Team'] = processed_df['Owner'].apply(get_team)

        # Set calculations target pool to mirror state memory (which supports live manual overrides)
        active_budget_hours = st.session_state.budget_hours_state

        # Calculations
        today = datetime.now().date()
        project_total_used = processed_df['Hours'].sum()
        total_project_days = max((end_date_input - start_date_input).days, 1)
        total_working_days = len(pd.bdate_range(start=today + timedelta(days=1), end=end_date_input)) if today < end_date_input else 0
        weeks_rem_decimal = max(total_working_days / 5, 0.1)
        days_passed_hist = max(((processed_df['Date'].max().date() if not processed_df.empty else today) - start_date_input).days, 1)
        ongoing_burn_rate = project_total_used / (days_passed_hist / 7)
        hours_remaining = active_budget_hours - project_total_used
        required_weekly_rate = max(hours_remaining / weeks_rem_decimal, 0.0)
        projected_total = ongoing_burn_rate * (total_project_days / 7)

        # --- UI HEADER & KPI CARDS ---
        st.title(f"📊 Project Dashboard")
        
        # Display feedback if the app successfully loaded context parameters via Salesforce
        if "last_checked_project" in st.session_state and st.session_state.last_checked_project:
            st.info(f"🔗 **Live Salesforce Alignment Active:** Connected to `{st.session_state.last_checked_project}` profile.")
        
        usage_pct = (project_total_used / active_budget_hours) * 100
        
        if usage_pct >= 100:
            st.error(f"🛑 **Project in overages:** {usage_pct:.1f}% of budget consumed.")
        elif usage_pct >= 80:
            st.error(f"⚠️ **Possible overages:** {usage_pct:.1f}% of budget consumed.")
        else:
            st.success(f"✅ **Budget Healthy:** {usage_pct:.1f}% of budget consumed.")
        
        if total_working_days > 0:
            st.info(f"🗓️ **Time Remaining:** {total_working_days} Business Days ({total_working_days // 5} weeks left)")
        
        ci1, ci2 = st.columns(2)
        ci1.info(f"**Actual Usage:** {project_total_used:.2f} / {active_budget_hours} Hours")
        ci2.warning(f"**Target Burn:** {required_weekly_rate:.2f} hrs/week required to stay on budget")
        
        kpi1, kpi2, kpi3, kpi4 = st.columns(4)
        kpi1.metric("Project Total Used", f"{project_total_used:.2f} hrs")
        kpi2.metric("Hours Left", f"{hours_remaining:.2f}")
        kpi3.metric("Burn Rate", f"{ongoing_burn_rate:.2f} /wk")
        kpi4.metric("Projected Total", f"{projected_total:.1f}", f"{projected_total - active_budget_hours:+.1f}")
        st.markdown("---")

        # Team Filter
        all_owners = sorted(processed_df['Owner'].unique())
        selected_owners = st.sidebar.multiselect("Filter Individuals:", options=all_owners, default=all_owners)
        filtered_df = processed_df[processed_df['Owner'].isin(selected_owners)].copy()

        # --- TABS ---
        tab1, tab2, tab3, tab4 = st.tabs(["🔥 Burn Rate Analysis", "📊 Distribution", "🛡️ Security vs Delivery", "📝 Activity Log"])
        
        with tab1:
            chart_df = filtered_df.groupby('Date')['Hours'].sum().reset_index().sort_values('Date')
            chart_df['Cumulative'] = chart_df['Hours'].cumsum()
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=chart_df['Date'], y=chart_df['Cumulative'], name='Ongoing Usage', line=dict(color='red', width=4)))
            fig.add_trace(go.Scatter(x=[start_date_input, end_date_input], y=[0, active_budget_hours], name='Budget Target', line=dict(color='gray', dash='dash')))
            st.plotly_chart(fig, use_container_width=True)

        with tab2:
            col1, col2 = st.columns(2)
            col1.plotly_chart(px.bar(filtered_df.groupby('Owner')['Hours'].sum().reset_index(), x='Hours', y='Owner', orientation='h', title="Hours by Individual"), use_container_width=True)
            col2.plotly_chart(px.pie(filtered_df.groupby('Milestone')['Hours'].sum().reset_index(), values='Hours', names='Milestone', title="Hours by Milestone"), use_container_width=True)

        with tab3:
            st.subheader("🛡️ Security vs Delivery Analysis")
            ana_rows = []
            for _, row in filtered_df.iterrows():
                acts = get_activities(row['Notes'], row['Owner'])
                share = row['Hours'] / len(acts)
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
            
            all_weeks = sorted(filtered_df['Date'].dt.strftime('%Y-%m-%d').unique(), reverse=True)
            selected_week = st.selectbox("Filter Log by Week Ending:", options=["All Weeks"] + all_weeks)
            
            log_display = filtered_df.copy()
            if selected_week != "All Weeks":
                log_display = log_display[log_display['Date'].dt.strftime('%Y-%m-%d') == selected_week]
            
            log_display['Date'] = log_display['Date'].dt.strftime('%Y-%m-%d')
            log_display['Hours'] = log_display['Hours'].round(2)
            
            st.dataframe(log_display[['Date', 'Owner', 'Team', 'Milestone', 'Hours', 'Notes']].sort_values(['Date', 'Owner'], ascending=[False, True]), use_container_width=True)

    except Exception as e:
        st.error(f"Error processing report: {e}")
else:
    st.info("👋 Upload a Salesforce report to begin.")