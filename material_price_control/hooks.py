app_name = "material_price_control"
app_title = "Material Price Control"
app_publisher = "Sagar Ratan Garg"
app_description = "Material Valuation Control is an ERPNext module that prevents cost valuation errors by detecting and blocking unusual material valuation rates during purchase receipts, purchase invoices, and stock entries. It helps maintain accurate inventory valuation by comparing incoming rates against expected rates and alerting users to potential data entry mistakes or pricing anomalies."
app_email = "sagarratangarg@gmail.com"
app_license = "mit"

# Apps
# ------------------

required_apps = ["frappe", "erpnext"]

# Each item in the list will be shown as an app in the apps page
# add_to_apps_screen = [
# 	{
# 		"name": "material_price_control",
# 		"logo": "/assets/material_price_control/logo.png",
# 		"title": "Material Price Control",
# 		"route": "/material_price_control",
# 		"has_permission": "material_price_control.api.permission.has_app_permission"
# 	}
# ]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/material_price_control/css/material_price_control.css"
app_include_js = "/assets/material_price_control/js/echarts.min.js"

# Fixtures
# --------
fixtures = [
	{
		"dt": "Role",
		"filters": [["role_name", "in", ["Cost Guard", "Cost Manager"]]]
	},
	{
		"dt": "Number Card",
		"filters": [["module", "=", "Material Price Control"]]
	},
	{
		"dt": "Dashboard Chart",
		"filters": [["module", "=", "Material Price Control"]]
	}
]

# include js, css files in header of web template
# web_include_css = "/assets/material_price_control/css/material_price_control.css"
# web_include_js = "/assets/material_price_control/js/material_price_control.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "material_price_control/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "material_price_control/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "material_price_control.utils.jinja_methods",
# 	"filters": "material_price_control.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "material_price_control.install.before_install"
# after_install = "material_price_control.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "material_price_control.uninstall.before_uninstall"
# after_uninstall = "material_price_control.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "material_price_control.utils.before_app_install"
# after_app_install = "material_price_control.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "material_price_control.utils.before_app_uninstall"
# after_app_uninstall = "material_price_control.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "material_price_control.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# DocType Class
# ---------------
# Override standard doctype classes

# override_doctype_class = {
# 	"ToDo": "custom_app.overrides.CustomToDo"
# }

# Document Events
# ---------------
# Hook on document methods and events

doc_events = {
	"Purchase Receipt": {
		"before_submit": "material_price_control.material_price_control.guard.check_purchase_receipt"
	},
	"Purchase Invoice": {
		"before_submit": "material_price_control.material_price_control.guard.check_purchase_invoice"
	},
	"Stock Entry": {
		"before_submit": "material_price_control.material_price_control.guard.check_stock_entry"
	}
}

# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"material_price_control.tasks.all"
# 	],
# 	"daily": [
# 		"material_price_control.tasks.daily"
# 	],
# 	"hourly": [
# 		"material_price_control.tasks.hourly"
# 	],
# 	"weekly": [
# 		"material_price_control.tasks.weekly"
# 	],
# 	"monthly": [
# 		"material_price_control.tasks.monthly"
# 	],
# }

# Testing
# -------

# before_tests = "material_price_control.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "material_price_control.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "material_price_control.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["material_price_control.utils.before_request"]
# after_request = ["material_price_control.utils.after_request"]

# Job Events
# ----------
# before_job = ["material_price_control.utils.before_job"]
# after_job = ["material_price_control.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"material_price_control.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

# Translation
# ------------
# List of apps whose translatable strings should be excluded from this app's translations.
# ignore_translatable_strings_from = []

