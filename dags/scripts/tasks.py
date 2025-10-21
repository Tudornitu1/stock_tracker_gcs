import os
import json
import requests
import datetime
import certifi
import time  
from dotenv import load_dotenv
from google.cloud import storage
from pymongo import MongoClient, errors, UpdateOne

# --- Configuration ---
load_dotenv()
API_KEY = os.getenv("POLYGON_API_KEY") 
GCS_BUCKET_NAME = "stock-data-lake-tn-2025" 
SYMBOLS = ['AAPL', 'GOOGL', 'MSFT', 'TSLA', 'NVDA']

MONGO_URI = os.getenv("MONGO_DB_CONNECTION_STRING")
MONGO_DATABASE_NAME = "stock_market"
MONGO_COLLECTION_NAME = "daily_prices"
# ---------------------

try:
    mongo_client = MongoClient(MONGO_URI, tlsCAFile=certifi.where())
    mongo_client.admin.command('ping')
    print("MongoDB connection successful.")
except Exception as e:
    print(f"Could not connect to MongoDB: {e}")
    mongo_client = None

def fetch_stock_data(symbol: str) -> dict:
    """Fetches 2 years of daily stock data for a given symbol from Polygon.io."""
    print(f"Fetching data for {symbol} from Polygon.io...")
    
    # Get dates for the last 2 years
    date_to = datetime.date.today().isoformat()
    date_from = (datetime.date.today() - datetime.timedelta(days=730)).isoformat()
    
    # Polygon's aggregate (bars) endpoint
    url = f"https://api.polygon.io/v2/aggs/ticker/{symbol}/range/1/day/{date_from}/{date_to}"
    params = {
        "apiKey": API_KEY,
        "sort": "asc",
        "limit": 5000 # Max limit
    }
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        print(f"Successfully fetched data for {symbol}.")
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data for {symbol}: {e}")
        return None

# GCS function 
def upload_to_gcs(bucket_name: str, data: dict, destination_blob_name: str):
    print(f"Starting GCS upload...")
    try:
        storage_client = storage.Client()
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(destination_blob_name)
        data_string = json.dumps(data, indent=4)
        blob.upload_from_string(data_string, content_type='application/json')
        print(f"Data successfully uploaded to gs://{bucket_name}/{destination_blob_name}")
    except Exception as e:
        print(f"Error uploading to GCS: {e}")

# *** Load function for Polygon's JSON structure ***
def load_data_to_mongodb(data: dict):
    """Parses raw Polygon JSON data and upserts it into a MongoDB collection."""
    if mongo_client is None:
        print("Skipping MongoDB load: client not initialized.")
        return
    
    symbol = data.get("ticker")
    if not symbol:
        print("No ticker symbol in Polygon response.")
        return
        
    print(f"Starting MongoDB upsert for {symbol}...")
    try:
        db = mongo_client[MONGO_DATABASE_NAME]
        collection = db[MONGO_COLLECTION_NAME]

        time_series = data.get("results", []) 
        
        if not time_series:
            print(f"No 'results' data found in Polygon response for {symbol}.")
            return

        operations = []
        for values in time_series:
            dt = datetime.datetime.fromtimestamp(values["t"] / 1000)
            
            operations.append(
                UpdateOne(
                    # Filter
                    {
                        "symbol": symbol,
                        "date": dt
                    },
                    # Update/Insert
                    {
                        "$set": {
                            "open": float(values["o"]),
                            "high": float(values["h"]),
                            "low": float(values["l"]),
                            "close": float(values["c"]),
                            "volume": int(values["v"])
                        }
                    },
                    upsert=True
                )
            )
        
        if not operations:
            print(f"No operations to perform for {symbol}.")
            return
        
        result = collection.bulk_write(operations)
        print(f"MongoDB upsert complete for {symbol}. Matched: {result.matched_count}, Upserted: {result.upserted_count}, Modified: {result.modified_count}")

    except errors.PyMongoError as e:
        print(f"Error loading to MongoDB for {symbol}: {e}")
    except Exception as e:
        print(f"An unexpected error occurred with MongoDB: {e}")

# *** Main pipeline function ***
def run_stock_pipeline():
    """The main pipeline function to be called by Airflow."""
    today_str = datetime.date.today().isoformat()
    print(f"Starting stock pipeline for date: {today_str}")
    
    for symbol in SYMBOLS:
        stock_data = fetch_stock_data(symbol)
        
        if stock_data and "results" in stock_data:
            
            # GCS load
            blob_name = f"raw_stock_data/ticker={symbol}/date={today_str}/data.json"
            upload_to_gcs(
                bucket_name=GCS_BUCKET_NAME,
                data=stock_data,
                destination_blob_name=blob_name
            )
            
            # MongoDB load
            load_data_to_mongodb(stock_data)
            
        else:
            print(f"Skipping all loads for {symbol} due to fetch error or invalid data.")
            print(f"API Response for {symbol}: {stock_data}")
        
        # Wait 15 seconds to respect Polygon's 5-call/minute limit
        print("Waiting 15 seconds to respect API limit...")
        time.sleep(15)