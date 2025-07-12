from transformers import pipeline
from sentence_transformers import SentenceTransformer, util
qa_pipeline = pipeline("text2text-generation", model="google/flan-t5-base")
similarity_model = SentenceTransformer("all-MiniLM-L6-v2")

def answer_question_from_transcript(transcript: str, question: str, threshold: float = 0.4) -> str:
    transcript_embedding = similarity_model.encode(transcript, convert_to_tensor=True)
    question_embedding = similarity_model.encode(question, convert_to_tensor=True)
    similarity_score = util.pytorch_cos_sim(transcript_embedding, question_embedding).item()

    if similarity_score < threshold:
        return "⚠️ This question appears to be outside the scope of the current lecture."
    prompt = f"Transcript: {transcript}\n\nQuestion: {question}\nAnswer:"
    result = qa_pipeline(prompt, max_length=100, do_sample=False)
    return result[0]['generated_text']
