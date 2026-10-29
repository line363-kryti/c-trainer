#include <stdio.h>

int add(int a, int b);
int multiply(int a, int b);

int main(void) {
    int a, b;
    scanf("%d %d", &a, &b);
    printf("%d\n%d\n", add(a, b), multiply(a, b));
    return 0;
}

int add(int a, int b) { return a + b; }
int multiply(int a, int b) { return a * b; }
