@echo off
echo Starting Trippy - AI Travel Planner...
echo.
echo Open your browser and go to: http://localhost:8501
echo.
echo Press Ctrl+C to stop the application
echo.
streamlit run app.py --server.port 8501 --server.address localhost
