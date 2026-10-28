#include <stdio.h>

int main()
{
    int age;
    scanf("%d", &age);

    if (age >= 18 && age <= 60)
    {
        printf("Working age\n");
    }
    else
    {
        printf("Not working age\n");
    }

    return 0;
}
