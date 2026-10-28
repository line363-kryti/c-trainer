// Тёмная / светлая тема. Выбор запоминается в браузере.
// По умолчанию тёмная, светлая — если так настроена система.
// (Тот же выбор делает маленький скрипт в <head> каждой страницы, чтобы не было вспышки.)

const KEY = "theme";

function saved() {
  try { return localStorage.getItem(KEY); } catch { return null; }
}

export function currentTheme() {
  return saved() || (matchMedia("(prefers-color-scheme: light)").matches ? "light" : "dark");
}

export function applyTheme(theme) {
  document.documentElement.dataset.theme = theme;
  try { localStorage.setItem(KEY, theme); } catch { /* приватный режим — просто не запоминаем */ }
}

export function toggleTheme() {
  const next = currentTheme() === "dark" ? "light" : "dark";
  applyTheme(next);
  return next;
}
