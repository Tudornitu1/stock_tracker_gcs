import os
import streamlit as st
import pandas as pd
from pymongo import MongoClient, errors
from dotenv import load_dotenv
import certifi
import datetime

# --- Page Configuration ---
st.set_page_config(
    page_title="Stock Management Dashboard",
    page_icon="📈",
    layout="wide"
)

# --- App Constants ---
SYMBOLS = ['AAPL', 'GOOGL', 'MSFT', 'TSLA', 'NVDA']

# --- MongoDB Connection ---
load_dotenv()
MONGO_URI = os.getenv("MONGO_DB_CONNECTION_STRING")
MONGO_DATABASE_NAME = "stock_market"
MONGO_COLLECTION_NAME = "daily_prices"

@st.cache_resource
def get_mongo_client():
    try:
        client = MongoClient(MONGO_URI, tlsCAFile=certifi.where())
        client.admin.command('ping')
        print("MongoDB connection successful for Streamlit app.")
        return client
    except Exception as e:
        st.error(f"Failed to connect to database: {e}")
        return None

client = get_mongo_client()
if client:
    db = client[MONGO_DATABASE_NAME]
    collection = db[MONGO_COLLECTION_NAME]

# --- Data Loading Function (READ) ---
@st.cache_data
def load_data(symbol: str):
    if client is None:
        return pd.DataFrame()
    
    cursor = collection.find({"symbol": symbol}, {"_id": 0}).sort("date", 1)
    df = pd.DataFrame(list(cursor))
    
    if not df.empty:
        df['date'] = pd.to_datetime(df['date'])
        df.set_index('date', inplace=True)
        df['50d_ma'] = df['close'].rolling(window=50).mean()
    
    return df

# --- UI Layout ---
st.title("📈 Stock Data Management Dashboard")

# Create tabs for each CRUD operation
tab_read, tab_create, tab_update_delete = st.tabs([
    "📈 Dashboard (Read)", 
    "➕ Create Record", 
    "✏️ Update / ❌ Delete Record"
])


# ==============================================================================
# TAB 1: READ 
# ==============================================================================
with tab_read:
    with st.sidebar:
        st.image("https://streamlit.io/images/brand/streamlit-logo-secondary-colormark-darktext.svg")
        st.title("Filters")
        selected_symbol = st.selectbox("Select a stock:", SYMBOLS)

    st.header(f"Visualizing Data for: {selected_symbol}")
    
    if selected_symbol:
        df = load_data(selected_symbol)
        
        if df.empty:
            st.warning("No data found for this symbol. Has the pipeline run yet?")
        else:
            latest_data = df.iloc[-1]
            prev_data = df.iloc[-2]
            price_diff = latest_data['close'] - prev_data['close']
            volume_diff = latest_data['volume'] - prev_data['volume']

            col1, col2 = st.columns(2)
            with col1:
                st.metric(
                    label=f"Latest Closing Price ({latest_data.name.strftime('%Y-%m-%d')})",
                    value=f"${latest_data['close']:,.2f}",
                    delta=f"${price_diff:,.2f} vs previous day"
                )
            with col2:
                st.metric(
                    label=f"Latest Volume",
                    value=f"{latest_data['volume']:,.0f}",
                    delta=f"{volume_diff:,.0f} vs previous day"
                )

            chart_df = df[['close', '50d_ma']]
            st.subheader("Closing Price vs. 50-Day Moving Average")
            st.line_chart(chart_df)
            
            st.subheader("Volume Over Time")
            st.bar_chart(df['volume'])
            
            with st.expander("Show Raw Data"):
                st.dataframe(df.tail(10))

# ==============================================================================
# TAB 2: CREATE
# ==============================================================================
with tab_create:
    st.header("➕ Add a New Stock Record")
    st.write("Use this form to manually insert a new daily record into the database.")
    
    with st.form("create_form"):
        c_symbol = st.selectbox("Symbol", SYMBOLS, key="c_symbol")
        c_date = st.date_input("Date")
        c_open = st.number_input("Open Price", min_value=0.0, format="%.2f")
        c_high = st.number_input("High Price", min_value=0.0, format="%.2f")
        c_low = st.number_input("Low Price", min_value=0.0, format="%.2f")
        c_close = st.number_input("Close Price", min_value=0.0, format="%.2f")
        c_volume = st.number_input("Volume", min_value=0)
        
        submitted = st.form_submit_button("Create New Record")
        
        if submitted and client:
            try:
                # Convert date to datetime for MongoDB
                c_datetime = datetime.datetime.combine(c_date, datetime.time(0))
                
                new_record = {
                    "symbol": c_symbol,
                    "date": c_datetime,
                    "open": c_open,
                    "high": c_high,
                    "low": c_low,
                    "close": c_close,
                    "volume": c_volume
                }
                
                collection.update_one(
                    {"symbol": c_symbol, "date": c_datetime},
                    {"$set": new_record},
                    upsert=True
                )
                
                st.success(f"Record for {c_symbol} on {c_date} created/updated successfully!")
                st.cache_data.clear() 
            except Exception as e:
                st.error(f"An error occurred: {e}")

# ==============================================================================
# TAB 3: UPDATE / DELETE
# ==============================================================================
with tab_update_delete:
    st.header("✏️ Find, Update, or Delete a Record")
    
    # --- Finder ---
    st.subheader("1. Find Record")
    with st.form("find_form"):
        find_symbol = st.selectbox("Symbol", SYMBOLS, key="ud_symbol")
        find_date = st.date_input("Date")
        
        find_button = st.form_submit_button("Find Record")
        
    if find_button and client:
        find_datetime = datetime.datetime.combine(find_date, datetime.time(0))
        
        st.session_state.record_to_edit = collection.find_one(
            {"symbol": find_symbol, "date": find_datetime}
        )
        
        if st.session_state.record_to_edit:
            st.success(f"Found record for {find_symbol} on {find_date}.")
        else:
            st.warning(f"No record found for {find_symbol} on {find_date}.")

    # --- Editor ---
    # This section only appears if a record has been found and stored in session_state
    if "record_to_edit" in st.session_state and st.session_state.record_to_edit:
        
        record = st.session_state.record_to_edit
        st.subheader(f"2. Modify Record for {record['symbol']} on {record['date'].strftime('%Y-%m-%d')}")
        
        # --- UPDATE Form ---
        with st.form("update_form"):
            st.write("Enter new values and click 'Update'.")
            
            # Pre-fill the form with the existing data
            u_open = st.number_input("Open", value=record.get('open', 0.0), format="%.2f")
            u_high = st.number_input("High", value=record.get('high', 0.0), format="%.2f")
            u_low = st.number_input("Low", value=record.get('low', 0.0), format="%.2f")
            u_close = st.number_input("Close", value=record.get('close', 0.0), format="%.2f")
            u_volume = st.number_input("Volume", value=record.get('volume', 0))
            
            update_button = st.form_submit_button("✏️ Update Record")
            
            if update_button:
                try:
                    collection.update_one(
                        {"_id": record["_id"]},
                        {"$set": {
                            "open": u_open,
                            "high": u_high,
                            "low": u_low,
                            "close": u_close,
                            "volume": u_volume
                        }}
                    )
                    st.success("Record updated!")
                    st.cache_data.clear() 
                    st.session_state.record_to_edit = None 
                except Exception as e:
                    st.error(f"An error occurred: {e}")

        # --- DELETE Button ---
        st.subheader("3. Delete Record")
        st.write("This action cannot be undone.")
        
        delete_button = st.button("❌ Delete This Record", type="primary")
        
        if delete_button:
            try:
                collection.delete_one({"_id": record["_id"]})
                st.success("Record deleted!")
                st.cache_data.clear() # Refresh dashboard
                st.session_state.record_to_edit = None # Clear state
            except Exception as e:
                st.error(f"An error occurred: {e}")