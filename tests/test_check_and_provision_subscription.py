import pytest

from hubmetrix_utils import check_and_provision_subscription


def test_check_and_provision_subscription_returns_true_when_expected(app_user, app_config):
    assert check_and_provision_subscription(app_user, app_config)


@pytest.mark.parametrize('chargebee_subscription_status', ['cancelled'])
def test_check_and_provision_subscription_deactivates_webhooks_when_expected(app_user, app_config):
    check_and_provision_subscription(app_user, app_config)
    assert not app_user.bc_webhooks_registered


@pytest.mark.parametrize('raise_bad_gateway_bool', [True])
@pytest.mark.parametrize('chargebee_subscription_status', ['cancelled'])
def test_check_and_provision_subscription_returns_false_when_webhooks_not_deactivated(app_user, app_config):
    assert not check_and_provision_subscription(app_user, app_config)