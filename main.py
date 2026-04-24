import streamlit as st
import subprocess

# --- AUTO-UPDATER LOGIC ---
def check_for_updates():
    try:
        # Fetch latest metadata from git
        subprocess.run(['git', 'fetch'], check=True, capture_output=True)
        
        # Compare local code fingerprint with the remote version
        local_hash = subprocess.check_output(['git', 'rev-parse', 'HEAD']).decode().strip()
        remote_hash = subprocess.check_output(['git', 'rev-parse', 'origin/main']).decode().strip()
        
        if local_hash != remote_hash:
            st.sidebar.warning("🚀 **Update Available!**")
            if st.sidebar.button("Update & Restart Toolbox", use_container_width=True):
                st.sidebar.info("Pulling latest changes...")
                subprocess.run(['git', 'pull', 'origin', 'main'], check=True)
                st.rerun()
    except Exception:
        pass

# 1. GLOBAL CONFIGURATION
st.set_page_config(
    page_title="Will Toolbox",
    page_icon="🛡️",
    layout="wide"
)

# 2. RUN UPDATER
check_for_updates()

# 3. BRANDING: Sidebar Logo
st.logo("https://www.akamai.com/content/dam/site/en/images/logo/akamai-logo.svg")

# 4. DEFINE PAGES
pages = {
    "Identity & Access": [
        st.Page("apps/apiusersv2.py", title="Identity Control (v7.2)", icon="🛡️"),
        st.Page("apps/account_finder.py", title="Account Switch Finder (v2.2)", icon="🔍"),
    ],
    "Certificates": [
        st.Page("apps/certs_audit.py", title="Master Certs Audit (v1.3.8)", icon="📜"),
    ],
    "Media Services Live": [
        st.Page("apps/app.py", title="MSL5 Bulk Tools (v11.6)", icon="🚀"),
        st.Page("apps/msl4app.py", title="MSL4 Mapping Dashboard (v30.3)", icon="📊"),
    ],
    "Project Tracking": [
        st.Page("apps/tcreport.py", title="TC Report Dashboard (v1.8.6)", icon="📈"),
    ]
}

# 5. INITIALIZE NAVIGATION
pg = st.navigation(pages)

# 6. SHARED SIDEBAR BRANDING
st.sidebar.markdown("# 🚀 Will Toolbox v1.7.1")
st.sidebar.caption("Unified Management Platform")
st.sidebar.caption("Created by wchavarr@akamai.com") # Added as requested
st.sidebar.divider()

# 7. RUN THE SELECTED PAGE
pg.run()