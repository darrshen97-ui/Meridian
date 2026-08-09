export class ApiError extends Error {
  status: number;
  body: Record<string, unknown>;

  constructor(status: number, message: string, body: Record<string, unknown>) {
    super(message);
    this.status = status;
    this.body = body;
  }
}

async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  const resp = await fetch(path, {
    method,
    credentials: "same-origin",
    headers: body !== undefined ? { "Content-Type": "application/json" } : undefined,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
  if (resp.status === 204) return undefined as T;
  let parsed: Record<string, unknown> = {};
  try {
    parsed = await resp.json();
  } catch {
    /* non-JSON body */
  }
  if (!resp.ok) {
    const detail = typeof parsed.detail === "string"
      ? parsed.detail
      : `The server returned ${resp.status}.`;
    throw new ApiError(resp.status, detail, parsed);
  }
  return parsed as T;
}

export const api = {
  get: <T>(path: string) => request<T>("GET", path),
  post: <T>(path: string, body?: unknown) => request<T>("POST", path, body),
  patch: <T>(path: string, body?: unknown) => request<T>("PATCH", path, body),
  put: <T>(path: string, body?: unknown) => request<T>("PUT", path, body),

  async uploadFiles<T>(path: string, files: File[]): Promise<T> {
    const form = new FormData();
    files.forEach((f) => form.append("files", f));
    const resp = await fetch(path, { method: "POST", credentials: "same-origin", body: form });
    const parsed = await resp.json();
    if (!resp.ok) {
      throw new ApiError(resp.status, String(parsed.detail ?? "Upload failed."), parsed);
    }
    return parsed as T;
  },
};
