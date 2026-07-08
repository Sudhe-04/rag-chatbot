#!/bin/bash
set -e

echo "Starting FastAPI backend on port 8000..."
uvicorn app.api.main:app --host 0.0.0.0 --port 8000 &

# Give the API a moment to start before Streamlit begins polling it
sleep 3

echo "Starting Streamlit user interface on port 8501..."
streamlit run streamlit_app.py \
    --server.port 8501 \
    --server.address 0.0.0.0 \
    --server.headless true

# If streamlit exits, bring down the whole container
wait
