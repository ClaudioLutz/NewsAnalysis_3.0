#!/usr/bin/env python
"""Run summarization and digest generation on filtered articles."""

import asyncio
import sys
from datetime import datetime
from pathlib import Path

# Fix Windows encoding
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from newsanalysis.core.config import Config
from newsanalysis.database.connection import init_database
from newsanalysis.integrations.provider_factory import ProviderFactory
from newsanalysis.pipeline.summarizers.article_summarizer import ArticleSummarizer
from newsanalysis.pipeline.generators.digest_generator import DigestGenerator
from newsanalysis.database.repository import ArticleRepository
from newsanalysis.database.digest_repository import DigestRepository
from newsanalysis.services.config_loader import ConfigLoader


async def main():
    """Run summarization and digest generation."""
    print("\n" + "=" * 70)
    print("SUMMARIZATION & DIGEST - Multi-Provider LLM System")
    print("=" * 70)
    print()

    # Initialize
    config = Config()
    db = init_database(Path(config.db_path))
    run_id = f"summarize-{datetime.now().strftime('%Y%m%d-%H%M%S')}"

    print(f"Run ID: {run_id}")
    print(f"Summarization Provider: {config.summarization_provider}")
    print(f"Digest Provider: {config.digest_provider}")
    print()

    # Initialize provider factory
    factory = ProviderFactory(config=config, db=db, run_id=run_id)

    # Get clients
    summarization_client = factory.get_summarization_client()
    digest_client = factory.get_digest_client()

    # Check scraped articles (ready for summarization)
    cursor = db.execute("""
        SELECT COUNT(*) as count FROM articles WHERE pipeline_stage = 'scraped'
    """)
    scraped_count = cursor.fetchone()['count']
    print(f"Scraped articles ready for summarization: {scraped_count}")

    if scraped_count == 0:
        print("No articles to process. Exiting.")
        db.close()
        return 0
    print()

    # ===================================================================
    # SUMMARIZATION (Gemini)
    # ===================================================================
    print("=" * 70)
    print("SUMMARIZATION (Gemini)")
    print("=" * 70)
    print()

    # Get articles ready for summarization (limit to 10 for demo)
    cursor = db.execute("""
        SELECT id, title, url, content, source, published_at
        FROM articles
        WHERE pipeline_stage = 'scraped'
        ORDER BY published_at DESC
        LIMIT 10
    """)

    articles_to_summarize = cursor.fetchall()
    print(f"Articles to summarize: {len(articles_to_summarize)}")
    print()

    summarizer = ArticleSummarizer(llm_client=summarization_client)

    summarized_count = 0
    summaries = []

    for article in articles_to_summarize:
        article_id = article['id']
        title = article['title']
        content = article['content'] or title

        print(f"[{summarized_count + 1}/{len(articles_to_summarize)}] {title[:60]}...")

        try:
            summary = await summarizer.summarize(
                title=title,
                url=article['url'],
                content=content,
                source=article['source'],
            )

            # Store summary in database
            db.execute("""
                UPDATE articles
                SET pipeline_stage = 'summarized',
                    summary_title = ?,
                    summary = ?,
                    key_points = ?,
                    summarized_at = ?
                WHERE id = ?
            """, (
                summary.summary_title,
                summary.summary,
                "|".join(summary.key_points),
                datetime.now().isoformat(),
                article_id,
            ))
            db.commit()

            summaries.append(summary)
            print(f"  ✓ Summarized")
            summarized_count += 1

        except Exception as e:
            print(f"  ✗ Error: {e}")
            continue

    print()
    print(f"Summarized: {summarized_count} articles")
    print()

    # Show summarization costs
    cursor = db.execute("""
        SELECT COUNT(*) as calls, SUM(cost) as total_cost
        FROM api_calls
        WHERE run_id = ? AND model LIKE 'gemini:%'
    """, (run_id,))
    row = cursor.fetchone()
    if row['total_cost']:
        print(f"Gemini Summarization Cost: ${row['total_cost']:.6f} ({row['calls']} calls)")
    print()

    if summarized_count < 2:
        print("Not enough summaries for digest (need at least 2). Exiting.")
        db.close()
        return 0

    # ===================================================================
    # DIGEST GENERATION (Gemini)
    # ===================================================================
    print("=" * 70)
    print("DIGEST GENERATION (Gemini)")
    print("=" * 70)
    print()

    # Initialize digest generator
    article_repo = ArticleRepository(db)
    digest_repo = DigestRepository(db)
    config_loader = ConfigLoader(Path("config"))

    digest_generator = DigestGenerator(
        llm_client=digest_client,
        article_repo=article_repo,
        digest_repo=digest_repo,
        config_loader=config_loader,
    )

    print(f"Generating digest from {len(summaries)} summaries...")
    print()

    try:
        digest = await digest_generator.generate(
            summaries=summaries,
            date=datetime.now(),
            run_id=run_id,
        )

        print("✓ Digest Generated Successfully!")
        print()
        print(f"Title: {digest.title}")
        print()
        print("Executive Summary:")
        print(f"  {digest.executive_summary[:300]}...")
        print()
        print(f"Themes: {len(digest.themes)}")
        for i, theme in enumerate(digest.themes[:3], 1):
            print(f"  {i}. {theme.title}")
        print()
        print(f"Articles Included: {len(digest.articles)}")
        print()

        # Save digest to file
        output_dir = Path("out/digests")
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file = output_dir / f"digest_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"

        with open(output_file, "w", encoding="utf-8") as f:
            f.write(f"# {digest.title}\n\n")
            f.write(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n")
            f.write(f"## Executive Summary\n\n{digest.executive_summary}\n\n")
            f.write("## Key Themes\n\n")
            for theme in digest.themes:
                f.write(f"### {theme.title}\n\n")
                f.write(f"{theme.summary}\n\n")
            if digest.trends:
                f.write("## Trends\n\n")
                for trend in digest.trends:
                    f.write(f"- **{trend.title}**: {trend.description}\n")
            f.write("\n## Articles\n\n")
            for article in digest.articles:
                f.write(f"- [{article.title}]({article.url}) ({article.source_name})\n")

        print(f"Digest saved to: {output_file}")
        print()

    except Exception as e:
        print(f"ERROR generating digest: {e}")
        import traceback
        traceback.print_exc()

    # ===================================================================
    # FINAL COST BREAKDOWN
    # ===================================================================
    print("=" * 70)
    print("FINAL COST BREAKDOWN")
    print("=" * 70)
    print()

    cursor = db.execute("""
        SELECT
            CASE
                WHEN model LIKE 'deepseek:%' THEN 'DeepSeek'
                WHEN model LIKE 'gemini:%' THEN 'Gemini'
                ELSE 'OpenAI'
            END as provider,
            COUNT(*) as calls,
            SUM(input_tokens) as input_tokens,
            SUM(output_tokens) as output_tokens,
            SUM(cost) as total_cost
        FROM api_calls
        GROUP BY provider
        ORDER BY total_cost DESC
    """)

    print(f"{'Provider':<15} {'Calls':>8} {'Input':>10} {'Output':>10} {'Cost':>12}")
    print("-" * 70)

    total_cost = 0.0
    total_calls = 0

    for row in cursor.fetchall():
        provider = row['provider']
        calls = row['calls']
        input_tokens = row['input_tokens'] or 0
        output_tokens = row['output_tokens'] or 0
        cost = row['total_cost'] or 0

        total_cost += cost
        total_calls += calls

        print(f"{provider:<15} {calls:>8} {input_tokens:>10,} {output_tokens:>10,} ${cost:>11.6f}")

    print("-" * 70)
    print(f"{'TOTAL':<15} {total_calls:>8} {' ':>10} {' ':>10} ${total_cost:>11.6f}")
    print()

    print("=" * 70)
    print("✓ PRODUCTION PIPELINE COMPLETE!")
    print("=" * 70)
    print()

    db.close()
    return 0


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\nInterrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
