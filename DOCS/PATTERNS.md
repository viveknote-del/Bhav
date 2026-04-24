# Design Patterns

Reference doc — read when designing a new feature or reviewing code. NOT auto-loaded.

---

## Backend patterns

### Repository pattern

Encapsulate all DB access behind a consistent interface. Routers and services never touch the DB client directly.

```python
class ItemRepository:
    def __init__(self, db: AsyncClient):
        self.db = db

    async def find_all(self, user_id: str, limit: int = 20, offset: int = 0) -> list[dict]:
        return (
            self.db.table("items")
            .select("*")
            .eq("user_id", user_id)
            .limit(limit)
            .offset(offset)
            .execute()
            .data
        )

    async def find_by_id(self, id: str, user_id: str) -> dict | None:
        result = (
            self.db.table("items")
            .select("*")
            .eq("id", id)
            .eq("user_id", user_id)
            .maybe_single()
            .execute()
        )
        return result.data

    async def create(self, **kwargs) -> dict:
        return self.db.table("items").insert(kwargs).execute().data[0]

    async def update(self, id: str, **kwargs) -> dict:
        return (
            self.db.table("items")
            .update(kwargs)
            .eq("id", id)
            .execute()
            .data[0]
        )

    async def delete(self, id: str) -> None:
        self.db.table("items").delete().eq("id", id).execute()
```

Use `find_by_id` + `user_id` check at repository level — RLS is a second line of defense, not the only defense.

### Dependency injection via FastAPI Depends

```python
# dependencies.py
def get_supabase() -> AsyncClient:
    return create_client(settings.supabase_url, settings.supabase_service_role_key)

def get_item_repo(db: AsyncClient = Depends(get_supabase)) -> ItemRepository:
    return ItemRepository(db)

def get_item_service(repo: ItemRepository = Depends(get_item_repo)) -> ItemService:
    return ItemService(repo)

# routers/items.py
@router.get("/items")
async def list_items(
    service: ItemService = Depends(get_item_service),
    user: dict = Depends(require_user),
):
    return await service.list(user_id=user["sub"])
```

### Worker pattern (arq)

```python
# workers/process_item.py
async def process_item(ctx: dict, item_id: str) -> None:
    """Async job — enqueued by the API, executed by the worker process."""
    db = ctx["db"]
    repo = ItemRepository(db)

    item = await repo.find_by_id(item_id, user_id=None)
    if not item:
        return  # already deleted — safe no-op

    # Do the work
    result = await generate_content(item)

    # Update status
    await repo.update(item_id, status="DONE", result=result)

# How to enqueue from a router/service:
async def enqueue_processing(item_id: str, redis: Redis):
    await redis.enqueue_job("process_item", item_id)
```

---

## Frontend patterns

### Container / Presentational split

```tsx
// Container — owns data fetching and state
function CampaignListContainer() {
  const { campaigns, isLoading, error, refetch } = useCampaigns()

  if (isLoading) return <CampaignListSkeleton />
  if (error) return <ErrorMessage message={error.message} onRetry={refetch} />
  if (!campaigns.length) return <EmptyState />

  return <CampaignList campaigns={campaigns} />
}

// Presentational — pure, no side effects
function CampaignList({ campaigns }: { campaigns: Campaign[] }) {
  return (
    <ul>
      {campaigns.map((c) => <CampaignCard key={c.id} campaign={c} />)}
    </ul>
  )
}
```

### Optimistic updates

```ts
async function publishCampaign(id: string) {
  // 1. Snapshot
  const previous = campaigns

  // 2. Optimistic update
  setCampaigns((prev) => prev.map((c) => c.id === id ? { ...c, status: 'PUBLISHING' } : c))

  try {
    await apiClient.post(`/campaigns/${id}/publish`)
    await refetch() // sync with server truth
  } catch (err) {
    // 3. Roll back
    setCampaigns(previous)
    toast.error('Failed to publish. Please try again.')
  }
}
```

### URL as state — persist shareable UI state in the URL

```ts
// Search, filters, pagination, active tab — always in URL params
const [searchParams, setSearchParams] = useSearchParams()
const page = Number(searchParams.get('page') ?? '1')
const status = searchParams.get('status') ?? 'all'
```

Never store these in component state — they become unshareable and break the back button.

### Error boundary

```tsx
// app/error.tsx (Next.js App Router error boundary)
'use client'

export default function Error({ error, reset }: { error: Error; reset: () => void }) {
  return (
    <div>
      <h2>Something went wrong</h2>
      <p>{error.message}</p>
      <button onClick={reset}>Try again</button>
    </div>
  )
}
```

Every route segment that fetches data must have an adjacent `error.tsx`.

### State management — don't mix concerns

| Concern | Tool |
|---|---|
| Server data (fetched from API) | SWR or TanStack Query or custom hook with useEffect |
| Client-only UI state (modal open, selected tab) | useState |
| URL state (filters, search, page) | searchParams |
| Form state | react-hook-form or controlled form |
| Global auth state | Context or Zustand |

Never put server data into Zustand/Context — it creates stale data bugs. Always re-fetch.

---

## AI provider patterns

### Single abstraction — providers/llm.py

All LLM calls go through `providers/llm.py`. Never import `anthropic` or `openai` directly from routers, services, or workers.

Benefits: model swaps happen in one file, retry logic is centralized, cost tracking is centralized.

### Prompt caching — always cache system prompts

```python
# providers/llm.py
async def complete_cached(
    prompt: str,
    system: str,
    model: str = "claude-haiku-4-5-20251001",
    max_tokens: int = 1024,
) -> str:
    """
    Uses prompt caching for the system prompt.
    Cache hits cost 10% of normal input tokens.
    For a 2,000-token system prompt called 100x/day: saves ~$1.80/day on Haiku.
    """
    response = await client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=[
            {
                "type": "text",
                "text": system,
                "cache_control": {"type": "ephemeral"},  # ← enables caching
            }
        ],
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text
```

Cache the system prompt whenever it's the same across calls (which it almost always is for workers).

### Graceful degradation

```python
async def generate_copy(campaign: dict) -> str:
    try:
        return await llm.complete(prompt=build_prompt(campaign))
    except anthropic.RateLimitError:
        logger.warning("llm.rate_limited — using fallback")
        return generate_template_copy(campaign)  # rule-based fallback
    except anthropic.APIError as e:
        logger.error("llm.api_error", error=str(e))
        raise HTTPException(503, "Content generation temporarily unavailable")
```

AI calls must never be a single point of failure for the user flow.

### Structured output with validation

```python
async def generate_structured(prompt: str, schema: type[BaseModel]) -> BaseModel:
    raw = await llm.complete(
        prompt=f"{prompt}\n\nRespond ONLY with valid JSON matching this schema:\n{schema.model_json_schema()}"
    )
    try:
        return schema.model_validate_json(raw)
    except ValidationError as e:
        logger.warning("llm.structured_output.invalid", error=str(e), raw=raw[:200])
        raise ValueError(f"LLM returned invalid structure: {e}")
```

Always validate LLM JSON output with Pydantic — never trust raw strings.

---

## Security patterns

### Authorization check order (every protected endpoint)

```python
# 1. Authenticate — verify JWT (handled by Depends(require_user))
# 2. Fetch the resource
item = await repo.find_by_id(item_id)
if not item:
    raise HTTPException(404)  # not found before ownership check — prevents enumeration
# 3. Authorize — verify ownership
if item["user_id"] != user["sub"]:
    raise HTTPException(403)
```

Always 404 before 403. Returning 403 on a non-existent ID leaks existence.

### Input sanitization

```python
# Use Pydantic for all input — never pass raw request body to DB
class ItemCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: str = Field(default="", max_length=2000)
    platform: Literal["instagram", "facebook", "google"]
```

Never `**request.json()` directly into a DB call.
