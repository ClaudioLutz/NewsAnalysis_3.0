#!/usr/bin/env python
"""Run full production pipeline with fresh database."""

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
from newsanalysis.core.article import Article
from newsanalysis.database.connection import init_database
from newsanalysis.integrations.provider_factory import ProviderFactory
from newsanalysis.pipeline.collectors import create_collector
from newsanalysis.pipeline.filters.ai_filter import AIFilter
from newsanalysis.pipeline.summarizers.article_summarizer import ArticleSummarizer
from newsanalysis.services.config_loader import load_feeds_config
from newsanalysis.database.repository import ArticleRepository


async def main():
    """Run full production pipeline."""
    print("\n" + "=" * 70)
    print("FULL PRODUCTION PIPELINE - Multi-Provider LLM System")
    print("=" * 70)
    print()

    # Initialize
    config = Config()
    db = init_database(Path(config.db_path))
    run_id = f"prod-{datetime.now().strftime('%Y%m%d-%H%M%S')}"

    print(f"Run ID: {run_id}")
    print()
    print("Provider Configuration:")
    print(f"  Classification: {config.classification_provider} (DeepSeek)")
    print(f"  Summarization: {config.summarization_provider} (Gemini)")
    print()

    # Initialize provider factory
    factory = ProviderFactory(config=config, db=db, run_id=run_id)

    # Get clients
    classification_client = factory.get_classification_client()
    summarization_client = factory.get_summarization_client()

    # Initialize repository
    repository = ArticleRepository(db)

    # ===================================================================
    # STAGE 1: COLLECTION
    # ===================================================================
    print("=" * 70)
    print("STAGE 1: COLLECTION")
    print("=" * 70)
    print()

    feeds = load_feeds_config(Path("config"))
    # Use all enabled feeds
    enabled_feeds = [f for f in feeds if f.enabled]
    print(f"Collecting from {len(enabled_feeds)} feeds...")

    total_collected = 0
    for feed in enabled_feeds:
        try:
            collector = create_collector(feed, timeout=config.request_timeout_sec)
            articles = await collector.collect()
            if articles:
                saved = repository.save_collected_articles(articles, run_id)
                print(f"  {feed.name}: {saved} articles")
                total_collected += saved
        except Exception as e:
            print(f"  {feed.name}: Error - {str(e)[:50]}")
        await asyncio.sleep(1)  # Rate limit

    print()
    print(f"Total collected: {total_collected}")
    print()

    if total_collected == 0:
        print("No articles collected. Exiting.")
        db.close()
        return 0

    # ===================================================================
    # STAGE 2: CLASSIFICATION (DeepSeek)
    # ===================================================================
    print("=" * 70)
    print("STAGE 2: CLASSIFICATION (DeepSeek)")
    print("=" * 70)
    print()

    ai_filter = AIFilter(llm_client=classification_client, config=config)

    cursor = db.execute("""
        SELECT id, title, url, normalized_url, url_hash, source, published_at, feed_priority
        FROM articles
        WHERE pipeline_stage = 'collected'
    """)
    rows = cursor.fetchall()

    print(f"Classifying {len(rows)} articles...")

    # Convert to Article objects
    from datetime import datetime as dt
    articles_to_filter = []
    for row in rows:
        pub_at = row['published_at']
        if isinstance(pub_at, str):
            pub_at = dt.fromisoformat(pub_at.replace('Z', '+00:00'))

        article = Article(
            id=row['id'],
            url=row['url'],
            normalized_url=row['normalized_url'],
            url_hash=row['url_hash'],
            title=row['title'],
            source=row['source'],
            published_at=pub_at,
            collected_at=dt.now(),
            feed_priority=row['feed_priority'],
            run_id=run_id,
        )
        articles_to_filter.append(article)

    # Filter all articles at once
    try:
        results = await ai_filter.filter_articles(articles_to_filter)

        classified = len(results)
        relevant = 0

        for article, result in zip(articles_to_filter, results):
            if result.is_match:
                db.execute("UPDATE articles SET pipeline_stage = 'filtered', confidence = ?, topic = ? WHERE id = ?",
                    (result.confidence, result.topic, article.id))
                relevant += 1
                print(f"  ✓ [{result.confidence:.0%}] {article.title[:50]}...")
            else:
                db.execute("UPDATE articles SET pipeline_stage = 'rejected', confidence = ?, topic = ? WHERE id = ?",
                    (result.confidence, result.topic, article.id))

        db.commit()

    except Exception as e:
        classified = 0
        relevant = 0
        print(f"  ✗ Error: {e}")
        import traceback
        traceback.print_exc()

    print()
    print(f"Classified: {classified}, Relevant: {relevant}")
    print()

    # Show DeepSeek costs
    cursor = db.execute("""
        SELECT COUNT(*) as calls, COALESCE(SUM(cost), 0) as cost
        FROM api_calls WHERE run_id = ? AND model LIKE 'deepseek:%'
    """, (run_id,))
    row = cursor.fetchone()
    print(f"DeepSeek Cost: ${row['cost']:.6f} ({row['calls']} calls)")
    print()

    if relevant == 0:
        print("No relevant articles found. Skipping summarization.")
        db.close()
        return 0

    # ===================================================================
    # STAGE 3: SUMMARIZATION (Gemini)
    # ===================================================================
    print("=" * 70)
    print("STAGE 3: SUMMARIZATION (Gemini)")
    print("=" * 70)
    print()

    # Mark filtered as scraped (use title as content since no real scraping)
    db.execute("""
        UPDATE articles
        SET pipeline_stage = 'scraped', content = title
        WHERE pipeline_stage = 'filtered'
    """)
    db.commit()

    summarizer = ArticleSummarizer(llm_client=summarization_client)

    cursor = db.execute("""
        SELECT id, title, url, content, source FROM articles
        WHERE pipeline_stage = 'scraped'
    """)
    articles = cursor.fetchall()

    print(f"Summarizing {len(articles)} articles...")

    summarized = 0
    summaries = []

    for article in articles:
        try:
            summary = await summarizer.summarize(
                title=article['title'],
                url=article['url'],
                content=article['content'],
                source=article['source'],
            )

            if summary:
                db.execute("""
                    UPDATE articles
                    SET pipeline_stage = 'summarized',
                        summary_title = ?,
                        summary = ?,
                        key_points = ?
                    WHERE id = ?
                """, (
                    summary.summary_title,
                    summary.summary,
                    "|".join(summary.key_points),
                    article['id'],
                ))
                db.commit()
                summaries.append(summary)
                summarized += 1
                print(f"  ✓ {summary.summary_title[:50]}...")

        except Exception as e:
            print(f"  ✗ Error: {e}")

    print()
    print(f"Summarized: {summarized}")
    print()

    # Show Gemini costs
    cursor = db.execute("""
        SELECT COUNT(*) as calls, COALESCE(SUM(cost), 0) as cost
        FROM api_calls WHERE run_id = ? AND model LIKE 'gemini:%'
    """, (run_id,))
    row = cursor.fetchone()
    print(f"Gemini Cost: ${row['cost']:.6f} ({row['calls']} calls)")
    print()

    # ===================================================================
    # FINAL COST BREAKDOWN
    # ===================================================================
    print("=" * 70)
    print("FINAL COST BREAKDOWN BY PROVIDER")
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
        WHERE run_id = ?
        GROUP BY provider
        ORDER BY total_cost DESC
    """, (run_id,))

    print(f"{'Provider':<15} {'Calls':>8} {'Input':>10} {'Output':>10} {'Cost':>12}")
    print("-" * 60)

    total_cost = 0.0
    for row in cursor.fetchall():
        total_cost += row['total_cost']
        print(f"{row['provider']:<15} {row['calls']:>8} {row['input_tokens']:>10,} {row['output_tokens']:>10,} ${row['total_cost']:>11.6f}")

    print("-" * 60)
    print(f"{'TOTAL':<15} {' ':>8} {' ':>10} {' ':>10} ${total_cost:>11.6f}")
    print()

    # Cost comparison
    openai_equivalent = total_cost * 15  # Rough estimate
    print("Cost Comparison:")
    print(f"  Multi-Provider (DeepSeek + Gemini): ${total_cost:.6f}")
    print(f"  OpenAI Only (estimated):            ${openai_equivalent:.6f}")
    print(f"  Estimated Savings:                  {((openai_equivalent - total_cost) / openai_equivalent * 100):.0f}%")
    print()

    # Show summaries
    if summaries:
        print("=" * 70)
        print("SAMPLE SUMMARIES")
        print("=" * 70)
        print()

        for i, summary in enumerate(summaries[:2], 1):
            print(f"{i}. {summary.summary_title}")
            print(f"   {summary.summary[:200]}...")
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
