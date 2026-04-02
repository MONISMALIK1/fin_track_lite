# FinTrack Lite 🚀

**FinTrack Lite** is a high-performance, role-based financial tracking ecosystem. It combines a robust **FastAPI** backend with a premium, real-time **HTML5/JS** dashboard, featuring local AI analysis and live data ingestion monitoring.

---

## 🌟 Key Features

- **Role-Based Access Control (RBAC)**: Distinct interfaces for Admins, Analysts, and Viewers.
- **AI-Powered Data Analysis**: Integrated with **Ollama (Qwen2.5:7b)** for natural language financial insights.
- **Live Upload Monitoring**: Server-Sent Events (SSE) stream real-time logs of data activities directly to the dashboard.
- **Bulk Data Operations**: Support for high-volume CSV uploads and filtered data exports.
- **Dynamic Visualizations**: Pure CSS/JS charts showing monthly trends and category breakdowns with context-aware explanations.
- **Robust Security**: JWT-based authentication with role-specific route protection.

---

## 📂 Project Structure

```text
fintrack_lite/
├── main.py           # Core FastAPI application & SSE logic
├── dashboard.html    # Premium standalone frontend dashboard
├── models.py         # SQLAlchemy ORM models (Users, Entries)
├── auth.py           # JWT, PWD hashing & role dependencies
├── services.py       # AI logic, CRUD & analytics engines
├── config.py         # Centralized settings (Model, URL, Keys)
├── upload_api.py     # CLI tool for bulk data ingestion
├── seed.py           # Database initializer (Setup users & samples)
├── test_app.py       # Comprehensive test suite (25+ tests)
└── requirements.txt  # Python dependencies
```

---

## ⚙️ Quick Start

### 1. Backend Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Seed the database (creates admin, analyst, viewer)
python seed.py

# Start the server
uvicorn main:app --reload
```

### 2. Local AI Setup
Ensure [Ollama](https://ollama.com/) is running on your system:
```bash
ollama serve
ollama pull qwen2.5:7b
```

### 3. Access the Dashboard
Simply browse to `http://localhost:8000` (FastAPI serves as the backend) and open **`dashboard.html`** in your browser to view the interactive UI.

---

## 🔑 User Roles & Permissions

| Role | Permissions | Dashboard Access |
| :--- | :--- | :--- |
| **Admin** | Full CRUD, User Management, CSV Upload/Download, AI | All Panels + Live Logs |
| **Analyst** | View, Filter, Export CSV, AI Analysis | All Panels + Live Logs |
| **Viewer** | Read-only view of summary and entries | Summary & Table Only |

---

## 🔌 API Operations

### 🔐 Authentication
- `POST /login`: Authenticate and receive a JWT.

### 📊 Dashboard & AI
- `GET /dashboard`: Fetch aggregated financial summaries.
- `POST /dashboard/ask`: Query the AI (**Qwen2.5:7b**) about your data.

### 📥 Data Management
- `POST /upload-csv` (Admin): Bulk upload financial records.
- `GET /export-csv` (Admin/Analyst): Download filtered data as CSV.
- `GET /logs/stream`: SSE endpoint for real-time activity monitoring.

### 📝 Entries (CRUD)
- `GET /entries`: List entries with advanced filters (`type`, `category`, `date`).
- `POST /entries` (Admin): Create a single entry.
- `PATCH /entries/{id}` (Admin): Modify existing data.

---

## 🛠️ Developer Tools

### Bulk Upload Tool (`upload_api.py`)
Used for ingesting large datasets directly via the terminal:
```bash
python upload_api.py path/to/your_data.csv
```

### Running Tests
Validated via Pytest to ensure 100% logic coverage:
```bash
pytest test_app.py -v
```
