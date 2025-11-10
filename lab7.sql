CREATE TABLE employee (
  empid INT,
  name STRING,
  designation STRING,
  year_of_joining INT,
  country STRING
)
ROW FORMAT DELIMITED
FIELDS TERMINATED BY ','
STORED AS TEXTFILE;

LOAD DATA LOCAL INPATH '/home/exam/file.txt' INTO TABLE employee;

SELECT * FROM employee;

ALTER TABLE employee ADD COLUMNS (salary FLOAT);

CREATE TABLE emp_partition (
  empid INT,
  name STRING,
  designation STRING,
  country STRING
)
PARTITIONED BY (year_of_joining INT)
ROW FORMAT DELIMITED
FIELDS TERMINATED BY ','
STORED AS TEXTFILE;

INSERT INTO TABLE emp_partition PARTITION (year_of_joining=2015)
SELECT empid, name, designation, country
FROM employee
WHERE year_of_joining=2015 AND country='India';

hdfs dfs -ls /user/hive/warehouse/emp_partition
