# Copyright (c) 2026, !! and contributors
# For license information, please see license.txt

import json
import re
from typing import Protocol

import frappe
import requests


def _store_chat_usage(data: dict):
	frappe.local.ai_engine_last_chat_usage = _extract_usage_from_response(data or {})


def _extract_usage_from_response(data: dict) -> dict:
	raw = data.get("usage") or {}
	if raw:
		prompt_tokens = int(raw.get("prompt_tokens") or 0)
		completion_tokens = int(raw.get("completion_tokens") or 0)
		total_tokens = int(raw.get("total_tokens") or 0)
		if not total_tokens:
			total_tokens = prompt_tokens + completion_tokens
		return {
			"prompt_tokens": prompt_tokens,
			"completion_tokens": completion_tokens,
			"total_tokens": total_tokens,
		}

	prompt_tokens = int(data.get("prompt_eval_count") or 0)
	completion_tokens = int(data.get("eval_count") or 0)
	if prompt_tokens or completion_tokens:
		return {
			"prompt_tokens": prompt_tokens,
			"completion_tokens": completion_tokens,
			"total_tokens": prompt_tokens + completion_tokens,
		}

	return {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}


def get_last_chat_usage() -> dict:
	return getattr(frappe.local, "ai_engine_last_chat_usage", None) or {
		"prompt_tokens": 0,
		"completion_tokens": 0,
		"total_tokens": 0,
	}


_QUOTA_ERROR_CODES = {"insufficient_quota", "billing_hard_limit_reached", "billing_not_active"}
AI_QUOTA_EXCEEDED_MESSAGE = (
	"The AI service has reached its usage budget, so this action can't be completed right now. "
	"Your work is saved. Please try again later or contact support."
)


class AIQuotaExceededError(frappe.ValidationError):
	"""Provider rejected the request because the account's budget/credit is used up."""


def _is_quota_error(response) -> bool:
	"""True when the provider refused the call for budget/credit reasons (not a rate limit)."""
	if response is None or response.status_code not in (400, 402, 403, 429):
		return False
	try:
		error = (response.json() or {}).get("error") or {}
	except ValueError:
		return False
	if not isinstance(error, dict):
		return False
	if error.get("code") in _QUOTA_ERROR_CODES or error.get("type") in _QUOTA_ERROR_CODES:
		return True
	message = str(error.get("message") or "").lower()
	return "exceeded your current quota" in message or "hard limit" in message


_QUOTA_ALERT_CACHE_KEY = "ai_engine_quota_alert_sent"
_QUOTA_ALERT_INTERVAL = 3600  # at most one alert per hour


def _alert_quota_exceeded() -> None:
	"""Tell System Managers a user just hit the provider's budget cap (throttled, never raises)."""
	try:
		# Atomic "first one wins" so concurrent workers don't each send an alert.
		key = frappe.cache.make_key(_QUOTA_ALERT_CACHE_KEY)
		if not frappe.cache.set(key, 1, nx=True, ex=_QUOTA_ALERT_INTERVAL):
			return

		from frappe.desk.doctype.notification_log.notification_log import enqueue_create_notification
		from frappe.utils.user import get_system_managers

		managers = get_system_managers(only_name=True)
		if not managers:
			return

		user = frappe.utils.escape_html(frappe.session.user or "unknown")
		subject = "AI budget cap reached: users are being blocked"
		enqueue_create_notification(
			managers,
			{
				"type": "Alert",
				"document_type": "AI Engine Settings",
				"document_name": "AI Engine Settings",
				"subject": subject,
				"from_user": "Administrator",
				"email_content": (
					f"<p>{subject}.</p>"
					f"<p>The AI provider rejected a request from <b>{user}</b> because the account's "
					"budget or credit is used up. AI features (paper generation, validation, "
					"embeddings) fail for everyone until the limit is raised or resets.</p>"
					"<p>Raise the monthly budget under OpenAI &rarr; Settings &rarr; Organization &rarr; Limits, "
					"or add credit. This alert is sent at most once per hour.</p>"
				),
			},
		)
	except Exception:
		frappe.log_error(title="AI budget alert failed", message=frappe.get_traceback())


def _raise_for_ai_error(response) -> None:
	"""Like response.raise_for_status(), but turns budget errors into a user-friendly message."""
	if _is_quota_error(response):
		_alert_quota_exceeded()
		frappe.throw(AI_QUOTA_EXCEEDED_MESSAGE, exc=AIQuotaExceededError, title="AI budget reached")
	response.raise_for_status()


class LLMClient(Protocol):
	def chat_json(self, system_prompt: str, user_prompt: str, model: str | None = None) -> dict: ...

	def vision_extract_text(self, images: list[dict], prompt: str | None = None) -> str: ...

	def test_connection(self) -> dict: ...


class OllamaClient:
	def __init__(
		self,
		base_url: str,
		model: str,
		vision_model: str,
		timeout: int = 120,
		embedding_model: str | None = None,
	):
		self.base_url = base_url.rstrip("/")
		self.model = model
		self.vision_model = vision_model
		self.timeout = timeout
		self.embedding_model = embedding_model or "nomic-embed-text"

	def list_models(self) -> list[str]:
		response = requests.get(f"{self.base_url}/api/tags", timeout=self.timeout)
		response.raise_for_status()
		data = response.json()
		return [m.get("name", "") for m in data.get("models", []) if m.get("name")]

	def test_connection(self) -> dict:
		models = self.list_models()
		return {
			"success": True,
			"provider": "Ollama",
			"message": f"Connected to Ollama. {len(models)} model(s) available.",
			"models": models[:20],
		}

	def chat_json(self, system_prompt: str, user_prompt: str, model: str | None = None) -> dict:
		content = self._chat(
			model=model or self.model,
			messages=[
				{"role": "system", "content": system_prompt},
				{"role": "user", "content": user_prompt},
			],
			json_mode=True,
		)
		return _parse_json_response(content)

	def vision_extract_text(self, images: list[dict], prompt: str | None = None) -> str:
		if not images:
			return ""

		user_prompt = prompt or _VISION_OCR_PROMPT
		images_b64 = [_image_data(image) for image in images]
		return self._chat(
			model=self.vision_model,
			messages=[{"role": "user", "content": user_prompt, "images": images_b64}],
			json_mode=False,
		)

	def _chat(self, model: str, messages: list[dict], json_mode: bool = False) -> str:
		payload = {"model": model, "messages": messages, "stream": False}
		if json_mode:
			payload["format"] = "json"

		response = requests.post(
			f"{self.base_url}/api/chat",
			json=payload,
			timeout=self.timeout,
		)
		_raise_for_ai_error(response)
		data = response.json()
		_store_chat_usage(data)
		return (data.get("message") or {}).get("content", "").strip()

	def embed(self, texts: list[str], model: str | None = None) -> list[list[float]]:
		if not texts:
			return []
		embedding_model = model or self.embedding_model
		if not embedding_model:
			frappe.throw("No Ollama embedding model configured in AI Engine Settings.")

		vectors: list[list[float]] = []
		for text in texts:
			response = requests.post(
				f"{self.base_url}/api/embeddings",
				json={"model": embedding_model, "prompt": text},
				timeout=self.timeout,
			)
			response.raise_for_status()
			data = response.json()
			vector = data.get("embedding")
			if not isinstance(vector, list):
				frappe.throw("Ollama embeddings response missing embedding vector.")
			vectors.append(vector)
		return vectors


from ai_engine.llm_api_presets import API_STARTER_PRESETS, get_api_starter_presets


class OpenAICompatibleClient:
	"""Remote LLM via OpenAI-compatible API (OpenAI, Groq, OpenRouter, Azure, etc.)."""

	def __init__(
		self,
		api_base_url: str,
		api_key: str,
		model: str,
		vision_model: str,
		timeout: int = 120,
		extra_headers: dict | None = None,
		provider_label: str = "Remote API",
		embedding_model: str | None = None,
	):
		self.api_base_url = api_base_url.rstrip("/")
		self.api_key = api_key
		self.model = model
		self.vision_model = vision_model
		self.timeout = timeout
		self.extra_headers = extra_headers or {}
		self.provider_label = provider_label
		self.embedding_model = embedding_model or "text-embedding-3-small"

	def test_connection(self) -> dict:
		content = self._chat_completion(
			model=self.model,
			messages=[{"role": "user", "content": "Reply with the word OK."}],
			json_mode=False,
			max_tokens=10,
		)
		return {
			"success": True,
			"provider": self.provider_label,
			"message": f"Connected to remote LLM. Model {self.model} responded: {content[:50]}",
			"models": [self.model, self.vision_model],
		}

	def chat_json(self, system_prompt: str, user_prompt: str, model: str | None = None) -> dict:
		content = self._chat_completion(
			model=model or self.model,
			messages=[
				{"role": "system", "content": system_prompt},
				{"role": "user", "content": user_prompt},
			],
			json_mode=True,
		)
		return _parse_json_response(content)

	def vision_extract_text(self, images: list[dict], prompt: str | None = None) -> str:
		if not images:
			return ""

		user_prompt = prompt or _VISION_OCR_PROMPT
		content_parts: list[dict] = [{"type": "text", "text": user_prompt}]
		for image in images[:5]:
			content_parts.append(
				{
					"type": "image_url",
					"image_url": {"url": _image_data_url(image)},
				}
			)

		return self._chat_completion(
			model=self.vision_model,
			messages=[{"role": "user", "content": content_parts}],
			json_mode=False,
		)

	def _chat_completion(
		self,
		model: str,
		messages: list[dict],
		json_mode: bool = False,
		max_tokens: int | None = None,
	) -> str:
		headers = {
			"Authorization": f"Bearer {self.api_key}",
			"Content-Type": "application/json",
			**self.extra_headers,
		}
		payload: dict = {"model": model, "messages": messages}
		if json_mode:
			payload["response_format"] = {"type": "json_object"}
		if max_tokens is not None:
			payload["max_tokens"] = max_tokens
		# Callers may attach extra request fields (e.g. an anonymous per-user id) for this call.
		payload.update(getattr(frappe.local, "ai_engine_payload_extras", None) or {})

		response = requests.post(
			f"{self.api_base_url}/chat/completions",
			headers=headers,
			json=payload,
			timeout=self.timeout,
		)
		_raise_for_ai_error(response)
		data = response.json()
		_store_chat_usage(data)
		return (data.get("choices") or [{}])[0].get("message", {}).get("content", "").strip()

	def embed(self, texts: list[str], model: str | None = None) -> list[list[float]]:
		if not texts:
			return []

		embedding_model = model or self.embedding_model
		if not embedding_model:
			frappe.throw(
				f"No embedding model configured for {self.provider_label}. "
				"Set Embedding Model on the LLM API row in AI Engine Settings."
			)

		headers = {
			"Authorization": f"Bearer {self.api_key}",
			"Content-Type": "application/json",
			**self.extra_headers,
		}
		payload = {"model": embedding_model, "input": texts}
		response = requests.post(
			f"{self.api_base_url}/embeddings",
			headers=headers,
			json=payload,
			timeout=self.timeout,
		)
		try:
			_raise_for_ai_error(response)
		except requests.HTTPError as exc:
			status = exc.response.status_code if exc.response is not None else None
			if status in (404, 405):
				frappe.throw(
					f"{self.provider_label} does not appear to support /embeddings "
					f"(HTTP {status}). Choose a provider with embeddings support "
					"or set a compatible Embedding Model."
				)
			raise

		data = response.json()
		items = data.get("data") or []
		if not items:
			frappe.throw(f"{self.provider_label} returned no embedding vectors.")

		# Preserve input order when providers include an index field.
		sorted_items = sorted(items, key=lambda row: int(row.get("index") or 0))
		vectors = [row.get("embedding") for row in sorted_items]
		if any(not isinstance(v, list) for v in vectors):
			frappe.throw(f"{self.provider_label} returned invalid embedding vectors.")
		return vectors


def _image_data(image: dict | str) -> str:
	if isinstance(image, dict):
		return image.get("data") or ""
	return image


def _image_data_url(image: dict | str) -> str:
	if isinstance(image, dict):
		mime = image.get("mime") or "image/png"
		return f"data:{mime};base64,{image.get('data', '')}"
	return f"data:image/png;base64,{image}"


_VISION_OCR_PROMPT = (
	"Extract all readable text from this document image. "
	"Preserve dates, names, reference numbers, and other key details. "
	"Return plain text only, no commentary."
)


def _parse_extra_headers(raw_value: str | None) -> dict:
	if not raw_value:
		return {}
	try:
		parsed = json.loads(raw_value)
	except json.JSONDecodeError:
		frappe.log_error(
			title="AI Engine invalid extra_headers JSON",
			message=raw_value,
		)
		return {}
	return parsed if isinstance(parsed, dict) else {}


def _get_settings_doc():
	if not frappe.db.exists("DocType", "AI Engine Settings"):
		return None
	return frappe.get_single("AI Engine Settings")


def _resolve_api_key(row) -> str:
	if not row.get("api_key"):
		return ""
	password = row.get_password("api_key", raise_exception=False)
	return password or ""


def get_api_row(settings_doc, row_name: str | None = None):
	rows = [row for row in settings_doc.llm_apis if row.enabled]
	if not rows:
		return None

	if row_name:
		for row in rows:
			if row.name == row_name:
				return row
		return None

	for row in rows:
		if row.is_default:
			return row

	return rows[0]


def get_embedding_api_row(settings_doc, row_name: str | None = None):
	rows = [row for row in (settings_doc.embedding_apis or []) if row.enabled]
	if not rows:
		return None

	if row_name:
		for row in rows:
			if row.name == row_name:
				return row
		return None

	for row in rows:
		if row.is_default:
			return row

	return rows[0]


def get_llm_settings():
	defaults = frappe._dict(
		enable_llm_analysis=1,
		connection_type="Remote API",
		request_timeout=120,
		ollama_base_url="http://127.0.0.1:11434",
		ollama_text_model="llama3.2",
		ollama_vision_model="llama3.2",
		ollama_embedding_model="nomic-embed-text",
		active_api=None,
		active_embedding_api=None,
	)

	settings_doc = _get_settings_doc()
	if not settings_doc:
		return defaults

	for key in (
		"enable_llm_analysis",
		"connection_type",
		"request_timeout",
		"ollama_base_url",
		"ollama_text_model",
		"ollama_vision_model",
		"ollama_embedding_model",
	):
		value = settings_doc.get(key)
		if value not in (None, ""):
			defaults[key] = value

	active_row = get_api_row(settings_doc)
	if active_row:
		defaults.active_api = frappe._dict(
			name=active_row.name,
			provider_name=active_row.provider_name,
			api_tier=active_row.api_tier,
			api_base_url=active_row.api_base_url,
			text_model=active_row.text_model,
			vision_model=active_row.vision_model,
			embedding_model=active_row.embedding_model or "text-embedding-3-small",
			api_key=_resolve_api_key(active_row),
			extra_headers=_parse_extra_headers(active_row.extra_headers),
		)
	elif frappe.conf.get("openai_api_key"):
		defaults.active_api = frappe._dict(
			provider_name="OpenAI (site_config)",
			api_tier="Paid",
			api_base_url="https://api.openai.com/v1",
			text_model="gpt-4o-mini",
			vision_model="gpt-4o",
			embedding_model="text-embedding-3-small",
			api_key=frappe.conf.get("openai_api_key"),
			extra_headers={},
		)

	embedding_row = get_embedding_api_row(settings_doc)
	if embedding_row:
		defaults.active_embedding_api = frappe._dict(
			name=embedding_row.name,
			provider_name=embedding_row.provider_name,
			api_base_url=embedding_row.api_base_url,
			embedding_model=embedding_row.embedding_model or "text-embedding-3-small",
			api_key=_resolve_api_key(embedding_row),
			extra_headers=_parse_extra_headers(embedding_row.extra_headers),
		)
	elif defaults.active_api:
		# Fallback: seed from default LLM API embedding_model until Embedding APIs are configured.
		defaults.active_embedding_api = frappe._dict(
			name=defaults.active_api.get("name"),
			provider_name=defaults.active_api.provider_name,
			api_base_url=defaults.active_api.api_base_url,
			embedding_model=defaults.active_api.embedding_model or "text-embedding-3-small",
			api_key=defaults.active_api.api_key,
			extra_headers=defaults.active_api.extra_headers or {},
		)
	elif frappe.conf.get("openai_api_key"):
		defaults.active_embedding_api = frappe._dict(
			provider_name="OpenAI (site_config)",
			api_base_url="https://api.openai.com/v1",
			embedding_model="text-embedding-3-small",
			api_key=frappe.conf.get("openai_api_key"),
			extra_headers={},
		)

	return defaults


def get_llm_client(settings=None, api_row=None):
	if settings is None:
		settings = get_llm_settings()

	timeout = int(settings.request_timeout or 120)
	connection_type = settings.connection_type or "Remote API"

	if connection_type == "Ollama (Local)":
		return OllamaClient(
			base_url=settings.ollama_base_url,
			model=settings.ollama_text_model,
			vision_model=settings.ollama_vision_model,
			timeout=timeout,
			embedding_model=settings.ollama_embedding_model,
		)

	active_api = api_row or settings.active_api
	if not active_api:
		frappe.throw(
			"No enabled LLM API configured. Add at least one API in AI Engine Settings "
			"and mark one as Default."
		)

	if not active_api.api_key:
		frappe.throw(
			f"API Key is required for {active_api.provider_name}. "
			"Set it on the LLM APIs child table in AI Engine Settings."
		)

	tier_label = getattr(active_api, "api_tier", None) or "Remote"
	provider_label = f"{active_api.provider_name} ({tier_label})"

	return OpenAICompatibleClient(
		api_base_url=active_api.api_base_url,
		api_key=active_api.api_key,
		model=getattr(active_api, "text_model", None) or "gpt-4o-mini",
		vision_model=getattr(active_api, "vision_model", None) or "gpt-4o",
		timeout=timeout,
		extra_headers=active_api.extra_headers or {},
		provider_label=provider_label,
		embedding_model=getattr(active_api, "embedding_model", None) or "text-embedding-3-small",
	)


def get_embedding_client(settings=None, api_row=None):
	"""Return a client for .embed() using the Default Embedding API (cloud) or Ollama."""
	if settings is None:
		settings = get_llm_settings()

	timeout = int(settings.request_timeout or 120)
	connection_type = settings.connection_type or "Remote API"

	if connection_type == "Ollama (Local)":
		return OllamaClient(
			base_url=settings.ollama_base_url,
			model=settings.ollama_text_model,
			vision_model=settings.ollama_vision_model,
			timeout=timeout,
			embedding_model=settings.ollama_embedding_model,
		)

	active_embedding = api_row or settings.active_embedding_api
	if not active_embedding:
		frappe.throw(
			"No enabled Embedding API configured. Add at least one row under "
			"Cloud Embeddings in AI Engine Settings and mark one as Default."
		)

	if not active_embedding.api_key:
		frappe.throw(
			f"API Key is required for embedding provider {active_embedding.provider_name}. "
			"Set it on the Embedding APIs table in AI Engine Settings."
		)

	provider_label = f"{active_embedding.provider_name} (Embeddings)"
	return OpenAICompatibleClient(
		api_base_url=active_embedding.api_base_url,
		api_key=active_embedding.api_key,
		model=getattr(active_embedding, "text_model", None) or "gpt-4o-mini",
		vision_model=getattr(active_embedding, "vision_model", None) or "gpt-4o",
		timeout=timeout,
		extra_headers=active_embedding.extra_headers or {},
		provider_label=provider_label,
		embedding_model=active_embedding.embedding_model or "text-embedding-3-small",
	)


def is_llm_enabled() -> bool:
	settings = get_llm_settings()
	return bool(settings.enable_llm_analysis)


def _parse_json_response(content: str) -> dict:
	content = content.strip()
	if not content:
		return {}

	try:
		return json.loads(content)
	except json.JSONDecodeError:
		pass

	match = re.search(r"\{.*\}", content, re.DOTALL)
	if match:
		try:
			return json.loads(match.group())
		except json.JSONDecodeError:
			pass

	frappe.log_error(title="AI Engine JSON parse error", message=content)
	return {}
