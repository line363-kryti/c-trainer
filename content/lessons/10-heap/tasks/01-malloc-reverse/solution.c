#include <stdio.h>
#include <stdlib.h>

int main()
{
    int n;
    scanf("%d", &n);

    int *numbers = malloc(n * sizeof(int));
    if (numbers == NULL)
    {
        return 1;
    }

    for (int i = 0; i < n; i++)
    {
        scanf("%d", &numbers[i]);
    }

    for (int i = n - 1; i >= 0; i--)
    {
        printf("%d\n", numbers[i]);
    }

    free(numbers);
    numbers = NULL;

    return 0;
}
