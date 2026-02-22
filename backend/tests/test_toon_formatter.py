"""
Unit tests for app/utils/toon_formatter.py

Covers:
- ToonFormatter.to_toon / from_toon (round-trip)
- format_article_for_bias_detection
- format_articles_batch
- format_bias_result
- create_prompt_with_toon
- module-level format_for_llm helper
- singleton toon_formatter instance
"""
import os
os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ.setdefault("MAIL_USERNAME", "t@t.com")
os.environ.setdefault("MAIL_PASSWORD", "test")
os.environ.setdefault("MAIL_FROM", "t@t.com")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-at-least-32-characters-long!")

import pytest
from app.utils.toon_formatter import ToonFormatter, toon_formatter, format_for_llm


class TestToonFormatterInit:
    def test_default_delimiter(self):
        tf = ToonFormatter()
        assert tf.delimiter == ","

    def test_default_indent(self):
        tf = ToonFormatter()
        assert tf.indent == 2

    def test_custom_delimiter(self):
        tf = ToonFormatter(delimiter="|")
        assert tf.delimiter == "|"

    def test_custom_indent(self):
        tf = ToonFormatter(indent=4)
        assert tf.indent == 4


class TestToToonAndFromToon:
    def setup_method(self):
        self.tf = ToonFormatter()

    def test_round_trip_dict(self):
        data = {"key": "value", "number": 42}
        toon = self.tf.to_toon(data)
        result = self.tf.from_toon(toon)
        assert result == data

    def test_round_trip_list(self):
        data = [1, 2, 3]
        toon = self.tf.to_toon(data)
        result = self.tf.from_toon(toon)
        assert result == data

    def test_to_toon_returns_string(self):
        assert isinstance(self.tf.to_toon({"x": 1}), str)

    def test_nested_dict_round_trip(self):
        data = {"outer": {"inner": "value"}}
        result = self.tf.from_toon(self.tf.to_toon(data))
        assert result == data

    def test_empty_dict_round_trip(self):
        data = {}
        result = self.tf.from_toon(self.tf.to_toon(data))
        assert result == data

    def test_string_value_round_trip(self):
        data = {"text": "বাংলা সংবাদ"}
        result = self.tf.from_toon(self.tf.to_toon(data))
        assert result["text"] == "বাংলা সংবাদ"


class TestFormatArticleForBiasDetection:
    def setup_method(self):
        self.tf = ToonFormatter()

    def test_returns_string(self):
        article = {"title": "Test", "content": "Some content", "source": "prothom_alo"}
        result = self.tf.format_article_for_bias_detection(article)
        assert isinstance(result, str)

    def test_contains_title(self):
        article = {"title": "My Article", "content": "Content here", "source": "daily_star"}
        result = self.tf.format_article_for_bias_detection(article)
        assert "My Article" in result

    def test_contains_content(self):
        article = {"title": "T", "content": "Important content", "source": "jugantor"}
        result = self.tf.format_article_for_bias_detection(article)
        assert "Important content" in result

    def test_optional_author_included_when_present(self):
        article = {
            "title": "T", "content": "C", "source": "s",
            "author": "John Doe"
        }
        result = self.tf.format_article_for_bias_detection(article)
        assert "John Doe" in result

    def test_missing_optional_fields_do_not_crash(self):
        article = {}  # all fields missing
        result = self.tf.format_article_for_bias_detection(article)
        assert isinstance(result, str)

    def test_author_absent_when_not_provided(self):
        article = {"title": "T", "content": "C", "source": "s"}
        result = self.tf.format_article_for_bias_detection(article)
        # Should not include an "author" key since it wasn't provided
        assert "John" not in result


class TestFormatArticlesBatch:
    def setup_method(self):
        self.tf = ToonFormatter()

    def test_returns_string(self):
        articles = [{"title": "T1", "content": "C1", "source": "s1", "id": "1"}]
        result = self.tf.format_articles_batch(articles)
        assert isinstance(result, str)

    def test_empty_batch_returns_string(self):
        result = self.tf.format_articles_batch([])
        assert isinstance(result, str)

    def test_multiple_articles(self):
        articles = [
            {"id": "1", "title": "T1", "content": "C1 " * 100, "source": "s1"},
            {"id": "2", "title": "T2", "content": "C2 " * 100, "source": "s2"},
        ]
        result = self.tf.format_articles_batch(articles)
        assert isinstance(result, str)
        assert "T1" in result
        assert "T2" in result

    def test_content_truncated_to_500_chars(self):
        long_content = "x" * 1000
        articles = [{"id": "1", "title": "T", "content": long_content, "source": "s"}]
        result = self.tf.format_articles_batch(articles)
        # Encoded result should not contain 1000 x's worth of content
        assert "x" * 600 not in result


class TestFormatBiasResult:
    def setup_method(self):
        self.tf = ToonFormatter()

    def test_returns_string(self):
        result_data = {"is_biased": True, "bias_score": 70}
        result = self.tf.format_bias_result(result_data)
        assert isinstance(result, str)

    def test_contains_bias_score(self):
        result_data = {"is_biased": True, "bias_score": 70}
        result = self.tf.format_bias_result(result_data)
        assert "70" in result

    def test_empty_dict(self):
        assert isinstance(self.tf.format_bias_result({}), str)


class TestCreatePromptWithToon:
    def setup_method(self):
        self.tf = ToonFormatter()

    def test_returns_string(self):
        result = self.tf.create_prompt_with_toon("Do this:", {"key": "val"})
        assert isinstance(result, str)

    def test_instruction_in_prompt(self):
        result = self.tf.create_prompt_with_toon("Analyze bias:", {"key": "val"})
        assert "Analyze bias:" in result

    def test_default_output_format_is_json(self):
        result = self.tf.create_prompt_with_toon("Instruction", {"a": 1})
        assert "JSON" in result

    def test_custom_output_format(self):
        result = self.tf.create_prompt_with_toon("Instruction", {"a": 1}, output_format="YAML")
        assert "YAML" in result

    def test_code_block_wraps_toon_by_default(self):
        result = self.tf.create_prompt_with_toon("Instruct", {"x": 1})
        assert "```toon" in result

    def test_no_code_block_when_disabled(self):
        result = self.tf.create_prompt_with_toon("Instruct", {"x": 1}, use_code_block=False)
        assert "```toon" not in result

    def test_data_encoded_in_prompt(self):
        result = self.tf.create_prompt_with_toon("Instruct", {"headline": "Test Article"})
        assert "Test Article" in result


class TestSingletonAndModuleHelper:
    def test_singleton_is_toon_formatter_instance(self):
        assert isinstance(toon_formatter, ToonFormatter)

    def test_format_for_llm_returns_string(self):
        result = format_for_llm({"data": "value"}, "Analyze this.")
        assert isinstance(result, str)

    def test_format_for_llm_contains_instruction(self):
        result = format_for_llm({"x": 1}, "My instruction here")
        assert "My instruction here" in result

    def test_format_for_llm_custom_output_format(self):
        result = format_for_llm({}, "Inst", output_format="XML")
        assert "XML" in result
