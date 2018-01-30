import bigcommerce
import chargebee
import pendulum
import pytest
from chargebee.result import Result
from pynamodb.models import Model
from werkzeug.exceptions import BadGateway

from dynamodb_utils import *
from hubmetrix_utils import get_chargebee_subscription_by_id, get_context_for_index


@pytest.fixture
def app_user_webhooks_registered():
    return True


@pytest.fixture
def app_user(app_user_webhooks_registered):
    user = AppUser(bc_store_hash='3c0o779wl7', bc_id=415079)
    user.bc_access_token = 'kmnhtzyinaj6zhl0hynd8ic5jj8b8qf'
    user.bc_email = 'joediffy@example.com'
    user.bc_id = 815279
    user.bc_scope = ('store_cart_read_only store_v2_customers_login store_v2_customers_read_only store_v2_default'
                     ' store_v2_information_read_only store_v2_orders_read_only store_v2_products_read_only '
                     'store_v2_transactions_read_only users_basic_information')
    user.bc_webhooks_registered = app_user_webhooks_registered
    user.cb_subscription_id = 'C5OEsoLhbW9taJwc'
    user.hm_last_sync_timestamp = 'Thursday, 25-Jan-2018 20:51:37 GMT'
    user.hs_access_token = 'JIKW3IKTLBICUQEYwoP6ASCr5rICKM7GAzIZABGuvl9ltsl3r_cUU0cYLf1GeFqrKCVodZ'
    user.hs_access_token_timestamp = '2018-01-25 20:41:06.728354'
    user.hs_app_id = '58190'
    user.hs_expires_in = '21600'
    user.hs_hub_domain = 'composed-dev-4096450.com'
    user.hs_hub_id = '4096450'
    user.hs_refresh_token = '5e7cdae2-3332-4094-994e-d99814f571f2'
    user.hs_scopes = ['contacts', 'automation', 'timeline', 'oauth']
    user.hs_token_type = 'access'
    user.hs_user = 'nathan@example.com'
    user.hs_user_id = '6046082'
    return user


@pytest.fixture
def session(app_user):
    return dict(
        storehash=app_user.bc_store_hash,
        storeuseremail=app_user.bc_email
    )


@pytest.fixture(scope='module')
def app_config():
    return {
        "SESSION_SECRET": "334e1ba54eea9fe117ca764c3cd96c16913db5c14c1ad9911ff99fb5c77474ad",
        "APP_URL": "https://9kr5377xjf.execute-api.us-west-1.amazonaws.com",
        "APP_BACKEND_URL": "https://up5sepzms9.execute-api.us-west-1.amazonaws.com",
        "BC_CLIENT_ID": "6sdgtpxp82axz6elfh6c5r2uvizd08g",
        "BC_CLIENT_SECRET": "sua2g12c7t6b6elouflse410jnmad5z",
        "HS_REDIRECT_URI": "https://9kr5377xjf.execute-api.us-west-1.amazonaws.com/dev/hsauth",
        "HS_CLIENT_ID": "f0e15e14-a1f2-48fe-83fd-56d741e2327e",
        "HS_CLIENT_SECRET": "64c89cfb-1bad-5770-7e32-a581cf14a281",
        "CHARGEBEE-API-KEY": "test_SqcuUObm2qv17jcusJ0eiapauZl1iQH7Zc",
        "CHARGEBEE-SITE": "composedcloud-test",
        "STAGE-PREFIX": "/dev",
        "APP_ID": "11672"
    }


@pytest.fixture
def chargebee_subscription_status():
    return 'active'


@pytest.fixture
def chargebee_subscription_cancelled_at():
    return pendulum.now().add(days=10).int_timestamp


@pytest.fixture
def chargebee_subscription_started_at():
    return pendulum.now().subtract(days=20).int_timestamp


@pytest.fixture
def chargebee_subscription_current_term_start():
    return pendulum.now().subtract(days=10).int_timestamp


@pytest.fixture
def chargebee_subscription_current_term_end():
    return pendulum.now().add(days=10).int_timestamp


@pytest.fixture
def chargebee_subscription_next_billing_at(chargebee_subscription_current_term_start):
    return pendulum.fromtimestamp(chargebee_subscription_current_term_start).add(days=30).int_timestamp


@pytest.fixture
def chargebee_subscription(chargebee_subscription_status, chargebee_subscription_current_term_start,
                           chargebee_subscription_current_term_end,
                           chargebee_subscription_cancelled_at,
                           chargebee_subscription_next_billing_at):
    return Result({
        "subscription": {
            "id": "8avVGOkx8U1MX",
            "customer_id": "8avVGOkx8U1MX",
            "plan_id": "basic",
            "plan_quantity": 1,
            "plan_unit_price": 900,
            "billing_period": 1,
            "billing_period_unit": "month",
            "plan_free_quantity": 0,
            "status": chargebee_subscription_status,
            "trial_start": 1412101817,
            "trial_end": 1414780217,
            "current_term_start": chargebee_subscription_current_term_start,
            "current_term_end": chargebee_subscription_current_term_end,
            "next_billing_at": chargebee_subscription_next_billing_at,
            "remaining_billing_cycles": 0,
            "created_at": 1412101817,
            "started_at": 1412101817,
            "activated_at": 1414780217,
            "cancelled_at": chargebee_subscription_cancelled_at,
            "updated_at": 1515494918,
            "has_scheduled_changes": False,
            "resource_version": 1515494918000,
            "deleted": False,
            "object": "subscription",
            "currency_code": "USD",
            "due_invoices_count": 3,
            "due_since": 1394532759,
            "total_dues": 6700,
            "mrr": 900,
            "exchange_rate": 1.0,
            "base_currency_code": "USD",
            "shipping_address": {
                "first_name": "Joe",
                "last_name": "Diffy",
                "line1": "PO Box 9999",
                "city": "Walnut",
                "state_code": "CA",
                "state": "California",
                "country": "US",
                "zip": "91789",
                "validation_status": "not_validated",
                "object": "shipping_address"
            },
        },
        "customer": {
            "id": "8avVGOkx8U1MX",
            "first_name": "Joe",
            "last_name": "Diffy",
            "email": "joediffy@example.com",
            "auto_collection": "on",
            "net_term_days": 0,
            "allow_direct_debit": False,
            "created_at": 1412101817,
            "taxability": "taxable",
            "updated_at": 1515495069,
            "resource_version": 1515495069000,
            "deleted": False,
            "object": "customer",
            "card_status": "valid",
            "contacts": [
                {
                    "id": "d334f4g45",
                    "first_name": "aasca",
                    "last_name": "asas",
                    "email": "sss@wss.asc",
                    "label": "ascasc",
                    "enabled": True,
                    "send_account_email": True,
                    "send_billing_email": False,
                    "object": "contact"
                },
            ],
            "primary_payment_source_id": "pm_XpbBroXQF5m78F6",
            "payment_method": {
                "object": "payment_method",
                "type": "card",
                "reference_id": "tok_XpbGEt7QgEHeQWG",
                "gateway": "chargebee",
                "gateway_account_id": "gw_XpbGEt7QgEHcaa2",
                "status": "valid"
            },
            "promotional_credits": 0,
            "refundable_credits": 0,
            "excess_payments": 0,
            "unbilled_charges": 0,
            "preferred_currency_code": "USD"
        },
        "card": {
            "status": "valid",
            "gateway": "chargebee",
            "gateway_account_id": "gw_XpbGEt7QgEHcaa2",
            "iin": "385200",
            "last4": "3237",
            "card_type": "diners_club",
            "funding_type": "not_known",
            "expiry_month": 12,
            "expiry_year": 2022,
            "object": "card",
            "masked_number": "************3237",
            "customer_id": "8avVGOkx8U1MX",
            "payment_source_id": "pm_XpbBroXQF5m78F6"
        }
    })


@pytest.fixture(autouse=True)
def chargebee_subscription_auto_retrieve(monkeypatch, chargebee_subscription):
    monkeypatch.setattr(chargebee.Subscription, 'retrieve', lambda x: chargebee_subscription)


@pytest.fixture(autouse=True)
def chargebee_subscription_auto_list(monkeypatch, chargebee_subscription):
    monkeypatch.setattr(chargebee.Subscription, 'list', lambda x: [chargebee_subscription] if x['email'] else [])


@pytest.fixture(autouse=True)
def pynamodb_model_query(monkeypatch, app_user):
    def get_user(user):
        if user != 'invalid':
            return [app_user]
        return []

    monkeypatch.setattr(Model, 'query', get_user)


@pytest.fixture(autouse=True)
def pynamodb_model_save(monkeypatch, app_user):
    monkeypatch.setattr(Model, 'save', lambda x: app_user)


@pytest.fixture
def ctx_for_idx(app_user, app_config):
    subscription = get_chargebee_subscription_by_id(app_user.cb_subscription_id, config=app_config)
    return get_context_for_index(app_user, subscription)


@pytest.fixture
def bc_store_info():
    return {'id': '2b0o559ql7', 'domain': 'composed-cloud10.mybigcommerce.com',
     'secure_url': 'https://store-2b0o559ql7.mybigcommerce.com', 'status': 'prelaunch', 'name': 'Composed Cloud',
     'first_name': 'Nathan', 'last_name': 'Rutan',
     'address': '123 Easy St.\nHonolulu, HI 96822\nUnited States of America', 'country': 'United States',
     'country_code': 'US', 'phone': '555-555-5555', 'admin_email': 'nprutan@gmail.com',
     'order_email': 'info@composed-cloud10.mybigcommerce.com',
     'favicon_url': 'https://cdn7.bigcommerce.com/r-fe9d5b0b14fc96661418eeb736c890d34aafc743/img/bc_favicon.ico',
     'timezone': {'name': 'Europe/London', 'raw_offset': 0, 'dst_offset': 0, 'dst_correction': False,
                  'date_format': {'display': 'M jS Y', 'export': 'M jS Y', 'extended_display': 'M jS Y @ g:i A'}},
     'language': 'en', 'currency': 'USD', 'currency_symbol': '$', 'decimal_separator': '.', 'thousands_separator': ',',
     'decimal_places': 2, 'currency_symbol_location': 'left', 'weight_units': 'Ounces', 'dimension_units': 'Inches',
     'dimension_decimal_places': '2', 'dimension_decimal_token': '.', 'dimension_thousands_token': ',',
     'plan_name': 'Partner Sandbox', 'plan_level': 'Free', 'industry': 'Other, something else', 'logo': [],
     'is_price_entered_with_tax': False, 'active_comparison_modules': [],
     'features': {'stencil_enabled': True, 'sitewidehttps_enabled': False, 'facebook_catalog_id': ''}}


@pytest.fixture
def bc_webhooks():
    hooks = [{'id': 13223385, 'client_id': '5sdgtpwp82lxz5elfh5c5e2uvjzd07g',
            'store_hash': '2b0o559ql7', 'scope': 'store/order/created',
            'destination': 'https://up5sepzms9.execute-api.us-west-1.amazonaws.com/dev/bc-ingest-orders',
            'headers': None, 'is_active': True, 'created_at': 1517004745, 'updated_at': 1517004745},
            {'id': 13223386, 'client_id': '5sdgtpwp82lxz5elfh5c5e2uvjzd07g', 'store_hash': '2b0o559ql7',
            'scope': 'store/order/statusUpdated',
            'destination': 'https://up5sepzms9.execute-api.us-west-1.amazonaws.com/dev/bc-ingest-orders',
            'headers': None, 'is_active': True, 'created_at': 1517004745, 'updated_at': 1517004745},
            {'id': 13223387, 'client_id': '5sdgtpwp82lxz5elfh5c5e2uvjzd07g', 'store_hash': '2b0o559ql7',
            'scope': 'store/customer/updated',
            'destination': 'https://up5sepzms9.execute-api.us-west-1.amazonaws.com/dev/bc-ingest-customers',
            'headers': None, 'is_active': True, 'created_at': 1517004745, 'updated_at': 1517004745}]
    return [bigcommerce.resources.Webhooks(hook) for hook in hooks]


@pytest.fixture
def bc_webhooks_single_hook():
    return bigcommerce.resources.Webhooks({'id': 13223385, 'client_id': '5sdgtpwp82lxz5elfh5c5e2uvjzd07g',
            'store_hash': '2b0o559ql7', 'scope': 'store/order/created',
            'destination': 'https://up5sepzms9.execute-api.us-west-1.amazonaws.com/dev/bc-ingest-orders',
            'headers': None, 'is_active': True, 'created_at': 1517004745, 'updated_at': 1517004745})


@pytest.fixture(autouse=True)
def get_bc_store(monkeypatch, bc_store_info):
    return monkeypatch.setattr(bigcommerce.resources.Store, 'all', lambda **kwargs: bc_store_info)


@pytest.fixture
def raise_bad_gateway_bool():
    return False


@pytest.fixture(autouse=True)
def bc_webhooks_all(monkeypatch, bc_webhooks, raise_bad_gateway_bool):
    def get_bc_webhooks(*args, **kwargs):
        if raise_bad_gateway_bool:
            raise BadGateway
        return bc_webhooks
    return monkeypatch.setattr(bigcommerce.resources.Webhooks, 'all', get_bc_webhooks)


@pytest.fixture(autouse=True)
def bc_webhook_get(monkeypatch, bc_webhooks_single_hook):
    return monkeypatch.setattr(bigcommerce.resources.Webhooks, 'get', lambda x, **kwargs: bc_webhooks_single_hook)


@pytest.fixture(autouse=True)
def bc_webhook_update(monkeypatch, bc_webhooks_single_hook):
    return monkeypatch.setattr(bigcommerce.resources.Webhooks, 'update',
                               lambda *args, **wkargs: bc_webhooks_single_hook)


@pytest.fixture(autouse=True)
def bc_webhook_create(monkeypatch, bc_webhooks_single_hook):
    return monkeypatch.setattr(bigcommerce.resources.Webhooks, 'create',
                               lambda x, y, z, connection=None:
                               bc_webhooks_single_hook)


@pytest.fixture
def chargebee_hosted_page():
    return Result({"hosted_page": {
        "id": "PKYW3j1UQAB6bzBWMcugfcZSGJpf2X5T7",
        "type": "checkout_new",
        "url": "https://yourapp.chargebee.com/pages/v2/PKYW3j1UQAB6bzBWMcugfcZSGJpf2X5T7/checkout",
        "state": "created",
        "embed": True,
        "created_at": 1515494922,
        "expires_at": 1515498522,
        "object": "hosted_page",
        "updated_at": 1515494922,
        "resource_version": 1515494922000
    }})


@pytest.fixture(autouse=True)
def chargebee_hosted_page_checkout_new(monkeypatch, chargebee_hosted_page):
    return monkeypatch.setattr(chargebee.HostedPage, 'checkout_new', lambda x: chargebee_hosted_page)
