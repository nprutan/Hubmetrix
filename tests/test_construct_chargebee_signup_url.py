from hubmetrix_utils import construct_chargebee_signup_url
import flask


def test_construct_chargebee_signup_url_returns_hosted_page(bc_store_info, app_config):
    app = flask.Flask(__name__)
    app.config['SERVER_NAME'] = 'localhost'
    app_url = app_config['APP_URL']
    with app.app_context():
        @app.route('/paymentsuccess')
        def payment_success():
            return None
        signup_page_id, signup_page_url = construct_chargebee_signup_url(bc_store_info, app_url, config=app_config)

        assert signup_page_id
        assert signup_page_url


def test_construct_chargebee_signup_hosted_page_checkout_new_returns_expected(bc_store_info, app_config):
    app = flask.Flask(__name__)
    app.config['SERVER_NAME'] = 'localhost'
    app_url = app_config['APP_URL']
    with app.app_context():
        @app.route('/paymentsuccess')
        def payment_success():
            return None

        signup_page_id, signup_page_url = construct_chargebee_signup_url(bc_store_info, app_url, config=app_config)

        assert signup_page_id == 'PKYW3j1UQAB6bzBWMcugfcZSGJpf2X5T7'
        assert signup_page_url == 'https://yourapp.chargebee.com/pages/v2/PKYW3j1UQAB6bzBWMcugfcZSGJpf2X5T7/checkout'
