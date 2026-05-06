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
🛠️ Installation & Setup
Step 1: Python Environment
Initialize Virtual Environment:

Bash
python3 -m venv venv
source venv/bin/activate
Install Dependencies:

Bash
pip install -r requirements.txt
Step 2: Salesforce CLI Setup
Installation: brew install --cask salesforce-cli (macOS).

Authentication: ```bash
sf org login web -a akamai_sf

*Note: You must use the alias `akamai_sf` for the sync engine to work.*

📘 Power User Guide: Using the Tools
1. MSL5 Bulk Tools (JWT Authentication)
Unlike other tools that use .edgerc, the MSL5 suite (Stream & Origin Creator) uses JWT Bearer Tokens.

Where to get it: Generate a token from the Akamai Identity Management portal or your specific MSL5 API client.

How to use: Paste the token into the sidebar. It is used as a Bearer header for all requests.

Origin Creator: Requires a CSV with host_name, contract_id, cptag, group_id, ingest_location, and backup_ingest_location.

2. TC Report Dashboard (Salesforce Sync)
This tool pulls data directly from your SF Reports.

Report IDs: Copy the 18-character ID from the Salesforce URL.

CRITICAL: In Salesforce, the report MUST have the "Detail Rows" toggle turned ON and be saved. If it only shows summary data, the sync will return 0 rows.

Manage IDs: Use the ⚙️ icon in the sidebar to add/remove reports without touching the code.

3. Quota-Safe Search (MSL4, Certs, Finder)
To prevent burning your API quota while typing, these tools use a "Find Account" form.

Type at least 3 characters of a customer name (e.g., "Disney").

Click the Find Account button.

Select the match from the dropdown. This ensures only one API call is made instead of dozens.

⚡ Terminal Shortcut (The "Toolbox" Command)
To launch the Toolbox from anywhere:

Open your config: nano ~/.zshrc

Add this line:

Bash
alias toolbox='source /[path/to/willapps]/venv/bin/activate && python -m streamlit run /[path/to/willapps]/main.py'
Refresh: source ~/.zshrc

Just type toolbox in any terminal window.