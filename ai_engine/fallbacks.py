# Copyright (c) 2026, !! and contributors
# For license information, please see license.txt

"""Per-provider fallback chain for LLM calls.

Each row of AI Engine Settings -> LLM APIs can name:
  * ``fallback_model``    another model on the same provider, and
  * ``fallback_provider`` the Provider Name of another enabled row.

The chain starts at the Default row: its text model, its fallback model, then the same
for the fallback provider, and so on. Callers try the steps in order.
"""

import frappe

from ai_engine.llm_client import _get_settings_doc, _parse_extra_headers, _resolve_api_key, get_api_row

MAX_PROVIDERS = 4


def _to_active_api(row):
	"""Same shape as ``get_llm_settings().active_api``, so ``get_llm_client(api_row=...)`` accepts it."""
	return frappe._dict(
		name=row.name,
		provider_name=row.provider_name,
		api_tier=row.api_tier,
		api_base_url=row.api_base_url,
		text_model=row.text_model,
		vision_model=row.vision_model,
		embedding_model=row.embedding_model or "text-embedding-3-small",
		api_key=_resolve_api_key(row),
		extra_headers=_parse_extra_headers(row.extra_headers),
	)


def get_fallback_chain(model: str | None = None, settings_doc=None) -> list:
	"""Ordered attempts as ``[{api, model, provider}, ...]``; empty if Remote API isn't in use.

	``model`` overrides the first provider's text model only. Fallback rows without an API
	key are skipped, and a provider is never visited twice.
	"""
	settings_doc = settings_doc or _get_settings_doc()
	if not settings_doc or (settings_doc.connection_type or "Remote API") != "Remote API":
		return []

	row = get_api_row(settings_doc)
	if not row:
		return []

	by_name = {r.provider_name: r for r in settings_doc.llm_apis if r.enabled}
	chain, seen = [], set()
	while row and row.name not in seen and len(seen) < MAX_PROVIDERS:
		seen.add(row.name)
		if chain and not row.api_key:
			row = by_name.get((row.get("fallback_provider") or "").strip())
			continue

		api = _to_active_api(row)
		models = []
		for candidate in ((model if not chain else None) or row.text_model, row.get("fallback_model")):
			candidate = (candidate or "").strip()
			if candidate and candidate not in models:
				models.append(candidate)
		for candidate in models:
			chain.append(frappe._dict(api=api, model=candidate, provider=row.provider_name))
		row = by_name.get((row.get("fallback_provider") or "").strip())
	return chain


def validate_fallbacks(rows) -> None:
	"""Raise if a fallback provider doesn't exist, points at itself, or forms a loop."""
	by_name = {r.provider_name: r for r in rows if r.enabled}
	for row in rows:
		target = (row.get("fallback_provider") or "").strip()
		if not target:
			continue
		if target == row.provider_name:
			frappe.throw(f"{row.provider_name}: a provider can't be its own fallback.")
		if target not in by_name:
			frappe.throw(f"{row.provider_name}: fallback provider '{target}' isn't an enabled row in this table.")

		seen, current = {row.provider_name}, target
		while current:
			if current in seen:
				frappe.throw(f"{row.provider_name}: fallback providers form a loop through '{current}'.")
			seen.add(current)
			current = (by_name[current].get("fallback_provider") or "").strip()
			if current and current not in by_name:
				break
