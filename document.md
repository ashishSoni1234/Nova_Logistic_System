# Nova AI Logistics Platform - Technical Documentation

## Overview
Nova is an advanced, AI-driven logistics and supply chain management platform designed to automate workflows, extract actionable data from documents, and detect anomalies in real-time. By leveraging autonomous AI agents and Retrieval-Augmented Generation (RAG), Nova streamlines operations and reduces manual oversight.

## Architecture

### Frontend
Built with modern web technologies to ensure a responsive and dynamic user experience:
*   **Framework:** React 19 via Vite
*   **Styling:** Tailwind CSS for a sleek, modern UI
*   **Data Visualization:** Recharts for analytics and dashboards
*   **Workflow Visualization:** ReactFlow for interactive agent routing and process flows
*   **State Management:** React Query for efficient data fetching and caching

### Backend
A robust, high-performance API that powers the AI operations:
*   **Framework:** FastAPI for high-speed, asynchronous REST APIs
*   **AI Engine:** LangGraph for building stateful, multi-actor AI agent workflows
*   **Database ORM:** SQLAlchemy for PostgreSQL interactions
*   **Embeddings & RAG:** SentenceTransformers (all-MiniLM-L6-v2)

### Infrastructure & Databases
Containerized services for easy deployment and scalability:
*   **Relational DB:** PostgreSQL (Stores relational data like orders and user info)
*   **Vector DB:** ChromaDB (Stores high-dimensional vectors for semantic search and RAG)
*   **Cache:** Redis (Used for session management and fast data retrieval)
*   **Containerization:** Docker & Docker Compose

## AI Agent System
Nova utilizes a multi-agent architecture where specialized agents handle distinct tasks:
1.  **Document Extractor Agent:** Automatically ingests logistics documents (like invoices from the SROIE dataset), parses the text, and extracts structured data.
2.  **Exception Detector Agent:** Continuously monitors supply chain data to flag anomalies, such as high "late delivery risk" or irregular purchasing patterns (using the Fraud dataset).
3.  **Validator Agent:** Cross-references extracted data against business rules to ensure compliance and accuracy.
4.  **Workflow Router Agent:** Intelligently routes flagged exceptions or processed documents to the appropriate human operator for approval.

## Datasets
The platform is pre-configured to utilize three primary datasets to fuel its AI capabilities:
*   **DataCo Supply Chain Dataset:** Contains over 180,000 rows of supply chain data, powering the dashboard analytics and RAG queries.
*   **Fraud Patterns Dataset:** Embedded into ChromaDB to help the Exception Detector identify fraudulent transactions.
*   **SROIE (Scanned Receipts OCR and Information Extraction):** Used for testing and training the Document Extractor agent on real-world invoices.

## RAG (Retrieval-Augmented Generation)
Nova features a powerful RAG system. By embedding the supply chain data, business rules, and fraud patterns into ChromaDB, users can query the system in natural language (e.g., "What are the common traits of delayed shipments in LATAM?"), and the AI will retrieve the most relevant context to generate an accurate answer.
