#include <stdio.h>

void counter(void) {
    int count = 0;
    count++;
    printf("%d\n", count);
}

int main(void) {
    int n;
    scanf("%d", &n);
    for (int i = 0; i < n; i++) counter();
    return 0;
}
