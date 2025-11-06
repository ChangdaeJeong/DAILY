function showLoadingSpinner() {
    const loadingContainer = document.getElementById('loading-spinner-container');
    if (loadingContainer) {
        loadingContainer.style.display = 'flex'; // 로딩 스피너 표시

        const wordElement = document.getElementById('word');
        const text1 = "Dev AI Loop for Your code";
        const text2 = "DAILY";

        const createSpans = (text) => {
            wordElement.innerHTML = '';
            text.split('').forEach(char => {
                const span = document.createElement('span');
                span.className = 'char';
                if (char === ' ') {
                    span.classList.add('space');
                } else {
                    span.textContent = char;
                }
                wordElement.appendChild(span);
            });
            return wordElement.querySelectorAll('.char');
        };

        const animateIn = (elements) => {
            elements.forEach((el, i) => {
                setTimeout(() => el.classList.add('visible'), i * 60);
            });
        };

        const animateOut = (elements) => {
            elements.forEach((el, i) => {
                setTimeout(() => el.classList.remove('visible'), i * 60);
            });
        };

        const sleep = (ms) => new Promise(resolve => setTimeout(resolve, ms));

        // Animation sequence
        (async () => {
            const chars1 = createSpans(text1);
            await sleep(100);
            animateIn(chars1);

            await sleep(text1.length * 60 + 1000);
            const chars2 = createSpans(text2);
            wordElement.style.letterSpacing = '0.2em';
            await sleep(100);
            animateIn(chars2);

            await sleep(text2.length * 60 + 2000);
            hideLoadingSpinner(); // 애니메이션 완료 후 로딩 스피너 숨기기
        })();
    }
}

function hideLoadingSpinner() {
    const loadingContainer = document.getElementById('loading-spinner-container');
    if (loadingContainer) {
        loadingContainer.style.display = 'none'; // 로딩 스피너 숨기기
    }
}
