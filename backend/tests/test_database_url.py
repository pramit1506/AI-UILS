import ssl

from app.database.url import async_database_connection


def test_neon_connection_uses_system_certificate_verification():
    url, kwargs = async_database_connection(
        "postgresql://example:percent%25encoded@ep-example.ap-southeast-1.aws.neon.tech/example"
        "?sslmode=require&channel_binding=require"
    )
    assert url.drivername == "postgresql+asyncpg"
    assert url.password == "percent%encoded"
    assert not url.query
    context = kwargs["ssl"]
    assert context.verify_mode == ssl.CERT_REQUIRED
    assert context.check_hostname


def test_plain_local_connection_leaves_tls_options_unset():
    url, kwargs = async_database_connection("postgresql://example:example@localhost/example")
    assert url.drivername == "postgresql+asyncpg"
    assert url.host == "localhost"
    assert not url.query
    assert not kwargs
