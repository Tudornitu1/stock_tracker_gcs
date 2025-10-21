End-to-End Stock Market Data Platform

This project is a complete, end-to-end data platform that automates the ingestion, storage, processing, and visualization of daily stock market data. It demonstrates a full data lifecycle, from a third-party API to an interactive user-facing web application.

The core of the project is an ELT (Extract, Load, Transform) pipeline orchestrated by Apache Airflow. This pipeline runs daily, ensuring the data is always fresh and reliable.

The interactive dashboard allows users to visualize historical data and manage database records directly.

Architecture

The platform is built on a modern data stack, separating raw data storage (Data Lake) from the application's operational database (Document DB).

Data Flow Diagram:

[Polygon.io API] -> [Python Script (in Airflow)] -> [GCS Data Lake (Raw JSON)]
|
L-> [MongoDB Atlas (Clean BSON)] -> [Streamlit UI]

Core Components:

Orchestration (Apache Airflow): Schedules and executes the Python ingestion script daily. Manages task dependencies and ensures reliability. Run locally via Docker and the Astro CLI.

Data Lake (Google Cloud Storage): Stores the raw, unmodified JSON responses from the API, partitioned by date and ticker. This provides a historical backup and allows for future re-processing.

Application Database (MongoDB Atlas): Stores clean, structured data in BSON format. A unique composite index (symbol, date) guarantees data integrity and prevents duplicates. The database is populated using an idempotent upsert strategy.

Web Application (Streamlit): A user-facing dashboard that reads data directly from MongoDB to provide visualizations and a full CRUD (Create, Read, Update, Delete) interface for managing records.

Tech Stack

Orchestrator: Apache Airflow (managed with Astro CLI)

Language: Python

Data Storage:

Data Lake: Google Cloud Storage (GCS)

Application DB: MongoDB Atlas (Cloud)

API Source: Polygon.io

Frontend/UI: Streamlit

Containerization: Docker

Key Features

Automated Daily Ingestion: The Airflow DAG runs automatically every day, fetching the latest stock data without manual intervention.

Data Source Migration: The pipeline was successfully migrated from two previous rate-limited sources (Alpha Vantage, FMP) to a more robust API (Polygon.io), demonstrating adaptability to changing data landscapes.

Idempotent & De-duplicated: The pipeline uses an upsert operation combined with a unique database index to ensure that running the pipeline multiple times does not create duplicate records.

Hybrid Storage Model: Implements a best-practice architecture by separating the raw data lake (GCS) from the structured application database (MongoDB).

Full CRUD Application: The Streamlit UI isn't just for reading data; it provides a complete interface for creating, updating, and deleting individual records, demonstrating a full grasp of database interactions.

Cloud-Native: Leverages managed cloud services (GCS, MongoDB Atlas) for scalability and reliability.

Setup and Local Execution

To run this project on your local machine, follow these steps.

Prerequisites

Python 3.10+

Docker Desktop

Astro CLI (brew install astro)

A Google Cloud account with a Service Account key (.json file).

A MongoDB Atlas account with a database user and connection string.

An API key from Polygon.io.

Installation & Configuration

Clone the repository:

git clone <your-repo-url>
cd stock_tracker

Set up Environment Variables:

Place your GCP Service Account key in the secrets/ folder and name it gcp-credentials.json.

Create a .env file in the root directory and populate it with your API key:

# No longer used, but kept for history

# ALPHA_VANTAGE_API_KEY=...

# FMP_API_KEY=...

# Not used in hardcoded setup, but good practice

# POLYGON_API_KEY=your_polygon_key_here

MONGO_DB_CONNECTION_STRING=your_mongodb_atlas_connection_string

Configure the Hardcoded API Key:

Open docker-compose.local.yml.

In the environment section for all three services (scheduler, webserver, triggerer), set your Polygon API key:

environment:

- POLYGON_API_KEY=your_polygon_key_here

# ... other variables

Install Python dependencies for the Streamlit app:

# Create and activate a virtual environment

python3 -m venv venv
source venv/bin/activate

# Install packages

pip install streamlit pandas pymongo python-dotenv certifi

Running the Project

Start the Airflow Pipeline Environment:

# This will start all necessary Docker containers

astro dev start

Access the Airflow UI at http://localhost:8080 (admin/admin).

Un-pause and trigger the stock_market_data_pipeline DAG to populate your database.

Launch the Streamlit Dashboard:

Make sure your virtual environment is active.

Run the following command:

streamlit run dashboard.py
