document.addEventListener('DOMContentLoaded', () => {
    const generateBtn = document.getElementById('generateLottoBtn');
    const lottoNumbersDiv = document.getElementById('lottoNumbers');

    generateBtn.addEventListener('click', () => {
        const numbers = generateLottoNumbers();
        displayLottoNumbers(numbers);
    });

    /**
     * 1에서 45 사이의 고유한 로또 번호 6개를 생성합니다.
     * @returns {number[]} 생성된 로또 번호 배열
     */
    function generateLottoNumbers() {
        const lottoSet = new Set();
        while (lottoSet.size < 6) {
            const randomNumber = Math.floor(Math.random() * 45) + 1; // 1부터 45까지
            lottoSet.add(randomNumber);
        }
        return Array.from(lottoSet).sort((a, b) => a - b); // 오름차순 정렬
    }

    /**
     * 생성된 로또 번호를 웹 페이지에 표시합니다.
     * @param {number[]} numbers - 표시할 로또 번호 배열
     */
    function displayLottoNumbers(numbers) {
        lottoNumbersDiv.innerHTML = ''; // 이전 번호 초기화
        numbers.forEach(number => {
            const numberDiv = document.createElement('div');
            numberDiv.classList.add('lotto-number');
            numberDiv.textContent = number;
            lottoNumbersDiv.appendChild(numberDiv);
        });
    }
});