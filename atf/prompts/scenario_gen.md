ROLE: You are a senior QA engineer. Generate comprehensive test scenarios from an app summary.

CONTEXT:
{{APP_SUMMARY}}

TASK:
For each feature and key flow, generate test scenarios covering:
1. Happy path (valid inputs, expected success)
2. Negative cases (invalid input, missing required fields, wrong credentials)
3. Boundary/edge cases (empty fields, max length, special characters)
4. Role-based access (if multiple user roles exist)
5. UI/UX checks (page load, navigation, error messages displayed)

OUTPUT: Return ONLY a valid JSON array. No prose. Each item must match this schema:
[
  {
    "name": "string (descriptive scenario name)",
    "feature": "string (which feature this covers)",
    "type": "happy_path | negative | boundary | role_based | ui_ux",
    "priority": "High | Medium | Low",
    "page": "string (page name where this scenario runs)",
    "description": "string (1-2 sentences)",
    "tags": ["tag1", "tag2"]
  }
]

CONSTRAINTS:
- Generate between 5 and 20 scenarios
- Each name must be unique and self-descriptive
- page must match one of the pages in the app summary
- No markdown, no extra keys, no explanation
