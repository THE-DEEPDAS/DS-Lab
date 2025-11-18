CREATE OR REPLACE VIEW view_employee_over_30000 AS
SELECT empid,
       name,
       salary,
       department,
       designation,
       year_of_joining
FROM employee
WHERE salary > 30000;

CREATE INDEX idx_employee_salary
ON TABLE employee (salary)
AS 'COMPACT'
WITH DEFERRED REBUILD;

ALTER INDEX idx_employee_salary ON employee REBUILD;

SELECT empid,
       name,
       salary,
       department,
       designation,
       year_of_joining
FROM employee
ORDER BY salary DESC;

SELECT department,
       COUNT(*) AS employee_count
FROM employee
GROUP BY department
ORDER BY department;

SELECT e.empid,
       e.name,
       e.department,
       d.dept_name,
       d.location,
       e.salary
FROM employee AS e
JOIN department_details AS d
  ON e.department = d.department;

SELECT e.empid,
       e.name,
       e.department,
       d.dept_name,
       d.location,
       e.salary
FROM employee AS e
LEFT JOIN department_details AS d
  ON e.department = d.department;
