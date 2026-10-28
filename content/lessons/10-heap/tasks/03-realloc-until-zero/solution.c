#include <stdio.h>
#include <stdlib.h>

int main()
{
    int capacity = 2;
    int size = 0;

    int *numbers = malloc(capacity * sizeof(int));
    if (numbers == NULL)
    {
        return 1;
    }

    int x;
    scanf("%d", &x);

    while (x != 0)
    {
        if (size >= capacity)
        {
            int *temp = realloc(numbers, capacity * 2 * sizeof(int));
            if (temp == NULL)
            {
                free(numbers);
                return 1;
            }
            numbers = temp;
            capacity = capacity * 2;
        }

        numbers[size] = x;
        size++;
        scanf("%d", &x);
    }

    printf("%d\n", size);

    for (int i = size - 1; i >= 0; i--)
    {
        printf("%d\n", numbers[i]);
    }

    free(numbers);
    numbers = NULL;

    return 0;
}
