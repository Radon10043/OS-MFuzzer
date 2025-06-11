Please identify the metamorphic relation of the linux kernel based on the following specification:

[specification]

Please identify the metamorphic relation of the linux kernel as much as possible and codify it. Note that you should just output the code block. For example:

```c
// Description of the metamorphic relation

// Include all necessary files

// The number of parameters need to be modified according to the actual situation
static long syz_mr(volatile long a0, volatile long a1) {
    // 1. Perform preparation, such as checking whether the file exists, creating folders to prevent errors, etc.
    // 2. Get the follow-up inputs through input relation
    // 3. Get the corresponding source output and follow-up output
    // 4. If outputs do not satisfy the output relation, a prompt message is printed
    if (output_relation_violated)
        printf("[SyzMeta]: MR is violated!")
}
```