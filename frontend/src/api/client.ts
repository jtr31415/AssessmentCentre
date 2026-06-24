async function request(method: string, path: string, body?: unknown) {
  const res = await fetch(path, {
    method,
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail || res.statusText);
  return res.json();
}

export const api = {
  get: (p: string) => request("GET", p),
  post: (p: string, b?: unknown) => request("POST", p, b),
  patch: (p: string, b?: unknown) => request("PATCH", p, b),
  del: (p: string) => request("DELETE", p),
};
