from unittest.mock import patch
from automation.opportunity_monitor.geocode import within_commute_radius


def test_remote_or_hybrid_always_passes():
    assert within_commute_radius("Anywhere, USA", remote_ok=True) is True


@patch("automation.opportunity_monitor.geocode._geocode")
def test_nearby_location_passes(mock_geocode):
    mock_geocode.return_value = (38.9784, -76.4922)  # Annapolis, MD
    assert within_commute_radius("Annapolis, MD", remote_ok=False) is True


@patch("automation.opportunity_monitor.geocode._geocode")
def test_far_location_fails(mock_geocode):
    mock_geocode.return_value = (34.0522, -118.2437)  # Los Angeles, CA
    assert within_commute_radius("Los Angeles, CA", remote_ok=False) is False


@patch("automation.opportunity_monitor.geocode._geocode")
def test_ungeocodable_location_fails_closed(mock_geocode):
    mock_geocode.return_value = None
    assert within_commute_radius("Nowhere Really", remote_ok=False) is False
