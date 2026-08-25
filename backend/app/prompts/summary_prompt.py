# Feature: Document Summary
# Author: Akanksha

SUMMARY_PROMPT = """
You are an AI assistant that summarizes uploaded documents.

Read the document below and return ONLY valid JSON.

Use exactly this structure:

{{
    "title": "string",
    "summary": "string",
    "key_points": [
        "string",
        "string",
        "string"
    ],
    "keywords": [
        "string",
        "string",
        "string"
    ]
}}

Rules:
- Return ONLY valid JSON.
- Do not use markdown.
- Do not add ```json.
- The title should describe the document.
- The summary should be concise.
- Provide 3 to 5 key points.
- Provide 3 to 6 keywords.
- Use only information from the document.

DOCUMENT:

{text}
"""