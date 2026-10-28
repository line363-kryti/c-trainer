#include <stdio.h>

int sum(int *p, int n)
{
    // верни сумму элементов p[0] ... p[n - 1]
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
