# Copyright (c) 2026, !! and contributors
# For license information, please see license.txt

import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from ai_engine import fallbacks


class Row(dict):
	"""Minimal stand-in for an AI Engine LLM API child row."""

	def __getattr__(self, key):
		return self.get(key)

	def get_password(self, field, raise_exception=False):
		return f"secret-{self.get('provider_name')}"


def row(name, default=0, enabled=1, key="x", **kw):
	return Row(name=name, provider_name=name, is_default=default, enabled=enabled, api_key=key,
		api_tier="Paid", api_base_url=f"https://{name}.test/v1", text_model=f"{name}-main",
		vision_model="v", embedding_model="e", extra_headers="", **kw)


def settings(*rows, connection_type="Remote API"):
	return SimpleNamespace(llm_apis=list(rows), connection_type=connection_type)


def chain_of(*rows, model=None):
	with patch.object(fallbacks, "_resolve_api_key", lambda r: r.get_password("api_key")), patch.object(
		fallbacks, "_parse_extra_headers", lambda v: {}
	):
		return [(s.provider, s.model) for s in fallbacks.get_fallback_chain(model, settings(*rows))]


class TestFallbackChain(unittest.TestCase):
	def test_no_fallbacks_is_a_single_step(self):
		self.assertEqual(chain_of(row("a", default=1)), [("a", "a-main")])

	def test_fallback_model_then_fallback_provider(self):
		rows = (
			row("a", default=1, fallback_model="a-lite", fallback_provider="b"),
			row("b", fallback_model="b-lite"),
		)
		self.assertEqual(chain_of(*rows), [("a", "a-main"), ("a", "a-lite"), ("b", "b-main"), ("b", "b-lite")])

	def test_model_override_applies_to_first_provider_only(self):
		rows = (row("a", default=1, fallback_provider="b"), row("b"))
		self.assertEqual(chain_of(*rows, model="custom"), [("a", "custom"), ("b", "b-main")])

	def test_duplicate_models_and_loops_are_ignored(self):
		rows = (
			row("a", default=1, fallback_model="a-main", fallback_provider="b"),
			row("b", fallback_provider="a"),
		)
		self.assertEqual(chain_of(*rows), [("a", "a-main"), ("b", "b-main")])

	def test_fallback_provider_without_key_or_disabled_is_skipped(self):
		rows = (
			row("a", default=1, fallback_provider="b"),
			row("b", key="", fallback_provider="c"),
			row("c"),
		)
		self.assertEqual(chain_of(*rows), [("a", "a-main"), ("c", "c-main")])
		rows = (row("a", default=1, fallback_provider="b"), row("b", enabled=0))
		self.assertEqual(chain_of(*rows), [("a", "a-main")])

	def test_non_remote_connection_has_no_chain(self):
		with patch.object(fallbacks, "_get_settings_doc", return_value=settings(row("a", default=1), connection_type="Ollama (Local)")):
			self.assertEqual(fallbacks.get_fallback_chain(), [])


class TestValidateFallbacks(unittest.TestCase):
	def _err(self, *rows):
		fake = MagicMock()
		fake.throw.side_effect = lambda msg, **kw: (_ for _ in ()).throw(Exception(msg))
		with patch.object(fallbacks, "frappe", fake):
			fallbacks.validate_fallbacks(list(rows))

	def test_valid_chain_passes(self):
		self._err(row("a", fallback_provider="b"), row("b"))

	def test_self_reference_unknown_and_loop_are_rejected(self):
		with self.assertRaisesRegex(Exception, "own fallback"):
			self._err(row("a", fallback_provider="a"))
		with self.assertRaisesRegex(Exception, "isn't an enabled row"):
			self._err(row("a", fallback_provider="nope"))
		with self.assertRaisesRegex(Exception, "loop"):
			self._err(row("a", fallback_provider="b"), row("b", fallback_provider="a"))


if __name__ == "__main__":
	unittest.main()
