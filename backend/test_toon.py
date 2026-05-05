"""
Test TOON formatter functionality
"""
import sys
sys.path.insert(0, '/home/bs01127/Desktop/SPL-3/bias_free/backend')

from app.utils.toon_formatter import toon_formatter, format_for_llm

# Test 1: Simple article formatting
print("=" * 60)
print("Test 1: Article Data in TOON Format")
print("=" * 60)

article = {
    "title": "রাজনৈতিক সংকট নিয়ে নতুন আলোচনা",
    "content": "সরকার এবং বিরোধী দলের মধ্যে আলোচনা শুরু হয়েছে। এই আলোচনা খুবই গুরুত্বপূর্ণ।",
    "source": "প্রথম আলো"
}

toon_output = toon_formatter.to_toon(article)
print("Original JSON-like structure:")
print(article)
print("\nTOON Format:")
print(toon_output)
print(f"\nOriginal size: ~{len(str(article))} chars")
print(f"TOON size: {len(toon_output)} chars")
print(f"Reduction: {100 * (1 - len(toon_output) / len(str(article))):.1f}%")

# Test 2: Biased terms list in TOON
print("\n" + "=" * 60)
print("Test 2: Biased Terms in TOON Format")
print("=" * 60)

biased_terms = [
    {
        "term": "জঙ্গি",
        "neutral_alternative": "সন্ত্রাসী",
        "reason": "আবেগপ্রবণ শব্দ",
        "severity": "high"
    },
    {
        "term": "দুর্নীতিবাজ",
        "neutral_alternative": "দুর্নীতির অভিযোগ রয়েছে",
        "reason": "অভিযোগমূলক ভাষা",
        "severity": "medium"
    }
]

toon_terms = toon_formatter.to_toon({"biased_terms": biased_terms})
print("TOON Format (Tabular):")
print(toon_terms)

# Test 3: Complete prompt with TOON
print("\n" + "=" * 60)
print("Test 3: Complete LLM Prompt with TOON")
print("=" * 60)

prompt = format_for_llm(
    data=article,
    instruction="Analyze this Bengali article for political bias.",
    output_format="JSON"
)
print(prompt)

# Test 4: Decode TOON back to Python
print("\n" + "=" * 60)
print("Test 4: Decode TOON back to Python")
print("=" * 60)

decoded = toon_formatter.from_toon(toon_output)
print("Decoded data:")
print(decoded)
print(f"\nDecoded matches original: {decoded == article}")

print("\n" + "=" * 60)
print("✅ All TOON tests completed!")
print("=" * 60)
