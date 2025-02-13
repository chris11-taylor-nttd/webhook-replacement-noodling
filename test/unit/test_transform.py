from launch_webhook_aws.transform import default_transform


def test_default_transform_does_nothing():
    assert default_transform({}) == {}
    assert default_transform({"foo": "bar"}) == {"foo": "bar"}
