#include <stdio.h>

static int generate_id(void) {
    // Допиши сохраняющийся счётчик.
    return 0;
}

int get_next_id(void) { return generate_id(); }

int main(void) {
    int n;
    scanf("%d", &n);
    for (int i = 0; i < n; i++) {
        int first = get_next_id();
        int second = get_next_id();
        printf("%d %d\n", first, second);
    }
    return 0;
}
