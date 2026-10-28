#include <stdio.h>

void reverse(int *p, int n)
{
    // разверни массив на месте
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
