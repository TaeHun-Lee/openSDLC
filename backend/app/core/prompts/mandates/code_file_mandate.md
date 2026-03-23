# CODE FILE OUTPUT MANDATE
In addition to the standard ImplementationArtifact fields, you MUST include a `code_files` field.
This field contains the COMPLETE, EXECUTABLE source code for every file you create or modify.

Format:
```
code_files:
  - path: "src/main.py"
    language: "python"
    content: |
      #!/usr/bin/env python3
      """Main entry point."""

      def main():
          print("Hello, World!")

      if __name__ == "__main__":
          main()

  - path: "src/utils.py"
    language: "python"
    content: |
      def helper():
          return 42
```

Rules:
1. Every file listed in `files_changed` MUST have a corresponding entry in `code_files`.
2. Each `content` field must contain the COMPLETE file — no placeholders, no "..." ellipsis, no "# TODO" stubs.
3. The code must be immediately executable with the command in `runtime_info.entrypoint`.
4. Use `|` (literal block scalar) for the `content` field to preserve formatting.
5. File paths must be relative (e.g., "src/app.py", not "/absolute/path/app.py").
6. Include ALL necessary files: entry points, modules, config files, requirements.txt, etc.
7. Do not omit imports, type hints, or error handling for brevity.
