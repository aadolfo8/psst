import asyncio
from datetime import UTC, datetime, timedelta

from httpx import AsyncClient, Response
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Participant
from app.security import LOCKOUT_DURATION, MAX_FAILED_ATTEMPTS
from tests.conftest import create_group, join


async def log_in(client: AsyncClient, slug: str, pin: str, name: str = "Ana") -> Response:
    return await client.post(f"/groups/{slug}/sessions", json={"name": name, "pin": pin})


async def test_fifth_failure_locks_even_the_right_pin(client: AsyncClient) -> None:
    slug = (await create_group(client))["group"]["slug"]

    for _ in range(MAX_FAILED_ATTEMPTS - 1):
        assert (await log_in(client, slug, "0000")).status_code == 401
    fifth = await log_in(client, slug, "0000")
    right_pin = await log_in(client, slug, "1234")

    assert fifth.status_code == 429
    assert right_pin.status_code == 429
    retry_after = int(right_pin.headers["Retry-After"])
    assert 0 < retry_after <= LOCKOUT_DURATION.total_seconds()


async def test_can_log_in_after_lock_expires(client: AsyncClient, db: AsyncSession) -> None:
    me = await create_group(client)
    slug = me["group"]["slug"]
    for _ in range(MAX_FAILED_ATTEMPTS):
        await log_in(client, slug, "0000")

    # En lugar de esperar 15 minutos, movemos el fin del bloqueo al pasado.
    await db.execute(
        update(Participant)
        .where(Participant.id == me["id"])
        .values(locked_until=datetime.now(UTC) - timedelta(seconds=1))
    )
    await db.commit()

    assert (await log_in(client, slug, "1234")).status_code == 200
    participant = await db.scalar(
        select(Participant)
        .where(Participant.id == me["id"])
        .execution_options(populate_existing=True)
    )
    assert participant is not None
    assert participant.failed_attempts == 0
    assert participant.locked_until is None


async def test_success_resets_failed_attempts(client: AsyncClient) -> None:
    slug = (await create_group(client))["group"]["slug"]

    for _ in range(MAX_FAILED_ATTEMPTS - 1):
        await log_in(client, slug, "0000")
    assert (await log_in(client, slug, "1234")).status_code == 200
    for _ in range(MAX_FAILED_ATTEMPTS - 1):
        assert (await log_in(client, slug, "0000")).status_code == 401

    assert (await log_in(client, slug, "1234")).status_code == 200


async def test_lock_only_affects_that_participant(client: AsyncClient, new_client) -> None:
    slug = (await create_group(client))["group"]["slug"]
    async with new_client() as luis:
        await join(luis, slug, "Luis", pin="5678")

    for _ in range(MAX_FAILED_ATTEMPTS):
        await log_in(client, slug, "0000")

    assert (await log_in(client, slug, "1234")).status_code == 429
    assert (await log_in(client, slug, "5678", name="Luis")).status_code == 200


async def test_parallel_attempts_cannot_skip_the_limit(client: AsyncClient) -> None:
    slug = (await create_group(client))["group"]["slug"]

    responses = await asyncio.gather(*(log_in(client, slug, "0000") for _ in range(10)))

    codes = sorted(r.status_code for r in responses)
    # Solo los 4 primeros fallos llegan a comprobar el PIN; el resto ya encuentra el bloqueo.
    assert codes == [401] * (MAX_FAILED_ATTEMPTS - 1) + [429] * (11 - MAX_FAILED_ATTEMPTS)
