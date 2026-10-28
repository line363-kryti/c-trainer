#include <stdio.h>

void printNumbers(int n)
{
    for (int i = 1; i <= n; i++)
    {
        printf("%d\n", i);
    }
}

int main()
{
    int n;
    scanf("%d", &n);

    printNumbers(n);

    return 0;
}
