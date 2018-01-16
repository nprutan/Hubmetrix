import json
import os

from flask import Flask, session, redirect, request, Response

from happiness_scale import get_happy
from hubmetrix_utils import *

app = Flask(__name__, static_folder='templates/static')

app.config['STAGE-PREFIX'] = os.environ.get('STAGE-PREFIX', '/dev')
app.config['APP_URL'] = os.environ.get('APP_URL', 'http://localhost')
app.config['APP_BACKEND_URL'] = os.environ.get('APP_BACKEND_URL', 'http://localhost/backend')
app.config['BC_CLIENT_ID'] = os.environ.get('BC_CLIENT_ID', '')
app.config['BC_CLIENT_SECRET'] = os.environ.get('BC_CLIENT_SECRET', '')
app.config['SESSION_SECRET'] = os.environ.get('SESSION_SECRET')
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
    sub = get_chargebee_subscription_by_id(app_user.cb_subscription_id, config=app.config)
    if sub.status == 'cancelled':
        return redirect(url_for('maybe_reactivate_plan'))

    next_charge, next_charge_explain, last_sync, days_left = get_context_for_index(app_user, sub)

    happy_scale, happy_encouragement = get_happy()

    context = dict(last_sync=last_sync,
                   next_charge_date=next_charge,
                   days_left=days_left,
                   next_charge_explain=next_charge_explain,
                   happy_scale=happy_scale,
                   happy_encouragement=happy_encouragement)

    return render_template('index.html', ctx=context)


@app.route('/bigcommerce/load')
def load():
    with payload_manager(request.args, app.config) as payload_ctx:
        bc_store_hash, bc_email = payload_ctx
        app_user = get_query_first_result(AppUser, bc_store_hash)

        session.permanent = True
        session['storehash'] = app_user.bc_store_hash
        session['storeuseremail'] = bc_email

        if not app_user.hs_access_token:
            return redirect(app.config['APP_URL'] + url_for('get_started'))

        if check_and_provision_subscription(app_user, app.config):
            session['cb_subscription_id'] = app_user.cb_subscription_id
            return redirect(app.config['APP_URL'] + url_for('index'))

        app_url = app.config['APP_URL']
        stage = app.config['STAGE-PREFIX']
        signup_page_id, signup_page_url = construct_chargebee_signup_url(bc_email, app_url, config=app.config)
        session['hosted_page_id'] = signup_page_id
        return render_template('success_hubspot.html', chargebee_hosted_url=signup_page_url, app_url=app_url+stage+'/')


@app.route('/bigcommerce/callback')
def auth_callback():
    with callback_manager(request.args, app.config) as callback_ctx:

        with bc_token_manager(callback_ctx, app.config) as token_ctx:
            bc_id, email, access_token = token_ctx

            with app_user_creation_manager(callback_ctx, token_ctx) as app_user:
                session['storehash'] = app_user.bc_store_hash
                session['storeuseremail'] = email
                return redirect(app.config['APP_URL'] + url_for('get_started'))


@app.route('/getstarted')
def get_started():
    hs_auth_url = construct_hubspot_auth_url(app.config)

    return render_template('get_started.html', hs_auth_url=hs_auth_url)


@app.route('/bigcommerce/uninstall')
def uninstall():
    with payload_manager(request.args, app.config) as payload_ctx:
        bc_store_hash, bc_email = payload_ctx

    app_user = get_query_first_result(AppUser, bc_store_hash)

    delete_all_webhooks(app_user, app.config)

    app_user.delete()

    return Response('Deleted', status=204)


@app.route('/hsauth')
def hs_auth_callback():
    with hubspot_auth_manager(request.args, app.config) as hubspot_auth_ctx:

        bc_store_hash = session['storehash']

        with app_user_hubspot_token_manager(bc_store_hash, hubspot_auth_ctx) as app_user:
            if check_and_provision_subscription(app_user, app.config):
                session['storehash'] = app_user.bc_store_hash
                session['storeuseremail'] = app_user.bc_email
                session['cb_subscription_id'] = app_user.cb_subscription_id
                return redirect(app.config['APP_URL'] + url_for('index'))

            app_user.save()
            app_url = app.config['APP_URL']
            signup_page_id, signup_page_url = (construct_chargebee_signup_url(app_user.bc_email, app_url,
                                                                              config=app.config))
            session['hosted_page_id'] = signup_page_id
        return render_template('success_hubspot.html', chargebee_hosted_url=signup_page_url)


@app.route('/paymentsuccess')
def payment_success():
    bc_store_hash = session['storehash']
    hosted_page_id = session['hosted_page_id']
    app_user = get_query_first_result(AppUser, bc_store_hash)
    cb_subscription = get_chargebee_hosted_page(hosted_page_id, config=app.config)
    cb_subscription_id = cb_subscription.content.subscription.id
    update_chargebee_subscription_with_meta_data(cb_subscription_id, bc_store_hash, config=app.config)
    app_user.cb_subscription_id = cb_subscription_id

    app_user.save()
    register_or_activate_bc_webhooks(app_user, app.config)

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
    reactivated_sub = reactivate_chargebee_subscription_by_id(app_user.cb_subscription_id, config=app.config)
    if reactivated_sub.status == 'active':
        register_or_activate_bc_webhooks(app_user, app.config)

    return redirect(url_for('index'))


@app.route('/subscription-events', methods=['POST'])
def subscription_cancelled():
    data = json.loads(request.data)
    subscription = data.get('content').get('subscription')
    if subscription and subscription.get('status') == 'cancelled':
        sub = get_chargebee_subscription_by_id(subscription['id'], config=app.config)
        meta_data = sub.meta_data
        bc_store_hash = meta_data['bc_store_hash']
        app_user = get_query_first_result(AppUser, bc_store_hash)
        deactivate_bc_webhooks(app_user, app.config)
    return 'Ok'


if __name__ == '__main__':
    app.run('0.0.0.0', debug=True, port=8100)
