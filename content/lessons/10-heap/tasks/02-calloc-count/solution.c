#include <stdio.h>
#include <stdlib.h>

int main()
{
    int n;
    scanf("%d", &n);

    int *counts = calloc(10, sizeof(int));
    if (counts == NULL)
    {
        return 1;
    }

    for (int i = 0; i < n; i++)
    {
        int digit;
        scanf("%d", &digit);
        counts[digit]++;
    }

    for (int d = 0; d < 10; d++)
    {
        if (counts[d] > 0)
        {
            printf("%d %d\n", d, counts[d]);
        }
    }

    free(counts);
    counts = NULL;

    return 0;
}
