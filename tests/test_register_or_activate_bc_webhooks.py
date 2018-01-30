import pytest

from hubmetrix_utils import register_or_activate_bc_webhooks


def test_register_or_activate_webhooks_returns_expected_true(app_user, app_config):
    assert register_or_activate_bc_webhooks(app_user, app_config)


@pytest.mark.parametrize('app_user_webhooks_registered', [False])
def test_register_or_activate_webhooks_returns_expected_false(app_user, app_config):
    assert register_or_activate_bc_webhooks(app_user, app_config)


@pytest.mark.parametrize('app_user_webhooks_registered', [False])
@pytest.mark.parametrize('raise_bad_gateway_bool', [True])
def test_register_or_activate_webhooks_returns_expected_false_after_exception(app_user, app_config):
    assert not register_or_activate_bc_webhooks(app_user, app_config)
