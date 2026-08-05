# Dataset Patterns

Use these patterns to design demo data that is professional, simple, and useful for automation practice.

## sales-orders

Core columns:

- `order_id`
- `order_date`
- `customer_id`
- `customer_name`
- `city`
- `product_name`
- `category`
- `quantity`
- `unit_price`
- `discount_percent`
- `payment_status`
- `delivery_status`
- `sales_owner`

Practice tasks:

- filter unpaid orders;
- calculate total revenue;
- send reminder messages by payment status;
- group revenue by city, category, or sales owner.

## office-tasks

Core columns:

- `task_id`
- `created_date`
- `department`
- `owner_name`
- `task_title`
- `priority`
- `due_date`
- `status`
- `estimated_hours`
- `actual_hours`

Practice tasks:

- find overdue tasks;
- build a weekly progress report;
- notify owners of high-priority pending work;
- compare estimated and actual hours.

## leads-crm

Core columns:

- `lead_id`
- `created_date`
- `lead_name`
- `company_name`
- `city`
- `source`
- `interest`
- `budget_vnd`
- `owner_name`
- `next_follow_up`
- `stage`
- `note`

Practice tasks:

- filter leads needing follow-up today;
- group leads by source and stage;
- create personalized outreach messages;
- calculate expected pipeline value.

## course-students

Core columns:

- `student_id`
- `registered_date`
- `student_name`
- `course_name`
- `class_code`
- `payment_status`
- `attendance_sessions`
- `total_sessions`
- `homework_status`
- `certificate_status`
- `support_owner`

Practice tasks:

- list students who have not paid;
- calculate attendance rate;
- find students needing support;
- export certificate-ready learners.

## inventory

Core columns:

- `sku`
- `product_name`
- `category`
- `supplier_name`
- `warehouse`
- `stock_quantity`
- `reorder_level`
- `unit_cost`
- `last_updated`
- `status`

Practice tasks:

- identify low-stock products;
- calculate inventory value;
- generate reorder requests;
- group stock by warehouse or supplier.

## hr-attendance

Core columns:

- `employee_id`
- `work_date`
- `employee_name`
- `department`
- `job_title`
- `check_in`
- `check_out`
- `work_hours`
- `leave_status`
- `approval_status`

Practice tasks:

- calculate monthly work hours;
- detect late check-ins;
- summarize leave days by department;
- build approval lists for managers.
