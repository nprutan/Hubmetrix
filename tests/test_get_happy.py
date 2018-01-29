from happiness_scale import get_happy, happy_encouragement, happy_scale


def test_get_happy():
    happy_scale_statement, happy_encouragement_statement = get_happy()

    assert happy_scale_statement in happy_scale
    assert happy_encouragement_statement in happy_encouragement

