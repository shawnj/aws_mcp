# AWS Cost Explorer MCP Server

A Python-based Model Context Protocol (MCP) server that provides tools for accessing AWS Cost Explorer data. This server enables AI assistants like Claude to query and analyze your AWS costs and usage.

## Features

- **Cost and Usage Analysis**: Get detailed cost breakdowns by time period
- **Dimension Values**: Discover available services, regions, accounts, etc.
- **Flexible Filtering**: Filter costs by various dimensions
- **Multiple Metrics**: Support for different cost metrics (UnblendedCost, AmortizedCost, etc.)
- **Secure Authentication**: Uses AWS profiles or environment variables

## Prerequisites

- Python 3.8 or higher
- AWS account with Cost Explorer access
- AWS credentials configured (via AWS CLI, environment variables, or IAM roles)

## Installation

1. Clone or download this repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Configure AWS credentials (choose one method):

   **Option A: AWS CLI Profile**
   ```bash
   aws configure --profile your-profile-name
   ```

   **Option B: Environment Variables**
   ```bash
   export AWS_ACCESS_KEY_ID=your_access_key
   export AWS_SECRET_ACCESS_KEY=your_secret_key
   export AWS_DEFAULT_REGION=us-east-1
   ```

   **Option C: Use .env file**
   ```bash
   cp .env.example .env
   # Edit .env with your credentials
   ```

## Usage

### Running the Server

```bash
python aws_mcp/main.py
```

The server will start and listen for MCP connections on stdio.

### Connecting with Claude Desktop

Add the following to your Claude Desktop configuration file:

**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "aws-cost-explorer": {
			"command": "uv",
			"args": [
				"--directory",
				"/absolute/path/to/aws_mcp",
				"run",
				"aws-cost-explorer",
				"--profile",
				"oms-dev"
			],
    }
  }
}
```

## Available Tools

### 1. get_cost_and_usage

Get AWS costs for a specified time period with optional grouping and filtering.

**Parameters:**
- `start` (optional): Start date (YYYY-MM-DD, inclusive)
- `end` (optional): End date (YYYY-MM-DD, exclusive)
- `granularity`: Time granularity - "DAILY" or "MONTHLY" (default: "MONTHLY")
- `group_by` (optional): List of dimensions to group by (max 2)
- `metrics` (optional): List of cost metrics (default: ["UnblendedCost"])
- `filter_config` (optional): Filter by dimension and values
- `max_results`: Maximum results (1-100, default: 100)
- `profile` (optional): AWS profile name

**Example Usage:**
```
"What were my AWS costs last month by service?"
"Show me daily costs for the last 30 days"
"Get costs by region for this year"
```

### 2. get_dimension_values

Get available values for a specific Cost Explorer dimension (services, regions, etc.).

**Parameters:**
- `dimension`: The dimension name (SERVICE, REGION, LINKED_ACCOUNT, etc.)
- `time_period_start` (optional): Start date for search
- `time_period_end` (optional): End date for search
- `search_string` (optional): Filter dimension values
- `max_results`: Maximum results (1-1000, default: 50)
- `profile` (optional): AWS profile name

**Example Usage:**
```
"What AWS services am I using?"
"Show me all available regions in my account"
"List my linked accounts"
```

## Supported Dimensions

- SERVICE
- LINKED_ACCOUNT
- REGION
- USAGE_TYPE
- OPERATION
- INSTANCE_TYPE
- PURCHASE_TYPE
- RECORD_TYPE

## Supported Metrics

- UnblendedCost
- AmortizedCost
- NetAmortizedCost
- NetUnblendedCost
- NormalizedUsageAmount
- UsageQuantity
- BlendedCost

## Security Considerations

- This server requires read access to AWS Cost Explorer
- Use least-privilege IAM policies
- Store credentials securely using AWS best practices
- Consider using IAM roles for EC2/Lambda deployments

## Required AWS Permissions

Your AWS credentials need the following permissions:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ce:GetCostAndUsage",
        "ce:GetDimensionValues"
      ],
      "Resource": "*"
    }
  ]
}
```

## Troubleshooting

### Common Issues

1. **"No credentials found"**
   - Ensure AWS credentials are properly configured
   - Check that the profile name is correct (if using profiles)

2. **"Access denied"**
   - Verify IAM permissions for Cost Explorer
   - Ensure billing access is enabled for your account

3. **"Invalid date format"**
   - Use YYYY-MM-DD format for dates
   - Ensure end date is after start date

## Testing

The server includes a test script to verify functionality:

```bash
# Basic functionality test (with credentials configured)
python test_server.py
```

Expected output when working correctly:
```
Initializing connection...
Available tools: ['get_cost_and_usage', 'get_dimension_values']
Testing get_cost_and_usage tool...
```

If you see "Unable to locate credentials", configure AWS credentials as described in the Configuration section above.

## Development

To extend this server:

1. Add new tools using the `@server.tool()` decorator
2. Follow the MCP protocol specifications
3. Use proper error handling for AWS API calls
4. Test with different AWS account configurations

## License

This project is open source. See LICENSE file for details.
