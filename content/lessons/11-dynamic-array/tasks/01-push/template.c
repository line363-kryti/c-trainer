#include <stdio.h>
#include <stdlib.h>

typedef struct
{
    int *data;        // указатель на данные
    size_t size;      // текущее количество элементов
    size_t capacity;  // выделенная вместимость
} DynamicArray;

DynamicArray *array_create(size_t initial_capacity)
{
    DynamicArray *arr = malloc(sizeof(DynamicArray));
    if (arr == NULL)
        return NULL;

    arr->data = malloc(initial_capacity * sizeof(int));
    if (arr->data == NULL)
    {
        free(arr);
        return NULL;
    }

    arr->size = 0;
    arr->capacity = initial_capacity;
    return arr;
}

void array_free(DynamicArray *arr)
{
    if (arr)
    {
        free(arr->data);  // сначала данные
        free(arr);        // потом структура
    }
}

void array_print(DynamicArray *arr)
{
    printf("Array [size=%zu, capacity=%zu]: [", arr->size, arr->capacity);
    for (size_t i = 0; i < arr->size; i++)
    {
        printf("%d", arr->data[i]);
        if (i < arr->size - 1)
            printf(", ");
    }
    printf("]\n");
}

int array_push(DynamicArray *arr, int value)
{
    // если места нет (size >= capacity) — удвой capacity через безопасный realloc;
    // затем запиши value в конец и увеличь size. Верни 0, а при ошибке памяти -1
}

int main()
{
    DynamicArray *arr = array_create(2);
    if (arr == NULL)
        return 1;

    int n;
    scanf("%d", &n);

    for (int i = 0; i < n; i++)
    {
        int value;
        scanf("%d", &value);
        array_push(arr, value);
    }

    array_print(arr);
    array_free(arr);

    return 0;
}
