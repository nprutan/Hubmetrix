from flask import Flask, session, redirect, request, Response
from datetime import datetime
from hubspot_utils import *
from dynamodb_utils import *
from hubmetrix_utils import *
from happiness_scale import get_happy
import pendulum
import os

app = Flask(__name__, static_folder='templates/static')

app.config['STAGE-PREFIX'] = os.environ.get('STAGE-PREFIX', '/dev')
app.config['APP_URL'] = os.environ.get('APP_URL', 'http://localhost')
app.config['APP_BACKEND_URL'] = os.environ.get('APP_BACKEND_URL', 'http://localhost/backend')
app.config['BC_CLIENT_ID'] = os.environ.get('BC_CLIENT_ID', '')
app.config['BC_CLIENT_SECRET'] = os.environ.get('BC_CLIENT_SECRET', '')
app.config['SESSION_SECRET'] = os.getenv('SESSION_SECRET', os.urandom(64))
app.config['HS_REDIRECT_URI'] = os.environ.get('APP_URL', '') + app.config['STAGE-PREFIX'] + '/hsauth'
app.config['HS_CLIENT_ID'] = os.environ.get('HS_CLIENT_ID', '')
app.config['HS_CLIENT_SECRET'] = os.environ.get('HS_CLIENT_SECRET', '')
app.config['CHARGEBEE-API-KEY'] = os.environ.get('CHARGEBEE-API-KEY', '')
app.config['CHARGEBEE-SITE'] = os.environ.get('CHARGEBEE-SITE', '')
app.config['APP_ID'] = os.environ.get('APP_ID')

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


@app.route('/')
def index():
    bc_store_hash = session['storehash']
    app_user = get_query_first_result(AppUser, bc_store_hash)
    last_sync = app_user.hm_last_sync_timestamp
    sub = get_chargebee_subscription_by_id(app_user.cb_subscription_id, config=app.config)

    if sub.cancelled_at:
        period = pendulum.from_timestamp(sub.cancelled_at) - pendulum.now()
        if sub.status == 'cancelled':
            return redirect(url_for('maybe_reactivate_plan'))
        else:
            next_charge = 'Cancels On: {}\r'.format(
                pendulum.from_timestamp(sub.cancelled_at).to_day_datetime_string())
            next_charge += 'Days Left In Subscription: {}'.format(period.days)
            next_charge_explain = 'We\'re sad you\'re leaving, but we know you will keep being awesome! Your plan ' \
                                  'stay active until the date above'
    else:
        next_charge = pendulum.from_timestamp(sub.next_billing_at).to_cookie_string()
        next_charge_explain = 'The date of your next charge. If you\'d like to change your plan click above on ' \
                              'Plan Info. '
    happy_scale, happy_encouragement = get_happy()
    context = dict(last_sync=last_sync,
                   next_charge_date=next_charge,
                   next_charge_explain=next_charge_explain,
                   happy_scale=happy_scale,
                   happy_encouragement=happy_encouragement)

    return render_template('index.html', ctx=context)


@app.route('/bigcommerce/load')
def load():
    # Decode and verify payload
    payload = request.args['signed_payload']
    user_data = BigcommerceApi.oauth_verify_payload(payload, get_bc_client_secret(app.config))
    if not user_data:
        return "Payload verification failed!", 401

    bc_store_hash = user_data['store_hash']
    bc_email = user_data['user']['email']

    app_user = get_query_first_result(AppUser, bc_store_hash)
    if not app_user:
        return 'You will need to re-install this app. Please uninstall and then go to marketplace and click install.'

    if not app_user.bc_webhooks_registered:
        register_or_activate_bc_webhooks(app_user, app.config)

    if not app_user.hs_access_token:
        return redirect(app.config['APP_URL'] + url_for('get_started'))

    if not app_user.cb_subscription_id:
        sub = get_chargebee_subscription_by_email(bc_email, config=app.config)
        if sub:
            update_subscription_id(app_user, sub.subscription.id)
        else:
            app_url = app.config['APP_URL']
            signup_page_id, signup_page_url = construct_chargebee_signup_url(session, app_url, config=app.config)
            session['hosted_page_id'] = signup_page_id
            return render_template('success_hubspot.html', chargebee_hosted_url=signup_page_url)

    # Log user in and redirect to app interface
    session['storehash'] = app_user.bc_store_hash
    session['storeuseremail'] = bc_email
    session['cb_subscription_id'] = app_user.cb_subscription_id

    return redirect(app.config['APP_URL'] + url_for('index'))


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
    client = BigcommerceApi(client_id=get_bc_client_id(app.config), store_hash=bc_store_hash)
    token = client.oauth_fetch_token(get_bc_client_secret(app.config), code, context, scope, redirect_uri)
    bc_id = token['user']['id']
    email = token['user']['email']
    access_token = token['access_token']

    app_user = get_query_first_result(AppUser, bc_store_hash)
    if not app_user:
        app_user = AppUser(bc_store_hash, bc_id, bc_email=email, bc_access_token=access_token, bc_scope=scope)

    app_user.save()

    register_or_activate_bc_webhooks(app_user, app.config)

    # Log user in and redirect to app home
    session['storehash'] = app_user.bc_store_hash
    session['storeuseremail'] = email
    return redirect(app.config['APP_URL'] + url_for('get_started'))


@app.route('/getstarted')
def get_started():
    hs_auth_url = construct_hubspot_auth_url(app.config)

    return render_template('get_started.html', hs_auth_url=hs_auth_url)


@app.route('/bigcommerce/uninstall')
def uninstall():
    payload = request.args['signed_payload']
    user_data = BigcommerceApi.oauth_verify_payload(payload, get_bc_client_secret(app.config))
    if not user_data:
        return "Payload verification failed!", 401

    bc_store_hash = user_data['store_hash']

    app_user = get_query_first_result(AppUser, bc_store_hash)

    delete_all_webhooks(app_user, app.config)

    app_user.delete()

    return Response('Deleted', status=204)


@app.route('/hsauth')
def hs_auth_callback():
    code = request.args.get('code')
    redir_uri = get_hs_redir_uri(app.config)
    client_id = get_hs_client_id(app.config)
    client_secret = get_hs_client_secret(app.config)

    try:
        bc_store_hash = session['storehash']
        app_user = get_query_first_result(AppUser, bc_store_hash)
    except KeyError:
        return "User not logged in! Please go back and click on app icon in admin panel.", 401

    if code and app_user:
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

        # TODO: Implement a check for a cancelled
        # TODO: subscription.
        if not app_user.cb_subscription_id:
            sub = get_chargebee_subscription_by_email(app_user.bc_email, config=app.config)
            if sub:
                update_subscription_id(app_user, sub.subscription.id)
                return redirect(app.config['APP_URL'] + url_for('index'))

        app_url = app.config['APP_URL']
        signup_page_id, signup_page_url = construct_chargebee_signup_url(session, app_url, config=app.config)
        session['hosted_page_id'] = signup_page_id
    return render_template('success_hubspot.html', chargebee_hosted_url=signup_page_url)


@app.route('/paymentsuccess')
def payment_success():
    try:
        bc_store_hash = session['storehash']
        hosted_page_id = session['hosted_page_id']
        app_user = get_query_first_result(AppUser, bc_store_hash)
        cb_subscription = get_chargebee_hosted_page(hosted_page_id, config=app.config)
        cb_subscription_id = cb_subscription.content.subscription.id
        app_user.update(actions=[
            AppUser.cb_subscription_id.set(cb_subscription_id)
        ]
        )
    except KeyError:
        return "User not logged in! Please go back and click on app icon in admin panel.", 401

    app_id = app.config['APP_ID']

    redirect_url = 'https://store-{}.mybigcommerce.com/manage/app/{}'.format(app_user.bc_store_hash, app_id)
    return redirect(redirect_url)


@app.route('/maybecancelplan')
def maybe_cancel_plan():
    return render_template('cancel_plan.html')


@app.route('/cancelplan')
def cancel_plan():
    bc_store_hash = session['storehash']
    app_user = get_query_first_result(AppUser, bc_store_hash)
    subscription_id = app_user.cb_subscription_id

    cancelled_sub = cancel_chargebee_subscription_by_id(subscription_id, config=app.config)
    session['cancelled_date'] = cancelled_sub.current_term_end

    return redirect(url_for('index'))


@app.route('/planinfo')
def plan_info():
    bc_store_hash = session['storehash']
    app_user = get_query_first_result(AppUser, bc_store_hash)
    sub = get_chargebee_subscription_by_id(app_user.cb_subscription_id, config=app.config)
    start = pendulum.from_timestamp(sub.current_term_start).to_date_string() if sub.current_term_start else 'In Trial'
    end = pendulum.from_timestamp(sub.current_term_end).to_date_string() if sub.current_term_end else 'In Trial'

    context = dict(current_term_start=start,
                   current_term_end=end,
                   status=sub.status,
                   plan_unit_price='${}'.format(sub.plan_unit_price / 100),
                   plan_id=sub.plan_id,
                   billing_period=sub.billing_period,
                   billing_period_unit=sub.billing_period_unit,
                   due_invoices_count=sub.due_invoices_count)
    return render_template('plan_info.html', ctx=context)


@app.route('/maybereactivateplan')
def maybe_reactivate_plan():
    return render_template('reactivate_plan.html')


@app.route('/reactivateplan')
def reactivate_plan():
    bc_store_hash = session['storehash']
    app_user = get_query_first_result(AppUser, bc_store_hash)
    reactivate_chargebee_subscription_by_id(app_user.cb_subscription_id, config=app.config)

    return redirect(url_for('index'))


if __name__ == '__main__':
    app.run('0.0.0.0', debug=True, port=8100)
