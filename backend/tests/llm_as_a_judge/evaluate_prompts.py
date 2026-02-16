#!/usr/bin/env python
"""Evaluate summarization prompts using LLM-as-judge framework.

This module uses an LLM-as-judge approach to evaluate different summarization prompt variants.

EVALUATION METRICS:
    - factual_accuracy (0-10): How accurately the summary represents the article content
    - information_density (0-10): How much useful information is included per word
    - clarity (0-10): How clear and well-structured the summary is
    - relevance (0-10): How relevant the summary is to HackerNews audience
    - length_compliance (0-10): How well the summary adheres to length constraints

SCORING:
    - overall_score (0-100): Composite score from all dimensions
    - pass_rate: Percentage of summaries scoring >= 80%
    - pass_threshold: 80% overall score required to pass

PROMPT VARIANTS EVALUATED:
    - basic: Detailed, comprehensive summaries
    - technical: Technical language, concepts emphasized
    - business: Business/professional focus
    - concise: Ultra-brief summaries for quick scanning
    - personalized: User preference-based summaries
"""

import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from openai import OpenAI

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class PromptEvaluator:
    """Evaluate summarization prompts using LLM-as-judge."""

    def __init__(self, openai_api_key: str, model: str = "gpt-4o-mini"):
        """Initialize evaluator.

        Args:
            openai_api_key: OpenAI API key
            model: Model to use for evaluation
        """
        self.client = OpenAI(api_key=openai_api_key)
        self.model = model
        self.judge_prompt = self._load_judge_prompt()

    def _load_judge_prompt(self) -> str:
        """Load judge evaluation prompt."""
        prompts_dir = Path(__file__).parent.parent.parent / "app/infrastructure/prompts"
        judge_file = prompts_dir / "judge.md"

        if not judge_file.exists():
            raise FileNotFoundError(f"Judge prompt not found: {judge_file}")

        return judge_file.read_text(encoding="utf-8")

    def _load_test_dataset(self) -> List[Dict[str, Any]]:
        """Load test dataset."""
        test_file = Path(__file__).parent.parent.parent.parent / "data/test_posts.json"

        if not test_file.exists():
            raise FileNotFoundError(f"Test dataset not found: {test_file}")

        with open(test_file, "r") as f:
            return json.load(f)

    def _get_summarization_prompt(self, prompt_type: str) -> str:
        """Load summarization prompt."""
        prompts_dir = Path(__file__).parent.parent.parent / "app/infrastructure/prompts"
        prompt_file = prompts_dir / f"summarizer_{prompt_type}.md"

        if not prompt_file.exists():
            raise FileNotFoundError(f"Prompt not found: {prompt_file}")

        return prompt_file.read_text(encoding="utf-8")

    def evaluate_summary(self, article_content: str, summary: str) -> Dict[str, Any]:
        """Evaluate a single summary using LLM-as-judge.

        Args:
            article_content: Original article content
            summary: Generated summary to evaluate

        Returns:
            Evaluation results with scores
        """
        # Prepare judge prompt
        judge_input = self.judge_prompt.format(
            article_content=article_content[:500],  # First 500 words
            summary=summary,
        )

        # Call judge
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": judge_input}],
            temperature=0.0,  # Deterministic evaluation
            max_tokens=500,
        )

        # Parse response
        result_text = response.choices[0].message.content
        try:
            # Try to extract JSON from response
            result = json.loads(result_text)
        except json.JSONDecodeError:
            # Try to find JSON in the response
            import re

            json_match = re.search(r"\{.*\}", result_text, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
            else:
                logger.error(f"Failed to parse judge response: {result_text}")
                result = {
                    "overall_score": 0,
                    "issues": ["Failed to parse judge response"],
                }

        return result

    def summarize_post(self, post: Dict[str, Any], prompt_type: str) -> str:
        """Generate summary for a post using specified prompt.

        Args:
            post: Post data
            prompt_type: Prompt variant to use

        Returns:
            Generated summary
        """
        prompt_template = self._get_summarization_prompt(prompt_type)

        # For personalized prompt, substitute variables
        if prompt_type == "personalized":
            prompt_template = prompt_template.format(
                user_topics="distributed systems, databases, performance",
                user_style="technical",
                markdown_content=post["markdown_content"],
            )
            input_text = prompt_template
        else:
            input_text = f"{prompt_template}\n\nArticle Content:\n{post['markdown_content']}"

        # Generate summary
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": input_text}],
            temperature=0.3,  # Lower for consistency
            max_tokens=200,
        )

        return response.choices[0].message.content.strip()

    def evaluate_prompt_variant(self, prompt_type: str) -> Dict[str, Any]:
        """Evaluate all test summaries for a prompt variant.

        Args:
            prompt_type: Prompt variant to evaluate

        Returns:
            Evaluation results for the variant
        """
        test_posts = self._load_test_dataset()
        results = {
            "variant": prompt_type,
            "summaries_evaluated": 0,
            "passed": 0,
            "dimension_scores": {
                "factual_accuracy": [],
                "information_density": [],
                "clarity": [],
                "relevance": [],
                "length_compliance": [],
            },
            "individual_scores": [],
            "issues": [],
        }

        for i, post in enumerate(test_posts, 1):
            logger.info(f"Evaluating {prompt_type} variant - Post {i}/{len(test_posts)}")

            try:
                # Generate summary
                summary = self.summarize_post(post, prompt_type)
                logger.info(f"Generated summary: {summary[:100]}...")

                # Evaluate summary
                evaluation = self.evaluate_summary(post["markdown_content"], summary)

                # Extract scores
                overall_score = evaluation.get("overall_score", 0)
                passed = overall_score >= 80

                results["summaries_evaluated"] += 1
                if passed:
                    results["passed"] += 1

                # Track dimension scores
                for dimension in results["dimension_scores"]:
                    if dimension in evaluation:
                        results["dimension_scores"][dimension].append(
                            evaluation[dimension]
                        )

                # Track individual result
                results["individual_scores"].append(
                    {
                        "post_id": post["hn_id"],
                        "post_title": post["title"][:50],
                        "summary": summary,
                        "overall_score": overall_score,
                        "passed": passed,
                        "evaluation": evaluation,
                    }
                )

                if not passed:
                    results["issues"].append(
                        f"Post {i}: Score {overall_score}% - {evaluation.get('issues', [])}"
                    )

            except Exception as e:
                logger.error(f"Error evaluating post {i}: {e}")
                results["issues"].append(f"Post {i}: Error - {str(e)}")

        # Calculate averages
        if results["dimension_scores"]["factual_accuracy"]:
            for dimension in results["dimension_scores"]:
                scores = results["dimension_scores"][dimension]
                results[f"{dimension}_avg"] = (
                    sum(scores) / len(scores) if scores else 0
                )

        results["pass_rate"] = (
            results["passed"] / results["summaries_evaluated"]
            if results["summaries_evaluated"] > 0
            else 0
        )

        return results

    def run_full_evaluation(self, prompt_variants: Optional[List[str]] = None):
        """Run evaluation on all prompt variants.

        Args:
            prompt_variants: List of variants to evaluate (default: all 5)
        """
        if prompt_variants is None:
            prompt_variants = ["basic", "technical", "business", "concise", "personalized"]

        logger.info(f"Starting evaluation of {len(prompt_variants)} prompt variants")
        logger.info(f"Variants: {', '.join(prompt_variants)}")

        all_results = {}
        for variant in prompt_variants:
            logger.info(f"\n{'='*60}")
            logger.info(f"Evaluating: {variant}")
            logger.info(f"{'='*60}")

            results = self.evaluate_prompt_variant(variant)
            all_results[variant] = results

            # Print interim results
            self._print_variant_results(results)

        # Print summary
        self._print_summary_report(all_results)

        # Save results to file
        self._save_results(all_results)

        return all_results

    def _print_variant_results(self, results: Dict[str, Any]):
        """Print results for a single variant."""
        print(f"\nVariant: {results['variant']}")
        print(f"Summaries Evaluated: {results['summaries_evaluated']}")
        print(f"Passed: {results['passed']}/{results['summaries_evaluated']}")
        print(f"Pass Rate: {results['pass_rate']:.1%}")

        print("\nDimension Averages:")
        for dimension in results["dimension_scores"]:
            avg_key = f"{dimension}_avg"
            if avg_key in results:
                print(f"  {dimension}: {results[avg_key]:.1f}/10")

        print("\nIndividual Scores:")
        for score in results["individual_scores"]:
            status = "✓" if score["passed"] else "✗"
            print(
                f"  {status} Post {score['post_id']}: {score['overall_score']:.0f}% - {score['post_title']}"
            )

        if results["issues"]:
            print("\nIssues:")
            for issue in results["issues"]:
                print(f"  - {issue}")

    def _print_summary_report(self, all_results: Dict[str, Dict[str, Any]]):
        """Print summary report for all variants."""
        print(f"\n{'='*60}")
        print("EVALUATION SUMMARY")
        print(f"{'='*60}\n")

        # Sort by pass rate
        sorted_variants = sorted(
            all_results.items(), key=lambda x: x[1]["pass_rate"], reverse=True
        )

        for variant, results in sorted_variants:
            status = "✓ APPROVED" if results["pass_rate"] >= 0.8 else "✗ NEEDS WORK"
            print(f"{variant:15} | Pass Rate: {results['pass_rate']:6.1%} | {status}")

        print(f"\n{'='*60}\n")

    def _save_results(self, all_results: Dict[str, Dict[str, Any]]):
        """Save evaluation results to file."""
        output_file = Path(__file__).parent.parent.parent.parent / "data/evaluation_results.json"
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, "w") as f:
            json.dump(all_results, f, indent=2)

        logger.info(f"Results saved to {output_file}")


def main():
    """Main entry point."""
    # Load environment variables from .env file
    load_dotenv()

    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        raise ValueError("OPENAI_API_KEY environment variable not set")

    evaluator = PromptEvaluator(openai_api_key)

    # Run evaluation
    results = evaluator.run_full_evaluation()

    # Print final recommendations
    print(f"\n{'='*60}")
    print("RECOMMENDATIONS")
    print(f"{'='*60}\n")

    approved = [v for v, r in results.items() if r["pass_rate"] >= 0.8]
    if approved:
        print(f"✓ Approved variants ({len(approved)}):")
        for v in approved:
            print(f"  - {v}: {results[v]['pass_rate']:.1%} pass rate")
    else:
        print("✗ No variants approved. Iteration needed.")

    needs_work = [v for v, r in results.items() if r["pass_rate"] < 0.8]
    if needs_work:
        print(f"\n⚠ Needs work ({len(needs_work)}):")
        for v in needs_work:
            print(f"  - {v}: {results[v]['pass_rate']:.1%} pass rate")
            if results[v]["issues"]:
                for issue in results[v]["issues"][:2]:  # Show first 2 issues
                    print(f"    - {issue}")


if __name__ == "__main__":
    main()
