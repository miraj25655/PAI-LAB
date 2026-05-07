from transformers import pipeline

summarizer = pipeline(
    'summarization',
    model='facebook/bart-large-cnn'
)


def generate_summary(text):
    max_len = max(40, len(text.split()) // 2)

    result = summarizer(
        text,
        max_length=max_len,
        min_length=20,
        do_sample=False
    )

    return result[0]['summary_text']
