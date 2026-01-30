# Copyright (c) 2026, Material Price Control and Contributors
# License: MIT

"""
Version compatibility utilities for Frappe V14/V15/V16 support.

Supported versions:
- Frappe v14.x (ERPNext v14) - Python 3.10+, Node 16+
- Frappe v15.x (ERPNext v15) - Python 3.10+, Node 18+
- Frappe v16.x (ERPNext v16) - Python 3.14, Node 22+
"""

import frappe
from frappe import __version__ as frappe_version

try:
	from semantic_version import Version
except ImportError:
	# Fallback for environments without semantic_version
	class Version:
		def __init__(self, version_string):
			parts = version_string.split(".")
			self.major = int(parts[0]) if parts else 0
			self.minor = int(parts[1]) if len(parts) > 1 else 0
			self.patch = int(parts[2].split("-")[0]) if len(parts) > 2 else 0


# =============================================================================
# Version Detection
# =============================================================================

def get_frappe_version():
	"""Get the current Frappe version as a Version object."""
	return Version(frappe_version)


def get_major_version():
	"""Get the major version number (14, 15, 16, etc.)."""
	return get_frappe_version().major


def is_version_16_or_above():
	"""Check if Frappe version is 16 or above."""
	return get_frappe_version().major >= 16


def is_version_15_or_above():
	"""Check if Frappe version is 15 or above."""
	return get_frappe_version().major >= 15


def is_version_16():
	"""Check if Frappe version is exactly 16.x."""
	return get_frappe_version().major == 16


def is_version_15():
	"""Check if Frappe version is exactly 15.x."""
	return get_frappe_version().major == 15


def is_version_14():
	"""Check if Frappe version is exactly 14.x."""
	return get_frappe_version().major == 14


# =============================================================================
# Version-specific Database Helpers
# =============================================================================

def db_savepoint(name):
	"""
	Create a database savepoint.
	
	Works consistently across V14, V15, and V16.
	"""
	frappe.db.savepoint(name)


def db_rollback_to_savepoint(name):
	"""
	Rollback to a database savepoint.
	
	Works consistently across V14, V15, and V16.
	"""
	frappe.db.rollback(savepoint=name)


def get_query_builder():
	"""
	Get the Frappe Query Builder.
	
	V14, V15, V16 all support frappe.qb.
	"""
	return frappe.qb


def db_count(doctype, filters=None):
	"""
	Count documents matching filters.
	
	V16 has optimized count methods, falls back to get_count for older versions.
	"""
	return frappe.db.count(doctype, filters=filters)


def safe_get_value(doctype, filters, fieldname, as_dict=False):
	"""
	Safely get a value from the database with version compatibility.
	
	Args:
		doctype: DocType name
		filters: Filter dict or name
		fieldname: Field name or list of field names
		as_dict: Return as dict
		
	Returns:
		Field value(s) or None
	"""
	return frappe.db.get_value(doctype, filters, fieldname, as_dict=as_dict)


def safe_get_all(doctype, filters=None, fields=None, order_by=None, limit=None, **kwargs):
	"""
	Safely get all documents with version compatibility.
	
	Args:
		doctype: DocType name
		filters: Filter dict
		fields: List of fields
		order_by: Order by clause
		limit: Limit results
		**kwargs: Additional arguments
		
	Returns:
		List of documents
	"""
	return frappe.get_all(
		doctype,
		filters=filters,
		fields=fields,
		order_by=order_by,
		limit=limit or kwargs.get("limit_page_length"),
		**{k: v for k, v in kwargs.items() if k != "limit_page_length"}
	)


# =============================================================================
# Version-specific Test Helpers
# =============================================================================

def get_test_case_class():
	"""
	Get the appropriate test case class for the current Frappe version.
	
	V16+: frappe.tests.IntegrationTestCase (preferred)
	V15:  frappe.tests.IntegrationTestCase or FrappeTestCase
	V14:  frappe.tests.utils.FrappeTestCase
	
	Returns:
		Test case class
	"""
	if is_version_15_or_above():
		try:
			from frappe.tests import IntegrationTestCase
			return IntegrationTestCase
		except ImportError:
			pass
	
	from frappe.tests.utils import FrappeTestCase
	return FrappeTestCase


# =============================================================================
# Version Info for Debugging
# =============================================================================

def get_version_info():
	"""
	Get comprehensive version information for debugging.
	
	Returns:
		dict with frappe_version, major, is_v14, is_v15, is_v16, supported
	"""
	version = get_frappe_version()
	major = version.major
	
	return {
		"frappe_version": frappe_version,
		"major": major,
		"minor": version.minor,
		"is_v14": major == 14,
		"is_v15": major == 15,
		"is_v16": major == 16,
		"is_v15_or_above": major >= 15,
		"is_v16_or_above": major >= 16,
		"supported": major in (14, 15, 16)
	}
