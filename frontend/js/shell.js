// Общая оболочка страниц: боковое меню (уроки с прогрессом, тема, выход)
// и мобильная шапка. Страница кладёт <div class="shell"><main class="main">…</main></div>,
// а initShell дорисовывает меню и проверяет вход.

import { api, currentUser } from "/js/api.js";
import { applyTheme, currentTheme, toggleTheme } from "/js/theme.js";

const SPRITE = "/img/icons.svg";

// Иконка из спрайта. Строка статичная (без данных пользователя), поэтому innerHTML безопасен
export function icon(name, cls = "icon") {
  return `<svg class="${cls}" aria-hidden="true"><use href="${SPRITE}#i-${name}"></use></svg>`;
}

// Фирменный знак: салатовая лента, свёрнутая в букву C
export const BRAND_MARK = `<svg class="brand-mark" viewBox="0 0 32 32" aria-hidden="true">
  <path d="M23.8 8.2A11 11 0 1 0 23.8 23.8" fill="none" stroke="var(--lime)" stroke-width="6.5" stroke-linecap="round"/>
</svg>`;

// Полоска прогресса: один сегмент — одна задача
export function segments(solved, total) {
  const bar = document.createElement("span");
  bar.className = "segs";
  bar.setAttribute("aria-hidden", "true");
  for (let i = 0; i < total; i++) {
    const seg = document.createElement("i");
    if (i < solved) seg.className = "on";
    bar.append(seg);
  }
  return bar;
}

export const pad2 = (n) => String(n).padStart(2, "0");
export const lessonUrl = (slug) => `/lesson.html?lesson=${encodeURIComponent(slug)}`;
export const taskUrl = (lesson, task) =>
  `/task.html?lesson=${encodeURIComponent(lesson)}&task=${encodeURIComponent(task)}`;

function toLogin() {
  location.href = `/login.html?next=${encodeURIComponent(location.pathname + location.search)}`;
}

// active: "home" или slug урока. Возвращает { user, lessons }
export async function initShell({ active = null } = {}) {
  applyTheme(currentTheme());

  const user = await currentUser();
  if (!user) {
    toLogin();
    return new Promise(() => {}); // страница уходит на вход — дальше ничего не делаем
  }
  const lessons = await api("/api/lessons");

  const shell = document.querySelector(".shell");
  const nav = document.createElement("nav");
  nav.className = "nav";
  nav.id = "nav";
  nav.setAttribute("aria-label", "Меню");
  nav.innerHTML = `
    <a class="brand" href="/">${BRAND_MARK}<span class="brand-name">C-тренажёр</span></a>
    <a class="nav-link" href="/" ${active === "home" ? 'aria-current="page"' : ""} title="Главная">
      ${icon("home")}<span class="label">Главная</span></a>
    <div class="nav-section">Уроки</div>
    <ol class="nav-lessons"></ol>
    <div class="nav-foot">
      <div class="nav-user"></div>
      <button class="btn btn-ghost" type="button" data-theme-toggle></button>
      <button class="btn btn-ghost" type="button" data-logout title="Выйти">${icon("logout")}<span class="label">Выйти</span></button>
    </div>`;

  const list = nav.querySelector(".nav-lessons");
  lessons.forEach((l, i) => {
    const a = document.createElement("a");
    a.className = "nav-lesson";
    a.href = lessonUrl(l.slug);
    if (l.slug === active) a.setAttribute("aria-current", "page");
    const n = Object.assign(document.createElement("span"), { className: "n", textContent: pad2(i + 1) });
    const title = Object.assign(document.createElement("span"), { textContent: l.title });
    a.append(n, title, segments(l.tasks_solved, l.tasks_total));
    const li = document.createElement("li");
    li.append(a);
    list.append(li);
  });
  nav.querySelector(".nav-user").textContent = user.email;

  // Тема
  const themeBtn = nav.querySelector("[data-theme-toggle]");
  const renderThemeBtn = () => {
    const dark = currentTheme() === "dark";
    themeBtn.innerHTML = `${icon(dark ? "sun" : "moon")}<span class="label">${dark ? "Светлая тема" : "Тёмная тема"}</span>`;
    themeBtn.title = dark ? "Светлая тема" : "Тёмная тема";
  };
  renderThemeBtn();
  themeBtn.onclick = () => {
    const theme = toggleTheme();
    renderThemeBtn();
    window.dispatchEvent(new CustomEvent("themechange", { detail: theme }));
  };

  nav.querySelector("[data-logout]").onclick = async () => {
    await api("/api/auth/logout", { method: "POST" });
    location.href = "/login.html";
  };

  // Мобильная шапка с кнопкой меню
  const topbar = document.createElement("header");
  topbar.className = "topbar";
  topbar.innerHTML = `
    <a class="brand" href="/" style="padding:0">${BRAND_MARK}<span class="brand-name">C-тренажёр</span></a>
    <button class="btn btn-ghost" type="button" aria-controls="nav" aria-expanded="false" aria-label="Меню">${icon("menu-2")}</button>`;
  const menuBtn = topbar.querySelector("button");
  const setOpen = (open) => {
    nav.classList.toggle("open", open);
    menuBtn.setAttribute("aria-expanded", String(open));
  };
  menuBtn.onclick = () => setOpen(!nav.classList.contains("open"));
  document.addEventListener("click", (e) => {
    if (nav.classList.contains("open") && !nav.contains(e.target) && !menuBtn.contains(e.target)) setOpen(false);
  });
  document.addEventListener("keydown", (e) => e.key === "Escape" && setOpen(false));

  shell.prepend(topbar, nav);
  return { user, lessons };
}
