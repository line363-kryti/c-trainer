#include <stdio.h>
#define SQUARE(x) 0

int main(void) {
    int a, b;
    scanf("%d %d", &a, &b);
    printf("%d\n", SQUARE(a + b));
    return 0;
}
