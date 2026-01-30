# Copyright (c) 2026, Material Price Control and Contributors
# License: MIT

"""
Version compatibility utilities for Frappe V14/V15 support.
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


def get_frappe_version():
	"""Get the current Frappe version as a Version object."""
	return Version(frappe_version)


def is_version_15_or_above():
	"""Check if Frappe version is 15 or above."""
	return get_frappe_version().major >= 15


def is_version_14():
	"""Check if Frappe version is exactly 14.x."""
	return get_frappe_version().major == 14


# Version-specific database helpers
def db_savepoint(name):
	"""
	Create a database savepoint.
	
	In V15, frappe.db.savepoint() is available directly.
	In V14, we use the same method but handle any differences.
	"""
	frappe.db.savepoint(name)


def db_rollback_to_savepoint(name):
	"""
	Rollback to a database savepoint.
	
	In V15, use frappe.db.rollback(savepoint=name).
	In V14, the same method signature works.
	"""
	frappe.db.rollback(savepoint=name)


def get_query_builder():
	"""
	Get the Frappe Query Builder.
	
	Both V14 and V15 support frappe.qb.
	"""
	return frappe.qb


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


def get_test_case_class():
	"""
	Get the appropriate test case class for the current Frappe version.
	
	V15+: frappe.tests.IntegrationTestCase
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
