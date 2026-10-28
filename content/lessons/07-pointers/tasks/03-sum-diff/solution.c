#include <stdio.h>

void sum_diff(int a, int b, int *sum, int *diff)
{
    *sum = a + b;
    *diff = a - b;
}

int main()
{
    int a;
    int b;
    scanf("%d", &a);
    scanf("%d", &b);

    int s = 0;
    int d = 0;
    sum_diff(a, b, &s, &d);

    printf("%d\n", s);
    printf("%d\n", d);

    return 0;
}
