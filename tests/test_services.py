# tests/test_services.py
import pytest
from datetime import datetime, timedelta, timezone
from src import services, api_client

# 1. Test a "pure" function with various inputs
@pytest.mark.parametrize("whois_output, expected_date_str", [
    # Test case 1: Standard format
    ("Registry Expiry Date: 2025-10-22T04:00:00Z", "2025-10-22 04:00:00"),
    # Test case 2: Different label
    ("Expiration Date: 2024-12-01", "2024-12-01 00:00:00"),
    # Test case 3: another label with different format
    ("expires: 31-Dec-2029", "2029-12-31 00:00:00"),
    # Test case 4: No match
    ("Domain is active.", None),
    # Test case 5: Malformed date string
    ("Expiry Date: not-a-date", None)
])

def test_parse_expiry_from_whois(whois_output, expected_date_str):
    """
    Tests the _parse_expiry_from_whois function with different WHOIS outputs.
    """
    parsed_date = services._parse_expiry_from_whois(whois_output)

    if expected_date_str:
        # Create the expected datetime object as timezone-aware UTC
        expected_date = datetime.strptime(expected_date_str, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
        assert parsed_date == expected_date
    else:
        assert parsed_date is None

# 2. Test a function with external dependencies using a mocker
def test_check_domain_expiry_updates_tags(mocker):
    """
    Tests that check_domain_expiry calls the API to update tags when expiry is soon.
    """
    # Arrange: Mock all external calls
    domain = "example.com"
    expiry_uuid = "test-expiry-uuid"

    # Mock the WHOIS call to return a fixed expiry date (e.g., 15 days from now)
    days_from_now = 15
    expiry_date = datetime.now(timezone.utc) + timedelta(days=days_from_now)
    mocker.patch(
        "src.services.run_whois",
        return_value=f"Registry Expiry Date: {expiry_date.strftime('%Y-%m-%dT%H:%M:%SZ')}"
    )

    # Mock the GoDaddy call so it's not attempted
    mocker.patch("src.services._get_expiry_from_godaddy", return_value=None)

    # Mock the API client calls
    mock_ping = mocker.patch("src.api_client.ping_check")
    mock_get_details = mocker.patch(
        "src.api_client.get_check_details",
        return_value={'uuid': expiry_uuid, 'tags': 'some_other_tag'}
    )
    mock_update_tags = mocker.patch("src.api_client.update_check_tags")

    # Act: Run the function we are testing
    from src.actions import check
    check.check_domain_expiry(domain, expiry_uuid)

    # Assert: Verify that the correct functions were called with the correct arguments
    # 1. It should have pinged the healthcheck
    mock_ping.assert_called_once()
    assert mock_ping.call_args[0][0] == expiry_uuid # check uuid
    assert "status=expiring_soon" in mock_ping.call_args[1]['payload'] # check payload

    # 2. It should have fetched the current tags
    mock_get_details.assert_called_once_with(expiry_uuid)

    # 3. It should have updated the tags to include 'expires_in_<30d'
    mock_update_tags.assert_called_once()
    # Check the second argument of the call (the list of tags)
    updated_tags = mock_update_tags.call_args[0][1]
    assert "expires_in_<30d" in updated_tags
    assert "some_other_tag" in updated_tags # Ensures we didn't lose existing tags
