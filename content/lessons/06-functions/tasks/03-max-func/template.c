#include <stdio.h>

int max(int numbers[], int size)
{
    // найди и верни максимальный элемент
}

int main()
{
    int numbers[5];

    for (int i = 0; i < 5; i++)
    {
        scanf("%d", &numbers[i]);
    }

    printf("Maximum: %d\n", max(numbers, 5));

    return 0;
}
