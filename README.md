# 🚀 Will Toolbox v1.7
**Akamai Enterprise Management & Project Analytics Suite**

A unified management platform consolidating Akamai-specific tools into a high-performance "Keyless" interface.

## 📁 Project Structure
The suite is organized into a modular "Engine Room" structure. Individual tool logic resides in `apps/`.

```plaintext
willapps/
├── main.py                # Central Hub, Navigation & Auto-Updater
├── requirements.txt       # Unified dependencies
├── .gitignore             # Credential protection
├── msl5_bulk_template.csv # Template for MSL5 mass creation
└── apps/                  # The "Engine Room"
    ├── apiusersv2.py      # Identity Control (v7.2)
    ├── certs_audit.py     # Master Certs Audit (v1.3.8)
    ├── msl4app.py         # MSL4 Mapping Dashboard (v30.3)
    ├── app.py             # MSL5 Bulk Tools (v11.6)
    ├── account_finder.py  # Account Switch Finder (v2.2)
    └── tcreport.py        # TC Report Dashboard (v1.8.6)
🛠️ Installation & Setup
1. Environment Initialization
Create a fresh virtual environment to isolate dependencies:

Bash
python3 -m venv venv
# Mac/Linux: source venv/bin/activate
# Windows: venv\Scripts\activate
2. Dependency Installation
Bash
pip install -r requirements.txt
3. Akamai Authentication
Ensure your .edgerc file is in your home directory (~/.edgerc) with a [default] section.

🚀 Key Features
Keyless Search: All tools support "Reverse Account Lookup" by name.

Primary Account Support: Audit your runner account by leaving search/key fields blank.

Outlook Triage: One-click professional email generation for expiring certificates.

MSL5 Bulk Creation: Use msl5_bulk_template.csv for mass stream uploads.

Auto-Updater: One-click sync to the latest GitHub version.

⚠️ Important Configuration
Outlook Triage: For the "Triage in Outlook" button to work, Microsoft Outlook must be set as the default Mail application on your operating system (Windows or macOS).

Security: Never upload your .edgerc or private JWTs to GitHub. Use the provided .gitignore.

💻 Running the Suite
Bash
streamlit run main.py