// Shared TypeScript types used across apps/web and any type-safe consumers.
// Add domain types here as they stabilize.

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  limit: number
}

export interface ErrorResponse {
  detail: string
  code?: string
}
