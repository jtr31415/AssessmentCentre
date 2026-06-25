async function request(method: string, path: string, body?: unknown) {
  const res = await fetch(path, {
    method,
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    const err = new Error((body as { detail?: string }).detail || res.statusText) as Error & { status?: number };
    err.status = res.status;
    throw err;
  }
  return res.json();
}

async function upload(method: string, path: string, form: FormData) {
  // Multipart: must NOT set Content-Type — the browser adds the boundary.
  const res = await fetch(path, { method, credentials: "include", body: form });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    const err = new Error(
      (body as { detail?: string }).detail || res.statusText
    ) as Error & { status?: number };
    err.status = res.status;
    throw err;
  }
  return res.json();
}

export const api = {
  get: (p: string) => request("GET", p),
  post: (p: string, b?: unknown) => request("POST", p, b),
  patch: (p: string, b?: unknown) => request("PATCH", p, b),
  put: (p: string, b?: unknown) => request("PUT", p, b),
  del: (p: string, b?: unknown) => request("DELETE", p, b),
  upload: (p: string, form: FormData) => upload("POST", p, form),
  uploadPut: (p: string, form: FormData) => upload("PUT", p, form),
};
