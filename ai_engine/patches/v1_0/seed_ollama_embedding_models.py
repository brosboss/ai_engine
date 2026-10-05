# Copyright (c) 2026, !! and contributors
# For license information, please see license.txt

import frappe

MODELS = (
	{
		"model_name": "nomic-embed-text",
		"description": "Nomic Embed Text — general-purpose local embeddings via Ollama.",
	},
	{
		"model_name": "bge-m3",
		"description": "BGE-M3 — multilingual dense embeddings via Ollama.",
	},
)


def execute():
	if not frappe.db.exists("DocType", "Ollama Embedding Model"):
		return

	for entry in MODELS:
		if frappe.db.exists("Ollama Embedding Model", entry["model_name"]):
			continue
		doc = frappe.get_doc(
			{
				"doctype": "Ollama Embedding Model",
				"model_name": entry["model_name"],
				"description": entry["description"],
			}
		)
		doc.insert(ignore_permissions=True)
