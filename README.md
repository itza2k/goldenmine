# Goldmine

Offline Windows desktop app for a single gold-loan / pawn shop. Records stay on this computer in SQLite. Employees can run the counter; they cannot rewrite history after five minutes.

## Run

```bash
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python run.py
```

On this Mac, use Anaconda Python (Tcl/Tk 8.6). Apple’s `/usr/bin/python3` uses Tcl 8.5 and shows a black window in Dark Mode:

```bash
/opt/anaconda3/bin/python3 -m venv .venv-mac
source .venv-mac/bin/activate
pip install -r requirements.txt
python run.py
```

On first launch, create the **owner** account. Then add employees under Settings → Users.

## Roles

- **Employee:** sign in, add customers, issue loans, search, view, print receipts. No deletes, reports, settings, backups, or rate changes. After a loan is created, they may correct it for **five minutes only**. After that the loan is locked.
- **Owner:** everything above, plus reports (PDF/Excel), backups, users, interest rates, closing/reopening loans, and the audit log. Changing a locked loan requires the owner password again and is written to the audit log.

## Data location (development)

`data/goldmine.db` plus `data/backups`, `data/exports`, and `data/receipts`.
