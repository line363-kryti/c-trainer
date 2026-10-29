#include <stdio.h>

int main(void) {
    int x;
    scanf("%d", &x);
    printf("%d\n", square(x));
    return 0;
}

double square(double x) { return x * x; }
