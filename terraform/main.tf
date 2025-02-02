provider "aws" {
  region = "us-east-1"
}

# IAM Role for Lambda
resource "aws_iam_role" "lambda_role" {
  name = "lambda-cost-optimizer-role"
  
  assume_role_policy = <<EOF
  {
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Principal": { "Service": "lambda.amazonaws.com" },
        "Action": "sts:AssumeRole"
      }
    ]
  }
  EOF
}

# IAM Policy for Lambda Permissions
resource "aws_iam_policy" "lambda_policy" {
  name        = "lambda-cost-optimizer-policy"
  description = "Policy to allow Lambda to read cost and security data"

  policy = <<EOF
  {
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Action": [
          "ce:GetCostAndUsage",
          "cloudwatch:GetMetricData",
          "securityhub:GetFindings",
          "ses:SendEmail"
        ],
        "Resource": "*"
      }
    ]
  }
  EOF
}

# Attach Policy to Role
resource "aws_iam_role_policy_attachment" "lambda_attach" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = aws_iam_policy.lambda_policy.arn
}

# AWS Lambda Function
resource "aws_lambda_function" "cost_optimizer" {
  function_name = "cost_optimizer"
  role          = aws_iam_role.lambda_role.arn
  runtime       = "python3.9"
  handler       = "lambda_function.lambda_handler"

  filename = "lambda_function.zip"  # Upload Python script as zip

  source_code_hash = filebase64sha256("lambda_function.zip")
}

# CloudWatch Log Group for Lambda
resource "aws_cloudwatch_log_group" "lambda_logs" {
  name              = "/aws/lambda/cost_optimizer"
  retention_in_days = 7
}
