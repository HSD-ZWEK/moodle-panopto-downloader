# Security Policy

## Supported versions

The latest released version receives security fixes.

## Reporting a vulnerability

Security-relevant issues are not reported through public issues. Instead, GitHub's
private vulnerability reporting ("Report a vulnerability" in the Security tab) is used,
or contact is made directly with the maintainers.

A report should include a description of the issue, steps to reproduce, and the affected
version. Reports are acknowledged and addressed as quickly as the maintainers' capacity
allows.

## Scope

This tool uses access credentials that the executing person already holds and does not
bypass authentication. Tokens and cookies are sensitive: they are never written to logs
and are excluded from version control by `.gitignore`. Reports concerning accidental
credential exposure in the codebase are in scope.
