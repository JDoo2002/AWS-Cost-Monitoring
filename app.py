from flask import Flask, render_template, jsonify
import plotly.graph_objects as go
import json
import pandas as pd
import plotly.express as px
import fetch_aws_cost  # Import the AWS cost fetching script

app = Flask(__name__)

# Run the cost fetching script when the app starts
fetch_aws_cost.get_cost_report()

def load_cost_data():
    """Load AWS cost data from JSON"""
    with open("aws_cost_report.json", "r") as file:
        data = json.load(file)
    
    records = []
    for entry in data:
        date = entry["TimePeriod"]["Start"]
        cost = float(entry["Total"]["UnblendedCost"].get("Amount", 0))
        records.append({"Date": date, "Cost": cost})

    return pd.DataFrame(records)

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/dashboard")
def dashboard():
    """Generate cost dashboard with multiple visualizations"""
    df = load_cost_data()

    # ✅ KPI Widget - Latest AWS Cost
    latest_cost = df.iloc[-1]["Cost"]
    kpi_fig = go.Figure(go.Indicator(
        mode="number",
        value=latest_cost,
        title={"text": "Latest AWS Cost ($)"}
    ))

    # ✅ Line Chart - AWS Cost Trend
    line_fig = px.line(df, x="Date", y="Cost", title="AWS Cost Trend (Last 7 Days)", markers=True)

    # ✅ Bar Chart - AWS Cost Breakdown
    bar_fig = px.bar(df, x="Date", y="Cost", title="Daily AWS Cost Breakdown", color="Cost")

    # Convert charts to HTML
    kpi_html = kpi_fig.to_html(full_html=False)
    line_html = line_fig.to_html(full_html=False)
    bar_html = bar_fig.to_html(full_html=False)

    return render_template("dashboard.html", kpi_html=kpi_html, line_html=line_html, bar_html=bar_html)

if __name__ == "__main__":
    app.run(debug=True)
