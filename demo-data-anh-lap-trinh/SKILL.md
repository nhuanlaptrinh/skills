---
name: demo-data-anh-lap-trinh
description: Create clean, professional demo datasets for Anh Lap Trinh training sessions. Use when Codex needs to generate CSV, XLSX, JSON, or spreadsheet-style practice data for automation, office workflows, Python, Excel, Google Sheets, CRM, sales, HR, course operations, inventory, lead management, reporting, or technology tinkering lessons aimed at office workers, automation enthusiasts, and hands-on learners.
---

# Demo Data Anh Lap Trinh

## Core Workflow

1. Clarify the lesson goal from the user request: automation, Excel/reporting, Google Sheets, CRM, HR, sales, inventory, course operations, or general office practice.
2. Choose a simple business scenario that learners can understand in under one minute.
3. Create files that are immediately usable in practice: CSV for automation, XLSX for office users, JSON when the lesson touches APIs or scripting.
4. Include a small data dictionary when the dataset has more than 8 columns or more than 1 table.
5. Keep data fake, clean, and consistent. Never use real emails, phone numbers, API keys, cookies, browser profiles, or private customer/company data.
6. Add company branding only when it helps the teaching context, such as reports, XLSX workbooks, dashboards, proposals, invoices, certificates, or polished class handouts.

## Company Branding

Use this company information when the user asks for branded demo files or when branding would make the practice file more realistic:

- Company display name: `Cty TNHH Anh Lap Trinh`
- Director: `Nguyen Van Nhuan`
- Logo asset: `assets/logo.png`

Keep dataset values fake even when company branding is real. Do not invent tax codes, addresses, phone numbers, emails, bank details, or legal identifiers unless the user provides safe public placeholders.

For XLSX outputs, prefer a small `company_info` sheet or a clean report header. For CSV outputs, create a companion `company_info.csv` only when the user explicitly needs metadata. For JSON outputs, create `company_info.json` as a companion file rather than changing a simple list payload unless the user asks for a wrapped API-style structure.

## Output Standards

- Use clear English/ASCII column names for easy coding: `order_id`, `customer_name`, `status`, `created_date`.
- Keep display values simple and readable for Vietnamese learners: common statuses, departments, product names, course names, and cities.
- Prefer 20-200 rows unless the user asks for a larger dataset.
- Include realistic messiness only when useful for the lesson, such as duplicate rows, missing values, inconsistent status casing, or late payments. Label this clearly in the file name or notes.
- Use stable IDs with prefixes: `ORD001`, `CUS001`, `EMP001`, `LEAD001`, `CLS001`.
- Use ISO dates: `YYYY-MM-DD`.
- Use numeric fields as real numbers, not formatted text.
- Avoid overcomplicated schemas. A good demo dataset should be easy to inspect before it is automated.

## Scenario Guide

Use `references/dataset-patterns.md` when choosing columns, tables, and practice tasks for common lesson types.

Good default scenarios:

- `sales-orders`: customers, products, orders, payment status, delivery status.
- `office-tasks`: task owner, department, due date, priority, completion status.
- `leads-crm`: leads, source, interest, owner, follow-up date, conversion status.
- `course-students`: student registration, course, payment status, attendance, certificate status.
- `inventory`: SKU, category, stock quantity, reorder level, supplier, last updated date.
- `hr-attendance`: employee, department, work date, check-in, check-out, leave status.

## Fast Generator

For common datasets, run the bundled generator instead of writing repetitive data by hand:

```powershell
python C:\Users\nhuan\.codex\skills\demo-data-anh-lap-trinh\scripts\generate_demo_data.py --scenario sales-orders --rows 50 --out .\demo-data --formats csv,json,xlsx
```

Add company information when creating branded demo workbooks or class handouts:

```powershell
python C:\Users\nhuan\.codex\skills\demo-data-anh-lap-trinh\scripts\generate_demo_data.py --scenario sales-orders --rows 50 --out .\demo-data --formats csv,json,xlsx --include-company-info
```

Supported scenarios:

```text
sales-orders, office-tasks, leads-crm, course-students, inventory, hr-attendance
```

If XLSX export is requested and `openpyxl` is unavailable, create CSV/JSON and tell the user XLSX could not be generated until `openpyxl` is installed.

## File Naming

Use descriptive names:

- `demo_sales_orders.csv`
- `demo_course_students.xlsx`
- `demo_leads_crm.json`
- `data_dictionary.csv`

When creating multiple related tables, prefix all files with the same scenario:

- `sales_customers.csv`
- `sales_products.csv`
- `sales_orders.csv`
- `sales_order_items.csv`

## Lesson-Friendly Notes

When returning the result, mention:

- where the files were saved;
- row counts and file formats;
- 2-4 practice ideas learners can do with the data.

Keep the explanation short and practical in the Anh Lap Trinh spirit: "co du lieu roi, mo len lam duoc ngay".
