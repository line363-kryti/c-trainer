#include <stdio.h>

struct Student
{
    char name[50];
    int age;
};

void birthday(struct Student *s)
{
    // увеличь возраст на 1
}

int main()
{
    struct Student student;
    scanf("%d", &student.age);

    birthday(&student);

    printf("%d\n", student.age);

    return 0;
}
