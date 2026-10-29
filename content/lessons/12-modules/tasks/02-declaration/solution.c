#include <stdio.h>

int square(int x);

int main(void) {
    int x;
    scanf("%d", &x);
    printf("%d\n", square(x));
    return 0;
}

int square(int x) { return x * x; }
