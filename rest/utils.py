import asyncio as aio


def to_coroutine(func):
    """Check if the given func is a coroutine function. If not convert it into an awaitable."""
    if aio.iscoroutinefunction(func):
        return func

    async def awaitable(*args, **kwargs):
        return func(*args, **kwargs)

    return awaitable
