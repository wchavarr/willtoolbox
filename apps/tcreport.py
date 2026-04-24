import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta

# --- VERSIONING ---
VERSION = "1.8.6"

# --- SIDEBAR: PROJECT CONFIGURATION ---
st.sidebar.title(f"TC Report Tool v{VERSION}")
st.sidebar.header("📋 Project Settings")

# Moved uploader to the top of sidebar to allow the "clean message" logic
uploaded_file = st.sidebar.file_uploader("Upload Salesforce Report (Excel or CSV)", type=["csv", "xlsx"])

# Initialize Session State for dynamic dates
if 'start_date' not in st.session_state:
    st.session_state.start_date = datetime(2026, 4, 1).date()
if 'end_date' not in st.session_state:
    st.session_state.end_date = datetime(2026, 6, 30).date()

budget_input = st.sidebar.number_input("Project Budgeted Hours", min_value=1, value=120, step=10)

# Sidebar date inputs
start_date_input = st.sidebar.date_input("Project Start Date", value=st.session_state.start_date)
end_date_input = st.sidebar.date_input("Project End Date", value=st.session_state.end_date)

# Update session state if manually adjusted
st.session_state.start_date = start_date_input
st.session_state.end_date = end_date_input

# --- THE CLEANUP LOGIC ---
# This only displays if a file is actually uploaded
if uploaded_file:
    total_project_days = max((end_date_input - start_date_input).days, 1)
    standard_burn_rate = (budget_input / (total_project_days / 7))
    st.sidebar.info(f"📍 **Project Standard Burn Rate:** {standard_burn_rate:.2f} hrs/week")

st.sidebar.error("⚠️ **IMPORTANT:** Update the Budget and Dates above first!")
manual_name = st.sidebar.text_input("Manual Project Name (Optional Override)", "")
st.sidebar.markdown("---")

# --- HELPER FUNCTIONS ---
def find_project_name_logic(df, is_tabular, header_row=0):
    blacklist = ["nan", "0", "0.0", "project", "project ↑", "project name", "sum of total hours", "none", "total", "subtotal", "sum of"]
    if is_tabular:
        cols = [str(c).strip().lower() for c in df.iloc[header_row]]
        for i, col_name in enumerate(cols):
            if "project" in col_name:
                for val in df.iloc[header_row+1:header_row+50, i]:
                    s_val = str(val).strip()
                    if s_val.lower() not in blacklist and len(s_val) > 2:
                        return s_val
    return "Project Dashboard"

if uploaded_file:
    try:
        # 1. LOAD DATA
        df_raw = pd.read_excel(uploaded_file, header=None) if uploaded_file.name.endswith('.xlsx') else pd.read_csv(uploaded_file, header=None)

        # 2. DETECT FORMAT
        is_tabular = False
        header_row = 0
        for r in range(min(20, len(df_raw))):
            row_str = " ".join([str(x) for x in df_raw.iloc[r].tolist()])
            if any(k in row_str for k in ["Total Hours", "Timecard Id", "Owner Name"]):
                header_row = r; is_tabular = True; break
        
        auto_name = find_project_name_logic(df_raw, is_tabular, header_row)
        display_name = manual_name if manual_name else auto_name

        # 3. NORMALIZE DATA
        if is_tabular:
            df = df_raw.copy()
            df.columns = [str(c).strip() for c in df.iloc[header_row]]
            df = df[header_row + 1:].reset_index(drop=True)
            df['Total Hours'] = pd.to_numeric(df['Total Hours'], errors='coerce').fillna(0)
            df['Date'] = pd.to_datetime(df['End Date'], errors='coerce')
            df = df.rename(columns={'Timecard: Owner Name': 'Owner', 'Milestone: Milestone Name': 'Milestone'})
            
            note_cols = [c for c in df.columns if 'Notes' in str(c)]
            df['Notes'] = df[note_cols].fillna('').agg(' | '.join, axis=1).str.replace(r'(\| )+', '| ', regex=True).str.strip(' |')
            processed_df = df[['Date', 'Owner', 'Milestone', 'Total Hours', 'Notes']].dropna(subset=['Date'])
        else:
            # MATRIX FORMAT
            idx_dates = df_raw[df_raw.iloc[:, 1].astype(str) == "End Date →"].index[0]
            idx_totals = df_raw[df_raw.iloc[:, 1].astype(str).isin(["Total", "Subtotal"])].index[-1]
            dates_row = df_raw.iloc[idx_dates]; owner_row = df_raw.iloc[idx_dates - 1]
            matrix_data = []
            for col_idx in range(3, len(dates_row)):
                if '/' in str(dates_row[col_idx]):
                    name = next((str(owner_row[i]) for i in range(col_idx, 1, -1) if str(owner_row[i]) not in ['nan', 'Subtotal', '']), "Unknown")
                    val = pd.to_numeric(df_raw.iloc[idx_totals, col_idx], errors='coerce')
                    if val > 0: 
                        matrix_data.append({'Date': pd.to_datetime(dates_row[col_idx]), 'Owner': name, 'Milestone': 'N/A', 'Total Hours': val, 'Notes': 'N/A'})
            processed_df = pd.DataFrame(matrix_data)

        # --- 4. SMART DATE AUTO-CALCULATION (Quarterly Window) ---
        if not processed_df.empty:
            raw_min = processed_df['Date'].min()
            calc_start = raw_min.replace(day=1).date()
            
            # Logic: End of the 3rd month
            month_val = calc_start.month - 1 + 3
            year_val = calc_start.year + month_val // 12
            month_val = month_val % 12 + 1
            calc_end = (datetime(year_val, month_val, 1) - timedelta(days=1)).date()

            if st.session_state.start_date != calc_start or st.session_state.end_date != calc_end:
                st.session_state.start_date = calc_start
                st.session_state.end_date = calc_end
                st.rerun()

        # --- CALCULATIONS ---
        today = datetime.now().date()
        project_total_used = processed_df['Total Hours'].sum()
        
        if today < end_date_input:
            business_days_list = pd.bdate_range(start=today + timedelta(days=1), end=end_date_input)
            total_working_days = len(business_days_list)
        else:
            total_working_days = 0
            
        weeks_rem = total_working_days // 5
        extra_days_rem = total_working_days % 5
        weeks_remaining_decimal = max(total_working_days / 5, 0.1)
        
        last_data_date = processed_df['Date'].max().date() if not processed_df.empty else today
        days_passed_hist = max((last_data_date - start_date_input).days, 1)
        ongoing_burn_rate = project_total_used / (days_passed_hist / 7)
        hours_remaining = budget_input - project_total_used
        required_weekly_rate = max(hours_remaining / weeks_remaining_decimal, 0.0)
        required_daily_rate = max(hours_remaining / total_working_days, 0.0) if total_working_days > 0 else 0.0
        projected_total = ongoing_burn_rate * (total_project_days / 7)

        # --- UI HEADER & ALERTS ---
        st.title(f"📊 {display_name}")

        usage_pct = (project_total_used / budget_input) * 100
        if usage_pct >= 100:
            st.error(f"🛑 **Project in overages:** {usage_pct:.1f}% of budget consumed.")
        elif usage_pct >= 80:
            st.error(f"⚠️ **Possible overages:** {usage_pct:.1f}% of budget consumed.")
        else:
            st.success(f"✅ **Budget Healthy:** {usage_pct:.1f}% of budget consumed.")
        
        if total_working_days > 0:
            st.info(f"🗓️ **Time Remaining:** {total_working_days} Business Days ({weeks_rem} weeks and {extra_days_rem} days left)")
        else:
            st.error(f"🚨 **Project Period Ended.**")

        # Restoration of usage notes
        c_info, c_warn = st.columns(2)
        c_info.info(f"**Actual Usage:** {project_total_used:.1f} / {budget_input} Hours Used")
        c_warn.warning(f"**Target Burn (Remaining Hours):** {required_weekly_rate:.2f} hrs/week ({required_daily_rate:.1f} hrs/day)")

        st.markdown("---")

        # --- FILTERS ---
        st.sidebar.header("👤 Team Filtering")
        all_owners = sorted(processed_df['Owner'].unique())
        selected_owners = st.sidebar.multiselect("Select Individuals:", options=all_owners, default=all_owners)
        st.sidebar.markdown(f"**Version:** {VERSION}")
        filtered_df = processed_df[processed_df['Owner'].isin(selected_owners)]

        # --- KPI CARDS ---
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Selection Total", f"{filtered_df['Total Hours'].sum():.1f} hrs")
        m2.metric("Project Hours Left", f"{hours_remaining:.1f}", delta_color="normal" if hours_remaining > 0 else "inverse")
        m3.metric("Ongoing Burn Rate", f"{ongoing_burn_rate:.2f} /wk")
        m4.metric("Projected Total", f"{projected_total:.1f}", f"{projected_total - budget_input:+.1f}", delta_color="inverse" if projected_total > budget_input else "normal")

        # --- TABS ---
        tab1, tab2, tab3 = st.tabs(["🔥 Burn Rate Analysis", "📊 Distribution", "📝 Activity Log"])
        
        with tab1:
            chart_df = filtered_df.groupby('Date')['Total Hours'].sum().reset_index().sort_values('Date')
            chart_df['Cumulative'] = chart_df['Total Hours'].cumsum()
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=chart_df['Date'], y=chart_df['Cumulative'], name='Ongoing Usage', line=dict(color='red', width=4), mode='lines+markers'))
            fig.add_trace(go.Scatter(x=[start_date_input, end_date_input], y=[0, budget_input], name='Standard (Ideal) Path', line=dict(color='gray', dash='dash')))
            st.plotly_chart(fig, use_container_width=True)
            
        with tab2:
            c1, c2 = st.columns(2)
            c1.plotly_chart(px.bar(filtered_df.groupby('Owner')['Total Hours'].sum().reset_index(), x='Total Hours', y='Owner', orientation='h', title="By Individual"), use_container_width=True)
            c2.plotly_chart(px.pie(filtered_df.groupby('Milestone')['Total Hours'].sum().reset_index(), values='Total Hours', names='Milestone', title="By Milestone"), use_container_width=True)

        with tab3:
            st.subheader("Timecard Logs & Notes")
            all_weeks = sorted(filtered_df['Date'].dt.strftime('%Y-%m-%d').unique(), reverse=True)
            selected_week = st.selectbox("Filter Log by Week Ending:", options=["All Weeks"] + all_weeks)
            log_display = filtered_df.copy()
            if selected_week != "All Weeks":
                log_display = log_display[log_display['Date'].dt.strftime('%Y-%m-%d') == selected_week]
            log_display['Date'] = log_display['Date'].dt.strftime('%Y-%m-%d')
            st.dataframe(log_display.sort_values(['Date', 'Owner'], ascending=[False, True]), use_container_width=True)

    except Exception as e:
        st.error(f"Error encountered: {e}")
else:
    st.info("👋 Welcome! Please upload your Salesforce report to begin.")