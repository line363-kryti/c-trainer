#include <stdio.h>

struct Student
{
    char name[50];
    int age;
};

int is_adult(struct Student *s)
{
    if (s->age >= 18)
    {
        return 1;
    }

    return 0;
}

int main()
{
    struct Student student;
    scanf("%d", &student.age);

    if (is_adult(&student))
    {
        printf("Adult\n");
    }
    else
    {
        printf("Not adult\n");
    }

    return 0;
}
