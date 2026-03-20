document.addEventListener('DOMContentLoaded', () => {
    const todoInput = document.getElementById('todo-input');
    const addButton = document.getElementById('add-button');
    const todoList = document.getElementById('todo-list');

    // 할 일 추가 함수
    const addTask = () => {
        const taskText = todoInput.value.trim();

        // UC-1-01 Alternate Flow: 입력값이 비어있으면 함수 종료
        if (taskText === '') {
            return;
        }

        // li 요소 생성
        const listItem = document.createElement('li');

        // 할 일 텍스트를 담을 span 요소 생성
        const taskSpan = document.createElement('span');
        taskSpan.textContent = taskText;
        listItem.appendChild(taskSpan);

        // 삭제 버튼 생성
        const deleteButton = document.createElement('button');
        deleteButton.textContent = '삭제';
        deleteButton.className = 'delete-btn';
        listItem.appendChild(deleteButton);

        // UC-1-01 Main Flow: 생성된 li 요소를 ul 목록에 추가
        todoList.appendChild(listItem);

        // UC-1-01 Main Flow: 입력 필드 비우기
        todoInput.value = '';
        todoInput.focus();
    };

    // '추가' 버튼 클릭 시 addTask 함수 실행
    addButton.addEventListener('click', addTask);

    // 입력 필드에서 Enter 키 입력 시 addTask 함수 실행
    todoInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            addTask();
        }
    });

    // 이벤트 위임을 사용하여 목록의 이벤트 처리
    todoList.addEventListener('click', (e) => {
        const clickedElement = e.target;
        const listItem = clickedElement.closest('li');

        if (!listItem) return;

        // UC-1-03: '삭제' 버튼 클릭 시 항목 제거
        if (clickedElement.classList.contains('delete-btn')) {
            todoList.removeChild(listItem);
        }
        // UC-1-02: 항목 클릭 시 완료/미완료 상태 토글
        else {
            listItem.classList.toggle('completed');
        }
    });
});