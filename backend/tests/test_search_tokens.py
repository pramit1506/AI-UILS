"""Exercise PostgreSQL's actual tokenizer on a migrated UTF-8 test database."""
import os

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine


@pytest.mark.skipif(not os.getenv("SEARCH_TEST_DATABASE_URL"), reason="needs migrated PostgreSQL")
async def test_json_terms_are_decoded_and_large_sources_keep_their_last_word():
    engine = create_async_engine(os.environ["SEARCH_TEST_DATABASE_URL"])
    try:
        async with engine.connect() as db:
            assert await db.scalar(text("""
                SELECT uils_search_terms_v1(uils_json_text_v1(
                    jsonb_build_object('nested_field', jsonb_build_array(
                        E'first\\nclause', 'café', 'परियोजना', 32, true, null
                    ))
                )) @> uils_search_terms_v1(:keywords)
            """), {"keywords": "nested field clause cafe\u0301 परियोजना 32 true null"})
            terms = await db.scalar(text("""
                SELECT uils_search_terms_v1(repeat('ordinary ', 150000) ||
                    repeat('z', 10000) || ' final-token')
            """))
            assert set(terms) == {"ordinary", "final", "token"}
    finally:
        await engine.dispose()
