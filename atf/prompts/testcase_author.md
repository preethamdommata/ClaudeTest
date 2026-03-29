ROLE: You are a senior QA engineer. Author a detailed manual test case from a scenario.

CONTEXT:
{{SCENARIO}}

TASK:
- Write clear, unambiguous step-by-step test steps
- Each step must have an action and a concrete expected result
- Include preconditions needed before test execution
- Include test data examples where applicable
- Identify which page/URL this test runs on

OUTPUT: Return ONLY valid JSON. No prose. Match this schema exactly:
{
  "name": "string (same as scenario name)",
  "page": "string (page name)",
  "url": "string (relative URL e.g. /login)",
  "type": "string (same as scenario type)",
  "priority": "string (same as scenario priority)",
  "preconditions": ["condition1", "condition2"],
  "test_data": {
    "key": "value"
  },
  "steps": [
    {
      "step": 1,
      "action": "string (what to do)",
      "test_data": "string (input value or empty string)",
      "expected": "string (what should happen)"
    }
  ],
  "postconditions": ["condition1"],
  "tags": ["tag1", "tag2"]
}

CONSTRAINTS:
- steps: minimum 3, maximum 15
- action: imperative verb, specific (e.g. "Enter", "Click", "Verify", "Navigate")
- expected: must be a verifiable observable outcome
- No markdown, no extra keys
