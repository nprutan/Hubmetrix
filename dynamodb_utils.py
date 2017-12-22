from pynamodb.exceptions import QueryError
from pynamodb.models import Model
from pynamodb.attributes import UnicodeAttribute, NumberAttribute, ListAttribute


__all__ = ['AppUser', 'get_query_first_result', 'QueryError']


def get_query_first_result(model, query_text):
    try:
        for response in model.query(query_text):
            return response
    except QueryError:
        return None


class AppUser(Model):
    """
    A user of the Hubmetrix app
    """
    class Meta:
        table_name = 'hubmetrix-user'
        region = 'us-west-1'

    email = UnicodeAttribute(hash_key=True)
    bc_id = NumberAttribute(range_key=True)
    bc_store_id = UnicodeAttribute(null=True)
    bc_store_hash = UnicodeAttribute()
    bc_access_token = UnicodeAttribute()
    bc_scope = UnicodeAttribute()
    hs_refresh_token = UnicodeAttribute(null=True)
    hs_access_token = UnicodeAttribute(null=True)
    hs_expires_in = UnicodeAttribute(null=True)
    hs_app_id = UnicodeAttribute(null=True)
    hs_hub_domain = UnicodeAttribute(null=True)
    hs_hub_id = UnicodeAttribute(null=True)
    hs_token_type = UnicodeAttribute(null=True)
    hs_user = UnicodeAttribute(null=True)
    hs_user_id = UnicodeAttribute(null=True)
    hs_scopes = ListAttribute(null=True)