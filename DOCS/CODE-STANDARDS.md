# Code Standards

Reference doc — read when implementing or reviewing. NOT auto-loaded.

---

## File size limits

| File type | Soft limit | Hard limit |
|---|---|---|
| CLAUDE.md | 250 lines | 300 lines |
| DOCS/*.md trackers | 100 lines active | Archive past that |
| Python source file | 300 lines | 500 lines |
| TypeScript source file | 300 lines | 500 lines |
| Test file | 200 lines | 400 lines |
| SQL migration | 100 lines | unbounded |

When a file hits the hard limit, split it or archive completed sections.

---

## Naming conventions

### Python
```python
# Variables, functions: snake_case
user_id: str
def get_campaign_by_id(id: str) -> Campaign: ...

# Classes, Pydantic models: PascalCase
class CampaignCreate(BaseModel): ...
class CampaignRepository: ...

# Constants: UPPER_SNAKE_CASE
MAX_CAMPAIGNS_PER_USER = 3

# Private helpers: _snake_case prefix
def _build_query(filters: dict) -> str: ...
```

### TypeScript / React
```ts
// Variables, functions, hooks: camelCase
const userId = '...'
function getCampaign(id: string): Campaign { ... }
function useAuth() { ... }

// Components: PascalCase
function CampaignCard({ campaign }: Props) { ... }

// Types, interfaces: PascalCase
interface Campaign { id: string; name: string }
type CampaignStatus = 'DRAFT' | 'PUBLISHED'

// Constants: UPPER_SNAKE_CASE
const MAX_RETRIES = 3

// Boolean vars: is/has/should/can prefix
const isLoading = true
const hasError = false
```

### CSS
- CSS classes: `kebab-case`
- CSS custom properties: `--semantic-name` (never `--color-1`, always `--color-primary`)

---

## Python patterns

### FastAPI endpoint shape
```python
@router.post("/campaigns", response_model=CampaignResponse, status_code=201)
async def create_campaign(
    body: CampaignCreate,
    user: dict = Depends(require_user),
    service: CampaignService = Depends(get_campaign_service),
) -> CampaignResponse:
    return await service.create(user_id=user["sub"], data=body)
```

Rules:
- Return the response model directly (FastAPI serializes it)
- Never put business logic in the router
- Always use `Depends()` for service injection — never instantiate inside the handler

### Pydantic models (separate request vs response)
```python
class CampaignCreate(BaseModel):
    name: str
    goal: str
    platform: Literal["instagram", "facebook"]

class CampaignResponse(BaseModel):
    id: str
    name: str
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
```

Never use the same model for both input and output.

### Service layer
```python
class CampaignService:
    def __init__(self, repo: CampaignRepository):
        self.repo = repo

    async def create(self, user_id: str, data: CampaignCreate) -> CampaignResponse:
        # 1. Validate business rules
        count = await self.repo.count_by_user(user_id)
        if count >= MAX_CAMPAIGNS_PER_USER:
            raise HTTPException(status_code=429, detail="Campaign limit reached")

        # 2. Build domain object
        campaign = await self.repo.create(user_id=user_id, **data.model_dump())

        # 3. Return response model
        return CampaignResponse.model_validate(campaign)
```

### Repository layer
```python
class CampaignRepository:
    def __init__(self, db: AsyncClient):
        self.db = db

    async def create(self, user_id: str, **kwargs) -> dict:
        result = (
            self.db.table("campaigns")
            .insert({"user_id": user_id, **kwargs})
            .execute()
        )
        return result.data[0]
```

Repositories return raw dicts — services own transformation.

### Error handling
```python
# Raise HTTPException with specific status codes — never 500 unless truly unexpected
raise HTTPException(status_code=404, detail="Campaign not found")
raise HTTPException(status_code=403, detail="Not authorized to access this campaign")
raise HTTPException(status_code=422, detail="Invalid platform value")

# Log unexpected errors with context before re-raising
except Exception as e:
    logger.error("campaign.create.failed", user_id=user_id, error=str(e))
    raise
```

Never swallow exceptions. Never `except Exception: pass`.

---

## TypeScript / React patterns

### API calls — always use apiClient, never fetch
```ts
// CORRECT
import { apiClient } from '@/lib/api'
const { data } = await apiClient.get<Campaign[]>('/campaigns')

// WRONG — never bare fetch, no auth header
const res = await fetch('/campaigns')
```

### Component state — loading / error / empty triad
Every data-fetching component must handle all three states:
```tsx
if (isLoading) return <CampaignListSkeleton />
if (error) return <ErrorMessage message={error.message} onRetry={refetch} />
if (!campaigns.length) return <EmptyState message="No campaigns yet" />
return <CampaignList campaigns={campaigns} />
```

Never render a half-loaded UI or leave errors silent.

### Immutability
```ts
// CORRECT — create new object
const updated = { ...campaign, status: 'PUBLISHED' }

// WRONG — mutate in place
campaign.status = 'PUBLISHED'
```

### Custom hooks — own one concern
```ts
// CORRECT — focused hook
function useCampaigns() {
  const [campaigns, setCampaigns] = useState<Campaign[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<Error | null>(null)
  // fetch logic...
  return { campaigns, isLoading, error, refetch }
}

// WRONG — god hook that fetches everything
function useAppData() { ... }
```

---

## Testing patterns

### Backend — pytest

```python
# Arrange / Act / Assert
async def test_create_campaign_enforces_limit(client, auth_headers):
    # Arrange — create 3 campaigns (the limit)
    for _ in range(3):
        await client.post("/campaigns", json={...}, headers=auth_headers)

    # Act — try to create a 4th
    response = await client.post("/campaigns", json={...}, headers=auth_headers)

    # Assert
    assert response.status_code == 429
    assert "limit" in response.json()["detail"].lower()
```

Test naming: `test_{what}_{condition}` → `test_create_campaign_enforces_limit`

Always test the failure path, not just the happy path.

### Frontend — Jest + Testing Library

```tsx
test('shows empty state when no campaigns exist', async () => {
  // Arrange
  server.use(rest.get('/campaigns', (_, res, ctx) => res(ctx.json([]))))

  // Act
  render(<CampaignList />)

  // Assert
  expect(await screen.findByText(/no campaigns/i)).toBeInTheDocument()
})
```

Prefer `findBy*` (async) over `getBy*` for anything that requires a network call.

---

## API response envelope

All list endpoints use a consistent envelope:
```json
{
  "items": [...],
  "total": 42,
  "page": 1,
  "limit": 20
}
```

All error responses use:
```json
{
  "detail": "Human-readable error message",
  "code": "CAMPAIGN_LIMIT_REACHED"
}
```

Never return raw arrays from list endpoints. Never return bare strings for errors.

---

## Logging

### Backend — structured logging only
```python
import logging
logger = logging.getLogger(__name__)

# CORRECT — structured key=value
logger.info("campaign.created", extra={"campaign_id": id, "user_id": user_id})
logger.error("campaign.create.failed", extra={"error": str(e), "user_id": user_id})

# WRONG — unstructured string interpolation
logger.info(f"Campaign {id} created by {user_id}")
```

Never log: passwords, tokens, PII, full request bodies containing sensitive fields.

### Frontend
```ts
// Only log errors — never console.log for debugging in production
console.error('Campaign fetch failed:', error.message)

// Remove all console.log before committing
```
