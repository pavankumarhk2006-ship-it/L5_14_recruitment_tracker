
"""Recruitment tracker application using an in-memory SQLite database."""

import ast
import csv
import math
import operator
import sqlite3


conn = sqlite3.connect(":memory:")
conn.execute(
    """
    CREATE TABLE applicants (
        id INTEGER PRIMARY KEY,
        name TEXT,
        role TEXT,
        expected_salary INTEGER,
        status TEXT
    )
    """
)


def add_applicant(name, role, expected_salary, status="applied"):
    """Add an applicant to the database."""
    conn.execute(
        """
        INSERT INTO applicants
            (name, role, expected_salary, status)
        VALUES (?, ?, ?, ?)
        """,
        (name, role, expected_salary, status),
    )
    conn.commit()


def evaluate_salary_rule(salary_rule):
    """Safely evaluate a simple arithmetic salary rule."""
    allowed_operators = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.FloorDiv: operator.floordiv,
        ast.Mod: operator.mod,
    }

    def evaluate(node):
        if isinstance(node, ast.Expression):
            return evaluate(node.body)

        if isinstance(node, ast.Constant) and type(node.value) in (int, float):
            return node.value

        if isinstance(node, ast.BinOp):
            operation = allowed_operators.get(type(node.op))
            if operation is None:
                raise ValueError("Unsupported salary rule operator.")
            return operation(evaluate(node.left), evaluate(node.right))

        if isinstance(node, ast.UnaryOp) and isinstance(
            node.op, (ast.UAdd, ast.USub)
        ):
            value = evaluate(node.operand)
            return value if isinstance(node.op, ast.UAdd) else -value

        raise ValueError("Invalid salary rule.")

    try:
        expression = ast.parse(salary_rule, mode="eval")
        result = evaluate(expression)
    except (SyntaxError, TypeError, ZeroDivisionError, OverflowError) as error:
        raise ValueError("Invalid salary rule.") from error

    if (
        not isinstance(result, (int, float))
        or not math.isfinite(result)
    ):
        raise ValueError("Salary rule must produce a finite number.")

    return result


def shortlist(role, salary_rule):
    """Return applicants whose expected salary meets the salary limit."""
    rows = conn.execute(
        """
        SELECT name, expected_salary
        FROM applicants
        WHERE role = ?
        """,
        (role,),
    ).fetchall()

    limit = evaluate_salary_rule(salary_rule)
    result = []

    for name, salary in rows:
        if salary <= limit:
            result.append(name)

    if result:
        return result
    return None


def update_status(applicant_id, status):
    """Update an applicant's recruitment status."""
    try:
        cursor = conn.execute(
            "UPDATE applicants SET status = ? WHERE id = ?",
            (status, applicant_id),
        )
        conn.commit()
        if cursor.rowcount == 0:
            print(f"No applicant found with ID {applicant_id}.")
    except sqlite3.Error as error:
        conn.rollback()
        print(f"Could not update applicant status: {error}")


def export_report(path):
    """Export applicant information to a CSV file."""
    try:
        with open(path, "w", newline="", encoding="utf-8") as report_file:
            writer = csv.writer(report_file)
            writer.writerow(["name", "role", "status"])
            writer.writerows(
                conn.execute("SELECT name, role, status FROM applicants")
            )
    except OSError as error:
        print(f"Could not export report: {error}")


def count_by_status(status):
    """Count applicants with the specified recruitment status."""
    return conn.execute(
        "SELECT COUNT(*) FROM applicants WHERE status = ?",
        (status,),
    ).fetchone()[0]


def main():
    """Run the recruitment tracker demonstration."""
    add_applicant("Nina", "analyst", 600000)
    add_applicant("Omar", "analyst", 750000, "interview")
    add_applicant("Priya", "developer", 900000)

    update_status(1, "interview")

    print(shortlist("analyst", "500000 + 150000"))
    export_report("applicants_report.csv")
    print(count_by_status("interview"), "in interview")


if __name__ == "__main__":
    main()
