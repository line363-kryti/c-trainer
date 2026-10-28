"""Сравнение вывода программы с ожидаемым.

Мелочи не считаем ошибкой: пробелы в конце строк, пустые строки в конце,
разницу между переводами строк Windows (\\r\\n) и Linux (\\n).
"""
from dataclasses import dataclass


@dataclass
class Diff:
    line: int  # номер строки, с 1
    expected: str | None  # None — такой строки нет
    got: str | None


def normalize(text: str) -> list[str]:
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    lines = [line.rstrip() for line in lines]
    while lines and lines[-1] == "":
        lines.pop()
    return lines


def first_diff(expected: str, got: str) -> Diff | None:
    """None — выводы совпали, иначе первая отличающаяся строка."""
    exp, out = normalize(expected), normalize(got)
    if exp == out:
        return None
    for i in range(max(len(exp), len(out))):
        e = exp[i] if i < len(exp) else None
        g = out[i] if i < len(out) else None
        if e != g:
            return Diff(line=i + 1, expected=e, got=g)
    return None  # сюда не попадём: списки разные, значит отличие найдётся
