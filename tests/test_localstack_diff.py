def test_localstack_diff(localstack_diff):
    assert "psutil==7.2.1" in localstack_diff
