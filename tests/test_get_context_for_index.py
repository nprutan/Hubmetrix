import pendulum
import pytest

from hubmetrix_utils import get_context_for_index, get_chargebee_subscription_by_id


def test_get_context_for_index_returns_context(app_user, app_config):
    subscription = get_chargebee_subscription_by_id(app_user.cb_subscription_id, config=app_config)
    context_for_index = get_context_for_index(app_user, subscription)

    assert context_for_index


def test_get_context_for_index_returns_corect_tuple_items(ctx_for_idx):
    next_charge, next_charge_explain, last_sync, days_left = ctx_for_idx

    assert next_charge
    assert next_charge_explain
    assert last_sync
    assert days_left


def test_get_context_for_index_returns_corect_tuple_item_types(ctx_for_idx):
    next_charge, next_charge_explain, last_sync, days_left = ctx_for_idx

    assert type(next_charge) is str
    assert type(next_charge_explain) is str
    assert type(last_sync) is str
    assert type(days_left) is str


@pytest.mark.parametrize('chargebee_subscription_cancelled_at', [None])
@pytest.mark.parametrize('chargebee_subscription_next_billing_at', [pendulum.now().add(days=30).int_timestamp])
def test_get_context_for_index_returns_correct_days_left_for_active_sub_status_next_billing(app_user,
                                                                                            chargebee_subscription):
    subscription = chargebee_subscription.subscription
    context_for_index = get_context_for_index(app_user, subscription)
    next_charge, next_charge_explain, last_sync, days_left = context_for_index
    period = pendulum.from_timestamp(pendulum.now().add(days=30).int_timestamp) - pendulum.now()

    assert days_left == 'Days Left In Subscription: {}'.format(period.days)


@pytest.mark.parametrize('chargebee_subscription_cancelled_at', [pendulum.now().add(days=10).int_timestamp])
def test_get_context_for_index_returns_correct_days_left_for_sub_status_cancelled_at_future(app_user,
                                                                                            chargebee_subscription):
    subscription = chargebee_subscription.subscription
    context_for_index = get_context_for_index(app_user, subscription)
    next_charge, next_charge_explain, last_sync, days_left = context_for_index
    period = pendulum.from_timestamp(pendulum.now().add(days=10).int_timestamp) - pendulum.now()

    assert days_left == 'Days Left In Subscription: {}'.format(period.days)


@pytest.mark.parametrize('chargebee_subscription_cancelled_at', [pendulum.now().add(days=10).int_timestamp])
def test_get_context_for_index_returns_correct_next_charge_for_sub_status_cancelled_at_future(app_user,
                                                                                              chargebee_subscription):
    subscription = chargebee_subscription.subscription
    context_for_index = get_context_for_index(app_user, subscription)
    next_charge, next_charge_explain, last_sync, days_left = context_for_index

    assert next_charge == 'Cancels On: {}\r'.format(pendulum.now().add(days=10).to_date_string())


@pytest.mark.parametrize('chargebee_subscription_cancelled_at', [pendulum.now().int_timestamp])
def test_get_context_for_index_returns_correct_next_charge_for_sub_status_cancelled_at_now(app_user,
                                                                                           chargebee_subscription):
    subscription = chargebee_subscription.subscription
    context_for_index = get_context_for_index(app_user, subscription)
    next_charge, next_charge_explain, last_sync, days_left = context_for_index

    assert next_charge == 'Cancels On: {}\r'.format(pendulum.now().to_date_string())


@pytest.mark.parametrize('chargebee_subscription_cancelled_at', [None])
@pytest.mark.parametrize('chargebee_subscription_status', ['active'])
def test_get_context_for_index_returns_correct_context_for_sub_status_active(app_user, chargebee_subscription):
    subscription = chargebee_subscription.subscription
    context_for_index = get_context_for_index(app_user, subscription)
    next_charge, next_charge_explain, last_sync, days_left = context_for_index

    assert next_charge == pendulum.from_timestamp(subscription.next_billing_at).to_cookie_string()
