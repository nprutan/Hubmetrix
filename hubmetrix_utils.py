from bigcommerce.api import BigcommerceApi
from bigcommerce.exception import ClientRequestException
from pynamodb.exceptions import QueryError
from werkzeug.exceptions import BadGateway
from flask import url_for, render_template
import chargebee


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

    return 'https://app.hubspot.com/oauth/authorize?client_id={}&scope=contacts%20automation%20timeline&redirect_uri={}'.format(
        client_id, redir_uri)


def construct_chargebee_signup_url(sess, config):
    chargebee.configure(config['CHARGEBEE-API-KEY'], config['CHARGEBEE-SITE'])

    try:
        email = sess['storeuseremail']
    except (KeyError, QueryError):
        return "User not logged in! Please go back and click on app icon in admin panel.", 401

    result = chargebee.HostedPage.checkout_new({
        "subscription": {
            "plan_id": "hubmetrix-base-plan"
        },
        "customer": {
            "email": email
        },
        "redirect_url": config['APP_URL'] + config['STAGE'] + url_for('payment_success'),
        "embed": True
    })
    return result.hosted_page.values['url']


def get_chargebee_subscription(user):
    result = chargebee.Subscription.retrieve(user.cb_subscription_id)
    return result.subscription


def register_or_activate_bc_webhooks(user, config):
    client = get_bc_client(user, config)

    try:
        existing_webhooks = get_existing_webhooks(client)
        if existing_webhooks:
            for hook in existing_webhooks:
                client.Webhook.get(hook.id).update(is_active=True)

        if not existing_webhooks:
            order_dest = config['APP_BACKEND_URL'] + '/dev/bc-ingest-orders'
            customer_dest = config['APP_BACKEND_URL'] + '/dev/bc-ingest-customers'
            # shipment_dest = app.config['APP_BACKEND_URL'] + '/dev/bc-ingest-shipments'

            client.Webhooks.create(scope='store/order/created', destination=order_dest, is_active=True)
            client.Webhooks.create(scope='store/order/statusUpdated', destination=order_dest, is_active=True)
            client.Webhooks.create(scope='store/customer/updated', destination=customer_dest, is_active=True)
            # client.Webhooks.create(scope='store/shipment/*', destination=shipment_dest, is_active=True)

            user.bc_webhooks_registered = True
            user.save()
    except BadGateway:
        pass
    finally:
        user.save()


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