#include <stdio.h>

static int generate_id(void) {
    static int id = 0;
    id++;
    return id;
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
