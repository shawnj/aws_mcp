"""Unit tests for the AWS Cost Explorer service layer."""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import date
import json

from aws_mcp.cost_explorer import AWSCostExplorerClient, CostExplorerService, AWSCostExplorerError


class TestAWSCostExplorerClient:
    """Test cases for AWS Cost Explorer client."""
    
    def test_init_without_profile(self):
        """Test client initialization without profile."""
        client = AWSCostExplorerClient()
        assert client.profile is None
        assert client._client is None
    
    def test_init_with_profile(self):
        """Test client initialization with profile."""
        client = AWSCostExplorerClient(profile="test-profile")
        assert client.profile == "test-profile"
        assert client._client is None
    
    @patch('aws_mcp.cost_explorer.boto3.Session')
    def test_create_client_success(self, mock_session):
        """Test successful client creation."""
        mock_boto_client = Mock()
        mock_session_instance = Mock()
        mock_session_instance.client.return_value = mock_boto_client
        mock_session.return_value = mock_session_instance
        
        client = AWSCostExplorerClient()
        boto_client = client.client
        
        mock_session.assert_called_once_with()
        mock_session_instance.client.assert_called_once()
        assert boto_client == mock_boto_client
    
    @patch('aws_mcp.cost_explorer.boto3.Session')
    def test_create_client_with_profile(self, mock_session):
        """Test client creation with AWS profile."""
        mock_boto_client = Mock()
        mock_session_instance = Mock()
        mock_session_instance.client.return_value = mock_boto_client
        mock_session.return_value = mock_session_instance
        
        client = AWSCostExplorerClient(profile="test-profile")
        boto_client = client.client
        
        mock_session.assert_called_once_with(profile_name="test-profile")
        assert boto_client == mock_boto_client
    
    @patch('aws_mcp.cost_explorer.boto3.Session')
    def test_create_client_no_credentials(self, mock_session):
        """Test client creation failure with no credentials."""
        from botocore.exceptions import NoCredentialsError
        mock_session.side_effect = NoCredentialsError()
        
        client = AWSCostExplorerClient()
        
        with pytest.raises(AWSCostExplorerError, match="AWS credentials not found"):
            _ = client.client


class TestCostExplorerService:
    """Test cases for Cost Explorer service."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_client = Mock()
        self.mock_aws_client = Mock()
        self.mock_aws_client.client = self.mock_client
        self.service = CostExplorerService(self.mock_aws_client)
    
    def test_validate_granularity_valid(self):
        """Test granularity validation with valid values."""
        self.service._validate_granularity("DAILY")
        self.service._validate_granularity("MONTHLY")
        # Should not raise any exception
    
    def test_validate_granularity_invalid(self):
        """Test granularity validation with invalid values."""
        with pytest.raises(AWSCostExplorerError, match="granularity must be"):
            self.service._validate_granularity("WEEKLY")
    
    def test_validate_group_by_valid(self):
        """Test group_by validation with valid dimensions."""
        self.service._validate_group_by(["SERVICE", "REGION"])
        self.service._validate_group_by(None)
        # Should not raise any exception
    
    def test_validate_group_by_invalid_dimension(self):
        """Test group_by validation with invalid dimensions."""
        with pytest.raises(AWSCostExplorerError, match="Invalid group_by dimensions"):
            self.service._validate_group_by(["INVALID_DIMENSION"])
    
    def test_validate_group_by_too_many(self):
        """Test group_by validation with too many dimensions."""
        with pytest.raises(AWSCostExplorerError, match="Maximum 2 group_by dimensions"):
            self.service._validate_group_by(["SERVICE", "REGION", "USAGE_TYPE"])
    
    def test_validate_metrics_valid(self):
        """Test metrics validation with valid values."""
        self.service._validate_metrics(["UnblendedCost"])
        self.service._validate_metrics(["UnblendedCost", "AmortizedCost"])
        # Should not raise any exception
    
    def test_validate_metrics_invalid(self):
        """Test metrics validation with invalid values."""
        with pytest.raises(AWSCostExplorerError, match="Invalid metrics"):
            self.service._validate_metrics(["InvalidMetric"])
    
    def test_validate_dimension_valid(self):
        """Test dimension validation with valid values."""
        self.service._validate_dimension("SERVICE")
        self.service._validate_dimension("REGION")
        # Should not raise any exception
    
    def test_validate_dimension_invalid(self):
        """Test dimension validation with invalid values."""
        with pytest.raises(AWSCostExplorerError, match="Invalid dimension"):
            self.service._validate_dimension("INVALID_DIMENSION")
    
    def test_validate_max_results_valid(self):
        """Test max_results validation with valid values."""
        self.service._validate_max_results(1)
        self.service._validate_max_results(500)
        self.service._validate_max_results(1000)
        # Should not raise any exception
    
    def test_validate_max_results_invalid(self):
        """Test max_results validation with invalid values."""
        with pytest.raises(AWSCostExplorerError, match="max_results must be between"):
            self.service._validate_max_results(0)
        
        with pytest.raises(AWSCostExplorerError, match="max_results must be between"):
            self.service._validate_max_results(1001)
    
    def test_build_cost_request_minimal(self):
        """Test building cost request with minimal parameters."""
        request = self.service._build_cost_request(
            start="2023-01-01",
            end="2023-01-02",
            granularity="DAILY",
            group_by=None,
            metrics=["UnblendedCost"],
            filter_config=None,
            next_page_token=None
        )
        
        expected = {
            "TimePeriod": {"Start": "2023-01-01", "End": "2023-01-02"},
            "Granularity": "DAILY",
            "Metrics": ["UnblendedCost"]
        }
        
        assert request == expected
    
    def test_build_cost_request_with_group_by(self):
        """Test building cost request with group_by."""
        request = self.service._build_cost_request(
            start="2023-01-01",
            end="2023-01-02",
            granularity="DAILY",
            group_by=["SERVICE", "REGION"],
            metrics=["UnblendedCost"],
            filter_config=None,
            next_page_token=None
        )
        
        assert "GroupBy" in request
        assert request["GroupBy"] == [
            {"Type": "DIMENSION", "Key": "SERVICE"},
            {"Type": "DIMENSION", "Key": "REGION"}
        ]
    
    def test_build_cost_request_with_filter(self):
        """Test building cost request with filter."""
        filter_config = {
            "dimension": "SERVICE",
            "values": ["Amazon EC2"]
        }
        
        request = self.service._build_cost_request(
            start="2023-01-01",
            end="2023-01-02",
            granularity="DAILY",
            group_by=None,
            metrics=["UnblendedCost"],
            filter_config=filter_config,
            next_page_token=None
        )
        
        assert "Filter" in request
        expected_filter = {
            "Dimensions": {
                "Key": "SERVICE",
                "Values": ["Amazon EC2"],
                "MatchOptions": ["EQUALS"]
            }
        }
        assert request["Filter"] == expected_filter
    
    def test_format_cost_response(self):
        """Test formatting of cost response."""
        mock_response = {
            "TimePeriod": {"Start": "2023-01-01", "End": "2023-01-02"},
            "ResultsByTime": [{"test": "data"}],
            "NextPageToken": "token123"
        }
        
        result = self.service._format_cost_response(
            response=mock_response,
            start="2023-01-01",
            end="2023-01-02",
            granularity="DAILY",
            metrics=["UnblendedCost"],
            group_by=["SERVICE"]
        )
        
        expected = {
            "time_period": {"Start": "2023-01-01", "End": "2023-01-02"},
            "granularity": "DAILY",
            "metrics": ["UnblendedCost"],
            "group_by": ["SERVICE"],
            "results_by_time": [{"test": "data"}],
            "next_page_token": "token123",
            "total_results": 1
        }
        
        assert result == expected
    
    @pytest.mark.asyncio
    async def test_get_cost_and_usage_success(self):
        """Test successful get_cost_and_usage call."""
        # Mock the AWS API response
        mock_response = {
            "TimePeriod": {"Start": "2023-01-01", "End": "2023-01-02"},
            "ResultsByTime": [{"test": "data"}]
        }
        self.mock_client.get_cost_and_usage.return_value = mock_response
        
        result = await self.service.get_cost_and_usage(
            start="2023-01-01",
            end="2023-01-02",
            granularity="DAILY"
        )
        
        assert "time_period" in result
        assert "results_by_time" in result
        assert result["granularity"] == "DAILY"
        self.mock_client.get_cost_and_usage.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_dimension_values_success(self):
        """Test successful get_dimension_values call."""
        # Mock the AWS API response
        mock_response = {
            "DimensionValues": [{"Value": "Amazon EC2"}],
            "TotalSize": 1,
            "ReturnSize": 1
        }
        self.mock_client.get_dimension_values.return_value = mock_response
        
        result = await self.service.get_dimension_values(
            dimension="SERVICE",
            time_period_start="2023-01-01",
            time_period_end="2023-01-02"
        )
        
        assert result["dimension"] == "SERVICE"
        assert "dimension_values" in result
        assert result["total_size"] == 1
        self.mock_client.get_dimension_values.assert_called_once()
