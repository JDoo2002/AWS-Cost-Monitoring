import boto3
import csv
import io
import json
import logging
import datetime
import os

# Initialize AWS Clients
ce = boto3.client("ce")
securityhub = boto3.client("securityhub")
ses = boto3.client("ses")
s3 = boto3.client("s3")

# AWS Config (Use environment variables)
SENDER = os.getenv("SENDER_EMAIL", "your-email@example.com")  # Default placeholder
RECIPIENT = os.getenv("RECIPIENT_EMAIL", "your-email@example.com")
AWS_REGION = os.getenv("us-east-1")  # Keep default unless changing region
S3_BUCKET = os.getenv("S3_BUCKET", "your-s3-bucket-name")


# Set up Logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def get_cost_report():
    """Fetch AWS cost data for the last 7 days"""
    try:
        today = datetime.date.today()
        start_date = (today - datetime.timedelta(days=7)).strftime("%Y-%m-%d")
        end_date = today.strftime("%Y-%m-%d")

        response = ce.get_cost_and_usage(
            TimePeriod={"Start": start_date, "End": end_date},
            Granularity="DAILY",
            Metrics=["UnblendedCost"]
        )

        logger.info("AWS Cost Report Fetched Successfully")
        return response["ResultsByTime"]

    except Exception as e:
        logger.error(f"Error fetching cost report: {str(e)}")
        return []

def check_security_findings():
    """Fetch AWS Security Hub findings"""
    try:
        response = securityhub.get_findings(MaxResults=5)
        return response["Findings"]
    except securityhub.exceptions.InvalidAccessException:
        logger.warning("AWS Security Hub is not enabled. Skipping security checks.")
        return []
    except Exception as e:
        logger.error(f"Error fetching security findings: {str(e)}")
        return []

def send_email(cost_data, security_data):
    """Send a nicely formatted email alert with cost and security findings"""
    try:
        subject = "🚨 AWS Cost & Security Alert 🚨"
        
        # Formatting the cost report
        cost_table = "<h3>💰 AWS Cost Report (Last 7 Days)</h3><table border='1'><tr><th>Date</th><th>Cost (USD)</th></tr>"
        for entry in cost_data:
            date = entry["TimePeriod"]["Start"]
            cost = float(entry["Total"]["UnblendedCost"].get("Amount", 0))
            cost_table += f"<tr><td>{date}</td><td>${cost:.4f} USD</td></tr>"
        cost_table += "</table>"

        # Formatting security findings
        security_section = "<h3>🔒 AWS Security Findings</h3>"
        if security_data:
            for finding in security_data:
                title = finding["Title"]
                severity = finding["Severity"]["Label"]
                description = finding["Description"]
                remediation_url = finding["Remediation"]["Recommendation"]["Url"]
                
                security_section += f"""
                <p><strong>🚨 {title}</strong></p>
                <p><strong>Severity:</strong> {severity}</p>
                <p>{description}</p>
                <p>🔗 <a href="{remediation_url}">Fix Here</a></p>
                <hr>
                """
        else:
            security_section += "<p>No security issues found ✅</p>"

        # Email Body
        body = f"""
        <html>
        <body>
            <h2>🚀 AWS Cost & Security Report</h2>
            {cost_table}
            {security_section}
        </body>
        </html>
        """

        ses.send_email(
            Source=SENDER,
            Destination={"ToAddresses": [RECIPIENT]},
            Message={
                "Subject": {"Data": subject},
                "Body": {"Html": {"Data": body}}
            }
        )
        logger.info("✅ Email sent successfully with formatted report.")

    except Exception as e:
        logger.error(f"❌ Error sending email: {str(e)}")


def save_to_s3(cost_data, security_data):
    """Save cost and security data as separate CSV files for QuickSight & send email with proper formatting."""
    try:
        today = datetime.date.today()

        # ✅ Save Cost Data for QuickSight (No "$" symbol)
        cost_filename = f"aws_cost_report_{today}.csv"
        cost_buffer = io.StringIO()
        cost_writer = csv.writer(cost_buffer)
        cost_writer.writerow(["Date", "UnblendedCost (USD)"])
        for entry in cost_data:
            date = entry["TimePeriod"]["Start"]
            cost = float(entry["Total"]["UnblendedCost"].get("Amount", 0))
            cost_writer.writerow([date, f"{cost:.4f}"])  # No "$" symbol for QuickSight
        s3.put_object(
            Bucket=S3_BUCKET,
            Key=cost_filename,
            Body=cost_buffer.getvalue(),
            ContentType="text/csv"
        )
        logger.info(f"✅ Cost report saved as CSV (QuickSight format): {cost_filename}")

        # ✅ Save Security Findings (No Change)
        security_filename = f"aws_security_findings_{today}.csv"
        security_buffer = io.StringIO()
        security_writer = csv.writer(security_buffer)
        security_writer.writerow(["Title", "Severity", "Description", "Fix URL"])
        for finding in security_data:
            title = finding["Title"]
            severity = finding["Severity"]["Label"]
            description = finding["Description"]
            remediation_url = finding["Remediation"]["Recommendation"]["Url"]
            security_writer.writerow([title, severity, description, remediation_url])
        s3.put_object(
            Bucket=S3_BUCKET,
            Key=security_filename,
            Body=security_buffer.getvalue(),
            ContentType="text/csv"
        )
        logger.info(f"✅ Security findings saved as CSV: {security_filename}")

        # ✅ Format Cost Data for Email (WITH "$" symbol)
        email_cost_data = "\n".join(
            f"{entry['TimePeriod']['Start']}: ${float(entry['Total']['UnblendedCost'].get('Amount', 0)):.4f}"
            for entry in cost_data
        )

        # ✅ Send email with correct formatting
        send_email(email_cost_data, security_data)

    except Exception as e:
        logger.error(f"❌ Error saving CSV to S3: {str(e)}")


def lambda_handler(event, context):
    logger.info("🚀 Lambda function started.")

    # Get cost & security reports
    cost_report = get_cost_report()
    security_findings = check_security_findings()

    # Calculate total AWS cost
    total_cost = sum(float(c["Total"].get("Amount", 0)) for c in cost_report)

    # ✅ Send email if cost > $50 or security risks exist
    if len(security_findings) > 0 or total_cost > 50:
        send_email(cost_report, security_findings)

    # ✅ Save both cost & security data to S3 for QuickSight
    save_to_s3(cost_report, security_findings)

    logger.info("✅ Lambda function execution completed.")
    return {"statusCode": 200, "body": json.dumps("Monitoring completed.")}

