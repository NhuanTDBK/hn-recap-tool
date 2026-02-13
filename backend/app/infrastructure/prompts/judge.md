# Summary Quality Evaluation

You are evaluating the quality of a HackerNews article summary.

## Original Article (first 500 words):
{article_content}

## Generated Summary:
{summary}

## Evaluation Criteria:

Rate each dimension on a scale of 0-10:

**Factual Accuracy (0-10):**
- Does the summary contain any factual errors or hallucinations?
- Are all claims verifiable in the source article?
- 10 = Perfect accuracy, 0 = Contains false information

**Information Density (0-10):**
- Does it capture the most important points?
- Is it concise without losing key insights?
- 10 = Perfect balance, 0 = Misses key points or too verbose

**Clarity & Readability (0-10):**
- Is it easy to understand?
- Does it flow naturally?
- 10 = Crystal clear, 0 = Confusing or poorly written

**Relevance (0-10):**
- Does it highlight why this matters to developers?
- Does it capture novel insights?
- 10 = Highly relevant, 0 = Misses the point

**Length Compliance (0-10):**
- Target: 2-3 sentences (40-100 words)
- 1 sentence max (concise variant): 20-30 words
- 10 = Perfect compliance, 0 = Severely violates target length

## Output Format (JSON only):
```json
{
  "factual_accuracy": <score 0-10>,
  "information_density": <score 0-10>,
  "clarity": <score 0-10>,
  "relevance": <score 0-10>,
  "length_compliance": <score 0-10>,
  "overall_score": <weighted average 0-100>,
  "reasoning": "<brief explanation of scores>",
  "issues": ["<specific issue 1>", "<issue 2>"]
}
```

Provide ONLY the JSON, no additional text.
