#include <stdio.h>
#define MAX(a, b) 0

int main(void) {
    int a, b, c;
    scanf("%d %d %d", &a, &b, &c);
    printf("%d\n", MAX(MAX(a, b), c));
    return 0;
}
