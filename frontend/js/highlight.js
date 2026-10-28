// Лёгкая подсветка кода на C для уроков и главной (Monaco там не нужен).
// Текст режется на куски регулярным выражением, каждый кусок вставляется через textContent —
// никакой HTML из кода не исполнится.

const KEYWORDS = new Set([
  "int", "double", "char", "void", "float", "long", "short", "unsigned", "signed", "const", "static",
  "return", "if", "else", "for", "while", "do", "break", "continue", "switch", "case", "default",
  "struct", "sizeof", "typedef", "NULL",
]);

// комментарий | строка или символ | директива #include <...> | число | слово
const TOKEN = /(\/\/[^\n]*|\/\*[\s\S]*?\*\/)|("(?:\\.|[^"\\\n])*"|'(?:\\.|[^'\\\n])*')|(#\s*\w+(?:[ \t]*<[^>\n]*>)?)|\b(\d+(?:\.\d+)?)\b|\b([A-Za-z_]\w*)\b/g;

export function highlightInto(target, code) {
  const frag = document.createDocumentFragment();
  let last = 0;
  const span = (cls, text) => frag.append(Object.assign(document.createElement("span"), { className: cls, textContent: text }));

  for (const m of code.matchAll(TOKEN)) {
    if (m.index > last) frag.append(code.slice(last, m.index));
    const [text, comment, string, directive, number, word] = m;
    if (comment) span("tok-comment", text);
    else if (string) span("tok-string", text);
    else if (directive) span("tok-directive", text);
    else if (number) span("tok-number", text);
    else if (word && KEYWORDS.has(word)) span("tok-keyword", text);
    else if (word && code[m.index + text.length] === "(") span("tok-func", text);
    else frag.append(text);
    last = m.index + text.length;
  }
  frag.append(code.slice(last));
  target.replaceChildren(frag);
}

// Подсветить блоки ```c внутри элемента (после marked). Блоки без языка — схемы и вывод — не трогаем
export function highlightAll(root) {
  root.querySelectorAll("pre > code.language-c").forEach((el) => highlightInto(el, el.textContent));
}
