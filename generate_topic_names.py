#!/usr/bin/env python3
"""
Generate descriptive English names for topics using LLM
"""

import json
import os
from pathlib import Path
from openai import OpenAI

def generate_topic_name(topic_id, keywords, sample_text, client):
    """Generate a descriptive English name for a topic using LLM"""

    # Truncate sample text to avoid token limits
    sample_text = sample_text[:500] if sample_text else ""

    prompt = f"""Based on the following information about a deliberation topic, generate a SHORT, DESCRIPTIVE English name (maximum 5 words).

Topic ID: {topic_id}
Keywords: {', '.join(keywords[:10])}
Sample text: {sample_text}

Generate a concise English topic name that captures the main theme. Respond with ONLY the topic name, nothing else."""

    try:
        response = client.chat.completions.create(
            model=os.getenv('OPENAI_STREAMING_MODEL_NAME', 'deepseek/deepseek-chat'),
            messages=[
                {"role": "system", "content": "You are a helpful assistant that generates concise topic names in English."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=50
        )

        name = response.choices[0].message.content.strip()
        # Remove quotes if present
        name = name.strip('"\'')
        return name

    except Exception as e:
        print(f"Error generating name for topic {topic_id}: {e}")
        return f"Topic {topic_id}"


def main():
    # Load topics JSON
    topics_file = Path("knowledge_graph/topic_models/topics_summary.json")

    if not topics_file.exists():
        print(f"Error: {topics_file} not found")
        return

    with open(topics_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Initialize OpenAI client
    client = OpenAI(
        api_key=os.getenv('OPENAI_API_KEY'),
        base_url=os.getenv('OPENAI_API_BASE', 'https://openrouter.ai/api/v1')
    )

    topics = data['topics']
    print(f"Generating names for {len(topics)} topics...")

    # Process topics in batches
    for i, topic in enumerate(topics):
        topic_id = topic['id']
        keywords = topic.get('keywords', [])
        sample_contrib = topic.get('sample_contributions', [''])[0]

        print(f"Processing topic {i+1}/{len(topics)}: Topic {topic_id}...")

        # Generate descriptive name
        name = generate_topic_name(topic_id, keywords, sample_contrib, client)
        topic['name'] = name

        print(f"  Generated name: {name}")

    # Save updated JSON
    output_file = topics_file
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"\n✓ Updated {len(topics)} topic names")
    print(f"✓ Saved to {output_file}")


if __name__ == "__main__":
    main()
