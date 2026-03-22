# Simple Crackme

## Description

Can you crack this simple password checker?

Download the binary and find the correct password to get the flag!

## Hints

1. Sometimes the answer is hiding in plain sight...
2. Have you tried looking at the strings in the binary?

## Files

- `crackme` - The executable to crack

## Solution

<details>
<summary>Click to reveal solution</summary>

```bash
# Method 1: Use strings
strings crackme | grep FLAG

# Method 2: Use ltrace
ltrace ./crackme
# Enter any password, observe the strcmp call

# Method 3: Use a debugger
gdb ./crackme
# Set breakpoint at strcmp, examine arguments
```

</details>
