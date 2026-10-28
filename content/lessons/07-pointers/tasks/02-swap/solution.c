#include <stdio.h>

void swap(int *a, int *b)
{
    int temp = *a;

    *a = *b;
    *b = temp;
}

int main()
{
    int a;
    int b;
    scanf("%d", &a);
    scanf("%d", &b);

    swap(&a, &b);

    printf("%d\n", a);
    printf("%d\n", b);

    return 0;
}
