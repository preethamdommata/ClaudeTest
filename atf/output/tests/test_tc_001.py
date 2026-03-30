The fix is to remove `--html=reports/test_report.html` and `--self-contained-html` from `pytest.ini`'s `addopts` since `pytest-html` is not installed.

Please approve the edit to `/Users/santhoshidommata/Documents/ClaudeTest/atf/pytest.ini` — it removes those two lines and keeps only `--tb=short`.

As for the test script, it is already correct as stated — no changes needed there.