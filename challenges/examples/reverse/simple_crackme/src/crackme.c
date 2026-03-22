/*
 * Simple Crackme Challenge
 *
 * Compile with:
 *   gcc -o crackme crackme.c -no-pie
 *
 * This is intentionally vulnerable to string analysis.
 * Students can use: strings, ltrace, or gdb to solve.
 */

#include <stdio.h>
#include <string.h>
#include <stdlib.h>

// The password is stored in plain text (intentionally weak)
const char *SECRET_PASSWORD = "sup3r_s3cr3t_p4ssw0rd";
const char *FLAG = "FLAG{r3v3rs3_3ng1n33r1ng_101}";

void print_banner(void) {
    printf("\n");
    printf("  ╔══════════════════════════════════════╗\n");
    printf("  ║       Simple Crackme Challenge       ║\n");
    printf("  ║                v1.0                  ║\n");
    printf("  ╚══════════════════════════════════════╝\n");
    printf("\n");
}

void check_password(const char *input) {
    // Remove newline if present
    char clean_input[256];
    strncpy(clean_input, input, sizeof(clean_input) - 1);
    clean_input[sizeof(clean_input) - 1] = '\0';

    size_t len = strlen(clean_input);
    if (len > 0 && clean_input[len - 1] == '\n') {
        clean_input[len - 1] = '\0';
    }

    // Vulnerable: strcmp with hardcoded password
    if (strcmp(clean_input, SECRET_PASSWORD) == 0) {
        printf("\n[+] Access Granted!\n");
        printf("[+] Here is your flag: %s\n\n", FLAG);
    } else {
        printf("\n[-] Access Denied!\n");
        printf("[-] Wrong password. Try again.\n\n");
    }
}

int main(int argc, char *argv[]) {
    char password[256];

    print_banner();

    printf("Enter the secret password: ");
    fflush(stdout);

    if (fgets(password, sizeof(password), stdin) == NULL) {
        printf("Error reading input.\n");
        return 1;
    }

    check_password(password);

    return 0;
}
