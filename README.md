# 🚀 Will Toolbox v1.7
**Akamai Enterprise Management & Project Analytics Suite**

## 📁 Project Structure
The suite uses a modular "Engine Room" structure. To add tools, drop the `.py` file into `apps/` and update `main.py`.

```plaintext
willapps/
├── main.py                # Central Hub v1.7 (Navigation & Auto-Updater)
├── requirements.txt       # Unified dependencies
├── .gitignore             # Credential protection
├── msl5_bulk_template.csv # Template for MSL5 mass creation
└── apps/                  # Individual Tool Logic
🛠️ Installation & Setup
1. Environment Initialization
Always use a virtual environment to prevent conflicts with system Python (especially on Mac/Homebrew):

Bash
python3 -m venv venv
# Mac/Linux:
source venv/bin/activate
# Windows:
venv\Scripts\activate
2. Dependency Installation
Install requirements directly from the file:

Bash
pip install --upgrade pip
pip install -r requirements.txt
🚀 Key Features
Auto-Updater: Detects code changes on GitHub and allows for a one-click sync to v1.7+.

Keyless Search: Support for "Reverse Account Lookup" across Identity, Certs, and MSL4 tools.

Primary Account Support: Audit runner accounts by leaving switch key fields blank.

⚠️ Troubleshooting & Compatibility
1. ModuleNotFoundError: No module named 'akamai'
Issue: You installed akamai-edgegrid but the code cannot find the module, or you are using Python 3.12+.
Fix: Use the specific package name edgegrid-python. This is the actively maintained distribution that provides the akamai.edgegrid module for modern Python versions:

Bash
pip install edgegrid-python
2. Streamlit ignoring the Virtual Environment
Issue: The app runs but ignores your installed libraries, often showing a path like /opt/homebrew/... in the error.
Fix: Always launch the app using the Python module syntax from within your activated venv:

Bash
python -m streamlit run main.py
3. Outlook Triage Button
Requirement: For the "Triage in Outlook" button to function in the Certs tool, Microsoft Outlook must be set as the default Mail application on your OS.

💻 Running the Suite
Bash
# Ensure venv is active!
python -m streamlit run main.py