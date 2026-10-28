"""Проверка запускателя кода на настоящих программах (не тест pytest — нужен живой Piston).

Запуск: docker compose exec backend python scripts/smoke_runner.py
"""
import asyncio
import sys

from app.config import settings
from app.runner.piston import PistonRunner

CASES = [
    ("ввод/вывод", "ok",
     '#include <stdio.h>\nint main(void){int a,b; scanf("%d %d",&a,&b); printf("%d\\n", a+b); return 0;}', "2 3"),
    ("ошибка компиляции", "compile_error",
     "int main(void){ int x = 1 return 0; }", ""),
    ("бесконечный цикл", "time_limit",
     "int main(void){ volatile unsigned long i = 0; for(;;) i++; }", ""),
    ("segfault", "runtime_error",
     "int main(void){ int *p = 0; *p = 1; return 0; }", ""),
    ("деление на ноль", "runtime_error",
     '#include <stdio.h>\nint main(void){ int z; scanf("%d",&z); printf("%d", 1/z); return 0; }', "0"),
    ("код возврата 3", "runtime_error",
     "int main(void){ return 3; }", ""),
    ("много памяти", "runtime_error",
     '#include <stdlib.h>\n#include <string.h>\nint main(void){ for(int i=0;i<64;i++){ char *p = malloc(16<<20); if(!p) return 7; memset(p,1,16<<20);} return 0; }', ""),
    ("длинный вывод", "runtime_error",
     '#include <stdio.h>\nint main(void){ for(int i=0;i<100000;i++) printf("0123456789\\n"); return 0; }', ""),
    ("math.h (-lm)", "ok",
     '#include <stdio.h>\n#include <math.h>\nint main(void){ printf("%.2f\\n", sqrt(2.0)); return 0; }', ""),
    ("сеть недоступна", "ok",
     '#include <stdio.h>\n#include <sys/socket.h>\n#include <netinet/in.h>\n#include <arpa/inet.h>\n#include <unistd.h>\n'
     'int main(void){ int s = socket(AF_INET, SOCK_STREAM, 0); struct sockaddr_in a = {0}; a.sin_family = AF_INET; a.sin_port = htons(80);'
     ' inet_pton(AF_INET, "1.1.1.1", &a.sin_addr); printf(connect(s,(void*)&a,sizeof a) == 0 ? "NET OPEN\\n" : "no network\\n"); return 0; }', ""),
]


async def main() -> int:
    runner = PistonRunner(settings.piston_url)
    failed = 0
    for name, want, code, stdin in CASES:
        r = await runner.run(code, stdin)
        good = r.status == want
        failed += not good
        out = (r.stdout[:40] or r.compile_output[:60]).replace("\n", "⏎")
        print(f"{'OK ' if good else 'BAD'} {name:20} status={r.status:14} t={r.time} mem={r.memory}КБ "
              f"msg={r.message!r} out={out!r}")
    return failed


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
