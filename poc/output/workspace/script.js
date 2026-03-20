document.addEventListener('DOMContentLoaded', () => {
    const generateButton = document.getElementById('generateButton');
    const lottoNumbersDisplay = document.getElementById('lottoNumbers');

    generateButton.addEventListener('click', generateLottoNumbers);

    function generateLottoNumbers() {
        const numbers = [];
        while (numbers.length < 6) {
            const randomNumber = Math.floor(Math.random() * 45) + 1; // Numbers from 1 to 45
            if (!numbers.includes(randomNumber)) {
                numbers.push(randomNumber);
            }
        }
        numbers.sort((a, b) => a - b); // Sort numbers for display
        displayNumbers(numbers);
    }

    function displayNumbers(numbers) {
        lottoNumbersDisplay.textContent = numbers.join(' ');
    }
});