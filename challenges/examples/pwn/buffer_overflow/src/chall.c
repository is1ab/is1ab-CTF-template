#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

// Flag 從文件讀取（防止 strings 直接取得）
#define FLAG_PATH "/home/ctf/flag.txt"
#define FLAG_SIZE 128

void win() {
    char flag[FLAG_SIZE];
    FILE *f = fopen(FLAG_PATH, "r");

    if (f == NULL) {
        printf("Error: Cannot read flag file.\n");
        printf("Please contact admin.\n");
        exit(1);
    }

    if (fgets(flag, FLAG_SIZE, f) == NULL) {
        printf("Error: Flag file is empty.\n");
        fclose(f);
        exit(1);
    }
    fclose(f);

    // 移除換行符
    flag[strcspn(flag, "\n")] = '\0';

    printf("🎉 Congratulations! You got the flag:\n");
    printf("%s\n", flag);
    exit(0);
}

void vuln() {
    char buffer[64];

    printf("==============================\n");
    printf("  Buffer Overflow Challenge\n");
    printf("==============================\n");
    printf("\n");
    printf("Can you overflow the buffer and call win()?\n");
    printf("Enter your input: ");
    fflush(stdout);

    // 危險函數 - 沒有檢查長度
    gets(buffer);

    printf("You entered: %s\n", buffer);
}

int main() {
    // 關閉 buffering
    setvbuf(stdin, NULL, _IONBF, 0);
    setvbuf(stdout, NULL, _IONBF, 0);
    setvbuf(stderr, NULL, _IONBF, 0);

    printf("Welcome to PWN 101!\n");
    printf("win() is at: %p\n", win);
    printf("\n");

    vuln();

    printf("Bye!\n");
    return 0;
}
