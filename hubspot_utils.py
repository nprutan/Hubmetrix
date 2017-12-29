import requests

HS_BASE_AUTH_URI = 'https://api.hubapi.com/oauth/v1/token'

__all__ = ['exchange_code_for_token', 'get_token_info']


def exchange_code_for_token(auth_code, clnt_id, clnt_secret, redir_uri):
    headers = {'Content-Type': 'application/x-www-form-urlencoded;charset=utf-8'}
    payload = 'grant_type=authorization_code&client_id={}&client_secret={}&redirect_uri={}&code={}'.format(clnt_id,
                                                                                                           clnt_secret,
                                                                                                           redir_uri,
                                                                                                           auth_code)

    return requests.post(HS_BASE_AUTH_URI, data=payload, headers=headers).json()


def get_token_info(token):
    base_uri = 'https://api.hubapi.com/oauth/v1/access-tokens/'
    return requests.get(base_uri + token).json()
