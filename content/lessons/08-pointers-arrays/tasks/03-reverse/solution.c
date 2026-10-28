#include <stdio.h>

void swap(int *a, int *b)
{
    int temp = *a;

    *a = *b;
    *b = temp;
}

void reverse(int *p, int n)
{
    for (int i = 0; i < n / 2; i++)
    {
        swap(p + i, p + n - 1 - i);
    }
}

int main()
{
    int numbers[100];
    int n;
    scanf("%d", &n);

    for (int i = 0; i < n; i++)
    {
        scanf("%d", &numbers[i]);
    }

    reverse(numbers, n);

    for (int i = 0; i < n; i++)
    {
        printf("%d\n", numbers[i]);
    }

    return 0;
}
