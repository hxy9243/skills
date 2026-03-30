tags

[Software Engineering](https://braindump.jethro.dev/posts/software_engineering)

## Core Tenets from Handmade (NO\_ITEM\_DATA:handmade\_how\_to\_write\_better)

### Maximize portability

- Write in C99 if possible
- Try to avoid:
	- compiler extensions
- Do:
	- Use the C standard library
		- Undef macros that should not be exposed to the end user
		- Prefix names to avoid collisions
		- Write the interface in C

### Be easy to build

- Don’t use a custom build system
- Make build system optional
- Allow people to compile from source
- Minimize dependencies
- don’t allocate memory or handle resources for the user
- be const correct
- always ask for the size of buffers

### Be easy to integrate

- Consider error codes or result structs that must be handled at runtime
- Keep error code/reason in struct
```c
ParsePNGFileResult result = ParsePNGFile(png_file_data);
  if (result.error) { /* handle error */ }
```

## Bibliography

NO\_ITEM\_DATA:handmade\_how\_to\_write\_better
