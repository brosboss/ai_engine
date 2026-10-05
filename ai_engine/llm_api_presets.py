# Copyright (c) 2026, !! and contributors
# For license information, please see license.txt

"""Starter LLM API provider rows for AI Engine Settings.

All providers listed here use OpenAI-compatible chat/completions APIs supported by ai_engine.
"""

import json

OPENROUTER_HEADERS = json.dumps(
	{
		"HTTP-Referer": "https://ai-engine.local",
		"X-Title": "AI Engine",
	}
)


def get_api_starter_presets():
	"""Return a fresh list of provider preset dicts for the LLM APIs child table."""
	return [
		# --- Free tier & generous free credits ---
		{
			"provider_name": "Groq",
			"api_tier": "Free Tier",
			"api_base_url": "https://api.groq.com/openai/v1",
			"text_model": "llama-3.3-70b-versatile",
			"vision_model": "meta-llama/llama-4-scout-17b-16e-instruct",
			"notes": "Very fast free tier. Keys: console.groq.com/keys",
			"is_default": 1,
		},
		{
			"provider_name": "Google Gemini",
			"api_tier": "Free Tier",
			"api_base_url": "https://generativelanguage.googleapis.com/v1beta/openai",
			"text_model": "gemini-2.0-flash-lite",
			"vision_model": "gemini-2.0-flash",
			"notes": "Generous free tier with vision. Keys: aistudio.google.com/apikey",
		},
		{
			"provider_name": "OpenRouter (Free Models)",
			"api_tier": "Free Tier",
			"api_base_url": "https://openrouter.ai/api/v1",
			"text_model": "meta-llama/llama-3.3-70b-instruct:free",
			"vision_model": "google/gemma-3-12b-it:free",
			"extra_headers": OPENROUTER_HEADERS,
			"notes": "Many free models via :free suffix. Keys: openrouter.ai/keys",
		},
		{
			"provider_name": "Cerebras",
			"api_tier": "Free Tier",
			"api_base_url": "https://api.cerebras.ai/v1",
			"text_model": "llama-3.3-70b",
			"vision_model": "llama-3.3-70b",
			"notes": "Fast free text inference. Vision OCR may not work. Keys: cloud.cerebras.ai",
		},
		{
			"provider_name": "GitHub Models",
			"api_tier": "Free Tier",
			"api_base_url": "https://models.inference.ai.azure.com",
			"text_model": "gpt-4o-mini",
			"vision_model": "gpt-4o",
			"notes": "Free for GitHub users. Keys: github.com/settings/tokens (models scope)",
		},
		{
			"provider_name": "NVIDIA NIM",
			"api_tier": "Free Tier",
			"api_base_url": "https://integrate.api.nvidia.com/v1",
			"text_model": "meta/llama-3.3-70b-instruct",
			"vision_model": "meta/llama-3.2-90b-vision-instruct",
			"notes": "Free developer tier on NVIDIA NIM. Keys: build.nvidia.com",
		},
		{
			"provider_name": "Hugging Face Inference",
			"api_tier": "Free Tier",
			"api_base_url": "https://router.huggingface.co/v1",
			"text_model": "meta-llama/Llama-3.3-70B-Instruct",
			"vision_model": "meta-llama/Llama-3.2-90B-Vision-Instruct",
			"notes": "Free credits on HF Inference Providers. Keys: huggingface.co/settings/tokens",
		},
		{
			"provider_name": "SambaNova",
			"api_tier": "Free Tier",
			"api_base_url": "https://api.sambanova.ai/v1",
			"text_model": "Meta-Llama-3.3-70B-Instruct",
			"vision_model": "Meta-Llama-3.2-90B-Vision-Instruct",
			"notes": "Free trial credits available. Keys: cloud.sambanova.ai/apis",
		},
		{
			"provider_name": "Together AI",
			"api_tier": "Free Tier",
			"api_base_url": "https://api.together.xyz/v1",
			"text_model": "meta-llama/Llama-3.3-70B-Instruct-Turbo",
			"vision_model": "meta-llama/Llama-Vision-Free",
			"notes": "Includes free trial credits. Keys: api.together.xyz/settings/api-keys",
		},
		{
			"provider_name": "Mistral (Free)",
			"api_tier": "Free Tier",
			"api_base_url": "https://api.mistral.ai/v1",
			"text_model": "mistral-small-latest",
			"vision_model": "pixtral-12b-2409",
			"notes": "Limited free experimentation tier. Keys: console.mistral.ai/api-keys",
		},
		{
			"provider_name": "DeepSeek",
			"api_tier": "Free Tier",
			"api_base_url": "https://api.deepseek.com/v1",
			"text_model": "deepseek-chat",
			"vision_model": "deepseek-chat",
			"notes": "Low-cost with new-user credits; excellent for text. Keys: platform.deepseek.com",
		},
		{
			"provider_name": "Fireworks AI",
			"api_tier": "Free Tier",
			"api_base_url": "https://api.fireworks.ai/inference/v1",
			"text_model": "accounts/fireworks/models/llama-v3p3-70b-instruct",
			"vision_model": "accounts/fireworks/models/llama-v3p2-90b-vision-instruct",
			"notes": "Trial credits available. Keys: app.fireworks.ai/api-keys",
		},
		{
			"provider_name": "DeepInfra",
			"api_tier": "Free Tier",
			"api_base_url": "https://api.deepinfra.com/v1/openai",
			"text_model": "meta-llama/Llama-3.3-70B-Instruct",
			"vision_model": "meta-llama/Llama-3.2-90B-Vision-Instruct",
			"notes": "Pay-as-you-go with competitive pricing. Keys: deepinfra.com/dash/api_keys",
		},
		{
			"provider_name": "Cloudflare Workers AI",
			"api_tier": "Free Tier",
			"api_base_url": "https://api.cloudflare.com/client/v4/accounts/ACCOUNT_ID/ai/v1",
			"text_model": "@cf/meta/llama-3.3-70b-instruct-fp8-fast",
			"vision_model": "@cf/meta/llama-3.2-11b-vision-instruct",
			"notes": "Replace ACCOUNT_ID in URL. Free daily quota. Keys: dash.cloudflare.com",
		},
		# --- Paid / production APIs ---
		{
			"provider_name": "OpenAI",
			"api_tier": "Paid",
			"api_base_url": "https://api.openai.com/v1",
			"text_model": "gpt-4o-mini",
			"vision_model": "gpt-4o",
			"notes": "Industry standard paid API. Keys: platform.openai.com/api-keys",
		},
		{
			"provider_name": "OpenAI (GPT-4.1)",
			"api_tier": "Paid",
			"api_base_url": "https://api.openai.com/v1",
			"text_model": "gpt-4.1-mini",
			"vision_model": "gpt-4.1",
			"notes": "Newer GPT-4.1 family on the same OpenAI endpoint.",
		},
		{
			"provider_name": "Anthropic (via OpenRouter)",
			"api_tier": "Paid",
			"api_base_url": "https://openrouter.ai/api/v1",
			"text_model": "anthropic/claude-sonnet-4",
			"vision_model": "anthropic/claude-sonnet-4",
			"extra_headers": OPENROUTER_HEADERS,
			"notes": "Claude via OpenRouter. Keys: openrouter.ai/keys",
		},
		{
			"provider_name": "xAI (Grok)",
			"api_tier": "Paid",
			"api_base_url": "https://api.x.ai/v1",
			"text_model": "grok-2-latest",
			"vision_model": "grok-2-vision-latest",
			"notes": "xAI Grok models. Keys: console.x.ai",
		},
		{
			"provider_name": "Mistral (Paid)",
			"api_tier": "Paid",
			"api_base_url": "https://api.mistral.ai/v1",
			"text_model": "mistral-large-latest",
			"vision_model": "pixtral-large-latest",
			"notes": "Production Mistral models. Keys: console.mistral.ai/api-keys",
		},
		{
			"provider_name": "Together AI (Paid)",
			"api_tier": "Paid",
			"api_base_url": "https://api.together.xyz/v1",
			"text_model": "meta-llama/Llama-3.3-70B-Instruct-Turbo",
			"vision_model": "meta-llama/Llama-3.2-90B-Vision-Instruct",
			"notes": "Broad model catalog for production workloads.",
		},
		{
			"provider_name": "DeepSeek (Paid)",
			"api_tier": "Paid",
			"api_base_url": "https://api.deepseek.com/v1",
			"text_model": "deepseek-reasoner",
			"vision_model": "deepseek-chat",
			"notes": "Reasoning model for complex analysis tasks.",
		},
		{
			"provider_name": "Perplexity",
			"api_tier": "Paid",
			"api_base_url": "https://api.perplexity.ai",
			"text_model": "sonar",
			"vision_model": "sonar",
			"notes": "Search-augmented answers. Keys: perplexity.ai/settings/api",
		},
		{
			"provider_name": "Cohere",
			"api_tier": "Paid",
			"api_base_url": "https://api.cohere.com/compatibility/v1",
			"text_model": "command-r-plus-08-2024",
			"vision_model": "command-r-plus-08-2024",
			"notes": "OpenAI-compatible Cohere endpoint. Keys: dashboard.cohere.com/api-keys",
		},
		{
			"provider_name": "Fireworks AI (Paid)",
			"api_tier": "Paid",
			"api_base_url": "https://api.fireworks.ai/inference/v1",
			"text_model": "accounts/fireworks/models/llama-v3p3-70b-instruct",
			"vision_model": "accounts/fireworks/models/llama-v3p2-90b-vision-instruct",
			"notes": "Production inference on Fireworks.",
		},
		{
			"provider_name": "OpenRouter (Paid Models)",
			"api_tier": "Paid",
			"api_base_url": "https://openrouter.ai/api/v1",
			"text_model": "openai/gpt-4o-mini",
			"vision_model": "openai/gpt-4o",
			"extra_headers": OPENROUTER_HEADERS,
			"notes": "Route to paid models from many vendors via one API key.",
		},
		{
			"provider_name": "Azure OpenAI",
			"api_tier": "Paid",
			"api_base_url": "https://YOUR_RESOURCE.openai.azure.com/openai/deployments/YOUR_DEPLOYMENT",
			"text_model": "gpt-4o-mini",
			"vision_model": "gpt-4o",
			"notes": "Replace YOUR_RESOURCE and YOUR_DEPLOYMENT. Keys: Azure portal.",
		},
		{
			"provider_name": "Amazon Bedrock (OpenAI compat)",
			"api_tier": "Paid",
			"api_base_url": "https://bedrock-runtime.us-east-1.amazonaws.com/openai/v1",
			"text_model": "anthropic.claude-3-5-sonnet-20241022-v2:0",
			"vision_model": "anthropic.claude-3-5-sonnet-20241022-v2:0",
			"notes": "AWS Bedrock OpenAI-compatible route. Configure AWS auth/region as required.",
		},
		{
			"provider_name": "AI21 Labs",
			"api_tier": "Paid",
			"api_base_url": "https://api.ai21.com/studio/v1",
			"text_model": "jamba-1.5-large",
			"vision_model": "jamba-1.5-large",
			"notes": "AI21 Studio API. Keys: studio.ai21.com",
		},
		{
			"provider_name": "Lepton AI",
			"api_tier": "Paid",
			"api_base_url": "https://api.lepton.ai/v1",
			"text_model": "meta-llama/Meta-Llama-3.1-70B-Instruct",
			"vision_model": "meta-llama/Meta-Llama-3.1-70B-Instruct",
			"notes": "Hosted open models. Keys: dashboard.lepton.ai",
		},
	]


# Backwards-compatible module constant used across ai_engine.
API_STARTER_PRESETS = get_api_starter_presets()
