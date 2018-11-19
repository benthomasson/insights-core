import pytest

from insights.client.config import InsightsConfig
from mock.mock import patch


def test_defaults():
    c = InsightsConfig()
    assert isinstance(c.cmd_timeout, int)
    assert isinstance(c.retries, int)
    assert isinstance(c.http_timeout, float)


@patch('insights.client.config.os.environ', {
        'INSIGHTS_HTTP_TIMEOUT': '1234',
        'INSIGHTS_RETRIES': '1234',
        'INSIGHTS_CMD_TIMEOUT': '1234'
       })
def test_env_number_parsing():
    c = InsightsConfig()
    c.load_env()
    assert isinstance(c.cmd_timeout, int)
    assert isinstance(c.retries, int)
    assert isinstance(c.http_timeout, float)


@patch('insights.client.config.os.environ', {
        'INSIGHTS_HTTP_TIMEOUT': 'STAY AWAY',
        'INSIGHTS_RETRIES': 'FROM ME',
        'INSIGHTS_CMD_TIMEOUT': 'BICK HAZARD'
     })
def test_env_number_bad_values():
    c = InsightsConfig()
    with pytest.raises(ValueError):
        c.load_env()
