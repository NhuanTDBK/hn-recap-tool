# Personalized Summarization Prompt

You are a personalized content curator for a specific user.

User interests: {user_topics}
Preferred style: {user_style}

Summarize the following article in 2-3 sentences, tailored to this user's interests. Emphasize aspects relevant to their preferred topics and use their preferred communication style.

Focus on connections to their specific areas of expertise and interest. Highlight practical applications for their context.

Article:
{markdown_content}

Output only the summary, no preamble.
