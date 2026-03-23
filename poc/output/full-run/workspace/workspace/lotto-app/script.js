const generateBtn = document.getElementById('generate-btn');
const numbersContainer = document.getElementById('lotto-numbers');

generateBtn.addEventListener('click', () => {
    const lottoNumbers = generateUniqueNumbers(6, 1, 45);
    const sortedNumbers = lottoNumbers.sort((a, b) => a - b);
    displayNumbers(sortedNumbers);
});

function generateUniqueNumbers(count, min, max) {
    const numbers = new Set();
    while (numbers.size < count) {
        const randomNumber = Math.floor(Math.random() * (max - min + 1)) + min;
        numbers.add(randomNumber);
    }
    return Array.from(numbers);
}

function displayNumbers(numbers) {
    numbersContainer.innerHTML = ''; // Clear previous numbers
    numbers.forEach(number => {
        const numberElement = document.createElement('div');
        numberElement.className = 'lotto-number';
        numberElement.textContent = number;
        numberElement.style.backgroundColor = getNumberColor(number);
        numbersContainer.appendChild(numberElement);
    });
}

function getNumberColor(number) {
    if (number <= 10) return '#fbc400'; // 노란색
    if (number <= 20) return '#69c8f2'; // 파란색
    if (number <= 30) return '#ff7272'; // 빨간색
    if (number <= 40) return '#aaa';    // 회색
    return '#b0d840';                   // 녹색
}