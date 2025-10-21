set -a 
source .env
set +a
source venv/Scripts/activate
# python3 -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000 --reload
