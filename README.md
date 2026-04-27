# 🚀 Will Toolbox v1.8.7
**Akamai Enterprise Management & Project Analytics Suite**

---

## 📁 Project Structure
The suite uses a modular "Engine Room" structure. To add tools, drop the `.py` file into `apps/` and update `main.py`. Local configurations (Salesforce IDs) are kept out of Git for security.

```plaintext
willapps/
├── main.py                # Central Hub v1.8.7 (Navigation & Auto-Updater)
├── sf_sync_cli.py         # Salesforce Sync Engine v1.0.4 (Matrix Flattener)
├── requirements.txt       # Unified dependencies
├── .gitignore             # Credential & local data protection
├── msl5_bulk_template.csv # Template for MSL5 mass creation
├── reports_config.json    # [LOCAL ONLY] User-defined Report IDs
└── apps/                  # Individual Tool Logic
🛠️ Step 1: Python Environment Setup
Initialize Virtual Environment:

Bash
python3 -m venv venv
source venv/bin/activate
What happens: This creates a clean "sandbox" for Python. You will see (venv) appear at the start of your terminal line.

Install Dependencies:

Bash
pip install -r requirements.txt
What happens: The terminal installs the Akamai and Streamlit libraries required for the tools.

🛠️ Step 2: Salesforce CLI Setup (Global System)
1. Installation (macOS Recommended):

Bash
brew install --cask salesforce-cli
2. Verification:
Restart your terminal and run: sf --version.

3. Authentication:
Authorize your Akamai SF account with the required alias:

Bash
sf org login web -a akamai_sf
Log in via the browser and click "Allow".

🚀 Step 3: Running & Configuring the App
Launch Command:

Bash
python -m streamlit run main.py
First-Time Configuration:

Go to Project Tracking > TC Report Dashboard.

Use the ⚙️ Manage Report IDs tool in the sidebar to add your Salesforce IDs.

Click 🔄 Sync Reports Now.

⚡ Step 4: Optional Terminal Shortcut (Alias)
To launch the Toolbox from anywhere without navigating to the folder:

Open your zsh config:

Bash
nano ~/.zshrc
Add this line at the bottom (replace [path/to/willapps] with your actual path):

Bash
alias toolbox='source /[path/to/willapps]/venv/bin/activate && python -m streamlit run /[path/to/willapps]/main.py'
Save and refresh:

Bash
source ~/.zshrc
Just type toolbox in any terminal window.

⚠️ Troubleshooting & Compatibility
ModuleNotFoundError: No module named 'akamai' Fix: pip install edgegrid-python

API Error 429 (Rate Limits) Fix: The Master Certs Audit (v1.4.8) includes an intelligent backoff engine. If you see a "Rate Limit" notification, the app will automatically pause and resume once Akamai clears the quota.

Salesforce Reports showing 0 rows Fix: In Salesforce, ensure the Detail Rows toggle is ON (bottom of report builder) and click Save.

Outlook Triage Button Requirement: Microsoft Outlook must be set as the default Mail application on your OS.

Created by wchavarr@akamai.com | Unified Management Platform v1.8.7