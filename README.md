# 🚢 PortPulse — Live Maritime Traffic Dashboard

**A beginner-friendly logistics analytics portfolio project built in Python.**

PortPulse v0.1 displays publicly accessible AIS vessel snapshots near Rotterdam, Hamburg, or Oslofjord. It refreshes every 60 seconds while the page is open, plots vessel locations on a map, and displays vessel counts and speeds.

## What this project demonstrates

- Calling a real REST API (`requests`)
- Converting GeoJSON into clean, testable records
- Creating an interactive dashboard (`Streamlit`, `pandas`, `pydeck`)
- Working with Git and GitHub
- Testing a data-transformation function using `unittest`

## Requirements

- Python 3.11 or newer
- Git
- Visual Studio Code + Microsoft Python extension
- Internet access for live vessel data and map tiles

## Windows PowerShell — first run

Open this folder in Visual Studio Code and open **Terminal → New Terminal**. Run:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m streamlit run app.py
```

If the `py` command is unavailable, replace `py -3` with `python` for the first command.

The app should open in your browser, typically at `http://localhost:8501`. Press **Ctrl+C** in the terminal to stop it.

Tip: In VS Code, use **Ctrl+Shift+P → Python: Select Interpreter** and pick `.venv\Scripts\python.exe`.

## Mac / Linux — first run

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python -m streamlit run app.py
```

## Repository structure

```text
portpulse/
├── app.py                   # Streamlit user interface
├── vessel_data.py           # API request + data cleaning logic
├── requirements.txt         # Packages to install
├── tests/
│   └── test_vessel_data.py # Automated tests
├── .gitignore               # Files Git should not track
└── README.md                # Setup guide and project overview
```

## First Git commit

```bash
git init
git add .
git commit -m "Build first live maritime dashboard"
git branch -M main
```

If Git asks for your name/email, set them using `git config --global user.name "Your Name"` and `git config --global user.email "your-email@example.com"`, then retry the commit. Prefer an email associated with your GitHub account (or a GitHub-provided no-reply address).

To publish, create an **empty** public repository named `portpulse` on GitHub. Do not auto-create README / license / .gitignore there. Then:

```bash
git remote add origin https://github.com/YOUR_USERNAME/portpulse.git
git push -u origin main
```

GitHub may ask you to sign in via browser. Replace `YOUR_USERNAME` with your own GitHub username.

## Where the live data comes from

[Open Waters AIS API](https://openwaters.io/api/ais/) — `GET /v1/vessels` with a geographic bounding box and `max_age=30m`. The free anonymous tier does not require a key for this endpoint. A cap of **1,000 positions per response** applies, and access limits may change. The API returns GeoJSON features, including ship coordinates (`[longitude, latitude]`) and reported speed over ground in **knots**.

### Limitations and licensing

- A snapshot is not a continuous WebSocket stream; it is **polled every minute** while the app is open.
- API coverage varies by source and region, and positions may be delayed. The app requests only vessels seen in the previous 30 minutes.
- A speed below 1 knot is labeled **nearly stationary**, not necessarily anchored or waiting for a berth.
- Vessel counts are not certified counts of port throughput or arrivals.
- The data provider attaches source metadata and attribution. PortPulse shows the API attribution object and per-vessel sources in the dashboard. Review [Open Waters' source-specific licensing and credit requirements](https://openwaters.io/ais/) before publicly deploying or redistributing any AIS data.

## Roadmap

- **v0.1:** Display live snapshot positions, vessel table, KPIs, and automatic refresh.
- **v0.2:** Save historical snapshots to SQLite; track activity over hours and days.
- **v0.3:** Replace polling with a WebSocket collection service for genuine event streaming.
- **v0.4:** Implement congestion **proxy** indicators, forecasting, and decision analytics; distinguish measured data from estimates.

## Learning exercise

Change `"Rotterdam"` in `REGIONS` or add a new monitoring region, then run tests, inspect the dashboard, and commit with a meaningful message.
