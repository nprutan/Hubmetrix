from contextlib import contextmanager
from datetime import datetime

import chargebee
import pendulum
import json
from bigcommerce.api import BigcommerceApi
from bigcommerce.exception import ClientRequestException
from flask import url_for, render_template
from werkzeug.exceptions import BadGateway

from dynamodb_utils import *
from hubspot_utils import *


@contextmanager
def callback_manager(request_args, config):
    code = request_args['code']
    context = request_args['context']
    scope = request_args['scope']
    bc_store_hash = context.split('/')[1]
    redirect_uri = config['APP_URL'] + url_for('auth_callback')
    yield (code, context, scope, bc_store_hash, redirect_uri)


@contextmanager
def bc_token_manager(context, config):
    code, context, scope, bc_store_hash, redirect_uri = context
    client = BigcommerceApi(client_id=get_bc_client_id(config), store_hash=bc_store_hash)
    token = client.oauth_fetch_token(get_bc_client_secret(config), code, context, scope, redirect_uri)
    bc_id = token['user']['id']
    email = token['user']['email']
    access_token = token['access_token']
    yield (bc_id, email, access_token)


@contextmanager
def app_user_creation_manager(callback_context, token_context):
    _, _, scope, bc_store_hash, _ = callback_context
    bc_id, email, access_token = token_context
    app_user = get_query_first_result(AppUser, bc_store_hash)
    if not app_user:
        app_user = (AppUser(bc_store_hash, bc_id, bc_email=email,
                            bc_access_token=access_token, bc_scope=scope))
    app_user.save()
    yield app_user


@contextmanager
def payload_manager(request_args, config):
    payload = request_args['signed_payload']
    user_data = BigcommerceApi.oauth_verify_payload(payload, get_bc_client_secret(config))
    if not user_data:
        raise LookupError('No user! Please uninstall and reinstall app from marketplace.')
    bc_store_hash = user_data['store_hash']
    bc_email = user_data['user']['email']
    yield (bc_store_hash, bc_email)


@contextmanager
def hubspot_auth_manager(request_args, config):
    code = request_args.get('code')
    redir_uri = get_hs_redir_uri(config)
    client_id = get_hs_client_id(config)
    client_secret = get_hs_client_secret(config)
    yield (code, redir_uri, client_id, client_secret)


@contextmanager
def app_user_hubspot_token_manager(store_hash, ctx):
    code, redir_uri, client_id, client_secret = ctx
    app_user = get_query_first_result(AppUser, store_hash)
    token_and_refresh = exchange_code_for_token(code, client_id, client_secret, redir_uri)
    token_info = get_token_info(token_and_refresh['access_token'])
    app_user.hs_refresh_token = token_and_refresh['refresh_token']
    app_user.hs_access_token = token_and_refresh['access_token']
    app_user.hs_expires_in = str(token_and_refresh['expires_in'])
    app_user.hs_app_id = str(token_info['app_id'])
    app_user.hs_hub_domain = token_info['hub_domain']
    app_user.hs_hub_id = str(token_info['hub_id'])
    app_user.hs_token_type = token_info['token_type']
    app_user.hs_user = token_info['user']
    app_user.hs_user_id = str(token_info['user_id'])
    app_user.hs_scopes = token_info['scopes']
    app_user.hs_access_token_timestamp = str(datetime.now())
    app_user.save()
    yield app_user


def check_and_provision_subscription(user, config):
    sub = get_chargebee_subscription_by_email(user.bc_email, config=config)
    if sub:
        user.cb_subscription_id = sub.id

        if sub.status != 'cancelled':
            return register_or_activate_bc_webhooks(user, config)

        return deactivate_bc_webhooks(user, config)
    return False


def get_context_for_index(user, sub):
    last_sync = user.hm_last_sync_timestamp
    period_timestamp = sub.cancelled_at if sub.cancelled_at else sub.next_billing_at
    period = pendulum.from_timestamp(period_timestamp) - pendulum.now()
    days_left = 'Days Left In Subscription: {}'.format(period.days)

    if sub.cancelled_at:
        next_charge = 'Cancels On: {}\r'.format(
            pendulum.from_timestamp(sub.cancelled_at).to_date_string())
        next_charge_explain = 'We\'re sad you\'re leaving, but we know you\'ll always be awesome! Your plan ' \
                              'will stay active until the date above.'
    else:
        next_charge = pendulum.from_timestamp(sub.next_billing_at).to_cookie_string()
        next_charge_explain = 'The date of your next charge. If you\'d like to change your plan click above on ' \
                              'Plan Info. '
    return next_charge, next_charge_explain, last_sync, days_left


def render(template, context):
    return render_template(template, **context)


def get_bc_client_id(config):
    return config['BC_CLIENT_ID']


def get_bc_client_secret(config):
    return config['BC_CLIENT_SECRET']


def get_hs_client_id(config):
    return config['HS_CLIENT_ID']


def get_hs_client_secret(config):
    return config['HS_CLIENT_SECRET']


def get_hs_redir_uri(config):
    return config['HS_REDIRECT_URI']


def construct_hubspot_auth_url(config):
    client_id = get_hs_client_id(config)
    redir_uri = get_hs_redir_uri(config)

    return ('https://app.hubspot.com/oauth/authorize?client_id={}'
            '&scope=contacts%20automation%20timeline&redirect_uri={}'.format(client_id, redir_uri))


def configure_chargebee_api(func):
    def wrapper(*args, **kwargs):
        chargebee.configure(kwargs['config']['CHARGEBEE-API-KEY'], kwargs['config']['CHARGEBEE-SITE'])
        return func(*args)

    return wrapper


@configure_chargebee_api
def construct_chargebee_signup_url(store_info, app_url):
    address_info = parse_bc_address(store_info['address'])

    result = chargebee.HostedPage.checkout_new({
        "subscription": {
            "plan_id": "hubmetrix-base-plan"
        },
        "customer": {
            "email": store_info['admin_email'],
            "first_name": store_info['first_name'],
            "last_name": store_info['last_name'],
            "phone": store_info['phone']
        },
        "billing_address": {
            "first_name": store_info['first_name'],
            "last_name": store_info['last_name'],
            "line1": address_info['line1'],
            "city": address_info['city'],
            "state": address_info['state'],
            "zip": address_info['zip'],
            "country": store_info['country_code']
        },
        "redirect_url": app_url + url_for('payment_success'),
        "embed": True
    })
    return result.hosted_page.values['id'], result.hosted_page.values['url']


def parse_bc_address(address):
    try:
        if address and hasattr(address, 'split'):
            addr = {}
            addr_split = address.splitlines()
            addr['line1'] = _safe_split(addr_split, 0)
            addr['city'] = _safe_split(_safe_split(addr_split, 1).split(' '), 0).replace(',', '')
            addr['state'] = _safe_split(_safe_split(addr_split, 1).split(' '), 1)
            addr['zip'] = _safe_split(_safe_split(addr_split, 1).split(' '), 2)
            return addr
    except IndexError:
        return dict(line1='', city='', state='', zip='')


def _safe_split(str_to_split, idx):
    try:
        return str_to_split[idx]
    except IndexError:
        return ''


def update_subscription_id(user, subscription_id):
    user.update(actions=[
        AppUser.cb_subscription_id.set(subscription_id)]
    )


@configure_chargebee_api
def get_chargebee_subscription_by_email(email):
    result = chargebee.Subscription.list({'email': email})
    if result:
        return result[0].subscription
    else:
        return result


@configure_chargebee_api
def get_chargebee_subscription_by_id(subscription_id):
    result = chargebee.Subscription.retrieve(subscription_id)
    return result.subscription


@configure_chargebee_api
def get_chargebee_hosted_page(page_id):
    result = chargebee.HostedPage.retrieve(page_id)
    return result.hosted_page


@configure_chargebee_api
def cancel_chargebee_subscription_by_id(subscription_id):
    result = chargebee.Subscription.cancel(subscription_id, {'end_of_term': True})
    return result.subscription


@configure_chargebee_api
def reactivate_chargebee_subscription_by_id(subscription_id):
    result = chargebee.Subscription.reactivate(subscription_id)
    return result.subscription


@configure_chargebee_api
def update_chargebee_subscription_with_meta_data(subscription_id, store_hash):
    meta_data = json.dumps({'bc_store_hash': store_hash})
    result = chargebee.Subscription.update(subscription_id, {'meta_data': meta_data})
    return result.subscription


def register_or_activate_bc_webhooks(user, config):
    client = get_bc_client(user, config)

    if not user.bc_webhooks_registered:
        try:
            existing_webhooks = get_existing_webhooks(client)
            if existing_webhooks:
                for hook in existing_webhooks:
                    client.Webhooks.get(hook.id).update(is_active=True)

            if not existing_webhooks:
                order_dest = config['APP_BACKEND_URL'] + '/dev/bc-ingest-orders'
                customer_dest = config['APP_BACKEND_URL'] + '/dev/bc-ingest-customers'

                client.Webhooks.create(scope='store/order/created', destination=order_dest, is_active=True)
                client.Webhooks.create(scope='store/order/statusUpdated', destination=order_dest, is_active=True)
                client.Webhooks.create(scope='store/customer/updated', destination=customer_dest, is_active=True)

            user.bc_webhooks_registered = True
            user.save()
            return True
        except BadGateway:
            return False
    return True


def deactivate_bc_webhooks(user, config):
    client = get_bc_client(user, config)

    try:
        existing_webhooks = get_existing_webhooks(client)
        if existing_webhooks:
            for hook in existing_webhooks:
                client.Webhooks.get(hook.id).update(is_active=False)
        user.bc_webhooks_registered = False
        user.save()
        return True
    except BadGateway:
        return False


def get_existing_webhooks(client):
    try:
        hooks = client.Webhooks.all()
        if hooks:
            return hooks
        return []
    except ClientRequestException:
        return []


def delete_all_webhooks(user, config):
    client = get_bc_client(user, config)

    try:
        hooks = client.Webhooks.all()
        if hooks:
            for hook in hooks:
                client.Webhooks.get(hook.id).delete()
            return True
        return False
    except ClientRequestException:
        return False


def get_bc_client(user, config):
    return BigcommerceApi(client_id=get_bc_client_id(config),
                          store_hash=user.bc_store_hash,
                          access_token=user.bc_access_token)


def get_bc_store_info(user, config):
    client = get_bc_client(user, config)

    return client.Store.all()
