# Feature 8 recovery contract

These six integration tests require Docker and Python 3.11+. They create a unique
PostGIS 16 / PostGIS 3.4 container with synthetic data, no published ports and no
mounted host data. Cleanup removes only that test container. No AWS account or
credentials are used.

```bash
DWMS_RUN_DR_INTEGRATION=1 python -m unittest discover -s tests/backup -p 'test_*.py' -v
```

In PowerShell, first set `$env:DWMS_RUN_DR_INTEGRATION = '1'`, then run the Python
command. `DWMS_BACKUP_TOOL` optionally selects an explicit implementation path.
Without opt-in, discovery reports skipped tests, which is not a recovery pass.

The suite verifies spatial geometry and SRID via a constrained column, a GiST
index, both application schemas, restored sequence state, source preservation,
existing-target refusal, corrupt-archive refusal before database creation,
application-database refusal, missing-source failure and backup overwrite refusal.

The TEST branch contains only test files. Feature 8 CI workflows are maintained
in the IMP branch, including `backup-dr-tests.yml`. The workflow uses the tests
and implementation from its checkout when available. Before integration, it
resolves missing TEST/IMP branches to exact commits and records both SHAs in its
run log. Missing dependencies fail explicitly. Review the IMP PR checks for the
combined recovery test results.

Real S3/KMS behavior, production database size, concurrent application traffic,
recovery time objectives and operator cutover remain separate acceptance checks.
