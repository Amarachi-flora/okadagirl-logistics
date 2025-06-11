# OkadaGirlLogistic Streamlit App

import streamlit as st
import json
import os
from datetime import datetime
from textblob import TextBlob
import pandas as pd
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderUnavailable
from io import BytesIO
from PIL import Image
import plotly.express as px

LOG_FILE = "delivery_logs.json"
geolocator = Nominatim(user_agent="okadagirl_app")

# --- Helper Functions ---
def load_logs():
    if not os.path.exists(LOG_FILE):
        return []
    with open(LOG_FILE, "r") as file:
        return json.load(file)

def save_logs(logs):
    with open(LOG_FILE, "w") as file:
        json.dump(logs, file, indent=4)

def analyze_sentiment(feedback):
    polarity = TextBlob(feedback).sentiment.polarity
    if polarity > 0:
        return "Positive"
    elif polarity < 0:
        return "Negative"
    return "Neutral"

def add_log(customer, destination, status, feedback, rating):
    new_log = {
        "customer": customer,
        "destination": destination,
        "status": status,
        "feedback": feedback,
        "rating": rating,
        "sentiment": analyze_sentiment(feedback),
        "date": datetime.now().strftime("%Y-%m-%d %H:%M")
    }
    logs = load_logs()
    logs.append(new_log)
    save_logs(logs)
    return True

def filter_logs(logs, keyword):
    keyword = keyword.lower()
    return [log for log in logs if keyword in log['customer'].lower() or keyword in log['date'].lower() or keyword in log['destination'].lower()]

def show_summary(logs):
    total = len(logs)
    delivered = sum(1 for log in logs if log['status'].lower() == 'delivered')
    pending = sum(1 for log in logs if log['status'].lower() == 'pending')
    not_delivered = sum(1 for log in logs if log['status'].lower() == 'not delivered')
    sentiments = {"Positive": 0, "Negative": 0, "Neutral": 0}
    for log in logs:
        sentiments[log['sentiment']] += 1
    avg_rating = pd.DataFrame(logs)['rating'].mean() if logs else 0
    return total, delivered, pending, not_delivered, sentiments, avg_rating

def get_coordinates(destination):
    try:
        location = geolocator.geocode(destination + ", Nigeria")
        if location:
            return location.latitude, location.longitude
    except GeocoderUnavailable:
        return None, None
    return None, None

def prepare_time_series(logs):
    if not logs:
        return None, None, None
    df = pd.DataFrame(logs)
    df['date'] = pd.to_datetime(df['date']).dt.date
    status_counts = df.groupby(['date', 'status']).size().unstack(fill_value=0).reset_index()
    sentiments = df['sentiment'].value_counts().reset_index()
    sentiments.columns = ['Sentiment', 'Count']
    avg_rating = df.groupby('date')['rating'].mean().reset_index()
    return status_counts, sentiments, avg_rating

def download_button(data, filename, file_format):
    if file_format == "JSON":
        content = json.dumps(data, indent=4)
        st.download_button("Download JSON", content, file_name=filename, mime="application/json")
    elif file_format == "CSV":
        df = pd.DataFrame(data)
        csv = df.to_csv(index=False)
        st.download_button("Download CSV", csv, file_name=filename, mime="text/csv")
    elif file_format == "Excel":
        df = pd.DataFrame(data)
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name='Logs')
        st.download_button("Download Excel", output.getvalue(), file_name=filename, mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

# --- UI Configuration ---
st.set_page_config(page_title="OkadaGirlLogistic", layout="centered")

page_bg_color = """
<style>
    body {
        background: linear-gradient(135deg, #a8edea 0%, #fed6e3 100%);
        color: #333;
    }
    .css-18e3th9 {
        padding-top: 1rem;
    }
</style>
"""
st.markdown(page_bg_color, unsafe_allow_html=True)

col1, col2 = st.columns([7, 1])
with col1:
    st.title("OkadaGirlLogistic - Delivery Tracker")
    st.markdown("**Fast, Friendly & Reliable Deliveries**")
with col2:
    try:
        logo = Image.open("image_logo.png")
        logo = logo.resize((140, int(140 * logo.height / logo.width)))
        st.image(logo)
    except FileNotFoundError:
        st.warning("Logo image not found!")

st.markdown("""
###  Welcome to OkadaGirlLogistic
This app allows customers to submit delivery feedback for our logistics services.  
**Note:** Only the admin can view delivery history, feedback trends, and statistics by logging in.
""")

# --- Admin Session ---
if "admin_logged_in" not in st.session_state:
    st.session_state.admin_logged_in = False

st.sidebar.header("Admin Login")
if not st.session_state.admin_logged_in:
    admin_password = st.sidebar.text_input("Enter admin password", type="password")
    if st.sidebar.button("Login"):
        if admin_password == "admin123":
            st.session_state.admin_logged_in = True
            st.sidebar.success("Logged in as Admin")
        else:
            st.sidebar.error("Incorrect password")
else:
    st.sidebar.success("Logged in as Admin")
    if st.sidebar.button("Logout"):
        st.session_state.admin_logged_in = False
        st.sidebar.info("Logged out")

# --- Customer Feedback Entry ---
with st.expander("Add New Delivery Log"):
    customer = st.text_input("Customer Name")
    destination = st.text_input("Delivery Location (e.g., Ikeja, Lagos)")
    status = st.selectbox("Status", ["delivered", "pending", "not delivered"])
    feedback = st.text_area("Customer Feedback")

    st.markdown("""
    **Rating Guide:**  
    1 = Very Bad  
    2 = Bad  
    3 = Average  
    4 = Good  
    5 = Excellent
    """)
    rating = st.slider("Rating (1 to 5)", min_value=1, max_value=5, value=3)

    if st.button("Add Log"):
        if customer and destination and status and feedback and rating:
            add_log(customer, destination, status, feedback, rating)
            st.success("Log added successfully!")
        else:
            st.error("Please fill all fields.")

# --- Load and Filter Logs ---
logs = load_logs() if st.session_state.admin_logged_in else []

if st.session_state.admin_logged_in:
    st.subheader(" Search & Filter Logs")
    search_keyword = st.text_input("Search by customer name, date, or destination")
    filtered_logs = filter_logs(logs, search_keyword) if search_keyword else logs

    if filtered_logs:
        df = pd.DataFrame(filtered_logs)
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values(by="date").reset_index(drop=True)

        def highlight_sentiment(row):
            if row['sentiment'] == "Negative":
                return ['background-color: #ffe6e6'] * len(row)
            elif row['sentiment'] == "Positive":
                return ['background-color: #e6ffe6'] * len(row)
            return [''] * len(row)

        st.subheader("Delivery Logs")
        st.dataframe(df.style.apply(highlight_sentiment, axis=1), use_container_width=True)

        st.subheader(" Download Logs")
        download_button(filtered_logs, "delivery_logs.json", "JSON")
        download_button(filtered_logs, "delivery_logs.csv", "CSV")
        download_button(filtered_logs, "delivery_logs.xlsx", "Excel")

        st.subheader("Delivery Destination Map")
        map_data = []
        for log in filtered_logs:
            lat, lon = get_coordinates(log['destination'])
            if lat and lon:
                map_data.append({"lat": lat, "lon": lon})

        if map_data:
            st.map(pd.DataFrame(map_data))
        else:
            st.warning("No valid coordinates found for the entered destinations.")

        st.subheader("Summary Stats")
        total, delivered, pending, not_delivered, sentiments, avg_rating = show_summary(filtered_logs)
        summary_df = pd.DataFrame({
            "Metric": ["Total Deliveries", "Delivered", "Pending", "Not Delivered", "Positive", "Negative", "Neutral", "Average Rating"],
            "Count": [total, delivered, pending, not_delivered, sentiments["Positive"], sentiments["Negative"], sentiments["Neutral"], round(avg_rating, 2)]
        })
        st.table(summary_df)

        status_counts, sentiments_df, avg_rating_df = prepare_time_series(filtered_logs)

        if status_counts is not None and not status_counts.empty:
            st.subheader("Delivery Status Over Time")
            fig_status = px.line(status_counts, x='date', y=status_counts.columns[1:], title="Delivery Status Trends")
            st.plotly_chart(fig_status, use_container_width=True)

        if sentiments_df is not None and not sentiments_df.empty:
            st.subheader("Feedback Sentiment Distribution")
            fig_sentiment = px.pie(sentiments_df, names='Sentiment', values='Count', title="Customer Feedback Sentiment")
            st.plotly_chart(fig_sentiment, use_container_width=True)

        if avg_rating_df is not None and not avg_rating_df.empty:
            st.subheader("Average Customer Rating Over Time")
            fig_rating = px.line(avg_rating_df, x='date', y='rating', title="Average Ratings Trend")
            st.plotly_chart(fig_rating, use_container_width=True)

    else:
        st.info("Enter a search term above to view delivery logs.")
else:
    st.info("Please login as Admin to access delivery logs, charts, and map features.")
