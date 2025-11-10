-- Assumes existing employee table with columns: empid, name, salary, department, designation, year_of_joining, country.
-- Assumes department_details table with columns: department, dept_name, location.

-- 1. Create view to list employees earning more than 30,000.
CREATE OR REPLACE VIEW view_employee_over_30000 AS
SELECT empid,
       name,
       salary,
       department,
       designation,
       year_of_joining
FROM employee
WHERE salary > 30000;

-- 2. Create index on salary column to speed up salary-based predicates.
CREATE INDEX idx_employee_salary
ON TABLE employee (salary)
AS 'COMPACT'
WITH DEFERRED REBUILD;

-- Rebuild the index immediately so it is available for queries.
ALTER INDEX idx_employee_salary ON employee REBUILD;

-- 3. Retrieve all employees ordered by salary descending.
SELECT empid,
       name,
       salary,
       department,
       designation,
       year_of_joining
FROM employee
ORDER BY salary DESC;

-- 4. Count how many employees each department has.
SELECT department,
       COUNT(*) AS employee_count
FROM employee
GROUP BY department
ORDER BY department;

-- 5. Join queries to combine employee data with department details.
-- 5a. Inner join to show only employees whose department metadata exists.
SELECT e.empid,
       e.name,
       e.department,
       d.dept_name,
       d.location,
       e.salary
FROM employee AS e
JOIN department_details AS d
  ON e.department = d.department;

-- 5b. Left join to list all employees with optional department metadata.
SELECT e.empid,
       e.name,
       e.department,
       d.dept_name,
       d.location,
       e.salary
FROM employee AS e
LEFT JOIN department_details AS d
  ON e.department = d.department;
