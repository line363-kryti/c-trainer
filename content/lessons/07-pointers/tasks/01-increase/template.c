#include <stdio.h>

void increase(int *x)
{
    // увеличь на 1 значение по адресу x
}

int main()
{
    int a;
    scanf("%d", &a);

    increase(&a);

    printf("%d\n", a);

    return 0;
}
