from flask import Flask, render_template, request, jsonify
from summarizer import generate_summary

app = Flask(__name__)


@app.route('/')
def home():
    return render_template('index.html')


@app.route('/summarize', methods=['POST'])
def summarize_text():
    data = request.get_json()
    text = data.get('text', '').strip()

    if not text:
        return jsonify({'error': 'Please enter some text'}), 400

    summary = generate_summary(text)

    return jsonify({
        'summary': summary,
        'original_words': len(text.split()),
        'summary_words': len(summary.split())
    })


if __name__ == '__main__':
    app.run(debug=True, port=3000)
