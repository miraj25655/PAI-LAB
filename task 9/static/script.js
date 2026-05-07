async function summarizeText() {
    const inputText = document.getElementById('inputText').value;
    const summary = document.getElementById('summary');
    const originalCount = document.getElementById('originalCount');
    const summaryCount = document.getElementById('summaryCount');

    summary.innerText = 'Generating summary...';

    const response = await fetch('/summarize', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ text: inputText })
    });

    const data = await response.json();

    if (data.error) {
        summary.innerText = data.error;
        return;
    }

    summary.innerText = data.summary;
    originalCount.innerText = `Original Words: ${data.original_words}`;
    summaryCount.innerText = `Summary Words: ${data.summary_words}`;
}
