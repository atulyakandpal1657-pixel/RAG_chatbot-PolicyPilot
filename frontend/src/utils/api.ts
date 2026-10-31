export interface ChatCitation {
  n: number;
  filename: string;
  page: number;
  snippet: string;
}

export interface ChatResponse {
  answer: string;
  citations: ChatCitation[];
  answerable: boolean;
  confidence: number;
  search_query?: string | null;
  gating_score?: number | null;
}

export function apiUrl(
  path: string,
  baseUrl = process.env.NEXT_PUBLIC_API_URL,
): string {
  if (!baseUrl?.trim()) {
    throw new Error(
      "NEXT_PUBLIC_API_URL is missing. Set it in frontend/.env.local for local development or in the Vercel project environment.",
    );
  }

  let base: URL;
  try {
    base = new URL(baseUrl.trim());
  } catch {
    throw new Error("NEXT_PUBLIC_API_URL must be an absolute HTTP(S) URL.");
  }

  if (base.protocol !== "http:" && base.protocol !== "https:") {
    throw new Error("NEXT_PUBLIC_API_URL must be an absolute HTTP(S) URL.");
  }

  const basePath = base.pathname.replace(/\/+$/, "");
  let endpoint = path.startsWith("/") ? path : `/${path}`;
  if (basePath.toLowerCase().endsWith("/api") && /^\/api(?:\/|$)/i.test(endpoint)) {
    endpoint = endpoint.slice(4) || "/";
  }

  return new URL(`${basePath}${endpoint}`, base.origin).toString();
}

export function apiFetch(path: string, init?: RequestInit): Promise<Response> {
  return fetch(apiUrl(path), init);
}

export function isChatResponse(value: unknown): value is ChatResponse {
  if (typeof value !== "object" || value === null) return false;

  const response = value as Record<string, unknown>;
  return (
    typeof response.answer === "string" &&
    typeof response.answerable === "boolean" &&
    typeof response.confidence === "number" &&
    Array.isArray(response.citations) &&
    response.citations.every(
      (citation: unknown) =>
        typeof citation === "object" &&
        citation !== null &&
        typeof (citation as Record<string, unknown>).n === "number" &&
        typeof (citation as Record<string, unknown>).filename === "string" &&
        typeof (citation as Record<string, unknown>).page === "number" &&
        typeof (citation as Record<string, unknown>).snippet === "string",
    ) &&
    (response.search_query === undefined ||
      response.search_query === null ||
      typeof response.search_query === "string") &&
    (response.gating_score === undefined ||
      response.gating_score === null ||
      typeof response.gating_score === "number")
  );
}
