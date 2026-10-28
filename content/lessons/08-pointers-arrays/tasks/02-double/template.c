#include <stdio.h>

void double_all(int *p, int n)
{
    // умножь каждый элемент на 2
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

    double_all(numbers, n);

    for (int i = 0; i < n; i++)
    {
        printf("%d\n", numbers[i]);
    }

    return 0;
}
