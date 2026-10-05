# Copyright (c) 2026, !! and contributors
# For license information, please see license.txt

import frappe

from ai_engine.llm_api_presets import get_api_starter_presets


def after_install():
	seed_llm_api_providers()


def after_migrate():
	seed_llm_api_providers()


def seed_llm_api_providers(merge_missing=True):
	"""Populate AI Engine Settings LLM API Providers from starter presets."""
	if not frappe.db.exists("DocType", "AI Engine Settings"):
		return

	settings = frappe.get_single("AI Engine Settings")
	settings.connection_type = settings.connection_type or "Remote API"

	existing = {row.provider_name for row in settings.llm_apis or []}
	presets = get_api_starter_presets()
	added = 0
	has_default = any(row.is_default and row.enabled for row in settings.llm_apis or [])

	for preset in presets:
		if merge_missing and preset["provider_name"] in existing:
			continue

		row = settings.append("llm_apis", {})
		row.provider_name = preset["provider_name"]
		row.api_tier = preset["api_tier"]
		row.api_base_url = preset["api_base_url"]
		row.text_model = preset["text_model"]
		row.vision_model = preset["vision_model"]
		row.notes = preset.get("notes") or ""
		row.extra_headers = preset.get("extra_headers") or ""
		row.enabled = 1
		row.is_default = 0

		if preset.get("is_default") and not has_default:
			row.is_default = 1
			has_default = True

		added += 1

	if not has_default and settings.llm_apis:
		for row in settings.llm_apis:
			if row.enabled:
				row.is_default = 1
				has_default = True
				break

	if added:
		settings.flags.ignore_validate = True
		settings.save(ignore_permissions=True)
		frappe.db.commit()
