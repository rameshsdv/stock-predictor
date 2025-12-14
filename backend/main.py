from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from service import predict_stock_price
import logging

app = FastAPI(title="NSE Stock Predictor API")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins (Mobile/LAN access)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class PredictionRequest(BaseModel):
    symbol: str

@app.get("/")
def read_root():
    return {"status": "healthy", "service": "NSE Predictor API"}

@app.post("/predict")
def predict_endpoint(request: PredictionRequest):
    try:
        # Validate symbol is strictly alphanumeric (plus .NS suffix logic handled in service)
        symbol = request.symbol.strip().upper()
        if not symbol:
             raise HTTPException(status_code=400, detail="Symbol cannot be empty")
             
        result = predict_stock_price(symbol)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logging.error(f"Prediction error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")

# For debugging locally
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
