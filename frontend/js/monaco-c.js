// Подключение Monaco (движок редактора VS Code) и подсказки для языка C.
// Monaco 0.52.2 лежит в проекте (frontend/vendor/monaco) — только нужные файлы: ядро,
// подсветка C, фоновый поток, иконки и русский перевод интерфейса. CDN и сеть не нужны.
// Подсветку C Monaco умеет сам; автодополнение добавляем своё: ключевые слова,
// частые функции стандартной библиотеки и сниппеты (шаблоны кода с переходом по Tab).

const MONACO_BASE = "/vendor/monaco";

const KEYWORDS = [
  "auto", "break", "case", "char", "const", "continue", "default", "do", "double", "else", "enum",
  "extern", "float", "for", "goto", "if", "inline", "int", "long", "register", "restrict", "return",
  "short", "signed", "sizeof", "static", "struct", "switch", "typedef", "union", "unsigned", "void",
  "volatile", "while", "_Bool", "NULL",
];

const FUNCTIONS = [
  "printf", "scanf", "puts", "getchar", "putchar", "fgets", "sprintf", "malloc", "calloc", "realloc",
  "free", "exit", "abs", "strlen", "strcpy", "strncpy", "strcmp", "strcat", "memset", "memcpy",
  "sqrt", "pow", "fabs", "floor", "ceil",
];

// $1, $2 — места, куда прыгает Tab; ${1:i} — с подставленным значением; $0 — финальная позиция курсора
const SNIPPETS = {
  main: ["Функция main", "#include <stdio.h>\n\nint main(void) {\n\t$0\n\treturn 0;\n}"],
  inc: ["#include", "#include <${1:stdio.h}>"],
  for: ["Цикл for", "for (int ${1:i} = 0; ${1:i} < ${2:n}; ${1:i}++) {\n\t$0\n}"],
  while: ["Цикл while", "while (${1:условие}) {\n\t$0\n}"],
  do: ["Цикл do-while", "do {\n\t$0\n} while (${1:условие});"],
  if: ["if", "if (${1:условие}) {\n\t$0\n}"],
  ife: ["if-else", "if (${1:условие}) {\n\t$2\n} else {\n\t$0\n}"],
  switch: ["switch", "switch (${1:x}) {\ncase ${2:1}:\n\t$0\n\tbreak;\ndefault:\n\tbreak;\n}"],
  pf: ["printf", "printf(\"${1:%d}\\n\", ${2:x});"],
  sf: ["scanf", "scanf(\"${1:%d}\", &${2:x});"],
  func: ["Функция", "${1:int} ${2:name}(${3:void}) {\n\t$0\n}"],
  struct: ["struct", "struct ${1:Name} {\n\t$0\n};"],
};

// Темы редактора в цветах сайта (те же, что у подсветки в уроках)
function defineThemes(monaco) {
  monaco.editor.defineTheme("ct-dark", {
    base: "vs-dark",
    inherit: true,
    rules: [
      { token: "keyword", foreground: "B9A7F6" },
      { token: "string", foreground: "CDF25C" },
      { token: "number", foreground: "FFB547" },
      { token: "comment", foreground: "727889", fontStyle: "italic" },
      { token: "delimiter", foreground: "A4AABB" },
    ],
    colors: {
      "editor.background": "#0F1016",
      "editor.foreground": "#EEF0F5",
      "editor.lineHighlightBackground": "#1A1C24",
      "editor.lineHighlightBorder": "#00000000",
      "editorLineNumber.foreground": "#4A4F60",
      "editorLineNumber.activeForeground": "#A4AABB",
      "editorCursor.foreground": "#CDF25C",
      "editor.selectionBackground": "#3B3F51",
      "editorIndentGuide.background1": "#22252F",
      "minimap.background": "#0F1016",
      "editorWidget.background": "#1C1E27",
      "editorSuggestWidget.background": "#1C1E27",
      "editorSuggestWidget.selectedBackground": "#2A2D3A",
    },
  });
  monaco.editor.defineTheme("ct-light", {
    base: "vs",
    inherit: true,
    rules: [
      { token: "keyword", foreground: "6A52D6" },
      { token: "string", foreground: "4A6800" },
      { token: "number", foreground: "B86E00" },
      { token: "comment", foreground: "767C8F", fontStyle: "italic" },
    ],
    colors: {
      "editor.background": "#ECEEF3",
      "editor.lineHighlightBackground": "#E2E5EC",
      "editor.lineHighlightBorder": "#00000000",
      "editorLineNumber.foreground": "#A0A5B4",
      "editorCursor.foreground": "#4A6800",
      "minimap.background": "#ECEEF3",
    },
  });
}

export const monacoTheme = (theme) => (theme === "dark" ? "ct-dark" : "ct-light");

let registered = false;

function registerCompletions(monaco) {
  if (registered) return;
  registered = true;
  const Kind = monaco.languages.CompletionItemKind;
  const Rule = monaco.languages.CompletionItemInsertTextRule;

  monaco.languages.registerCompletionItemProvider("c", {
    provideCompletionItems(model, position) {
      const word = model.getWordUntilPosition(position);
      const range = {
        startLineNumber: position.lineNumber, endLineNumber: position.lineNumber,
        startColumn: word.startColumn, endColumn: word.endColumn,
      };
      return {
        suggestions: [
          ...KEYWORDS.map((k) => ({ label: k, kind: Kind.Keyword, insertText: k, range })),
          ...FUNCTIONS.map((f) => ({ label: f, kind: Kind.Function, insertText: f, range })),
          ...Object.entries(SNIPPETS).map(([label, [detail, body]]) => ({
            label, detail, kind: Kind.Snippet, insertText: body, insertTextRules: Rule.InsertAsSnippet, range,
          })),
        ],
      };
    },
  });
}

let loading = null;

// Загружает Monaco и возвращает объект monaco. Можно вызывать сколько угодно раз —
// загрузка начнётся при первом вызове, остальные получат тот же результат.
export function loadMonaco() {
  loading ??= new Promise((resolve, reject) => {
    window.require.config({ paths: { vs: `${MONACO_BASE}/vs` } });
    // Сначала русский перевод интерфейса («Найти», «Заменить»…), потом сам редактор
    window.require(["vs/nls.messages.ru"], () => {
      window.require(["vs/editor/editor.main"], () => {
        registerCompletions(window.monaco);
        defineThemes(window.monaco);
        resolve(window.monaco);
      }, reject);
    }, reject);
  });
  return loading;
}
