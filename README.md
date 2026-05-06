You're absolutely right—not everyone wants to set up an alias right away. We should make sure the standard "manual" startup is crystal clear.

I've updated the Step 3 in the README.md to show the standard run commands, including the python -m variation which is often more stable across different OS environments.

README.md | Version 1.9.3 (Full Revision)
Markdown
# 🚀 Will Toolbox v1.9.3
**Akamai Enterprise Management & Project Analytics Suite**

The Will Toolbox is a unified command center designed for Akamai Architects and Consultants. It automates high-friction tasks like bulk MSL5 creation, certificate auditing, and Salesforce project synchronization.

---

## 📁 Project Structure
The suite uses a modular "Engine Room" structure. To add tools, drop the `.py` file into `apps/` and update `main.py`. 

```plaintext
willapps/
├── main.py                # Central Hub v1.9.3 (Navigation & Auto-Updater)
├── sf_sync_cli.py         # Salesforce Sync Engine v1.0.4 (Matrix Flattener)
├── requirements.txt       # Unified dependencies
├── .gitignore             # Credential & local data protection
├── msl5_bulk_template.csv # Template for MSL5 mass creation
├── apps/                  # Individual Tool Logic
│   ├── app.py             # MSL5 Bulk Tools v12.2 (Origin & Stream Creator)
│   ├── msl4app.py         # MSL4 Mapping Dashboard v30.6
│   ├── account_finder.py  # Account Switch Finder v2.3
│   ├── certs_audit.py     # Master Certs Audit v1.4.8
│   └── tcreport.py        # TC Report Dashboard v1.8.6
🛠️ Step 1: Python Environment Setup
Initialize Virtual Environment:

Bash
python3 -m venv venv
source venv/bin/activate
Install Dependencies:

Bash
pip install -r requirements.txt
🛠️ Step 2: Salesforce CLI Setup (Optional for Tracking)
Installation: brew install --cask salesforce-cli (macOS).

Authentication: ```bash
sf org login web -a akamai_sf

*Note: You must use the alias `akamai_sf` for the sync engine to work.*

🚀 Step 3: Running the Application
To start the toolbox, ensure your virtual environment is active, then run either of these commands from the root directory:

Standard Command:

Bash
streamlit run main.py
Alternative (Recommended for path issues):

Bash
python3 -m streamlit run main.py
📘 Step 4: Power User Configuration
1. MSL5 Bulk Tools (JWT Authentication)
The MSL5 suite (Stream & Origin Creator) uses JWT Bearer Tokens instead of .edgerc.

How to use: Paste the token into the sidebar. It is used as a Bearer header for all requests.

Origin Creator: Requires a CSV with headers: host_name, contract_id, cptag, group_id, ingest_location, backup_ingest_location.

2. TC Report Dashboard (Salesforce Sync)
Report IDs: Copy the 18-character ID from the Salesforce URL.

CRITICAL: In Salesforce, the report MUST have the "Detail Rows" toggle turned ON and be saved.

Manage IDs: Use the ⚙️ icon in the sidebar of the TC Report page to add/remove reports.

3. Quota-Safe Search (MSL4, Certs, Finder)
To prevent burning your API quota while typing, these tools use a "Find Account" form.

Type at least 3 characters of a customer name.

Click the Find Account button.

Select the match from the dropdown to activate the tool.

⚡ Step 5: Optional Terminal Shortcut (Alias)
To launch the Toolbox from anywhere without navigating to the folder:

Open your config: nano ~/.zshrc

Add this line (replace [path] with your actual folder path):

Bash
alias toolbox='source /[path]/venv/bin/activate && python3 -m streamlit run /[path]/main.py'
Refresh: source ~/.zshrc

Just type toolbox in any terminal window.

Created by wchavarr@akamai.com | Unified Management Platform v1.9.3