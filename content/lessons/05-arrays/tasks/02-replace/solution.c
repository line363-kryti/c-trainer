#include <stdio.h>

int main()
{
    int numbers[5];

    for (int i = 0; i < 5; i++)
    {
        scanf("%d", &numbers[i]);
    }

    int k;
    int v;
    scanf("%d", &k);
    scanf("%d", &v);

    numbers[k] = v;

    for (int i = 0; i < 5; i++)
    {
        printf("%d\n", numbers[i]);
    }

    return 0;
}
