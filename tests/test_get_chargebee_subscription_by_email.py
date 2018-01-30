from hubmetrix_utils import get_chargebee_subscription_by_email


def test_get_chargebee_subscription_by_email_returns_subsription(app_user, app_config):
    subscription = get_chargebee_subscription_by_email(app_user.bc_email, config=app_config)

    assert subscription


def test_get_chargebee_subscription_by_email_returns_empty_list(app_config):
    subscription = get_chargebee_subscription_by_email('', config=app_config)

    assert subscription == []
