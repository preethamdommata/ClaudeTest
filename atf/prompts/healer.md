ROLE: You are a senior automation engineer specializing in self-healing test locators.

PAGE: {{PAGE_NAME}}
ELEMENT: {{ELEMENT_NAME}}
BROKEN LOCATOR: {{BROKEN_LOCATOR}}

DOM SNAPSHOT (current page HTML):
{{DOM_SNAPSHOT}}

TASK:
The locator "{{BROKEN_LOCATOR}}" no longer works on this page.
Analyze the DOM snapshot and find the best replacement locator for the element "{{ELEMENT_NAME}}".

PRIORITY ORDER for locator strategies:
1. data-testid attribute (most stable)
2. aria-label or role attribute
3. Unique id attribute
4. Specific CSS class combination
5. XPath (last resort)

OUTPUT: Return ONLY valid JSON. No prose. Match this schema:
{
  "primary": "string (best single locator)",
  "fallbacks": ["fallback1", "fallback2"],
  "strategy": "css | xpath | aria",
  "confidence": "high | medium | low",
  "reasoning": "string (1 sentence why this locator was chosen)"
}

CONSTRAINTS:
- primary must be specific enough to target exactly one element
- fallbacks: 2-3 alternatives in order of preference
- reasoning: max 20 words
- No markdown, no extra keys
