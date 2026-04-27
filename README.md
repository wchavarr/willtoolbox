# 🚀 Will Toolbox v1.8.6
**Akamai Enterprise Management & Project Analytics Suite**

## 📁 Project Structure
The suite uses a modular "Engine Room" structure. To add tools, drop the `.py` file into `apps/` and update `main.py`. Local configurations (Salesforce IDs) are kept out of Git for security.

```plaintext
willapps/
├── main.py                # Central Hub v1.8.6 (Navigation & Auto-Updater)
├── sf_sync_cli.py         # Salesforce Sync Engine v1.0.3 (Matrix Flattener)
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
What happens: This creates a clean "sandbox" for Python and activates it. You will see (venv) appear at the start of your terminal line.

Install Dependencies:

Bash
pip install -r requirements.txt
What happens: The terminal will scroll with progress bars as it installs the Akamai and Streamlit libraries required for the tools.

🛠️ Step 2: Salesforce CLI Setup (Global System)
The Toolbox requires the Salesforce CLI (sf) to be installed on your operating system.

Installation (macOS Recommended):

Bash
brew install --cask salesforce-cli
What happens: Homebrew will download the CLI and link it to your system paths.
(Note: If you don't have Homebrew, use the Manual Installer).

Verification:
Restart your terminal and run: sf --version.
What happens: You should see a version string (e.g., @salesforce/cli/2.x.x).

Authentication:
Authorize your Akamai SF account with the required alias:

Bash
sf org login web -a akamai_sf
What happens: * Your default web browser will automatically open to the Salesforce login page.

Log in using your Akamai credentials/SSO.

Click "Allow" when prompted for permissions.

Once finished, your terminal will display: Successfully authorized ... with alias akamai_sf.

🚀 Step 3: Running & Configuring the App
Launch Command:

Bash
python -m streamlit run main.py
What happens: A new tab opens in your browser at http://localhost:8501.

First-Time Configuration:

Go to Project Tracking > TC Report Dashboard.

Use the ⚙️ Manage Report IDs tool in the sidebar to add your Salesforce IDs.

Click 🔄 Sync Reports Now.
What happens: The sidebar will show a progress status for each report. Once finished, your CSVs are saved to ./downloads and the dashboard charts will instantly appear.

⚠️ Troubleshooting & Compatibility
1. ModuleNotFoundError: No module named 'akamai'
Fix: Use the edgegrid-python package:

Bash
pip install edgegrid-python
2. Streamlit ignoring the Virtual Environment
Fix: Always launch using the Python module syntax: python -m streamlit run main.py.

3. Salesforce Reports showing 0 rows
Fix: The API cannot see unsaved detail rows. In Salesforce, ensure the Detail Rows toggle is ON (bottom of report builder) and click Save.

4. Outlook Triage Button
Requirement: For the "Triage in Outlook" button, Microsoft Outlook must be the default Mail application on your OS.

Created by wchavarr@akamai.com | Unified Management Platform v1.8.6