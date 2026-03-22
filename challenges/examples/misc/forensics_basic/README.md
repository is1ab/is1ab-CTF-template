# Hidden Message

## Description

I found this mysterious image file. I heard there's a hidden message inside...

Can you find it?

## Hints

1. Not everything that looks like an image is just an image.
2. Try looking beyond what your eyes can see.

## Files

- `mystery.png` - A mysterious image file

## Solution

<details>
<summary>Click to reveal solution</summary>

```bash
# Method 1: Use strings
strings mystery.png | grep FLAG

# Method 2: Use file and binwalk
file mystery.png
binwalk mystery.png

# Method 3: Check file metadata
exiftool mystery.png

# Method 4: Look at the hex
xxd mystery.png | grep -i flag
```

The flag is hidden as a comment in the PNG metadata or appended at the end of the file.

</details>
