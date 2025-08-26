"""Constants for AWS Cost Explorer MCP Server."""

# AWS Cost Explorer allowed dimensions
DIMENSIONS_ALLOWED = [
    "SERVICE",
    "LINKED_ACCOUNT", 
    "REGION",
    "USAGE_TYPE",
    "OPERATION",
    "INSTANCE_TYPE",
    "PURCHASE_TYPE",
    "RECORD_TYPE",
]

# AWS Cost Explorer allowed metrics
METRICS_ALLOWED = [
    "UnblendedCost",
    "AmortizedCost", 
    "NetAmortizedCost",
    "NetUnblendedCost",
    "NormalizedUsageAmount",
    "UsageQuantity",
    "BlendedCost",
]

# Default values
DEFAULT_GRANULARITY = "MONTHLY"
DEFAULT_METRICS = ["UnblendedCost"]
DEFAULT_MAX_RESULTS = 50
DEFAULT_DAYS_LOOKBACK = 30

# AWS Configuration
AWS_REGION = "us-east-1"  # Cost Explorer is a global service
USER_AGENT = "mcp-aws-cost-explorer/1.0"
MAX_RETRIES = 10
