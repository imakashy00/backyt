#  Contains reusable utility functions like date formatting, text processing, URL validation, pagination helpers, response formatters, and common data transformations
from langchain.text_splitter import RecursiveCharacterTextSplitter
from pinecone import Pinecone
from langchain_openai import OpenAIEmbeddings
from dotenv import load_dotenv
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.formatters import TextFormatter
from openai import AsyncOpenAI
from pytube import YouTube
from typing import List
import asyncio
import os

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client = AsyncOpenAI(api_key=OPENAI_API_KEY)
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
pc = Pinecone(api_key=PINECONE_API_KEY)


def parse_url(youtube_url: str):
    try:
        video_id = YouTube(youtube_url).video_id
        print(video_id)
        return video_id
    except:
        return None


def extract_video_transcript(video_id: str):
    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id)
        formatter = TextFormatter()
        formatted_text = formatter.format_transcript(transcript)
        return formatted_text
    except Exception as e:
        print(f"--> While extracting the transcript following error occured {e} ")
        return None


def break_into_chunks(transcript):
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=4000, chunk_overlap=400)
    chunks = text_splitter.split_text(transcript)

    return chunks


async def create_embeddings(chunks: List[str]):
    # Generate embeddings
    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
    vectors = await embeddings.aembed_documents(chunks)
    return vectors


async def store_in_pinecone(
    chunks: List[str], vectors: List[List[float]], video_id: str
):
    try:
        index = pc.Index("ytnote")

        vector_metadata = [
            {
                "id": f"{video_id}_{i}",
                "values": vector,
                "metadata": {"text": chunk, "video_id": video_id, "chunk_index": i},
            }
            for i, (chunk, vector) in enumerate(zip(chunks, vectors))
        ]
        index.upsert(vectors=vector_metadata)
    except Exception as e:
        print(f"Error {e} while storing in pinecone db")


async def gen_small_notes(chunk: str):
    """Generate quill format notes for the small chunk"""
    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": f"Generates stuctured Markdown notes from the following text add emoji also",
            },
            {"role": "user", "content": chunk},
        ],
    )
    return response.choices[0].message.content


async def generate_notes(chunks: List[str]):
    small_notes = [gen_small_notes(chunk) for chunk in chunks]
    notes = await asyncio.gather(*small_notes)

    # join all the notes with newlines
    combined_notes = "\n\n".join(str(note) for note in notes)

    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": f"Create concise notes in structured Markdown format from these notes.",
            },
            {"role": "user", "content": combined_notes},
        ],
    )
    return response.choices[0].message.content


async def query_transcript(question: str, video_id: str):
    """
    Query Pinecone for relevant transcript chunks based on user question.
    """
    # Convert question to embedding
    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
    question_vector = await embeddings.aembed_query(question)

    # Query Pinecone
    index = pc.Index("ytnote")

    # Query with video_id filter
    query_response = index.query(
        vector=question_vector,
        top_k=3,
        filter={"video_id": video_id},
        include_metadata=True,
    )

    # Extract relevant transcript chunks
    contexts = []
    print(f"-->Query response{query_response}")
    for match in query_response["matches"]:
        if match["score"] > 0.10:  # Similarity threshold
            contexts.append(match["metadata"]["text"])
    return contexts


async def answer_question(question: str, video_id: str):
    """
    Answer questions about a video transcript using context from Pinecone.
    """
    # Retrieve relevant context
    contexts = await query_transcript(question, video_id)
    print(f"-->Context{contexts}")
    if not contexts:
        return "I couldn't find relevant information in the transcript to answer your question."

    # Combine contexts
    context_text = "\n\n".join(contexts)

    # Generate answer using context
    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": "You are a helpful assistant answering questions about video content. "
                "Use only the provided transcript context to answer the question. "
                "If the answer isn't in the context, say you don't know.",
            },
            {
                "role": "user",
                "content": f"Context from video transcript:\n\n{context_text}\n\nQuestion: {question}",
            },
        ],
    )
    print(f"The answer by chatGPT=> {response.choices[0].message.content}")

    return response.choices[0].message.content


async def create_embedding_and_store(chunks: List[str], video_id: str):
    vectors = await create_embeddings(chunks)
    await store_in_pinecone(chunks, vectors, video_id)
