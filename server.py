import asyncio
import json
import os
from datetime import date, timedelta, datetime
from typing import Any, Dict, List, Optional

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError, NoCredentialsError
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Initialize MCP server
server = Server("aws-cost-explorer")

# AWS Cost Explorer constants
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

METRICS_ALLOWED = [
    "UnblendedCost",
    "AmortizedCost", 
    "NetAmortizedCost",
    "NetUnblendedCost",
    "NormalizedUsageAmount",
    "UsageQuantity",
    "BlendedCost",
]

def _iso_date(d: date) -> str:
    """Convert date to ISO format string"""
    return d.strftime("%Y-%m-%d")

def _validate_date(s: str) -> str:
    """Validate date string format (YYYY-MM-DD)"""
    try:
        datetime.strptime(s, "%Y-%m-%d")
        return s
    except ValueError:
        raise ValueError(f"Invalid date format: {s}. Expected YYYY-MM-DD")

def _default_dates(granularity: str) -> tuple[str, str]:
    """Generate default start and end dates based on granularity"""
    today = date.today()
    if granularity == "DAILY":
        start = today - timedelta(days=30)
        end = today
    else:  # MONTHLY
        start = today.replace(day=1)
        end = today
    return _iso_date(start), _iso_date(end)

def _get_ce_client(profile: Optional[str] = None) -> boto3.client:
    """Create AWS Cost Explorer client with optional profile"""
    try:
        session_kwargs = {}
        if profile:
            session_kwargs["profile_name"] = profile
        
        session = boto3.Session(**session_kwargs)
        
        # Cost Explorer is a global service; us-east-1 is canonical
        return session.client(
            "ce",
            region_name="us-east-1",
            config=Config(
                retries={"max_attempts": 10, "mode": "standard"},
                user_agent_extra="mcp-aws-cost-explorer/1.0"
            ),
        )
    except NoCredentialsError:
        raise ValueError("AWS credentials not found. Please configure AWS credentials or specify a profile.")

@server.list_tools()
async def handle_list_tools() -> list[Tool]:
    """List available tools"""
    return [
        Tool(
            name="get_cost_and_usage",
            description="Get AWS costs for a time period, optionally grouped by dimensions. End date is exclusive (YYYY-MM-DD).",
            inputSchema={
                "type": "object",
                "properties": {
                    "start": {"type": "string", "description": "Start date (YYYY-MM-DD, inclusive)"},
                    "end": {"type": "string", "description": "End date (YYYY-MM-DD, exclusive)"},
                    "granularity": {"type": "string", "enum": ["DAILY", "MONTHLY"], "default": "MONTHLY"},
                    "group_by": {
                        "type": "array",
                        "items": {"type": "string", "enum": DIMENSIONS_ALLOWED},
                        "description": "Dimensions to group by (max 2 per CE API).",
                    },
                    "metrics": {
                        "type": "array",
                        "items": {"type": "string", "enum": METRICS_ALLOWED},
                        "default": ["UnblendedCost"],
                    },
                    "filter_config": {
                        "type": "object",
                        "properties": {
                            "dimension": {"type": "string", "enum": DIMENSIONS_ALLOWED},
                            "values": {"type": "array", "items": {"type": "string"}},
                        },
                        "required": ["dimension", "values"],
                    },
                    "next_page_token": {"type": "string"},
                    "profile": {"type": "string", "description": "AWS profile name from ~/.aws/config"},
                },
            },
        ),
        Tool(
            name="get_dimension_values",
            description="Get available values for a specific Cost Explorer dimension.",
            inputSchema={
                "type": "object",
                "properties": {
                    "dimension": {"type": "string", "enum": DIMENSIONS_ALLOWED},
                    "time_period_start": {"type": "string", "description": "Start date (YYYY-MM-DD)"},
                    "time_period_end": {"type": "string", "description": "End date (YYYY-MM-DD)"},
                    "search_string": {"type": "string"},
                    "max_results": {"type": "integer", "minimum": 1, "maximum": 1000, "default": 50},
                    "next_page_token": {"type": "string"},
                    "profile": {"type": "string", "description": "AWS profile name from ~/.aws/config"},
                },
                "required": ["dimension"],
            },
        ),
    ]

@server.call_tool()
async def handle_call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Handle tool calls"""
    if name == "get_cost_and_usage":
        result = await get_cost_and_usage(**arguments)
        return [TextContent(type="text", text=result)]
    elif name == "get_dimension_values":
        result = await get_dimension_values(**arguments)
        return [TextContent(type="text", text=result)]
    else:
        raise ValueError(f"Unknown tool: {name}")

async def get_cost_and_usage(
    start: Optional[str] = None,
    end: Optional[str] = None,
    granularity: str = "MONTHLY",
    group_by: Optional[List[str]] = None,
    metrics: Optional[List[str]] = None,
    filter_config: Optional[Dict[str, Any]] = None,
    next_page_token: Optional[str] = None,
    profile: Optional[str] = None,
) -> str:
    """
    Get AWS costs for a time period, optionally grouped by dimensions.
    
    Args:
        start: Start date (YYYY-MM-DD, inclusive). Defaults to appropriate period.
        end: End date (YYYY-MM-DD, exclusive). Defaults to today.
        granularity: Time granularity - DAILY or MONTHLY
        group_by: List of dimensions to group by (max 2 per AWS API)
        metrics: List of cost metrics to retrieve
        filter_config: Filter configuration with dimension and values
        max_results: Maximum number of results (1-100)
        next_page_token: Token for pagination
        profile: AWS profile name from ~/.aws/config
    
    Returns:
        JSON response with cost data
    """
    # Set default values
    metrics = metrics or ["UnblendedCost"]
    
    # Validate inputs
    if granularity not in ["DAILY", "MONTHLY"]:
        raise ValueError("granularity must be 'DAILY' or 'MONTHLY'")
    
    if group_by:
        invalid_dimensions = [d for d in group_by if d not in DIMENSIONS_ALLOWED]
        if invalid_dimensions:
            raise ValueError(f"Invalid group_by dimensions: {invalid_dimensions}")
        if len(group_by) > 2:
            raise ValueError("Maximum 2 group_by dimensions allowed")
    
    invalid_metrics = [m for m in metrics if m not in METRICS_ALLOWED] 
    if invalid_metrics:
        raise ValueError(f"Invalid metrics: {invalid_metrics}")
        
    # Set default dates if not provided
    if not start or not end:
        start, end = _default_dates(granularity)
    else:
        start = _validate_date(start)
        end = _validate_date(end)
    
    def _call_ce_api():
        """Make the actual API call (synchronous)"""
        client = _get_ce_client(profile)
        
        request_params: Dict[str, Any] = {
            "TimePeriod": {"Start": start, "End": end},
            "Granularity": granularity,
            "Metrics": metrics,
        }
        
        if group_by:
            request_params["GroupBy"] = [
                {"Type": "DIMENSION", "Key": dimension}
                for dimension in group_by[:2]  # AWS allows max 2
            ]
        
        if filter_config:
            request_params["Filter"] = {
                "Dimensions": {
                    "Key": filter_config["dimension"],
                    "Values": filter_config.get("values", []),
                    "MatchOptions": ["EQUALS"],
                }
            }
        
        if next_page_token:
            request_params["NextPageToken"] = next_page_token
        
        try:
            response = client.get_cost_and_usage(**request_params)
            
            # Format response
            result = {
                "time_period": response.get("TimePeriod", {"start": start, "end": end}),
                "granularity": granularity,
                "metrics": metrics,
                "group_by": group_by or [],
                "results_by_time": response.get("ResultsByTime", []),
                "next_page_token": response.get("NextPageToken"),
                "total_results": len(response.get("ResultsByTime", [])),
            }
            
            return result
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            raise ValueError(f"AWS Cost Explorer API error ({error_code}): {error_message}")
    
    # Execute API call in thread pool to avoid blocking
    result = await asyncio.to_thread(_call_ce_api)
    
    # Return as JSON string
    return json.dumps(result, separators=(",", ":"), default=str, indent=2)

async def get_dimension_values(
    dimension: str,
    time_period_start: Optional[str] = None,
    time_period_end: Optional[str] = None,
    search_string: Optional[str] = None,
    max_results: int = 50,
    next_page_token: Optional[str] = None,
    profile: Optional[str] = None,
) -> str:
    """
    Get available values for a specific Cost Explorer dimension.
    
    Args:
        dimension: The dimension to get values for (e.g., 'SERVICE', 'REGION')
        time_period_start: Start date for dimension search (YYYY-MM-DD)
        time_period_end: End date for dimension search (YYYY-MM-DD)
        search_string: Search string to filter dimension values
        max_results: Maximum number of results (1-1000)
        next_page_token: Token for pagination
        profile: AWS profile name from ~/.aws/config
    
    Returns:
        JSON response with dimension values
    """
    # Validate dimension
    if dimension not in DIMENSIONS_ALLOWED:
        raise ValueError(f"Invalid dimension: {dimension}. Allowed: {DIMENSIONS_ALLOWED}")
    
    if not (1 <= max_results <= 1000):
        raise ValueError("max_results must be between 1 and 1000")
    
    # Set default time period (last 30 days)
    if not time_period_start or not time_period_end:
        today = date.today()
        time_period_start = _iso_date(today - timedelta(days=30))
        time_period_end = _iso_date(today)
    else:
        time_period_start = _validate_date(time_period_start)
        time_period_end = _validate_date(time_period_end)
    
    def _call_dimension_api():
        """Make the dimension values API call"""
        client = _get_ce_client(profile)
        
        request_params = {
            "Dimension": dimension,
            "TimePeriod": {
                "Start": time_period_start,
                "End": time_period_end
            },
            "MaxResults": max_results,
        }
        
        if search_string:
            request_params["SearchString"] = search_string
        
        if next_page_token:
            request_params["NextPageToken"] = next_page_token
        
        try:
            response = client.get_dimension_values(**request_params)
            
            result = {
                "dimension": dimension,
                "time_period": {
                    "start": time_period_start,
                    "end": time_period_end
                },
                "dimension_values": response.get("DimensionValues", []),
                "next_page_token": response.get("NextPageToken"),
                "total_size": response.get("TotalSize", 0),
                "return_size": response.get("ReturnSize", 0),
            }
            
            return result
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            raise ValueError(f"AWS Cost Explorer API error ({error_code}): {error_message}")
    
    result = await asyncio.to_thread(_call_dimension_api)
    
    return json.dumps(result, separators=(",", ":"), default=str, indent=2)

if __name__ == "__main__":
    async def main():
        async with stdio_server() as (read, write):
            await server.run(read, write, server.create_initialization_options())
    
    asyncio.run(main())
