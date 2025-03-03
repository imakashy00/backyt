from fastapi import Request, HTTPException
from redis.asyncio import Redis

# Create async Redis client
redis_client = Redis(host="localhost", port=6379, db=0, decode_responses=True)


async def rate_limit_middleware(request: Request, call_next):
    try:
        # Get client IP with fallback for when client is None
        client_ip = None
        if request.client:
            client_ip = request.client.host
        else:
            # Use a default or header-based IP if client is None
            client_ip = request.headers.get("X-Forwarded-For", "unknown")

        # Create rate limit key based on path and IP
        route = request.url.path
        key = f"ratelimit:{client_ip}:{route}"

        # Check if rate limited (use proper await with async Redis)
        requests = await redis_client.get(key)

        # Set limits based on route
        if route == "/auth/refresh":
            limit = 20  # 20 requests
            period = 60  # per minute
        elif route.startswith("/auth"):
            limit = 10  # 10 requests
            period = 60  # per minute
        else:
            limit = 100  # 100 requests
            period = 60  # per minute

        if requests and int(requests) > limit:
            raise HTTPException(status_code=429, detail="Rate limit exceeded")

        # Use transaction for atomic operations
        async with redis_client.pipeline(transaction=True) as pipe:
            await pipe.incr(key)
            await pipe.expire(key, period)
            await pipe.execute()  # This returns a list, don't await the result

        # Process the request
        response = await call_next(request)
        return response
    except Exception as e:
        # Log the error
        print(f"Rate limit middleware error: {e}")
        # Allow the request to proceed even if rate limiting fails
        return await call_next(request)
