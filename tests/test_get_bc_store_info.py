from hubmetrix_utils import get_bc_store_info, parse_bc_address


def test_get_bc_store_info_returns_store_info(app_user, app_config):
    bc_store_info = get_bc_store_info(app_user, app_config)

    assert bc_store_info


def test_get_bc_store_info_returns_expected_store_hash(app_user, app_config):
    bc_store_info = get_bc_store_info(app_user, app_config)
    store_hash = '2b0o559ql7'

    assert bc_store_info['id'] == store_hash


def test_parse_address_info_from_store_info(bc_store_info):
    address_info = parse_bc_address(bc_store_info['address'])

    assert address_info


def test_parse_address_info_returns_correct_address_parts(bc_store_info):
    address_info = parse_bc_address(bc_store_info['address'])

    assert address_info['line1'] == '123 Easy St.'
    assert address_info['city'] == 'Honolulu'
    assert address_info['state'] == 'HI'
    assert address_info['zip'] == '96822'
