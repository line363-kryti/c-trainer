Соберём из структуры и `realloc` **динамический массив** — массив, который сам растёт (как `ArrayList` в Java). Ему нужно знать три вещи: где лежат данные, сколько элементов сейчас и сколько помещается.

```c
typedef struct
{
    int *data;        // указатель на данные
    size_t size;      // текущее количество элементов
    size_t capacity;  // выделенная вместимость
} DynamicArray;
```

`typedef` даёт типу короткое имя — можно писать `DynamicArray`, а не `struct …`. `size_t` — беззнаковый тип для размеров; в `printf` для него используют `%zu`.

```
size=3, capacity=5
data → [10|20|30|__|__]
```

**Создание:** `malloc` под саму структуру, затем `malloc` под данные; `size = 0`, `capacity` — начальная вместимость. `arr` указывает на структуру, а `arr->data` — на массив чисел.

**Добавление (`array_push`):** если `size >= capacity`, места нет — **удваиваем** вместимость через безопасный `realloc`. Почему не на 1? Тогда `realloc` вызывался бы почти при каждом добавлении, а он может искать новый блок и переносить данные. Поэтому выделяем с запасом.

```c
if (arr->size >= arr->capacity)
{
    size_t new_capacity = arr->capacity * 2;
    int *temp = realloc(arr->data, new_capacity * sizeof(int));
    if (temp == NULL)
        return -1;
    arr->data = temp;
    arr->capacity = new_capacity;
}
arr->data[arr->size] = value;
arr->size++;
```

**Чтение (`array_get`):** проверяем границы (`index >= size` — ошибка) и отдаём значение через указатель `out_value`.

**Освобождение:** сначала `free(arr->data)`, потом `free(arr)` — в обратном порядке создания.
