from groq import Groq
from dotenv import load_dotenv
import os

load_dotenv()

# Initialize the Groq client. If API key is missing, we handle it gracefully.
api_key = os.getenv("GROQ_API_KEY")
if api_key:
    client = Groq(api_key=api_key)
else:
    client = None

def get_response(
    prompt,
    history=None,
    temperature=0.7,
    top_p=1.0,
    max_tokens=1024,
    system_prompt=None,
    model_name="llama-3.3-70b-versatile",
    stream=False
):
    """
    Sends a request to Groq client and returns either the full response string or a generator for streaming.
    """
    if not client:
        error_msg = "Error: GROQ_API_KEY is not set in your environment or .env file."
        if stream:
            def err_gen():
                yield error_msg
            return err_gen()
        return error_msg

    messages = []

    # Insert system prompt at the beginning if defined
    if system_prompt:
        messages.append({
            "role": "system",
            "content": system_prompt
        })

    # Append history (expects list of dicts: [{"role": "user"/"assistant", "content": "..."}])
    if history:
        # Convert any custom keys if necessary, ensuring we only pass role and content
        formatted_history = []
        for msg in history:
            formatted_history.append({
                "role": msg.get("role", "user"),
                "content": msg.get("content", "")
            })
        messages.extend(formatted_history)

    # Append new user prompt
    messages.append({
        "role": "user",
        "content": prompt
    })

    # Build Groq completion arguments
    kwargs = {
        "model": model_name,
        "messages": messages,
        "temperature": temperature,
        "top_p": top_p,
        "max_tokens": max_tokens,
        "stream": stream
    }

    try:
        response = client.chat.completions.create(**kwargs)
        if stream:
            def chunk_generator():
                for chunk in response:
                    # Some chunks might have empty content or delta
                    if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content is not None:
                        yield chunk.choices[0].delta.content
            return chunk_generator()
        else:
            if response.choices and response.choices[0].message:
                return response.choices[0].message.content
            return "Error: No response received from the model."
    except Exception as e:
        error_text = f"Groq API Error: {str(e)}"
        if stream:
            def err_gen():
                yield error_text
            return err_gen()
        return error_text