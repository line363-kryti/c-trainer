// Страница задачи: условие, редактор, «Запустить», «Проверить», подсказка, эталон.
// Адрес: /task.html?lesson=<урок>&task=<задача>

import { api } from "/js/api.js";
import { highlightInto } from "/js/highlight.js";
import { loadMonaco, monacoTheme } from "/js/monaco-c.js";
import { icon, initShell, lessonUrl, taskUrl } from "/js/shell.js";
import { currentTheme } from "/js/theme.js";

const params = new URLSearchParams(location.search);
const lessonSlug = params.get("lesson") || "";
const taskSlug = params.get("task") || "";
const base = `/api/tasks/${encodeURIComponent(lessonSlug)}/${encodeURIComponent(taskSlug)}`;

const $ = (id) => document.getElementById(id);
const AUTOSAVE_MS = 1500;

const STATUS_TEXT = {
  ok: "Программа отработала",
  compile_error: "Ошибка компиляции",
  runtime_error: "Ошибка во время работы",
  time_limit: "Превышен лимит времени",
  internal_error: "Внутренняя ошибка песочницы",
};

let editor;
let task;
let saveTimer;

init().catch(showFatal);

async function init() {
  await initShell({ active: lessonSlug });
  task = await api(base);
  renderTask();

  const monaco = await loadMonaco();
  $("editor").replaceChildren(); // убираем надпись «Загружаю редактор…»
  editor = monaco.editor.create($("editor"), {
    value: task.code,
    language: "c",
    theme: monacoTheme(currentTheme()),
    automaticLayout: true,
    minimap: { enabled: true },
    fontFamily: "JetBrains Mono, Consolas, monospace",
    fontSize: 14,
    lineHeight: 22,
    tabSize: 4,
    insertSpaces: true,
    scrollBeyondLastLine: false,
    padding: { top: 14 },
    renderLineHighlight: "all",
  });
  // Шрифт мог догрузиться после создания редактора — пересчитываем ширину символов
  document.fonts.ready.then(() => monaco.editor.remeasureFonts());

  // Горячие клавиши в дополнение к стандартным VS Code (Ctrl+F, Ctrl+H, Alt+клик — несколько курсоров…)
  editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.Enter, runCode);
  editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyMod.Shift | monaco.KeyCode.Enter, checkCode);
  editor.onDidChangeModelContent(scheduleSave);
  window.addEventListener("themechange", (e) => monaco.editor.setTheme(monacoTheme(e.detail)));

  $("run-btn").onclick = runCode;
  $("check-btn").onclick = checkCode;
  $("reset-btn").onclick = resetCode;
  $("hint-btn").onclick = showHint;
  $("solution-btn").onclick = showSolution;
}

function renderTask() {
  document.title = `${task.title} — C-тренажёр`;
  $("crumb").href = lessonUrl(task.lesson_slug);
  $("crumb-text").textContent = task.lesson_title;
  $("title").textContent = task.title;
  $("tests-count").textContent = `тестов: ${task.tests_count}`;
  // Условие — Markdown. DOMPurify вычищает из HTML всё опасное
  $("statement").innerHTML = DOMPurify.sanitize(marked.parse(task.statement));
  $("hint-btn").hidden = !task.has_hint;
  $("solution-btn").hidden = !task.has_solution;

  const next = $("next-task");
  next.href = task.next_task ? taskUrl(task.lesson_slug, task.next_task) : lessonUrl(task.lesson_slug);
  next.textContent = task.next_task ? "Следующая задача" : "Вернуться к уроку";
  next.insertAdjacentHTML("beforeend", icon("arrow-right", "icon-s"));
  next.hidden = false;
  renderStatus();
}

function renderStatus() {
  const chip = $("task-status");
  chip.className = task.status === "solved" ? "chip ok" : "chip";
  chip.textContent = task.status === "solved" ? "Решена" : task.attempts ? `Попыток: ${task.attempts}` : "Не решена";
}

// ---------- сохранение ----------

function scheduleSave() {
  $("save-state").textContent = "изменено";
  clearTimeout(saveTimer);
  saveTimer = setTimeout(saveCode, AUTOSAVE_MS);
}

async function saveCode() {
  try {
    await api(`${base}/code`, { method: "PUT", body: { code: editor.getValue() } });
    $("save-state").textContent = "сохранено";
  } catch (e) {
    $("save-state").textContent = `не сохранено: ${e.message}`;
  }
}

function resetCode() {
  if (editor && confirm("Вернуть заготовку? Код в редакторе заменится.")) editor.setValue(task.template);
}

// ---------- запуск и проверка ----------

async function withBusy(button, fn) {
  if (!editor) return;
  const buttons = [$("run-btn"), $("check-btn")];
  if (buttons.some((b) => b.getAttribute("aria-busy"))) return; // уже идёт запуск
  button.setAttribute("aria-busy", "true");
  clearTimeout(saveTimer); // run/check сохраняют код сами
  try {
    await fn();
    $("save-state").textContent = "сохранено";
  } catch (e) {
    showOutput(verdict(false, e.message));
  } finally {
    button.removeAttribute("aria-busy");
  }
}

function runCode() {
  return withBusy($("run-btn"), async () => {
    showOutput(el("p", { className: "empty", textContent: "Компилирую и запускаю…" }));
    const r = await api(`${base}/run`, { method: "POST", body: { code: editor.getValue(), stdin: $("stdin").value } });
    renderRun(r);
  });
}

function checkCode() {
  return withBusy($("check-btn"), async () => {
    showOutput(el("p", { className: "empty", textContent: `Проверяю на ${task.tests_count} тестах…` }));
    const r = await api(`${base}/check`, { method: "POST", body: { code: editor.getValue() } });
    renderCheck(r);
    task.attempts += 1;
    if (r.solved) task.status = "solved";
    renderStatus();
  });
}

// ---------- вывод результатов (только textContent — без риска XSS) ----------

function el(tag, props = {}, ...children) {
  const node = Object.assign(document.createElement(tag), props);
  node.append(...children.filter((c) => c !== null && c !== undefined));
  return node;
}

const block = (text) => el("pre", { className: "block", textContent: text === "" ? "(пусто)" : text });
const labelled = (label, node) => [el("div", { className: "out-label", textContent: label }), node];

// Показать результат; пустые (null) блоки пропускаем, иначе браузер выведет слово «null»
function showOutput(...nodes) {
  $("output").replaceChildren(...nodes.flat().filter((n) => n !== null && n !== undefined));
}

function verdict(ok, text, stats = "") {
  const v = el("div", { className: `verdict ${ok ? "ok" : "bad"}` });
  v.innerHTML = icon(ok ? "circle-check" : "alert-triangle");
  v.append(text);
  if (stats) v.append(el("span", { className: "stats", textContent: stats }));
  return v;
}

function renderRun(r) {
  const stats = r.time !== null ? `${r.time.toFixed(3)} с, ${r.memory} КБ` : "";
  showOutput(
    verdict(r.status === "ok", STATUS_TEXT[r.status], stats),
    r.message ? el("p", { textContent: r.message }) : null,
    r.compile_output ? labelled("Компилятор", block(r.compile_output)) : null,
    r.status !== "compile_error" ? labelled("Вывод программы", block(r.stdout)) : null,
    r.stderr ? labelled("stderr", block(r.stderr)) : null,
  );
}

function renderCheck(r) {
  if (r.compile_error !== null) {
    showOutput(verdict(false, "Ошибка компиляции, тесты не запускались"), block(r.compile_error));
    return;
  }
  const head = r.solved ? `Все тесты пройдены: ${r.total} из ${r.total}` : `Пройдено ${r.passed} из ${r.total}`;
  showOutput(verdict(r.solved, head), ...r.results.map(renderTest));
}

function renderTest(t) {
  const why = t.passed ? "пройден" : t.status === "ok" ? "неверный ответ" : STATUS_TEXT[t.status];
  const rows = [
    ["Ввод", block(t.input)],
    ["Ожидалось", block(t.expected)],
    ["Получено", block(t.got)],
  ];
  if (t.diff) {
    const show = (s) => (s === null ? "строки нет" : `«${s}»`);
    const d = el("div", { className: "diff" });
    d.append(`Строка ${t.diff.line}: ожидалось ${show(t.diff.expected)}, получено `, el("b", { textContent: show(t.diff.got) }));
    rows.push(["Отличие", d]);
  }
  if (t.message) rows.push(["Почему", el("div", { className: "diff", textContent: t.message })]);
  if (t.stderr) rows.push(["stderr", block(t.stderr)]);

  return el("details", { className: `test ${t.passed ? "passed" : "failed"}`, open: !t.passed },
    el("summary", {},
      el("span", { textContent: `Тест ${t.index}` }),
      el("span", { className: "why", textContent: why }),
      t.time !== null ? el("span", { className: "t", textContent: `${t.time.toFixed(3)} с` }) : null,
    ),
    el("dl", {}, ...rows.flatMap(([k, v]) => [el("dt", { textContent: k }), el("dd", {}, v)])),
  );
}

// ---------- подсказка и эталон ----------

async function showHint() {
  try {
    const { hint } = await api(`${base}/hint`);
    $("hint").innerHTML = icon("bulb");
    $("hint").append(el("div", { textContent: hint }));
    $("hint").hidden = false;
    $("hint").scrollIntoView({ behavior: "smooth", block: "nearest" });
  } catch (e) {
    showOutput(verdict(false, e.message));
  }
}

async function showSolution() {
  if (!confirm("Показать эталонное решение? Лучше сначала попробовать самому.")) return;
  try {
    const { code } = await api(`${base}/solution`);
    highlightInto($("solution-code"), code);
    $("solution").hidden = false;
    $("solution").scrollIntoView({ behavior: "smooth", block: "nearest" });
  } catch (e) {
    showOutput(verdict(false, e.message));
  }
}

function showFatal(e) {
  $("title").textContent = e.status === 404 ? "Задача не найдена" : "Задача не загрузилась";
  $("statement").textContent = e.status === 404 ? "Проверь ссылку или выбери урок в меню." : e.message || String(e);
}
