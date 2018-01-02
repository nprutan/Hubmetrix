from bigcommerce.api import BigcommerceApi
from bigcommerce.exception import ClientRequestException
from flask import Flask, session, redirect, url_for, request, render_template, Response
from werkzeug.exceptions import BadGateway
from datetime import datetime

from hubspot_utils import *
from dynamodb_utils import *
import chargebee
import os
import json

app = Flask(__name__)


app.config['APP_URL'] = os.environ.get('APP_URL')
app.config['APP_BACKEND_URL'] = os.environ.get('APP_BACKEND_URL')
app.config['BC_CLIENT_ID'] = os.environ.get('BC_CLIENT_ID')
app.config['BC_CLIENT_SECRET'] = os.environ.get('BC_CLIENT_SECRET')
app.config['SESSION_SECRET'] = os.getenv('SESSION_SECRET', os.urandom(64))
app.config['HS_REDIRECT_URI'] = os.environ.get('HS_REDIRECT_URI')
app.config['HS_CLIENT_ID'] = os.environ.get('HS_CLIENT_ID')
app.config['HS_CLIENT_SECRET'] = os.environ.get('HS_CLIENT_SECRET')

app.secret_key = app.config['SESSION_SECRET']

#
# Error handling and helpers
#
def error_info(e):
    content = ""
    try:  # it's probably a HttpException, if you're using the bigcommerce client
        content += str(e.headers) + "<br>" + str(e.content) + "<br>"
        req = e.response.request
        content += "<br>Request:<br>" + req.url + "<br>" + str(req.headers) + "<br>" + str(req.body)
    except AttributeError as e:  # not a HttpException
        content += "<br><br> (This page threw an exception: {})".format(str(e))
    return content


@app.errorhandler(500)
def internal_server_error(e):
    content = "Internal Server Error: " + str(e) + "<br>"
    content += error_info(e)
    return content, 500


@app.errorhandler(400)
def bad_request(e):
    content = "Bad Request: " + str(e) + "<br>"
    content += error_info(e)
    return content, 400


# Helper for template rendering
def render(template, context):
    return render_template(template, **context)


def get_bc_client_id():
    return app.config['BC_CLIENT_ID']


def get_bc_client_secret():
    return app.config['BC_CLIENT_SECRET']


def get_hs_client_id():
    return app.config['HS_CLIENT_ID']


def get_hs_client_secret():
    return app.config['HS_CLIENT_SECRET']


def get_hs_redir_uri():
    return app.config['HS_REDIRECT_URI']


def construct_hubspot_auth_url():
    client_id = get_hs_client_id()
    redir_uri = get_hs_redir_uri()

    return 'https://app.hubspot.com/oauth/authorize?client_id={}&scope=contacts%20automation%20timeline&redirect_uri={}'.format(
        client_id, redir_uri)


def construct_chargebee_signup_url(sess):
    chargebee.configure("test_RqcuUOam2qv17jcusG0eiypcuZlaiQH7Zc", "composedcloud-test")

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
        "redirect_url": app.config['APP_URL'] + url_for('payment_success'),
        "embed": True
    })
    return result.hosted_page.values['url']


def register_or_activate_bc_webhooks(user):
    client = get_bc_client(user)

    try:
        existing_webhooks = get_existing_webhooks(client)
        if existing_webhooks:
            for hook in existing_webhooks:
                client.Webhook.get(hook.id).update(is_active=True)

        if not existing_webhooks:
            order_dest = app.config['APP_BACKEND_URL'] + '/dev/bc-ingest-orders'
            customer_dest = app.config['APP_BACKEND_URL'] + '/dev/bc-ingest-customers'
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


def delete_all_webhooks(user):
    client = get_bc_client(user)

    try:
        hooks = client.Webhooks.all()
        if hooks:
            for hook in hooks:
                client.Webhooks.get(hook.id).delete()
            return True
        return False
    except ClientRequestException:
        return False


def get_bc_client(user):
    return BigcommerceApi(client_id=get_bc_client_id(),
                            store_hash=user.bc_store_hash,
                            access_token=user.bc_access_token)

@app.route('/')
def index():

    return render_template('index.html')


@app.route('/bigcommerce/callback')
def auth_callback():
    # Put together params for token request
    code = request.args['code']
    context = request.args['context']
    scope = request.args['scope']
    bc_store_hash = context.split('/')[1]
    redirect_uri = app.config['APP_URL'] + url_for('auth_callback')

    # Fetch a permanent oauth token. This will throw an exception on error,
    # which will get caught by our error handler above.
    client = BigcommerceApi(client_id=get_bc_client_id(), store_hash=bc_store_hash)
    token = client.oauth_fetch_token(get_bc_client_secret(), code, context, scope, redirect_uri)
    bc_id = token['user']['id']
    email = token['user']['email']
    access_token = token['access_token']

    app_user = get_query_first_result(AppUser, bc_store_hash)
    if not app_user:
        app_user = AppUser(bc_store_hash, bc_id, bc_email=email, bc_access_token=access_token, bc_scope=scope)

    app_user.save()

    register_or_activate_bc_webhooks(app_user)

    # Log user in and redirect to app home
    session['storehash'] = app_user.bc_store_hash
    session['storeuseremail'] = email
    return redirect(app.config['APP_URL'] + url_for('get_started'))


# TODO: Need to enforce context
# TODO: If user bails in the middle of install
# TODO: take them to the appropriate step
@app.route('/bigcommerce/load')
def load():
    # Decode and verify payload
    payload = request.args['signed_payload']
    user_data = BigcommerceApi.oauth_verify_payload(payload, get_bc_client_secret())
    if not user_data:
        return "Payload verification failed!", 401

    bc_store_hash = user_data['store_hash']
    bc_email = user_data['user']['email']

    app_user = get_query_first_result(AppUser, bc_store_hash)
    if not app_user:
        return 'You will need to re-install this app. Please uninstall and then go to marketplace and click install.'

    if not app_user.bc_webhooks_registered:
        register_or_activate_bc_webhooks(app_user)

    if not app_user.hs_access_token:
        return redirect(app.config['APP_URL'] + url_for('get_started'))

    if not

    # Log user in and redirect to app interface
    session['storehash'] = app_user.bc_store_hash
    session['storeuseremail'] = bc_email
    return redirect(app.config['APP_URL'] + url_for('index'))


@app.route('/bigcommerce/uninstall')
def uninstall():
    payload = request.args['signed_payload']
    user_data = BigcommerceApi.oauth_verify_payload(payload, get_bc_client_secret())
    if not user_data:
        return "Payload verification failed!", 401

    bc_store_hash = user_data['store_hash']

    app_user = get_query_first_result(AppUser, bc_store_hash)

    delete_all_webhooks(app_user)

    app_user.delete()

    return Response('Deleted', status=204)


@app.route('/hsauth')
def hsauth():
    global signup_page
    code = request.args.get('code')
    redir_uri = get_hs_redir_uri()
    client_id = get_hs_client_id()
    client_secret = get_hs_client_secret()

    try:
        bc_store_hash = session['storehash']
        app_user = get_query_first_result(AppUser, bc_store_hash)
    except KeyError:
        return "User not logged in! Please go back and click on app icon in admin panel.", 401

    if code and app_user:
        token_and_refresh = exchange_code_for_token(code, client_id, client_secret, redir_uri)
        print(token_and_refresh)
        token_info = get_token_info(token_and_refresh['access_token'])
        print(token_info)
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

        signup_page = construct_chargebee_signup_url(session)
    return render_template('success_hubspot.html', chargebee_hosted_url=signup_page)


@app.route('/getstarted')
def get_started():
    hs_auth_url = construct_hubspot_auth_url()

    return render_template('get_started.html', hs_auth_url=hs_auth_url)

@app.route('/paymentsetup')
def payment_setup():
    signup_page = construct_chargebee_signup_url(session)

    return render_template('chargebee_setup.html', chargebee_hosted_url=signup_page)


@app.route('/paymentsuccess')
def payment_success():

    return render_template('success_chargebee.html')

@app.route('/backtobigcommerce')
def back_to_bigcommerce():
    try:
        bc_store_hash = session['storehash']
        app_user = get_query_first_result(AppUser, bc_store_hash)
    except KeyError:
        return "User not logged in! Please go back and click on app icon in admin panel.", 401

    redirect_url = 'https://store-{}.mybigcommerce.com/manage/'.format(app_user.bc_store_hash)
    return redirect(redirect_url)


if __name__ == '__main__':
    app.run('0.0.0.0', debug=True, port=8100)