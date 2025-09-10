import pytest
from datetime import datetime, timedelta, timezone
from healthchecks_utilities import services, api_client # type: ignore
from healthchecks_utilities.actions import check # type: ignore

# 1. Test a "pure" function with various inputs
@pytest.mark.parametrize(
    "whois_text, expected_datetime_str",
    [
        # --- Standard and Common Formats ---
        pytest.param(
            "Registry Expiry Date: 2025-10-22T04:00:00Z", "2025-10-22 04:00:00",
            id="iso-8601-utc"
        ),
        pytest.param(
            "Expiration Date: 2024-12-01", "2024-12-01 00:00:00",
            id="yyyy-mm-dd"
        ),
        pytest.param(
            "expires: 31-Dec-2029", "2029-12-31 00:00:00",
            id="dd-mon-yyyy"
        ),
        pytest.param(
            "paid-till: 2027.08.15", "2027-08-15 00:00:00",
            id="dot-separated-date"
        ),

        # --- Real-world Inconsistencies ---
        pytest.param(
            "   EXPIRY DATE:   2026-05-10  ", "2026-05-10 00:00:00",
            id="case-and-whitespace-insensitive"
        ),
        pytest.param(
            "Creation Date: 2020-01-01\nRegistry Expiry Date: 2025-01-01\nUpdated Date: 2024-01-01",
            "2025-01-01 00:00:00",
            id="correct-date-among-multiple"
        ),

        # --- Failure and Edge Cases ---
        pytest.param(
            "Domain is active.", None,
            id="no-match-informational"
        ),
        pytest.param(
            "Expiry Date: not-a-date", None,
            id="malformed-date-string"
        ),
        pytest.param(
            "Expiration Date:", None,
            id="label-present-but-no-date"
        ),
        pytest.param(
            "Creation Date: 2025-01-01", None,
            id="non-expiry-label"
        ),
        pytest.param(
            "", None,
            id="empty-string-input"
        ),
    ],
)

def test_parse_expiry_from_whois(whois_text, expected_datetime_str):
    """
    Tests the _parse_expiry_from_whois function with a wide variety of
    real-world WHOIS data, including different formats, inconsistencies,
    and edge cases.
    """
    # Act: Run the function we are testing
    parsed_date = services._parse_expiry_from_whois(whois_text)

    # Assert: Check the results
    if expected_datetime_str is None:
        assert parsed_date is None, "Expected no date to be parsed, but one was."
    else:
        # Create the expected datetime object as timezone-aware UTC
        expected_date = datetime.strptime(
            expected_datetime_str, "%Y-%m-%d %H:%M:%S"
        ).replace(tzinfo=timezone.utc)

        assert parsed_date is not None, "Expected a date to be parsed, but got None."
        assert parsed_date == expected_date, "The parsed date does not match the expected date."


# 2. Test the main logic with multiple scenarios
@pytest.mark.parametrize("days_from_now, expected_tag, expected_ping_suffix, expected_status_in_payload", [
    (5, 'expires_in_<7d', '/fail', 'status=expiring_soon'),
    (15, 'expires_in_<30d', '', 'status=expiring_soon'),
    (49, 'expires_in_<60d', '', 'status=expiring_soon'),
    (74, 'expires_in_<90d', '', 'status=expiring_soon'),
    (100, 'expiry_ok', '', 'status=ok'),
    (-2, 'expired', '/fail', 'status=expired'),
])
def test_check_domain_expiry_scenarios(
    mocker, days_from_now, expected_tag, expected_ping_suffix, expected_status_in_payload
):
    """
    Tests that check_domain_expiry pings and updates tags correctly for various expiry dates.
    """
    # Arrange: Mock all external calls
    domain = "example.com"
    expiry_uuid = "test-expiry-uuid"

    # 1. Define the fixed point in time.
    FROZEN_TIME = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)

    # 2. Patch the entire `datetime` module *where it is used* (in `check.py`).
    #    We replace it with a mock object.
    mock_dt = mocker.patch('healthchecks_utilities.actions.check.datetime')

    # 3. Configure the mock. We tell its 'datetime' attribute (which mimics the class)
    #    that its 'now' method should return our frozen time.
    mock_dt.datetime.now.return_value = FROZEN_TIME

    # 4. We also need to provide the original timedelta class to our mock,
    #    otherwise `expiry_date - datetime.datetime.now()` would fail because
    #    the mocked datetime object doesn't know about timedelta.
    mock_dt.timedelta = timedelta
    mock_dt.timezone = timezone

    # Calculate the expiry date relative to our fixed time.
    expiry_date = FROZEN_TIME + timedelta(days=days_from_now)

    # Mock other external calls as before
    mocker.patch.object(
        services, "run_whois",
        return_value=f"Registry Expiry Date: {expiry_date.strftime('%Y-%m-%dT%H:%M:%SZ')}"
    )
    mocker.patch.object(services, "_get_expiry_from_godaddy", return_value=None)
    mocker.patch('healthchecks_utilities.actions.check.file_handler.is_marker_valid', return_value=False)
    mock_ping = mocker.patch.object(api_client, "ping_check")
    mock_get_details = mocker.patch.object(
        api_client, "get_check_details",
        return_value={'uuid': expiry_uuid, 'tags': 'some_other_tag'}
    )
    mock_update_tags = mocker.patch.object(api_client, "update_check_tags")

    # Act: Run the function we are testing
    check.check_domain_expiry(domain, expiry_uuid)

    # Assert: Verify that the correct functions were called with the correct arguments
    mock_ping.assert_called_once()
    assert mock_ping.call_args[0][0] == expiry_uuid + expected_ping_suffix
    # The 'days_left' calculation should now be correct because of our mock
    # Note: `days_from_now` is an integer, so for exact match it should be `days_from_now`.
    # For dates like 5 days away, the `days` property calculation might be 4 if there's
    # a time-of-day difference, but since we mock both, it will be exact.
    if days_from_now >= 0:
        assert f"days_left={days_from_now}" in mock_ping.call_args[1]['payload']
    else:
        # When days_from_now is -2, days_left will also be -2.
        assert f"days_left={days_from_now}" in mock_ping.call_args[1]['payload']

    assert expected_status_in_payload in mock_ping.call_args[1]['payload']

    mock_get_details.assert_called_once_with(expiry_uuid)
    mock_update_tags.assert_called_once()
    updated_tags = mock_update_tags.call_args[0][1]
    assert expected_tag in updated_tags
    assert "some_other_tag" in updated_tags
