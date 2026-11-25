import ssl

from sqlalchemy.engine import URL, make_url


def async_database_connection(connection_string: str) -> tuple[URL, dict]:
    url = make_url(connection_string)
    if url.drivername in {"postgres", "postgresql"}:
        url = url.set(drivername="postgresql+asyncpg")

    if url.drivername != "postgresql+asyncpg":
        return url, {}

    sslmode = url.query.get("sslmode")
    if url.host and url.host.endswith(".neon.tech"):
        # Neon libpq URLs commonly include channel_binding=require. The
        # asyncpg connector uses its SSL option and verifies Neon by hostname.
        return (
            url.difference_update_query(["sslmode", "ssl", "channel_binding"]),
            {"ssl": ssl.create_default_context()},
        )
    if sslmode is not None:
        ssl_option = url.query.get("ssl", sslmode)
        return url.difference_update_query(["sslmode"]).update_query_dict({"ssl": ssl_option}), {}
    return url, {}
