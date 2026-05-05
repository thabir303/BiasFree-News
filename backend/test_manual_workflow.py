"""
Test script for manual bias analysis workflow.
Verifies scraping-only and manual analysis functionality.
"""

import asyncio
import requests
import json
from datetime import date, datetime


BASE_URL = "http://localhost:8000"


def test_api_call(method, endpoint, data=None, params=None):
    """Helper function for API calls."""
    url = f"{BASE_URL}{endpoint}"
    
    try:
        if method == "GET":
            response = requests.get(url, params=params)
        elif method == "POST":
            response = requests.post(url, json=data, params=params)
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"❌ Error {response.status_code}: {response.text}")
            return None
    except Exception as e:
        print(f"❌ Request failed: {str(e)}")
        return None


async def test_manual_workflow():
    """Test the complete manual processing workflow."""
    print("🧪 Testing Manual Bias Analysis Workflow")
    print("=" * 50)
    
    # Test 1: Manual scraping (no processing)
    print("\n1️⃣ Testing Manual Scraping (No Processing)")
    print("-" * 30)
    
    scrape_result = test_api_call(
        "POST",
        "/api/manual/scrape-only",
        params={
            "newspapers": ["prothom_alo"],
            "start_date": str(date.today()),
            "end_date": str(date.today()),
            "max_articles": 5
        }
    )
    
    if scrape_result:
        print(f"✅ Scraping started: {scrape_result['message']}")
        print(f"📊 Processing mode: {scrape_result['processing_mode']}")
    else:
        print("❌ Scraping failed")
    
    # Wait a bit for scraping to complete
    await asyncio.sleep(3)
    
    # Test 2: Get unprocessed articles
    print("\n2️⃣ Getting Unprocessed Articles")
    print("-" * 30)
    
    unprocessed = test_api_call(
        "GET",
        "/api/manual/unprocessed-articles",
        params={"limit": 5}
    )
    
    if unprocessed and unprocessed['articles']:
        print(f"✅ Found {len(unprocessed['articles'])} unprocessed articles")
        
        # Pick the first article for testing
        test_article = unprocessed['articles'][0]
        article_id = test_article['id']
        print(f"📝 Testing with article: '{test_article['title'][:50]}...'")
        print(f"🔍 Article ID: {article_id}")
        
        # Test 3: Manual bias analysis (without TOON)
        print("\n3️⃣ Manual Bias Analysis (Original Format)")
        print("-" * 30)
        
        analysis_result = test_api_call(
            "POST",
            f"/api/manual/analyze-article/{article_id}",
            params={"use_toon_format": False}
        )
        
        if analysis_result:
            print(f"✅ Analysis complete")
            print(f"📊 Biased: {analysis_result['is_biased']}")
            print(f"📈 Bias Score: {analysis_result['bias_score']}/100")
            print(f"🎯 Confidence: {analysis_result['confidence']}")
            if analysis_result['biased_terms']:
                print(f"📝 Biased terms: {len(analysis_result['biased_terms'])} found")
        else:
            print("❌ Analysis failed")
        
        # Test 4: Manual bias analysis (with TOON)
        print("\n4️⃣ Manual Bias Analysis (TOON Format)")
        print("-" * 30)
        
        # Reset article for testing TOON format
        reset_result = test_api_call(
            "POST",
            f"/api/articles/{article_id}/reprocess"
        )
        
        if reset_result:
            print("✅ Article reset for TOON testing")
            
            toon_analysis_result = test_api_call(
                "POST",
                f"/api/manual/analyze-article/{article_id}",
                params={"use_toon_format": True}
            )
            
            if toon_analysis_result:
                print(f"✅ TOON analysis complete")
                print(f"📊 Biased: {toon_analysis_result['is_biased']}")
                print(f"📈 Bias Score: {toon_analysis_result['bias_score']}/100")
                print(f"🎯 Confidence: {toon_analysis_result['confidence']}")
            else:
                print("❌ TOON analysis failed")
        
        # Test 5: Debiasing (if biased)
        if analysis_result and analysis_result['is_biased']:
            print("\n5️⃣ Manual Debiasing")
            print("-" * 30)
            
            debias_result = test_api_call(
                "POST",
                f"/api/manual/debias-article/{article_id}"
            )
            
            if debias_result:
                print(f"✅ Debiasing complete")
                print(f"📊 Changes made: {debias_result['changes_made']}")
                print(f"📈 Bias reduction: {debias_result['bias_reduction_score']}%")
                
                if debias_result['changes_made'] > 0:
                    print(f"📝 Sample change: {debias_result['changes_made']} terms replaced")
            else:
                print("❌ Debiasing failed")
        
        # Test 6: Get article status
        print("\n6️⃣ Article Status Check")
        print("-" * 30)
        
        status_result = test_api_call(
            "GET",
            f"/api/articles/{article_id}"
        )
        
        if status_result:
            print(f"✅ Status retrieved")
            print(f"📊 Processed: {status_result['processed']}")
            print(f"🔍 Biased: {status_result['is_biased']}")
            print(f"📝 Has debiased content: {bool(status_result.get('debiased_content'))}")
            print(f"🎯 Has generated headlines: {bool(status_result.get('generated_headlines'))}")
        else:
            print("❌ Status check failed")
    
    else:
        print("❌ No unprocessed articles found")
    
    # Test 7: TOON format demo
    print("\n7️⃣ TOON Format Demo")
    print("-" * 30)
    
    toon_demo = test_api_call("GET", "/api/enhanced/toon-demo")
    
    if toon_demo:
        print(f"✅ TOON demo retrieved")
        print(f"💰 Token savings: {toon_demo['token_savings']['savings_percent']}%")
        print(f"📊 Efficiency: {toon_demo['efficiency_improvement']}")
        print(f"📄 Sample TOON format:")
        print(toon_demo['toon_format'][:200] + "...")
    else:
        print("❌ TOON demo failed")
    
    print("\n" + "=" * 50)
    print("🎉 Manual Workflow Test Complete!")
    print("=" * 50)


async def main():
    """Main test function."""
    print("🚀 Starting Manual Bias Analysis Workflow Test")
    print("Make sure the server is running on http://localhost:8000")
    
    # Check if server is running
    try:
        response = requests.get(f"{BASE_URL}/")
        if response.status_code == 200:
            print(f"✅ Server is running: {response.json()['name']}")
            await test_manual_workflow()
        else:
            print("❌ Server is not responding properly")
    except Exception as e:
        print(f"❌ Cannot connect to server: {str(e)}")
        print("Please start the server first with: uvicorn app.main:app --reload")


if __name__ == "__main__":
    asyncio.run(main())