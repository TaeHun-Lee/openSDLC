import { toast } from "sonner"

const BASE_URL = "/api"

function getApiKey(): string {
  return localStorage.getItem("opensdlc_api_key") || ""
}

export class ApiError extends Error {
  status: number
  detail: unknown

  constructor(status: number, detail: unknown) {
    super(`API error ${status}`)
    this.status = status
    this.detail = detail
  }
}

function extractMessage(detail: unknown): string {
  if (typeof detail === "string") return detail
  if (detail && typeof detail === "object") {
    const d = detail as Record<string, unknown>
    if (typeof d.detail === "string") return d.detail
    if (typeof d.message === "string") return d.message
  }
  return ""
}

// 401 handler — triggers API Key dialog via a callback set by App.tsx
let _on401: (() => void) | null = null
export function setOn401Handler(handler: () => void) {
  _on401 = handler
}

function handleApiError(error: ApiError): void {
  const msg = extractMessage(error.detail)

  switch (error.status) {
    case 401:
      _on401?.()
      toast.error("인증이 필요합니다", {
        description: "API Key를 입력해주세요.",
      })
      break
    case 403:
      toast.error("접근 거부", {
        description: msg || "이 작업을 수행할 권한이 없습니다.",
      })
      break
    case 404:
      toast.error("리소스를 찾을 수 없습니다", {
        description: msg || "요청한 항목이 존재하지 않습니다.",
      })
      break
    case 409:
      toast.error("충돌", {
        description: msg || "요청이 현재 상태와 충돌합니다.",
      })
      break
    case 422:
      // Validation errors — let the caller handle inline display
      break
    case 429:
    case 503:
      toast.error("서버 과부하", {
        description: msg || "잠시 후 다시 시도해주세요.",
      })
      break
    default:
      if (error.status >= 500) {
        toast.error("서버 오류", {
          description: msg || "서버 오류가 발생했습니다. 잠시 후 다시 시도해주세요.",
        })
      }
  }
}

const MAX_RETRIES = 3
const RETRY_DELAY = 1000

export async function apiFetch<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const apiKey = getApiKey()
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(apiKey ? { "X-API-Key": apiKey } : {}),
    ...(options.headers as Record<string, string> || {}),
  }

  let lastError: Error | null = null

  for (let attempt = 0; attempt <= MAX_RETRIES; attempt++) {
    try {
      const response = await fetch(`${BASE_URL}${path}`, {
        ...options,
        headers,
      })

      if (!response.ok) {
        let detail: unknown
        try {
          detail = await response.json()
        } catch {
          detail = response.statusText
        }
        const apiError = new ApiError(response.status, detail)
        handleApiError(apiError)
        throw apiError
      }

      if (response.status === 204) {
        return undefined as T
      }

      return response.json()
    } catch (error) {
      if (error instanceof ApiError) {
        throw error
      }
      // Network error — retry
      lastError = error as Error
      if (attempt < MAX_RETRIES) {
        await new Promise((r) => setTimeout(r, RETRY_DELAY * (attempt + 1)))
        continue
      }
    }
  }

  toast.error("서버에 연결할 수 없습니다", {
    description: `네트워크 오류: ${lastError?.message || "연결 실패"}. ${MAX_RETRIES}회 재시도 후 실패했습니다.`,
  })
  throw lastError!
}

export const api = {
  get: <T>(path: string) => apiFetch<T>(path),
  post: <T>(path: string, body?: unknown) =>
    apiFetch<T>(path, { method: "POST", body: body ? JSON.stringify(body) : undefined }),
  put: <T>(path: string, body?: unknown) =>
    apiFetch<T>(path, { method: "PUT", body: body ? JSON.stringify(body) : undefined }),
  delete: <T>(path: string) =>
    apiFetch<T>(path, { method: "DELETE" }),
}
