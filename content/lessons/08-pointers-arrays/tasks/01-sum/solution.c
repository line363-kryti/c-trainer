#include <stdio.h>

int sum(int *p, int n)
{
    int result = 0;

    for (int i = 0; i < n; i++)
    {
        result += *(p + i);
    }

    return result;
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

    printf("%d\n", sum(numbers, n));

    return 0;
}
