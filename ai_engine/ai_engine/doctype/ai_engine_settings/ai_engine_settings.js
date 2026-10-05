// Copyright (c) 2026, !! and contributors
// For license information, please see license.txt

frappe.ui.form.on("AI Engine Settings", {
	onload(frm) {
		render_setup_notes(frm);
	},

	refresh(frm) {
		render_setup_notes(frm);
		setup_api_grid(frm);

		frm.add_custom_button(__("Test Default API"), () => test_api_connection(frm));
		frm.add_custom_button(__("Test Ollama Embedding"), () => test_ollama_embedding(frm));
		if (frm.doc.connection_type === "Remote API") {
			frm.add_custom_button(__("Load Starter APIs"), () => load_starter_presets(frm), __("LLM APIs"));
			frm.add_custom_button(
				__("Load Starter Embeddings"),
				() => load_starter_embeddings(frm),
				__("Embeddings")
			);
		}
	},

	connection_type(frm) {
		render_setup_notes(frm);
	},
});

frappe.ui.form.on("AI Engine LLM API", {
	is_default(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		if (!row.is_default) {
			return;
		}

		(frm.doc.llm_apis || []).forEach((api_row) => {
			if (api_row.name !== row.name && api_row.is_default) {
				frappe.model.set_value(api_row.doctype, api_row.name, "is_default", 0);
			}
		});
	},

	form_render(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		if (!row || !frm.fields_dict.llm_apis?.grid) {
			return;
		}

		const grid_row = frm.fields_dict.llm_apis.grid.grid_rows_by_docname?.[cdn];
		if (!grid_row) {
			return;
		}

		const indicator = row.api_tier === "Paid" ? "orange" : "green";
		grid_row.columns.api_tier?.toggle_label(true);
		grid_row.columns.api_tier?.refresh(
			`<span class="indicator-pill ${indicator} filterable no-indicator-dot">${frappe.utils.escape_html(
				row.api_tier || ""
			)}</span>`
		);
	},
});

frappe.ui.form.on("AI Engine Embedding API", {
	is_default(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		if (!row.is_default) {
			return;
		}
		(frm.doc.embedding_apis || []).forEach((api_row) => {
			if (api_row.name !== row.name && api_row.is_default) {
				frappe.model.set_value(api_row.doctype, api_row.name, "is_default", 0);
			}
		});
	},
});

function setup_api_grid(frm) {
	if (!frm.fields_dict.llm_apis?.grid) {
		return;
	}

	frm.fields_dict.llm_apis.grid.wrapper.find(".grid-row").each(function () {
		const $row = $(this);
		const row_name = $row.attr("data-name");
		const row = (frm.doc.llm_apis || []).find((entry) => entry.name === row_name);
		if (!row) {
			return;
		}

		const indicator = row.api_tier === "Paid" ? "orange" : "green";
		$row.find('[data-fieldname="api_tier"]').html(
			`<span class="indicator-pill ${indicator} filterable no-indicator-dot">${frappe.utils.escape_html(
				row.api_tier || ""
			)}</span>`
		);
	});
}

function load_starter_presets(frm) {
	frappe.call({
		method: "ai_engine.ai_engine.doctype.ai_engine_settings.ai_engine_settings.get_api_starter_presets",
		callback(r) {
			const presets = r.message || [];
			const existing = new Set((frm.doc.llm_apis || []).map((row) => row.provider_name));
			let added = 0;

			presets.forEach((preset) => {
				if (existing.has(preset.provider_name)) {
					return;
				}
				const row = frm.add_child("llm_apis");
				Object.assign(row, {
					provider_name: preset.provider_name,
					api_tier: preset.api_tier,
					api_base_url: preset.api_base_url,
					text_model: preset.text_model,
					vision_model: preset.vision_model,
					notes: preset.notes || "",
					extra_headers: preset.extra_headers || "",
					enabled: 1,
					is_default: preset.is_default ? 1 : 0,
				});
				added += 1;
			});

			if (!added) {
				frappe.msgprint(__("Starter APIs are already loaded."));
				return;
			}

			ensure_single_default(frm);
			frm.refresh_field("llm_apis");
			render_setup_notes(frm);
			frappe.show_alert({
				message: __("Added {0} starter API provider(s). Enter API keys and save.", [added]),
				indicator: "green",
			});
		},
	});
}

function load_starter_embeddings(frm) {
	const presets = [
		{
			provider_name: "OpenAI Embeddings",
			api_base_url: "https://api.openai.com/v1",
			embedding_model: "text-embedding-3-small",
			notes: "Cloud embeddings for knowledge-source indexing.",
			is_default: 1,
		},
		{
			provider_name: "OpenRouter Embeddings",
			api_base_url: "https://openrouter.ai/api/v1",
			embedding_model: "openai/text-embedding-3-small",
			notes: "OpenRouter OpenAI-compatible embeddings.",
			is_default: 0,
		},
	];
	const existing = new Set((frm.doc.embedding_apis || []).map((row) => row.provider_name));
	let added = 0;
	presets.forEach((preset) => {
		if (existing.has(preset.provider_name)) {
			return;
		}
		const row = frm.add_child("embedding_apis");
		Object.assign(row, {
			provider_name: preset.provider_name,
			api_base_url: preset.api_base_url,
			embedding_model: preset.embedding_model,
			notes: preset.notes || "",
			enabled: 1,
			is_default: preset.is_default ? 1 : 0,
		});
		added += 1;
	});
	if (!added) {
		frappe.msgprint(__("Starter embedding providers are already loaded."));
		return;
	}
	ensure_single_embedding_default(frm);
	frm.refresh_field("embedding_apis");
	render_setup_notes(frm);
	frappe.show_alert({
		message: __("Added {0} embedding provider(s). Enter API keys and save.", [added]),
		indicator: "green",
	});
}

function ensure_single_default(frm) {
	const enabled_rows = (frm.doc.llm_apis || []).filter((row) => row.enabled);
	const defaults = enabled_rows.filter((row) => row.is_default);
	if (defaults.length === 1) {
		return;
	}
	if (defaults.length > 1) {
		defaults.slice(1).forEach((row) => {
			row.is_default = 0;
		});
		return;
	}
	if (enabled_rows.length) {
		enabled_rows[0].is_default = 1;
	}
}

function ensure_single_embedding_default(frm) {
	const enabled_rows = (frm.doc.embedding_apis || []).filter((row) => row.enabled);
	const defaults = enabled_rows.filter((row) => row.is_default);
	if (defaults.length === 1) {
		return;
	}
	if (defaults.length > 1) {
		defaults.slice(1).forEach((row) => {
			row.is_default = 0;
		});
		return;
	}
	if (enabled_rows.length) {
		enabled_rows[0].is_default = 1;
	}
}

function test_api_connection(frm) {
	if (frm.doc.connection_type === "Ollama (Local)") {
		return frappe.call({
			method: "ai_engine.ai_engine.doctype.ai_engine_settings.ai_engine_settings.test_llm_connection",
			freeze: true,
			freeze_message: __("Testing Ollama connection..."),
			callback(r) {
				show_connection_result(r.message);
			},
		});
	}

	const default_row = (frm.doc.llm_apis || []).find((row) => row.enabled && row.is_default);
	if (!default_row) {
		frappe.msgprint(__("Mark one enabled API row as Default before testing."));
		return;
	}

	frappe.call({
		method: "ai_engine.ai_engine.doctype.ai_engine_settings.ai_engine_settings.test_llm_connection",
		args: {
			api_row_name: default_row.name,
			api_key: default_row.api_key,
		},
		freeze: true,
		freeze_message: __("Testing {0}...", [default_row.provider_name]),
		callback(r) {
			show_connection_result(r.message);
		},
	});
}

function test_ollama_embedding(frm) {
	if (!frm.doc.ollama_base_url) {
		frappe.msgprint(__("Set Ollama Base URL before testing embeddings."));
		return;
	}
	if (!frm.doc.ollama_embedding_model) {
		frappe.msgprint(__("Select an Embedding Model before testing."));
		return;
	}

	frappe.call({
		method: "ai_engine.ai_engine.doctype.ai_engine_settings.ai_engine_settings.test_ollama_embedding",
		args: {
			ollama_base_url: frm.doc.ollama_base_url,
			ollama_embedding_model: frm.doc.ollama_embedding_model,
		},
		freeze: true,
		freeze_message: __("Testing Ollama embedding ({0})...", [frm.doc.ollama_embedding_model]),
		callback(r) {
			show_connection_result(r.message);
		},
	});
}

function show_connection_result(message) {
	if (!message?.success) {
		return;
	}
	frappe.msgprint({
		title: __("Connection Successful"),
		message: message.message,
		indicator: "green",
	});
}

function render_setup_notes(frm) {
	const container = frm.fields_dict.setup_notes?.$wrapper?.find("#ai-engine-setup-notes");
	if (!container?.length) {
		return;
	}

	const embedding_model = frappe.utils.escape_html(frm.doc.ollama_embedding_model || "nomic-embed-text");
	const local_embed_notes = `
		<p><b>Local embeddings (Ollama)</b></p>
		<ul>
			<li>Pull the selected model on the Ollama host, e.g. <code>ollama pull ${embedding_model}</code></li>
			<li>Base URL defaults to <code>http://127.0.0.1:11434</code> (use this on a VPS with an SSH reverse tunnel)</li>
			<li>Use <i>Test Ollama Embedding</i> to probe <code>/api/embeddings</code> with the selected model only</li>
		</ul>
	`;

	if (frm.doc.connection_type === "Ollama (Local)") {
		container.html(`
			<p><b>Ollama (local)</b></p>
			<ul>
				<li>Install Ollama and pull models, e.g. <code>ollama pull llama3.2</code></li>
				<li>Set the text and vision model names to match your pulled models</li>
				<li>Default base URL: <code>http://127.0.0.1:11434</code></li>
				<li><i>Test Default API</i> checks Ollama reachability (<code>/api/tags</code>)</li>
			</ul>
			${local_embed_notes}
			<p>Best for production when documents must stay on-premises.</p>
		`);
		return;
	}

	const rows = frm.doc.llm_apis || [];
	const free_count = rows.filter((row) => row.api_tier === "Free Tier").length;
	const paid_count = rows.filter((row) => row.api_tier === "Paid").length;
	const default_row = rows.find((row) => row.enabled && row.is_default);
	const embedding_rows = frm.doc.embedding_apis || [];
	const default_embedding = embedding_rows.find((row) => row.enabled && row.is_default);

	container.html(`
		<p><b>Remote LLM APIs</b></p>
		<p>Add providers in the table above. Each row shows whether it is a <span class="indicator-pill green no-indicator-dot">Free Tier</span> or <span class="indicator-pill orange no-indicator-dot">Paid</span> API.</p>
		<ul>
			<li><b>Configured:</b> ${rows.length} provider(s) — ${free_count} free, ${paid_count} paid</li>
			<li><b>Default:</b> ${frappe.utils.escape_html(default_row?.provider_name || "Not set")}</li>
		</ul>
		<p>Use <i>Load Starter APIs</i> to add Groq, OpenRouter, Gemini, Cerebras, and OpenAI templates. Paste API keys per row, mark one as <b>Default</b>, then click <i>Test Default API</i>.</p>
		<p><b>Cloud Embeddings</b></p>
		<p>Knowledge Source indexing uses the <b>Default</b> Embedding API row (not the chat LLM Default).</p>
		<ul>
			<li><b>Embedding providers:</b> ${embedding_rows.length}</li>
			<li><b>Default embedding:</b> ${frappe.utils.escape_html(
				default_embedding
					? `${default_embedding.provider_name} / ${default_embedding.embedding_model}`
					: "Not set"
			)}</li>
		</ul>
		<p>Use <i>Load Starter Embeddings</i> under Embeddings, paste an API key, and mark one row as Default.</p>
		${local_embed_notes}
	`);
}
