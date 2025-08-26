"""Configuration settings for AWS Cost Explorer MCP Server."""

import os
from typing import Optional


class Config:
    """Configuration class for the AWS Cost Explorer MCP Server."""
    
    # AWS Configuration
    DEFAULT_AWS_REGION: str = "us-east-1"
    MAX_RETRIES: int = 10
    USER_AGENT: str = "mcp-aws-cost-explorer/1.0"
    
    # Cost Explorer Defaults
    DEFAULT_GRANULARITY: str = "MONTHLY"
    DEFAULT_METRICS: list = ["UnblendedCost"]
    DEFAULT_MAX_RESULTS: int = 50
    DEFAULT_DAYS_LOOKBACK: int = 30
    
    # Server Configuration
    SERVER_NAME: str = "aws-cost-explorer"
    
    @classmethod
    def get_aws_profile(cls) -> Optional[str]:
        """Get AWS profile from environment variable."""
        return os.getenv("AWS_PROFILE")
    
    @classmethod
    def get_aws_region(cls) -> str:
        """Get AWS region from environment variable or use default."""
        return os.getenv("AWS_DEFAULT_REGION", cls.DEFAULT_AWS_REGION)
