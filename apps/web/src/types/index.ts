export interface User {
  id: string
  email: string
  created_at: string
}

export interface ApiResponse<T> {
  data: T | null
  error: string | null
}
