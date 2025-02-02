import boto3
import json
import datetime
import os

# Load AWS credentials from environment variables
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")

# AWS Cost Explorer Client
ce = boto3.client(
    "ce",
    region_name=AWS_REGION,
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY
)

def get_cost_report():
    """Fetch AWS cost data for the last 7 days"""
    today = datetime.date.today()
    start_date = (today - datetime.timedelta(days=7)).strftime("%Y-%m-%d")
    end_date = today.strftime("%Y-%m-%d")

    response = ce.get_cost_and_usage(
        TimePeriod={"Start": start_date, "End": end_date},
        Granularity="DAILY",
        Metrics=["UnblendedCost"]
    )

    with open("aws_cost_report.json", "w") as file:
        json.dump(response["ResultsByTime"], file, indent=2)

    print("✅ AWS Cost Report Updated!")

# If run as a script, fetch the cost data
if __name__ == "__main__":
    get_cost_report()
