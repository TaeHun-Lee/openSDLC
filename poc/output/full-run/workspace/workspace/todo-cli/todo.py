import sys
import json
import os

# 데이터 파일 경로 설정
DATA_FILE = "todos.json"

def load_todos():
    """todos.json 파일에서 할 일 목록을 불러옵니다. 파일이 없으면 빈 리스트를 반환합니다."""
    if not os.path.exists(DATA_FILE):
        return []
    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            # 파일이 비어있는 경우 JSONDecodeError 방지
            content = f.read()
            if not content:
                return []
            return json.loads(content)
    except (json.JSONDecodeError, IOError):
        return []

def save_todos(todos):
    """할 일 목록을 todos.json 파일에 저장합니다."""
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(todos, f, ensure_ascii=False, indent=4)

def add_todo(task):
    """새로운 할 일을 목록에 추가합니다."""
    if not task:
        print("추가할 내용이 없습니다.")
        return
    todos = load_todos()
    todos.append(task)
    save_todos(todos)
    print("할 일이 추가되었습니다.")

def list_todos():
    """모든 할 일 목록을 출력합니다."""
    todos = load_todos()
    if not todos:
        print("할 일이 없습니다.")
    else:
        for i, task in enumerate(todos, 1):
            print(f"{i}. {task}")

def complete_todo(task_number_str):
    """지정된 번호의 할 일을 완료(삭제)합니다."""
    try:
        index = int(task_number_str) - 1
        todos = load_todos()
        if 0 <= index < len(todos):
            todos.pop(index)
            save_todos(todos)
            print("할 일이 완료되었습니다.")
        else:
            print("해당 번호의 할 일이 없습니다.")
    except ValueError:
        print("해당 번호의 할 일이 없습니다.")

def print_usage():
    """사용법을 출력합니다."""
    print("사용법:")
    print("  python todo.py list              - 모든 할 일 목록 보기")
    print("  python todo.py add '<내용>'    - 새로운 할 일 추가하기")
    print("  python todo.py complete <번호> - 특정 번호의 할 일 완료하기")

def main():
    """애플리케이션의 메인 로직을 처리합니다."""
    # 실행 경로를 스크립트 파일이 있는 디렉토리로 변경
    # 이렇게 하면 어디서 실행하든 todos.json 파일이 스크립트와 같은 위치에 생성됨
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    args = sys.argv[1:]
    if not args:
        print_usage()
        return

    command = args[0]

    if command == "list":
        list_todos()
    elif command == "add":
        if len(args) > 1:
            add_todo(args[1])
        else:
            add_todo("")  # 빈 내용을 전달하여 오류 메시지 트리거
    elif command == "complete":
        if len(args) > 1:
            complete_todo(args[1])
        else:
            print("완료할 할 일의 번호를 입력하세요.")
    else:
        print(f"알 수 없는 명령어: {command}")
        print_usage()

if __name__ == "__main__":
    main()