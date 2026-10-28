#include <stdio.h>

void increase(int *x)
{
    *x = *x + 1;
}

int main()
{
    int a;
    scanf("%d", &a);

    increase(&a);

    printf("%d\n", a);

    return 0;
}
