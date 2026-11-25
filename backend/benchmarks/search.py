"""Benchmark the first results page using synthetic rows in a PostgreSQL temp table.

From backend/, set SEARCH_BENCHMARK_DATABASE_URL to a migrated test database,
then run python -m benchmarks.search --records 100000 --samples 40.
"""
import argparse
import asyncio
import math
import os
import statistics
import time
import uuid

from sqlalchemy import String, cast, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.models.log_record import LogRecord
from app.repositories.log_record_repository import log_record_repository


OWNER = uuid.UUID("00000000-0000-0000-0000-000000000001")
PAGE_SIZE = 25


async def benchmark(records: int, samples: int):
    engine = create_async_engine(os.environ["SEARCH_BENCHMARK_DATABASE_URL"])
    try:
        async with engine.begin() as connection:
            await connection.execute(text(
                "CREATE TEMP TABLE log_record (LIKE public.log_record INCLUDING ALL) ON COMMIT DROP"
            ))
            # PostgreSQL implicitly searches the temp schema before public.
            started = time.perf_counter()
            await connection.execute(text("""
                INSERT INTO pg_temp.log_record
                    (id, user_id, log_reference, schema_name, domain, data, field_metadata,
                     requires_review, summary, source_filename, source_text, created_at, updated_at)
                SELECT gen_random_uuid(),
                       CASE WHEN n % 2 = 0 THEN CAST(:owner AS uuid) ELSE md5((n % 19)::text)::uuid END,
                       'LOG-SYN-' || n, 'Report', 'Operations',
                       jsonb_build_object('asset', 'asset' || n, 'amount', n % 7000),
                       '{}'::jsonb, n % 5 = 0, 'Equipment inspection', 'report-' || n || '.txt',
                       'Routine inspection of the automobile pump and motor assembly. Tag marker' || n,
                       now() - n * interval '1 second', now()
                FROM generate_series(1, :records) AS n
            """), {"records": records, "owner": OWNER})
            print(f"Inserted {records:,} records in {time.perf_counter() - started:.2f} seconds.")
            await connection.execute(text("ANALYZE pg_temp.log_record"))
            print("Temporary relation and indexes:", await connection.scalar(text(
                "SELECT pg_size_pretty(pg_total_relation_size('pg_temp.log_record'))"
            )))
            async with AsyncSession(bind=connection) as session:
                async def indexed(term):
                    return await log_record_repository.search(
                        session, term, user_id=OWNER, limit=PAGE_SIZE
                    )

                async def previous(term):
                    pattern = "%" + term + "%"
                    columns = (LogRecord.schema_name, LogRecord.domain, LogRecord.summary,
                               LogRecord.log_reference, cast(LogRecord.data, String))
                    query = select(LogRecord).where(
                        LogRecord.user_id == OWNER,
                        or_(*(column.ilike(pattern) for column in columns)),
                    ).order_by(LogRecord.created_at.desc()).limit(PAGE_SIZE)
                    return list((await session.scalars(query)).all())

                # The old substring query must have one matching row too. Choose its
                # final even asset identifier so no longer identifiers share its prefix.
                last_owned = records - records % 2
                plan = await connection.scalars(text("""
                    EXPLAIN (ANALYZE, BUFFERS)
                    SELECT id, data FROM pg_temp.log_record
                    WHERE user_id = :owner AND search_terms @> uils_search_terms_v1(:term)
                    ORDER BY created_at DESC, id DESC LIMIT 25
                """), {"owner": OWNER, "term": f"asset{last_owned}"})
                print("Selective lookup plan:", *plan, sep="\n")
                for label, lookup, term, expected in (
                    ("Previous lookup, rare field", previous, f"asset{last_owned}", 1),
                    ("Indexed, rare field", indexed, f"asset{last_owned}", 1),
                    ("Indexed, source text only", indexed, f"marker{last_owned}", 1),
                    ("Indexed, common field", indexed, "Report", PAGE_SIZE),
                    ("Indexed prefix", indexed, "inspec", PAGE_SIZE),
                    ("Indexed synonym", indexed, "car", PAGE_SIZE),
                    ("Indexed, missing word", indexed, "nomatchxyz", 0),
                ):
                    results = await lookup(term)
                    assert len(results) == expected, f"{label}: got {len(results)} hits"
                    durations = []
                    for _ in range(samples):
                        start = time.perf_counter_ns()
                        await lookup(term)
                        durations.append((time.perf_counter_ns() - start) / 1_000_000)
                    p95 = sorted(durations)[math.ceil(0.95 * samples) - 1]
                    print(f"{label}: p50 {statistics.median(durations):.2f} ms, p95 {p95:.2f} ms")
    finally:
        await engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--records", type=int, default=100_000)
    parser.add_argument("--samples", type=int, default=40)
    args = parser.parse_args()
    if args.records < 50 or args.samples < 1:
        parser.error("Use at least 50 records and one sample.")
    asyncio.run(benchmark(args.records, args.samples))
