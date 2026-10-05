# Copyright (c) 2026, !! and contributors
# For license information, please see license.txt

import frappe


def execute():
	"""Seed Cloud Embeddings table from the default LLM API row when empty."""
	if not frappe.db.exists("DocType", "AI Engine Settings"):
		return
	if not frappe.db.exists("DocType", "AI Engine Embedding API"):
		return

	settings = frappe.get_single("AI Engine Settings")
	if settings.connection_type != "Remote API":
		return
	if settings.embedding_apis:
		return

	active = None
	for row in settings.llm_apis or []:
		if row.enabled and row.is_default:
			active = row
			break
	if not active:
		enabled = [row for row in (settings.llm_apis or []) if row.enabled]
		active = enabled[0] if enabled else None
	if not active:
		return

	api_key = ""
	if active.get("api_key"):
		api_key = active.get_password("api_key", raise_exception=False) or ""

	settings.append(
		"embedding_apis",
		{
			"provider_name": f"{active.provider_name} Embeddings",
			"enabled": 1,
			"is_default": 1,
			"api_base_url": active.api_base_url,
			"embedding_model": active.embedding_model or "text-embedding-3-small",
			"api_key": api_key,
			"extra_headers": active.extra_headers or "",
			"notes": "Seeded from default LLM API row.",
		},
	)
	settings.save(ignore_permissions=True)
