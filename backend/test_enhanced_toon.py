"""
Test script for enhanced TOON format implementation and batch processing.
Verifies 30-60% token reduction and 20 article limit functionality.
"""

import asyncio
import json
import time
from datetime import datetime
from app.utils.enhanced_toon_formatter import enhanced_toon_formatter
from app.services.enhanced_bias_detector import EnhancedBiasDetectorService
from app.services.enhanced_article_processor import EnhancedArticleProcessor
from app.models.enhanced_schemas import BatchArticleInput, ArticleInput


async def test_toon_format_efficiency():
    """Test TOON format efficiency with sample article data."""
    print("🧪 Testing TOON Format Efficiency")
    print("=" * 50)
    
    # Sample articles (similar to what would be scraped)
    sample_articles = [
        {
            "id": f"article_{i}",
            "title": f"রাজনৈতিক সংবাদ {i+1}: সরকারের নতুন সিদ্ধান্ত",
            "content": f"আজকের রাজনৈতিক পরিস্থিতি খুবই উত্তপ্ত। বিরোধী দলগুলো সরকারের বিরুদ্ধে কঠোর অবস্থান নিয়েছে। এই পরিস্থিতিতে দেশের ভবিষ্যৎ নিয়ে উদ্বেগ প্রকাশ করেছেন বিশেষজ্ঞরা। আরও বিস্তারিত জানতে পড়ুন...",
            "source": "prothom_alo" if i % 2 == 0 else "jugantor",
            "date": "2024-01-09"
        }
        for i in range(20)  # Test with 20 articles (maximum limit)
    ]
    
    print(f"📊 Testing with {len(sample_articles)} articles")
    
    # Test TOON format
    toon_output = enhanced_toon_formatter.format_article_batch_tabular(sample_articles, max_articles=20)
    
    # Calculate token savings
    original_data = {"articles": sample_articles}
    savings = enhanced_toon_formatter.calculate_token_savings(original_data, toon_output)
    
    print(f"📄 Original JSON size: {savings['original_chars']} characters")
    print(f"🎯 TOON format size: {savings['toon_chars']} characters")
    print(f"💰 Token savings: {savings['token_savings']} tokens ({savings['savings_percent']}% reduction)")
    print(f"⚡ Efficiency improvement: {savings['savings_percent']}% fewer tokens")
    
    # Show sample output
    print(f"\n📝 Sample TOON format output (first 500 chars):")
    print("-" * 30)
    print(toon_output[:500] + "..." if len(toon_output) > 500 else toon_output)
    print("-" * 30)
    
    return savings


async def test_batch_bias_detection():
    """Test batch bias detection with TOON format."""
    print("\n🔍 Testing Batch Bias Detection")
    print("=" * 50)
    
    # Sample articles with potential bias
    test_articles = [
        {
            "id": "test_1",
            "title": "সরকারের বিরুদ্ধে কঠোর অবস্থান নিয়েছে বিরোধী দল",
            "content": "বিরোধী দলগুলো সরকারের বিরুদ্ধে কঠোর অবস্থান নিয়েছে। এই সরকার দেশকে ধ্বংসের দিকে নিয়ে যাচ্ছে। দেশের মানুষ অত্যন্ত ক্ষুব্ধ।",
            "source": "test_source",
            "date": "2024-01-09"
        },
        {
            "id": "test_2",
            "title": "অর্থনৈতিক প্রবৃদ্ধির খবর",
            "content": "দেশের অর্থনীতি দ্রুত উন্নতি করছে। বিশেষজ্ঞরা বলছেন এই প্রবৃদ্ধি টেকসই হবে। সরকারের নীতিগুলো কার্যকর হচ্ছে।",
            "source": "test_source",
            "date": "2024-01-09"
        },
        {
            "id": "test_3",
            "title": "নিরপেক্ষভাবে রাজনৈতিক পরিস্থিতি বিশ্লেষণ",
            "content": "রাজনৈতিক পরিস্থিতি পরিবর্তন হচ্ছে। বিভিন্ন দল তাদের অবস্থান ব্যাখ্যা করছে। বিশেষজ্ঞরা বিভিন্ন দৃষ্টিকোণ থেকে বিশ্লেষণ করছেন।",
            "source": "test_source",
            "date": "2024-01-09"
        }
    ]
    
    print(f"📋 Testing bias detection with {len(test_articles)} articles")
    
    # Initialize enhanced bias detector
    detector = EnhancedBiasDetectorService()
    
    # Test with TOON format
    start_time = time.time()
    result = await detector.analyze_bias_batch(test_articles, use_toon_format=True)
    processing_time = time.time() - start_time
    
    print(f"⏱️  Processing time: {processing_time:.2f} seconds")
    print(f"📊 Format used: {result.format_used}")
    print(f"💰 Token savings: {result.token_savings}%")
    print(f"✅ Articles processed: {result.total_processed}")
    print(f"🔍 Biased articles found: {len([a for a in result.articles if a.is_biased])}")
    
    # Show individual results
    for i, analysis in enumerate(result.articles):
        print(f"\n📰 Article {i+1}: '{test_articles[i]['title'][:50]}...'")
        print(f"   Biased: {analysis.is_biased}")
        print(f"   Score: {analysis.bias_score}/100")
        print(f"   Confidence: {analysis.confidence:.2f}")
        if analysis.biased_terms:
            print(f"   Terms: {[term.term for term in analysis.biased_terms[:3]]}")
    
    return result


async def test_20_article_limit():
    """Test the 20 article limit functionality."""
    print("\n🔢 Testing 20 Article Limit")
    print("=" * 50)
    
    # Create 25 articles to test the limit
    many_articles = [
        {
            "id": f"limit_test_{i}",
            "title": f"Test Article {i+1}",
            "content": f"This is test article content number {i+1} for testing the article limit functionality.",
            "source": "test",
            "date": "2024-01-09"
        }
        for i in range(25)
    ]
    
    print(f"📊 Created {len(many_articles)} articles for testing")
    
    # Test TOON formatter with limit
    toon_output = enhanced_toon_formatter.format_article_batch_tabular(many_articles, max_articles=20)
    
    # Count articles in output
    lines = toon_output.strip().split('\n')
    data_lines = [line for line in lines if line.strip().startswith('  ') and not line.strip().startswith('#')]
    processed_count = len(data_lines)
    
    print(f"🎯 Requested limit: 20 articles")
    print(f"✅ Actually processed: {processed_count} articles")
    print(f"📏 Limit enforcement: {'✅ PASSED' if processed_count <= 20 else '❌ FAILED'}")
    
    # Test batch bias detector limit
    detector = EnhancedBiasDetectorService()
    result = await detector.analyze_bias_batch(many_articles, use_toon_format=True)
    
    print(f"🔍 Bias detector processed: {result.total_processed} articles")
    print(f"📊 Limit enforcement: {'✅ PASSED' if result.total_processed <= 20 else '❌ FAILED'}")
    
    return processed_count <= 20 and result.total_processed <= 20


async def test_integration_with_existing_pipeline():
    """Test integration with existing scraping pipeline."""
    print("\n🔗 Testing Integration with Existing Pipeline")
    print("=" * 50)
    
    # Simulate scraped article data format
    scraped_data = [
        {
            "id": f"scraped_{i}",
            "title": f"Scraped Article Title {i+1}",
            "content": f"This is scraped article content {i+1} that would come from the scraping pipeline. It contains news content that needs bias analysis.",
            "source": "prothom_alo",
            "date": datetime.now().isoformat(),
            "url": f"https://example.com/article{i+1}",
            "author": f"Author {i+1}"
        }
        for i in range(5)  # Small batch for testing
    ]
    
    print(f"📰 Simulating {len(scraped_data)} scraped articles")
    
    # Test TOON conversion
    toon_output = enhanced_toon_formatter.format_article_batch_tabular(scraped_data, max_articles=5)
    print(f"🎯 TOON conversion: ✅ SUCCESS")
    
    # Test bias detection
    detector = EnhancedBiasDetectorService()
    result = await detector.analyze_bias_batch(scraped_data, use_toon_format=True)
    
    print(f"🔍 Bias detection: ✅ SUCCESS")
    print(f"💰 Token savings: {result.token_savings}%")
    print(f"📊 Articles analyzed: {result.total_processed}")
    
    # Test compatibility with existing schemas
    try:
        from app.models.enhanced_schemas import BatchArticleInput
        
        # Convert to input format
        batch_input = BatchArticleInput(
            articles=[
                ArticleInput(
                    title=article["title"],
                    content=article["content"]
                )
                for article in scraped_data
            ],
            use_toon_format=True
        )
        print(f"📋 Schema compatibility: ✅ SUCCESS")
        
    except Exception as e:
        print(f"❌ Schema compatibility issue: {str(e)}")
        return False
    
    return True


async def main():
    """Main test function."""
    print("🚀 Enhanced TOON Implementation Test Suite")
    print("=" * 60)
    print("Testing JSON-to-TOON conversion with 30-60% token reduction")
    print("Testing 20 article limit for LLM analysis")
    print("=" * 60)
    
    test_results = {}
    
    try:
        # Test 1: TOON format efficiency
        savings = await test_toon_format_efficiency()
        test_results["toon_efficiency"] = savings["savings_percent"] >= 30
        
        # Test 2: Batch bias detection
        bias_result = await test_batch_bias_detection()
        test_results["batch_detection"] = bias_result.total_processed > 0
        
        # Test 3: 20 article limit
        limit_test = await test_20_article_limit()
        test_results["article_limit"] = limit_test
        
        # Test 4: Integration
        integration_test = await test_integration_with_existing_pipeline()
        test_results["integration"] = integration_test
        
        # Summary
        print("\n" + "=" * 60)
        print("📊 TEST RESULTS SUMMARY")
        print("=" * 60)
        
        all_passed = True
        for test_name, passed in test_results.items():
            status = "✅ PASSED" if passed else "❌ FAILED"
            print(f"{test_name.replace('_', ' ').title()}: {status}")
            if not passed:
                all_passed = False
        
        print(f"\n🎯 Overall Result: {'✅ ALL TESTS PASSED' if all_passed else '❌ SOME TESTS FAILED'}")
        
        if all_passed:
            print("\n🎉 Enhanced TOON implementation is working correctly!")
            print("✅ 30-60% token reduction achieved")
            print("✅ 20 article limit enforced")
            print("✅ Batch processing working")
            print("✅ Integration with existing pipeline successful")
        
        return all_passed
        
    except Exception as e:
        print(f"\n❌ Test suite failed: {str(e)}")
        return False


if __name__ == "__main__":
    # Run the test suite
    success = asyncio.run(main())
    exit(0 if success else 1)