# Copyright (c) 2026, !! and contributors
# For license information, please see license.txt
"""System Manager admin telemetry aggregates over NScribe billing and vectors."""

from __future__ import annotations

from typing import Any

import frappe
from frappe import _
from frappe.utils import cint, cstr


def _is_system_manager() -> bool:
	return "System Manager" in frappe.get_roles(frappe.session.user)


def _table_exists(doctype: str) -> bool:
	"""Return True when the DocType (and its SQL table) is available on this site."""
	try:
		return bool(frappe.db.exists("DocType", doctype))
	except Exception:
		return False


def _vector_store_by_provider() -> list[dict[str, Any]]:
	if not _table_exists("NScribe Vector Store"):
		return []
	try:
		rows = frappe.db.sql(
			"""
			SELECT
				IFNULL(provider, '') AS provider,
				COUNT(*) AS chunk_count,
				COALESCE(SUM(IFNULL(vector_dimensions, 0)), 0) AS dimensions_sum
			FROM `tabNScribe Vector Store`
			GROUP BY IFNULL(provider, '')
			ORDER BY provider
			""",
			as_dict=True,
		)
	except Exception:
		frappe.log_error(
			title="get_admin_telemetry_metrics: vector store aggregate failed",
			message=frappe.get_traceback(),
		)
		return []

	return [
		{
			"provider": cstr(row.get("provider")),
			"chunk_count": cint(row.get("chunk_count")),
			"dimensions_sum": cint(row.get("dimensions_sum")),
		}
		for row in rows or []
	]


def _paystack_topups() -> dict[str, int]:
	empty = {"count": 0, "credits_credited": 0}
	if not _table_exists("NScribe Credit Ledger"):
		return empty
	try:
		rows = frappe.db.sql(
			"""
			SELECT
				COUNT(*) AS topup_count,
				COALESCE(SUM(-IFNULL(top_up_credits_spent, 0)), 0) AS credits_credited
			FROM `tabNScribe Credit Ledger`
			WHERE action_type = 'Wallet Top-Up'
			""",
			as_dict=True,
		)
	except Exception:
		frappe.log_error(
			title="get_admin_telemetry_metrics: paystack top-up aggregate failed",
			message=frappe.get_traceback(),
		)
		return empty

	row = rows[0] if rows else {}
	return {
		"count": cint(row.get("topup_count")),
		"credits_credited": cint(row.get("credits_credited")),
	}


def _ledger_by_action_type() -> list[dict[str, Any]]:
	if not _table_exists("NScribe Credit Ledger"):
		return []
	try:
		rows = frappe.db.sql(
			"""
			SELECT
				IFNULL(action_type, '') AS action_type,
				COUNT(*) AS entry_count,
				COALESCE(SUM(IFNULL(subscription_credits_spent, 0)), 0) AS subscription_credits_spent,
				COALESCE(SUM(IFNULL(top_up_credits_spent, 0)), 0) AS top_up_credits_spent
			FROM `tabNScribe Credit Ledger`
			GROUP BY IFNULL(action_type, '')
			ORDER BY action_type
			""",
			as_dict=True,
		)
	except Exception:
		frappe.log_error(
			title="get_admin_telemetry_metrics: ledger aggregate failed",
			message=frappe.get_traceback(),
		)
		return []

	return [
		{
			"action_type": cstr(row.get("action_type")),
			"entry_count": cint(row.get("entry_count")),
			"subscription_credits_spent": cint(row.get("subscription_credits_spent")),
			"top_up_credits_spent": cint(row.get("top_up_credits_spent")),
		}
		for row in rows or []
	]


@frappe.whitelist()
def get_admin_telemetry_metrics() -> dict[str, Any]:
	"""Return System Manager–only aggregates for vectors, Paystack top-ups, and ledger spend."""
	user = frappe.session.user
	if not user or user == "Guest":
		frappe.throw(_("Authentication required."), frappe.PermissionError)
	if not _is_system_manager():
		frappe.throw(_("Only System Managers can view admin telemetry."), frappe.PermissionError)

	return {
		"ok": True,
		"vector_store_by_provider": _vector_store_by_provider(),
		"paystack_topups": _paystack_topups(),
		"ledger_by_action_type": _ledger_by_action_type(),
	}
