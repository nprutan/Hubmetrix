import pytest
from hubmetrix_utils import get_chargebee_subscription_by_id


def test_get_subscription_by_id_returns_valid_subscription(app_user, app_config):
    sub = get_chargebee_subscription_by_id(app_user.cb_subscription_id, config=app_config)

    assert sub


@pytest.mark.parametrize('chargebee_subscription_status', ['active'])
def test_get_subscription_by_id_returns_active_status(app_user, app_config):
    sub = get_chargebee_subscription_by_id(app_user.cb_subscription_id, config=app_config)

    assert sub.status == 'active'


@pytest.mark.parametrize('chargebee_subscription_status', ['cancelled'])
def test_get_subscription_by_id_returns_active_status(app_user, app_config):
    sub = get_chargebee_subscription_by_id(app_user.cb_subscription_id, config=app_config)

    assert sub.status == 'cancelled'


@pytest.mark.parametrize('app_config', [None])
def test_get_subscription_by_id_with_no_config_raises_exception(app_user, app_config):
    with pytest.raises(TypeError):
        get_chargebee_subscription_by_id(app_user.cb_subscription_id, config=app_config)

