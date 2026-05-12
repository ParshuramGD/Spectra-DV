Spectra-DV
A local, database-driven Simulation Regression Tracking and Triage Dashboard designed for Design Verification (DV) and CAD automation workflows.

Why Spectra-DV Exists
When verifying digital designs, running regressions output thousands of lines of raw terminal logs. Checking which randomized seeds failed and why is a tedious task.

Spectra-DV bridges the gap between running simulations in a terminal and tracking them on a clean web dashboard. It gives hardware engineering students and small design teams a focused, self-healing platform to track projects, regressions, runs, test results, and recurring failure signatures without needing general-purpose software trackers or messy spreadsheets.

Core Features
Dynamic CAD Log Ingestion: Includes a local Python client parser (ci_tools/import_test.py) that scans raw ModelSim simulation logs and transmits data over secure HTTP POST payloads.

State-Aware Triage (Sticky Status): Once the parser encounters an RTL failure (fail or fatal), the status locks. Trailing cleanup success messages are blocked from overwriting the failure.

First-Failure Lock-in: Automatically isolates and displays the first encountered error message (e.g., a specific UVM or assertion failure) to highlight the actual root cause rather than downstream symptoms.

Interactive Health Analytics: Regression-specific dashboard screens tracking chronological pass/fail rate curves over time using Chart.js.

Self-Healing Provisioning: Ingesting a log for a new project automatically provisions the database relationships on-the-fly.

Robust Database Transactions: Uses Django's atomic transaction gateways to ensure bulk data uploads are "all-or-nothing."

## Screenshots and Video Demo

<video src="assets/demo.mp4" controls width="100%" poster="assets/01_dashboard_overview.png"></video>

---
All visual assets are stored in the assets/images.

1. Centralized Engineering Dashboard
The landing page consolidates high-level project health at a glance, tracking active runs and calculating cumulative pass rates across different hardware blocks.

2. Regression Pass Rate Trends
Tracks pass/fail metrics chronologically over the last 25 runs, making it easy to identify the exact moment a design fix or testbench update was merged.

3. Chronological Runs Ledger
A historical sequence of all executed regressions, maintaining run counts and parent project mapping.

4. RTL Error Triage View
Opening an individual run extracts the exact UVM error or assertion failure from the ModelSim console log directly onto a clean web card, eliminating manual log searches.

5. Consolidated Results Ledger
Displays a detailed test-by-test breakdown featuring parsed simulation seeds, run indices, and custom failure signatures.

Verification Vehicles (Simulated Circuits)
To test the parsing logic end-to-end, the system was validated using raw console logs compiled from active ModelSim simulation runs of five different hardware designs:

4-Bit Binary Counter: Simple sequential validation to verify clean, passing log parsing.

Synchronous FIFO: Parameterized FIFO queue containing assertion checks for empty/full flags. Tested with a simulated [FIFO_OVERFLOW] assertion error.

D Flip-Flop (DFF) Registry: Simple multi-bit register verifying dynamic environment provisioning.

Pipelined MIPS32 Processor Core: Explores system data hazards and ALU mismatches. Tested with simulated Read-After-Write (RAW) bypass hazard failures ([SUB_FAIL]) and arithmetic calculation mismatches ([ADD_FAIL]).

Digital FIR Filter: Digital Signal Processing (DSP) datapath block. Tested using large positive and negative inputs to verify pipeline clamping saturation logic (+32767 and -32768) under overflow conditions.

Demo & Seed Data
Ensure your virtual environment is active, then run:

Bash
# 1. Run migrations and database setup
python manage.py migrate

# 2. Ingest authentic ModelSim test logs using the local parser
python ci_tools/import_test.py my_real_logs

# 3. Create a read-only demo user
python manage.py create_demo_user --username demo --password demo

# 4. Start the Django server
python manage.py runserver 0.0.0.0:8000
Open http://127.0.0.1:8000/ in your browser and sign in with credentials: demo / demo.
or
python manage.py runserver 0.0.0.0:8001

Open http://127.0.0.1:8001/ in your browser and sign in with credentials: demo / demo.


Tech Stack
Backend: Python 3.11+ / Django 6.0.5 (SQLite for local storage)

Frontend: Django Templates, Tailwind CSS, Preline UI, Chart.js (CDN)

HDL Environment: Verilog / SystemVerilog (ModelSim Intel FPGA Edition 10.5b)

Quick Start (Local Setup)
Bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
npm install
cp .env.example .env
python manage.py migrate
npm run build-css
python manage.py runserver 0.0.0.0:8000
Future Roadmap
Compute Grid Security: Implement private subnet IP checking using Classless Inter-Domain Routing (CIDR) to restrict log ingestion to authorized compilation clusters.

Client Resiliency: Integrate exponential connection backoff with randomized jitter inside the Python script to handle heavy network loads.

Transport-Layer Streaming: Transition from HTTP POST requests to raw TCP Socket streaming for real-time console telemetry updates.

PostgreSQL Database Profile: Set up environment variables to swap SQLite with PostgreSQL for multi-user production environments.

Credits & Acknowledgements
The visual interface and responsive dashboard design of this project are inspired by SimTrack, an excellent open-source project created by Anup Kumar Reddy.

While the original SimTrack project provided a clean frontend layout using synthetic mock-data generators, Spectra-DV extends this work by building out a functional backend pipeline, writing a client-side regex parsing script, implementing state-aware failure logic, and validating the ingestion system using physical ModelSim simulation transcripts from real Verilog hardware blocks.

License
This project is licensed under the MIT License. See LICENSE for details.