#include <stdio.h>

struct Student
{
    char name[50];
    int age;
};

int is_adult(struct Student *s)
{
    // верни 1, если s->age >= 18, иначе 0
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
