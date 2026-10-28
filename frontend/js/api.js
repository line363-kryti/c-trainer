// Обёртка над fetch для нашего API.
// Сайт и API на одном адресе, поэтому cookie со входом браузер отправляет сам.

export class ApiError extends Error {
  constructor(status, message) {
    super(message);
    this.status = status;
  }
}

function errorText(status, data) {
  if (data && typeof data.detail === "string") return data.detail;
  if (status === 422) return "Проверь email; пароль — от 8 до 128 символов";
  return `Ошибка сервера (${status})`;
}

export async function api(path, { method = "GET", body } = {}) {
  const res = await fetch(path, {
    method,
    headers: body ? { "Content-Type": "application/json" } : {},
    body: body ? JSON.stringify(body) : undefined,
  });
  const data = res.status === 204 ? null : await res.json().catch(() => null);
  if (!res.ok) throw new ApiError(res.status, errorText(res.status, data));
  return data;
}

// Текущий пользователь или null, если не вошёл
export async function currentUser() {
  try {
    return await api("/api/auth/me");
  } catch (e) {
    if (e.status === 401) return null;
    throw e;
  }
}
