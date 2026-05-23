# 🚀 Nova: AI-Powered Logistics Platform

![Nova Banner](https://img.shields.io/badge/Status-Active-brightgreen) ![Python](https://img.shields.io/badge/Python-3.14-blue) ![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-teal) ![React](https://img.shields.io/badge/React-19-61dafb)

Nova is an intelligent, next-generation logistics and supply chain management platform. It uses autonomous **AI Agents** and **Retrieval-Augmented Generation (RAG)** to automate complex workflows, extract structured data from unstructured documents, and detect supply chain anomalies in real-time.

---

## 📖 Comprehensive Documentation
For a deep dive into the architecture, AI Agent design, and database schemas, please refer to our detailed documentation:
👉 **[View Detailed Documentation](document.md)**

---

## ✨ Key Features
*   **🤖 Autonomous AI Agents:** Features specialized agents for Document Extraction, Exception Detection, Validation, and Workflow Routing.
*   **📊 Dynamic Dashboard:** Real-time analytics built with Recharts, pulling from PostgreSQL.
*   **🔍 Semantic Search (RAG):** Ask questions about your logistics data in natural language, powered by ChromaDB.
*   **⚡ High-Performance Backend:** Built on FastAPI and LangGraph for robust AI orchestration.
*   **🐳 Dockerized Infrastructure:** One-click setup for PostgreSQL, Redis, and pgAdmin.

---

## 🛠️ Getting Started

Follow these steps to run the Nova platform locally.

### 1. Start Infrastructure (Docker)
Open a terminal in the project root and run the Docker services:
```bash
start_docker.bat
# Or manually: cd infra && docker-compose up -d
```
*This starts PostgreSQL (Port 5432), Redis (Port 6379), and pgAdmin.*

### 2. Start the Backend
Open a new terminal and run the backend script:
```bash
start_backend.bat
# Or manually: cd backend && python main.py
```
*The FastAPI server will start on port 8000.*

### 3. Start the Frontend
Open a new terminal and run the frontend script:
```bash
start_frontend.bat
# Or manually: cd frontend && npm run dev
```
*The Vite development server will start on port 5173.*

### 4. Load Datasets (Optional but Recommended)
To populate the database and ChromaDB with sample data, run the data loaders from the `backend` directory:
```bash
cd backend
python data_loaders/load_dataco.py
python data_loaders/load_fraud.py
python data_loaders/load_sroie.py
```

---

## 📸 Platform Demo

Here is a visual walkthrough of the Nova platform:

### 1. Dashboard Overview
![Dashboard](images/Screenshot%202026-05-23%20215427.png)

### 2. Workflow Automation
![Workflow](images/Screenshot%202026-05-23%20215432.png)

### 3. Document Extraction
![Documents](images/Screenshot%202026-05-23%20215440.png)

### 4. Approvals Management
![Approvals](images/Screenshot%202026-05-23%20215459.png)

### 5. Exception Detection
![Exceptions](images/Screenshot%202026-05-23%20215511.png)

### 6. Platform Settings
![Settings](images/Screenshot%202026-05-23%20215521.png)

### 7. AI Query & Analysis
![RAG Query](images/Screenshot%202026-05-23%20215530.png)

---
*Built with ❤️ for modern supply chain management.*
