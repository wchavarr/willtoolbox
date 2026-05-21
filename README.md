# 🚀 Will Toolbox v2.1.2
**Akamai Enterprise Management & Project Analytics Suite**

The Will Toolbox is a unified command center built for Akamai Architects and Consultants. It automates high-friction tasks like bulk MSL5 stream/origin creation, certificate auditing, and automated timecard project tracking.

---

## 📁 Project Structure
The suite uses a modular "Engine Room" architecture. To add tools, drop the `.py` file into `apps/` and update `main.py`.

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
│   └── tcreport.py        # TC Report Dashboard v2.1.2 (Salesforce Connected)
📥 Step 1: How to Download the Toolbox from Git
If you are new to Git or terminal environments, follow these steps to download the toolbox code repository to your local machine.

Method A: Using the Terminal (Recommended)
Open the Terminal application on your Mac (Press Cmd + Space, type Terminal, and hit Enter).

Navigate to the folder where you want to save the project (e.g., your Desktop):

Bash
cd ~/Desktop
Copy the project repository using git clone:

Bash
git clone [PASTE_YOUR_REPOSITORY_URL_HERE]
Move your terminal focus inside the newly downloaded directory:

Bash
cd willapps
Method B: Downloading via Web Browser
Open the Git repository webpage in your browser.

Click the green Code button on the top right.

Select Download ZIP.

Locate the downloaded .zip file in your Downloads folder, double-click it to unpack it, and drag the extracted willapps folder to your workspace.

🛠️ Step 2: Environment & Local Dependencies Setup
Ensure your local Python interpreter environment is isolated and packages are fully updated.

Initialize Virtual Environment:

Bash
python3 -m venv venv
source venv/bin/activate
Install Dependencies:

Bash
pip install -r requirements.txt
🛰️ Step 3: Salesforce CLI Authentication Setup
Required if utilizing live background contract metric syncing on the Timecard Dashboard.

Install the CLI Engine:

Bash
brew install --cask salesforce-cli
Authenticate with Akamai's Salesforce Node: Run the following command in your terminal. A web browser window will open automatically prompting you to log in with your Akamai Single Sign-On (SSO) credentials.

Bash
sf org login web -a akamai_sf
Note: You must use the alias akamai_sf precisely for the background script connectors to resolve queries.

🚀 Step 4: Running the Application
To launch the central toolbox navigation window, execute this command from the root folder:

Bash
streamlit run main.py
Alternative fallback if you encounter shell environment path issues:

Bash
python3 -m streamlit run main.py
📘 User Guide & Engine Room Walkthrough
1. 📊 TC Report Dashboard (tcreport.py v2.1.2)
What it does: Automates project management metrics by processing raw manual export sheets and tracking burn rates against Salesforce budgets.

How to use it:

Open your Salesforce browser tab, generate your timecard report, toggle "Detail Rows" ON, and export it as a Details Only CSV or Excel spreadsheet.

Drop the file into the "Upload Salesforce Report" box in the sidebar.

What to expect: The tool instantly strips hidden white spaces and processes the grid. It reads the oldest timestamp from Timecard: Created Date and automatically sets your Project Start Date to Day 1 of that month, and your Project End Date exactly 3 months out.

Simultaneously, it grabs the project string name from your data row and dispatches a background Salesforce CLI calculation to pull contract hours.

Smart Override: If Salesforce matches a record, your graphs and status bars snap to that exact contract hours total automatically. If the connection fails or you wish to simulate scenarios, you can manually override the calculation using the Project Budgeted Hours box in the sidebar.

2. 📡 MSL5 Bulk Tools (app.py v12.2)
What it does: Automates mass creation of Media Services Live (MSL5) Origins and Streams, bypassing tedious manual property manager UI adjustments.

How to use it:

Obtain your Akamai JWT Bearer Token from your Identity Access profile.

Paste the token into the sidebar authentication entry prompt box.

Prepare a configuration file matching the schema layout inside msl5_bulk_template.csv (host_name, contract_id, cptag, group_id, ingest_location, backup_ingest_location).

Upload your CSV and click "Execute Bulk Provisioning".

What to expect: The script validates your token, builds individual secure API request headers, and spins up your properties sequentially. An active progress status tracker bar will display provisioned updates in real time.

🗺️ 3. MSL4 Mapping Dashboard (msl4app.py v30.6)
What it does: Visually audits legacy Media Services Live (MSL4) distribution streams and ingress pathways map layers.

How to use it:

Use the Quota-Safe Account Search form in the sidebar.

Type at least 3 characters of the target customer name and click "Find Account".

Select the exact match from the populated dropdown selector box to load metrics.

What to expect: The system processes active network telemetry mappings without burning API thresholds, drawing clean visual interactive grid tables of your active legacy delivery profiles.

🔒 4. Master Certs Audit Engine (certs_audit.py v1.4.8)
What it does: Audits globally deployed TLS/SSL security certificate pipelines across customer slots to pinpoint immediate expiration vulnerabilities.

How to use it:

Authenticate your account target slot profile using the Quota-Safe Account Search container form.

Click "Run Certificate Security Audit Scan".

What to expect: The suite loops through live hostname configurations and displays a clean, color-coded tabular timeline ledger. Approaching certificate renewals are highlighted in yellow, while expired or high-risk assets flash immediate red warning indicators.

🔍 5. Account Switch Finder (account_finder.py v2.3)
What it does: A utility for quick-switching tenant account environments, allowing consultants to resolve ambiguous customer tracking IDs instantly.

How to use it:

Input a partial customer name string or internal system contract switch ID parameter.

Click the search execution button.

What to expect: Displays clear data rows mapping verified parent companies to active functional properties, removing the guesswork when hunting for client configurations.

⚡ Optional Terminal Shortcut (Alias Configuration)
To launch the Toolbox instantly from any open terminal window without manually running setup commands:

Open your terminal profile setup configuration file:

Bash
nano ~/.zshrc
Paste this shortcut rule at the absolute bottom of the document (replace [path] with the true folder path directory on your Mac):

Bash
alias toolbox='source /[path]/willapps/venv/bin/activate && python3 -m streamlit run /[path]/willapps/main.py'
Save and close the editor (Ctrl + O, Enter, then Ctrl + X).

Apply the update instantly:

Bash
source ~/.zshrc
Now, simply type toolbox in any new terminal pane to launch your platform environment immediately!

Created by wchavarr@akamai.com | Unified Akamai Management Platform v2.1.2