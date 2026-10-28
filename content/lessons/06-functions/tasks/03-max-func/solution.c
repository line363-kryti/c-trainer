#include <stdio.h>

int max(int numbers[], int size)
{
    int result = numbers[0];

    for (int i = 1; i < size; i++)
    {
        if (numbers[i] > result)
        {
            result = numbers[i];
        }
    }

    return result;
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
