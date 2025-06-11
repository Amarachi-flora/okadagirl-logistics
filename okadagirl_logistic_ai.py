import json
import os
from datetime import datetime
from textblob import TextBlob
from colorama import Fore, Style, init
from geopy.distance import geodesic
from geopy.geocoders import Nominatim

init(autoreset=True)

LOG_FILE = "delivery_logs.json"

# For geolocation (route optimization)
geolocator = Nominatim(user_agent="okadagirl_logistics")

def load_logs():
    if not os.path.exists(LOG_FILE):
        return []
    with open(LOG_FILE, "r") as file:
        return json.load(file)

def save_logs(logs):
    with open(LOG_FILE, "w") as file:
        json.dump(logs, file, indent=4)

def export_logs_to_csv():
    logs = load_logs()
    if not logs:
        return

    export_file = "delivery_logs.csv"
    with open(export_file, "w") as f:
        f.write("Date,Customer,Destination,Status,Feedback,Sentiment,Predicted_Delivery_Time\n")
        for log in logs:
            feedback_safe = log['feedback'].replace(',', ';')
            pred_time = log.get('predicted_delivery_time', 'N/A')
            f.write(f"{log['date']},{log['customer']},{log['destination']},{log['status']},{feedback_safe},{log['sentiment']},{pred_time}\n")

def analyze_sentiment(feedback):
    analysis = TextBlob(feedback)
    polarity = analysis.sentiment.polarity
    if polarity > 0:
        return "Positive"
    elif polarity < 0:
        return "Negative"
    else:
        return "Neutral"

def predict_delivery_time(destination):
    # Very basic predictive model:
    # Average delivery time = 30 minutes + 1 min per km from a fixed depot location (e.g. Lagos)
    depot_coords = (6.5244, 3.3792)  # Lagos approx coordinates
    try:
        location = geolocator.geocode(destination)
        if location:
            dest_coords = (location.latitude, location.longitude)
            distance_km = geodesic(depot_coords, dest_coords).km
            estimated_time = 30 + distance_km  # minutes
            return f"{int(estimated_time)} mins"
        else:
            return "Unknown"
    except Exception:
        return "Unknown"

def print_log(log):
    print(f"{Fore.CYAN}Date: {log['date']}")
    print(f"{Fore.YELLOW}Customer: {log['customer']}")
    print(f"{Fore.GREEN}Destination: {log['destination']}")
    print(f"{Fore.MAGENTA}Status: {log['status']}")
    print(f"{Fore.BLUE}Feedback: {log['feedback']} ({log['sentiment']})")
    pred_time = log.get('predicted_delivery_time', 'N/A')
    print(f"{Fore.LIGHTMAGENTA_EX}Predicted Delivery Time: {pred_time}\n")

def add_log():
    print(f"\n{Fore.CYAN}--- Add New Delivery Log ---{Style.RESET_ALL}")
    customer = input("Customer Name: ")
    destination = input("Destination: ")
    status = input("Status (delivered/pending): ")
    feedback = input("Customer Feedback: ")
    date = datetime.now().strftime("%Y-%m-%d %H:%M")
    sentiment = analyze_sentiment(feedback)
    predicted_time = predict_delivery_time(destination)

    new_log = {
        "customer": customer,
        "destination": destination,
        "status": status,
        "feedback": feedback,
        "sentiment": sentiment,
        "date": date,
        "predicted_delivery_time": predicted_time
    }

    logs = load_logs()
    logs.append(new_log)
    save_logs(logs)
    export_logs_to_csv()
    print(f"{Fore.GREEN}Log saved successfully. JSON and CSV updated.\n")

def view_logs():
    logs = load_logs()
    if not logs:
        print(f"{Fore.RED}No delivery logs found.\n")
        return

    print(f"\n{Fore.CYAN}--- All Delivery Logs ---{Style.RESET_ALL}")
    for log in logs:
        print_log(log)

def filter_logs():
    logs = load_logs()
    if not logs:
        print(f"{Fore.RED}No delivery logs found.\n")
        return

    keyword = input("Enter customer name or date to filter: ").lower()
    filtered = [log for log in logs if keyword in log['customer'].lower() or keyword in log['date'].lower()]

    if not filtered:
        print(f"{Fore.YELLOW}No logs match your search.\n")
    else:
        for log in filtered:
            print_log(log)

def show_summary():
    logs = load_logs()
    if not logs:
        print(f"{Fore.RED}No delivery logs to summarize.\n")
        return

    total = len(logs)
    delivered = sum(1 for log in logs if log['status'].lower() == 'delivered')
    pending = total - delivered
    sentiments = {"Positive": 0, "Negative": 0, "Neutral": 0}
    for log in logs:
        sentiments[log['sentiment']] += 1

    print(f"\n{Fore.CYAN}--- Delivery Summary ---")
    print(f"Total Deliveries: {total}")
    print(f"Delivered: {Fore.GREEN}{delivered}")
    print(f"Pending: {Fore.YELLOW}{pending}")
    print(f"\nSentiment Breakdown:")
    for k, v in sentiments.items():
        print(f"{k}: {v}")
    print()

def optimize_route():
    logs = load_logs()
    if not logs:
        print(f"{Fore.RED}No delivery logs found for route optimization.\n")
        return

    depot_coords = (6.5244, 3.3792)  # Lagos depot
    destinations = []

    # Get geocoded destinations
    for log in logs:
        try:
            location = geolocator.geocode(log['destination'])
            if location:
                destinations.append((log['destination'], (location.latitude, location.longitude)))
            else:
                print(f"{Fore.YELLOW}Warning: Could not geocode destination: {log['destination']}")
        except Exception:
            print(f"{Fore.YELLOW}Error geocoding {log['destination']}")

    if not destinations:
        print(f"{Fore.RED}No valid destinations for optimization.\n")
        return

    # Simple nearest neighbor route ordering starting from depot
    route = []
    current_loc = depot_coords
    remaining = destinations.copy()

    while remaining:
        next_dest = min(remaining, key=lambda x: geodesic(current_loc, x[1]).km)
        route.append(next_dest[0])
        current_loc = next_dest[1]
        remaining.remove(next_dest)

    print(f"\n{Fore.CYAN}-Optimized Delivery Route-{Style.RESET_ALL}")
    for i, dest in enumerate(route, 1):
        print(f"{i}. {dest}")
    print()

def chatbot():
    print(f"\n{Fore.CYAN}-OkadaGirl Logistic Chatbot-{Style.RESET_ALL}")
    print("Ask me about deliveries or commands. Type 'exit' to quit.\n")
    logs = load_logs()
    while True:
        question = input("You: ").strip().lower()
        if question == "exit":
            print("Chatbot session ended.\n")
            break
        elif "how many deliveries" in question or "total deliveries" in question:
            print(f"Bot: Total deliveries so far: {len(logs)}")
        elif "pending deliveries" in question:
            pending = sum(1 for log in logs if log['status'].lower() == 'pending')
            print(f"Bot: Pending deliveries: {pending}")
        elif "delivered deliveries" in question or "completed deliveries" in question:
            delivered = sum(1 for log in logs if log['status'].lower() == 'delivered')
            print(f"Bot: Delivered deliveries: {delivered}")
        elif "summary" in question:
            sentiments = {"Positive": 0, "Negative": 0, "Neutral": 0}
            for log in logs:
                sentiments[log['sentiment']] += 1
            print(f"Bot: Delivery Summary - Total: {len(logs)}, Delivered: {sum(1 for l in logs if l['status'].lower()=='delivered')}, Pending: {sum(1 for l in logs if l['status'].lower()=='pending')}")
            print(f"Sentiments - Positive: {sentiments['Positive']}, Negative: {sentiments['Negative']}, Neutral: {sentiments['Neutral']}")
        else:
            print("Bot: Sorry, I don't understand. Try asking about deliveries or type 'exit'.")

def main():
    while True:
        print(f"""
{Fore.LIGHTBLUE_EX}=OkadaGirlLogistic – Delivery Tracker={Style.RESET_ALL}
[1] Add New Delivery Log
[2] View All Logs
[3] Search/Filter Logs
[4] Show Summary Stats
[5] Export Logs to CSV
[6] Optimize Delivery Route
[7] Chatbot Support
[8] Exit
        """)

        choice = input("Select an option: ")

        if choice == "1":
            add_log()
        elif choice == "2":
            view_logs()
        elif choice == "3":
            filter_logs()
        elif choice == "4":
            show_summary()
        elif choice == "5":
            export_logs_to_csv()
            print(f"{Fore.GREEN}Logs exported to delivery_logs.csv\n")
        elif choice == "6":
            optimize_route()
        elif choice == "7":
            chatbot()
        elif choice == "8":
            print("Goodbye.")
            break
        else:
            print(f"{Fore.RED}Invalid choice. Please try again.\n")

if __name__ == "__main__":
    main()
