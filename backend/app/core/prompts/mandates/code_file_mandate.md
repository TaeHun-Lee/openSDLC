# CODE FILE OUTPUT MANDATE
아티팩트 YAML과 별도로, narrative 영역에 모든 소스코드 파일을 마크다운 코드 블록으로 출력하라.
아티팩트 YAML 안에 code_files 필드를 포함하지 마라.

## 출력 형식
각 코드 파일 앞에 반드시 HTML 주석 마커를 배치하라:

```
<!-- FILE: {relative_path} -->
```{language}
{complete source code}
```
```

예시:
```
<!-- FILE: src/main.py -->
```python
#!/usr/bin/env python3
"""Main entry point."""

def main():
    print("Hello, World!")

if __name__ == "__main__":
    main()
```

<!-- FILE: src/utils.py -->
```python
def helper():
    return 42
```
```

## 규칙
1. `files_changed`에 나열된 모든 파일은 반드시 위 형식의 코드 블록으로 출력해야 한다.
2. 각 코드 블록은 COMPLETE 파일이어야 한다 — placeholder, "..." 생략, "# TODO" 스텁 금지.
3. 코드는 `runtime_info.entrypoint` 명령으로 즉시 실행 가능해야 한다.
4. 파일 경로는 상대 경로를 사용하라 (예: "src/app.py", 절대 경로 금지).
5. 진입점, 모듈, 설정 파일, requirements.txt 등 필요한 모든 파일을 포함하라.
6. import, type hints, 에러 처리를 생략하지 마라.
7. 코드 블록을 모두 출력한 후, 아티팩트 YAML을 ```yaml 펜스로 감싸서 출력하라.
8. 아티팩트 YAML에는 `code_files` 필드를 절대 포함하지 마라. 템플릿에 정의된 필드만 사용하라.
