# Copyright (c) 2026, !! and contributors
# For license information, please see license.txt

import frappe
import requests
from frappe import _
from frappe.model.document import Document

from ai_engine.llm_api_presets import get_api_starter_presets as build_api_starter_presets
from ai_engine.llm_client import (
	OllamaClient,
	_get_settings_doc,
	_parse_extra_headers,
	get_api_row,
	get_llm_client,
)


def _resolve_api_key_from_row(row) -> str:
	if not row.get("api_key"):
		return ""
	password = row.get_password("api_key", raise_exception=False)
	return password or ""


class AIEngineSettings(Document):
	def validate(self):
		if self.connection_type != "Remote API":
			return

		enabled_rows = [row for row in self.llm_apis if row.enabled]
		if not enabled_rows:
			frappe.throw(_("Add at least one enabled LLM API provider."))

		default_rows = [row for row in enabled_rows if row.is_default]
		if len(default_rows) != 1:
			frappe.throw(_("Mark exactly one enabled LLM API as Default."))

		from ai_engine.fallbacks import validate_fallbacks

		validate_fallbacks(self.llm_apis)

		embedding_rows = [row for row in (self.embedding_apis or []) if row.enabled]
		if embedding_rows:
			default_embeddings = [row for row in embedding_rows if row.is_default]
			if len(default_embeddings) != 1:
				frappe.throw(_("Mark exactly one enabled Embedding API as Default."))


def _is_masked_password(value: str | None) -> bool:
	return bool(value) and set(value) == {"*"}


def _build_api_row_dict(row, api_key_override: str | None = None):
	if api_key_override and not _is_masked_password(api_key_override):
		api_key = api_key_override
	else:
		api_key = _resolve_api_key_from_row(row)
	return frappe._dict(
		name=row.name,
		provider_name=row.provider_name,
		api_tier=row.api_tier,
		api_base_url=row.api_base_url,
		text_model=row.text_model,
		vision_model=row.vision_model,
		embedding_model=row.embedding_model or "text-embedding-3-small",
		api_key=api_key,
		extra_headers=_parse_extra_headers(row.extra_headers),
	)


@frappe.whitelist()
def get_api_starter_presets():
	"""Return starter rows for the LLM APIs child table."""
	return build_api_starter_presets()


@frappe.whitelist()
def test_llm_connection(api_row_name: str | None = None, api_key: str | None = None):
	"""Test connectivity to a configured LLM API row or the default provider."""
	settings_doc = _get_settings_doc()
	if not settings_doc:
		frappe.throw(_("AI Engine Settings not found."))

	if settings_doc.connection_type == "Ollama (Local)":
		client = get_llm_client()
		try:
			return client.test_connection()
		except requests.exceptions.Timeout:
			frappe.throw(
				_(
					"Ollama did not respond within {0}s at {1}. "
					"Confirm the SSH tunnel is up and that curl {1}/api/tags works on this host."
				).format(client.timeout, client.base_url)
			)
		except requests.exceptions.ConnectionError:
			frappe.throw(
				_(
					"Could not connect to Ollama at {0}. "
					"Confirm Ollama is running and the tunnel/port is listening."
				).format(client.base_url)
			)

	row = get_api_row(settings_doc, api_row_name)
	if not row:
		frappe.throw(_("No enabled LLM API row found to test."))

	api_row = _build_api_row_dict(row, api_key)
	client = get_llm_client(api_row=api_row)
	try:
		return client.test_connection()
	except requests.HTTPError as exc:
		status = exc.response.status_code if exc.response is not None else None
		if status == 401:
			frappe.throw(
				_(
					"Authentication failed (401). Verify the API key and API Base URL "
					"for {0}, then save settings before testing."
				).format(row.provider_name)
			)
		if status == 404:
			frappe.throw(_("API endpoint not found (404). Check the API Base URL for {0}.").format(row.provider_name))
		raise


@frappe.whitelist()
def test_ollama_embedding(
	ollama_base_url: str | None = None,
	ollama_embedding_model: str | None = None,
):
	"""Probe local Ollama with POST /api/embeddings using the selected embedding model."""
	settings_doc = _get_settings_doc()
	if not settings_doc:
		frappe.throw(_("AI Engine Settings not found."))

	base_url = (ollama_base_url or settings_doc.ollama_base_url or "").strip()
	model = (ollama_embedding_model or settings_doc.ollama_embedding_model or "").strip()
	timeout = int(settings_doc.request_timeout or 120)

	if not base_url:
		frappe.throw(_("Set Ollama Base URL before testing embeddings."))
	if not model:
		frappe.throw(_("Select an Embedding Model before testing."))

	client = OllamaClient(
		base_url=base_url,
		model=settings_doc.ollama_text_model or "llama3.2",
		vision_model=settings_doc.ollama_vision_model or "llama3.2",
		timeout=timeout,
		embedding_model=model,
	)

	try:
		vectors = client.embed(["ping"])
	except requests.exceptions.Timeout:
		frappe.throw(
			_(
				"Ollama embedding timed out after {0}s at {1} (model {2}). "
				"Confirm the SSH tunnel is up and that the model is pulled "
				"(ollama pull {2})."
			).format(timeout, client.base_url, model)
		)
	except requests.exceptions.ConnectionError:
		frappe.throw(
			_(
				"Could not connect to Ollama at {0}. "
				"Confirm Ollama is running and the tunnel/port is listening."
			).format(client.base_url)
		)
	except requests.HTTPError as exc:
		status = exc.response.status_code if exc.response is not None else None
		detail = ""
		if exc.response is not None:
			try:
				detail = exc.response.text[:300]
			except Exception:
				detail = ""
		frappe.throw(
			_("Ollama embedding request failed (HTTP {0}) for model {1}. {2}").format(
				status or "?", model, detail
			)
		)

	if not vectors or not isinstance(vectors[0], list) or not vectors[0]:
		frappe.throw(_("Ollama returned an empty embedding vector for model {0}.").format(model))

	dimensions = len(vectors[0])
	return {
		"success": True,
		"provider": "Ollama",
		"model": model,
		"dimensions": dimensions,
		"message": _("Ollama embedding OK — model {0}, {1} dimensions.").format(model, dimensions),
	}
