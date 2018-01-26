from dynamodb_utils import get_query_first_result, AppUser


def test_get_query_result_returns_user():
    user = get_query_first_result(AppUser, 'store_hash')
    assert user


def test_get_query_first_result_returns_empty_list():
    user = get_query_first_result(AppUser, 'invalid')
    assert user is None
