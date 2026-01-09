import pytest

from depdiff.pypi.metadata import MetadataClient


@pytest.mark.vcr
def test_requests():
    client = MetadataClient()

    metadata = client.get("requests", "2.9.2")

    assert metadata.urls == [
        "https://files.pythonhosted.org/packages/8b/e7/229a428b8eb9a7f925ef16ff09ab25856efe789410d661f10157919f2ae2/requests-2.9.2-py2.py3-none-any.whl",
        "https://files.pythonhosted.org/packages/64/20/2133a092a0e87d1c250fe48704974b73a1341b7e4f800edecf40462a825d/requests-2.9.2.tar.gz",
    ]
    assert metadata.info.url == "http://python-requests.org"
