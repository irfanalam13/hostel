
# Enterprise API Performance & Request Pipeline Audit Prompt

## Objective

Act as a **Senior Staff Full-Stack Performance Engineer**, **Next.js App Router Expert**, **Django REST Framework Architect**, **Network Engineer**, and **DevOps Performance Specialist**.

Your mission is **NOT to immediately fix code**.

Your mission is to perform a **complete end-to-end investigation** of every request flowing through the application, identify every bottleneck, explain the root cause with evidence, and then implement the correct solution.

Never guess.

Every conclusion must be backed by logs, measurements, traces, or profiling.

---

# Tech Stack

Frontend

- Next.js 15+
- React 19
- TypeScript
- App Router
- Server Components
- Client Components
- Turbopack
- TailwindCSS

Backend

- Django 5+
- Django REST Framework
- PostgreSQL
- Redis
- Celery
- JWT Authentication

Infrastructure

- Docker Compose
- Nginx (future production)
- HTTPS ready

---

# Primary Goal

Investigate why any API request may become:

- Pending forever
- Extremely slow
- Waiting during routing
- Stuck on Rendering...
- Stuck on Loading...
- Infinite spinner
- Navigation never completes
- Login never loads
- Signup never loads
- Dashboard never loads

The audit must discover **exactly where** the request becomes blocked.

---

# Golden Rule

Never assume.

For every request answer these questions:

1. Did the frontend send the request?
2. Did the request leave the browser?
3. Did Next.js receive it?
4. Did middleware execute?
5. Did App Router block?
6. Did Server Components wait?
7. Did React Suspense suspend forever?
8. Did fetch() complete?
9. Did Django receive the request?
10. Did middleware block?
11. Did authentication block?
12. Did database query block?
13. Did Redis block?
14. Did serializer block?
15. Did response leave Django?
16. Did browser receive response?
17. Did React render response?
18. Did router finish navigation?

Every stage must be measured.

---

# Phase 1

## Browser Investigation

Inspect

- Network Tab
- Performance Tab
- Memory
- Sources
- Console
- Initiator
- Timing
- Waterfall

For every API request record

- DNS
- TCP
- SSL
- Request Start
- Waiting (TTFB)
- Download
- Total Time

Find

- Pending requests
- Cancelled requests
- Duplicate requests
- Infinite retries
- CORS issues
- Preflight issues
- HTTP errors
- Stalled requests
- Chunk loading failures

---

# Phase 2

## React Investigation

Audit every

useEffect()

Find

- Infinite loops
- Dependency mistakes
- Missing dependency arrays
- Continuous re-rendering
- Recursive state updates
- Endless fetches

Audit

useMemo

useCallback

Suspense

Error Boundaries

Lazy loading

Server Components

Client Components

Dynamic imports

Hydration

Streaming rendering

Detect

- Hydration mismatch
- Infinite rendering
- Component remount loops
- Router refresh loops
- Recursive rendering

---

# Phase 3

## Next.js Routing Audit

Inspect

App Router

Layouts

Nested layouts

Loading.tsx

Error.tsx

NotFound

Middleware

Route Handlers

Server Actions

Navigation

Redirects

router.push()

router.replace()

router.refresh()

Detect

- Infinite redirect
- Middleware recursion
- Authentication redirect loop
- Route mismatch
- Dynamic route blocking
- Missing await
- Promise never resolved

Measure routing time.

---

# Phase 4

## Authentication Investigation

Audit

JWT

Access Token

Refresh Token

Cookie

Headers

Authorization

CSRF

Session validation

Detect

- Infinite refresh
- Endless auth check
- Token validation loops
- Expired token retry loop
- Multiple refresh requests
- Cookie mismatch

---

# Phase 5

## API Client Investigation

Inspect

fetch()

Axios

Interceptors

Request wrappers

AbortController

Retry logic

Timeout logic

Caching

Request deduplication

Detect

- Missing timeout
- Infinite retries
- Promise never resolved
- Hanging requests
- Missing await
- Deadlock

Every request should include

Request Start

Request End

Duration

Status

Error

---

# Phase 6

## Backend Request Audit

Measure

Request arrival

Middleware

Authentication

Permissions

Throttle

View execution

Serializer

Database

Response serialization

Response sending

Log execution time for every layer.

---

# Phase 7

## Django Middleware Audit

Inspect every middleware.

Measure execution time.

Detect

- Blocking middleware
- Authentication delay
- Session lookup
- Cache delay
- Logging delay

Generate timing report.

---

# Phase 8

## Database Investigation

Enable SQL profiling.

Measure

Every query

Query count

Execution time

Rows scanned

Indexes used

Find

N+1 queries

Missing indexes

Sequential scans

Long transactions

Locks

Deadlocks

Blocking queries

Large joins

Repeated queries

Recommend

select_related()

prefetch_related()

bulk_create()

bulk_update()

Database indexes

---

# Phase 9

## Redis Investigation

Measure

Cache hit ratio

Cache miss ratio

Redis latency

Connection pool

Blocking commands

Key expiration

---

# Phase 10

## Celery Investigation

Ensure

Frontend never waits for Celery.

Detect

Synchronous tasks

Blocking task execution

Long-running jobs

Missing background processing

---

# Phase 11

## Docker Investigation

Measure

docker stats

CPU

Memory

Disk

Swap

Network

Container restart count

Health checks

Detect

Container starvation

Resource exhaustion

OOM

Slow filesystem

Volume latency

---

# Phase 12

## Network Investigation

Inspect

localhost communication

Docker bridge

Port forwarding

Proxy

Nginx

DNS

TCP retries

Keep-alive

HTTP/2

Compression

Chunked transfer

---

# Phase 13

## Logging

Implement structured logs.

Every request must log

Request ID

Timestamp

Route

Method

Authenticated user

Duration

Database time

Cache time

Serializer time

Response size

Status code

---

# Phase 14

## Distributed Tracing

Instrument

Frontend

Backend

Database

Redis

Every request receives

Trace ID

Span ID

Measure

Frontend → Backend

Backend → Database

Database → Backend

Backend → Frontend

Visualize complete request timeline.

---

# Phase 15

## Performance Profiling

Profile

CPU

Memory

Garbage Collection

Heap

Flame Graph

Function execution

Find

Hot paths

Slow functions

Blocking operations

---

# Phase 16

## Frontend Rendering Audit

Measure

Time to Interactive

First Paint

Largest Contentful Paint

Hydration

Streaming

Rendering

Component mount

Component update

Detect

Rendering waterfall

Blocking component

Large bundle

Slow hydration

---

# Phase 17

## Error Investigation

Capture

Unhandled Promise

Unhandled Exception

Network Error

Timeout

React Error

Django Error

Serializer Error

Database Error

Redis Error

Routing Error

Middleware Error

Never swallow exceptions.

---

# Phase 18

## Monitoring

Integrate

OpenTelemetry

Prometheus

Grafana

Jaeger

Collect

API latency

P95

P99

Request count

Error rate

Database latency

Cache latency

CPU

Memory

Network

---

# Deliverables

Produce a comprehensive report including:

1. Complete request lifecycle diagram.
2. Frontend request timeline.
3. Backend request timeline.
4. Database query analysis.
5. Redis analysis.
6. Authentication flow analysis.
7. Routing analysis.
8. Middleware analysis.
9. Performance bottlenecks ranked by severity.
10. Root cause(s) with supporting evidence.
11. Recommended fixes with code changes.
12. Before vs. after performance comparison.
13. Performance optimization checklist.
14. Validation tests proving the issue is resolved.

---

# Success Criteria

The application should achieve:

- No request remains pending indefinitely.
- No infinite routing or rendering loops.
- Navigation between pages completes reliably.
- Authentication flow finishes without deadlocks.
- All API requests have measurable latency.
- Average API response time < 200 ms (development targets may vary).
- P95 API latency < 500 ms.
- No N+1 database queries.
- No middleware bottlenecks.
- No infinite React re-renders.
- No unresolved Promises.
- No hanging `fetch()` calls.
- Every request includes structured logs and trace IDs.
- The entire request lifecycle is observable from browser to database and back.
