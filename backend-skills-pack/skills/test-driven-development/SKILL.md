---
name: test-driven-development
description: Use when implementing any feature, function or bug fix, before writing implementation code. Red-green-refactor: write one failing test, watch it fail for the right reason, write the least code to pass, run the whole suite. Not for prototypes, generated code or config.
model: sonnet
---

# Test-Driven Development

Model: sonnet, because the loop is routine coding work (CONVENTIONS rule 5).
Source: adapted from github.com/obra/superpowers @ 22f0b463e7a5e579904dd6211a520321035526f7, `skills/test-driven-development` (MIT, see LICENSE). The changes: the body is cut from 330 lines to fit 150, the TypeScript examples are replaced with one language-neutral example, the Graphviz chart is replaced with a list, and "Good tests" moved to `references/writing-good-tests.md` (upstream `writing-good-tests.md`, unchanged).

**Core principle:** if you did not watch the test fail, you do not know that it tests the right thing.

## When to use

Always for new features, bug fixes, refactoring and behaviour changes.
Exceptions, only with the user's agreement: throwaway prototypes, generated code, configuration files.

## The iron law

```
NO PRODUCTION CODE WITHOUT A FAILING TEST FIRST
```

Wrote code before the test? Delete it and start again from the test. Do not keep it "as a reference" and do not adapt it while writing the tests: that is testing after.

## The cycle

1. **RED.** Write one minimal test for one behaviour, with a clear name, using real code (mock only when it can't be avoided).
2. **Verify RED. Mandatory.** Run it. It must *fail* (not error), with the expected message, because the feature is missing (not because of a typo).
   - Passes at once? It tests existing behaviour. Fix the test.
   - Errors? Fix the error and re-run until it fails correctly.
3. **GREEN.** Write the simplest code that passes. No extra options, no refactoring of other code, no "improvements" beyond the test.
4. **Verify GREEN. Mandatory.** Run the test, then **the project's full test command** (whatever the repo uses), even if the task named one file. The output is clean: no errors, no warnings.
   - Test fails? Fix the code, not the test.
   - Another test fails? Fix it now. Any failure you see, including one you did not cause, goes into your report by name.
5. **REFACTOR**, only when green: remove duplication, improve names, extract helpers. Stay green and add no behaviour.
6. Repeat with the next failing test.

## Example: a bug fix

Bug: an empty email is accepted.

```
RED      test "rejects empty email": submit_form(email="") returns error "Email required"
VERIFY   run tests -> FAIL: expected "Email required", got nothing      (fails for the right reason)
GREEN    in submit_form: if email is blank after trimming, return error "Email required"
VERIFY   run the full suite -> all pass, no warnings
REFACTOR extract field validation only if a second field needs it
```

Never fix a bug without a test that reproduces it first. The test proves the fix and guards against the bug coming back.

## Good tests

| Quality | Good | Bad |
|---|---|---|
| Minimal | One thing. "and" in the name? Split it. | "validates email and domain and whitespace" |
| Clear | The name describes the behaviour | "test1" |
| Shows intent | Shows the API you want | Hides what the code should do |

Read `references/writing-good-tests.md` when writing or changing any test. It covers naming the production change that would make the test fail before writing it, asserting on real behaviour and never on a mock, keeping test-only code out of production classes, and understanding a dependency's side effects before mocking it.

## Rationalizations

| Excuse | Reality |
|---|---|
| "Too simple to test" | Simple code breaks. The test takes 30 seconds. |
| "I'll test after" | A test written after passes at once and proves nothing. You never saw it catch the bug. |
| "Tests after reach the same goal" | Tests after answer "what does this do?". Tests first answer "what should this do?". |
| "Already tested by hand" | No record and no re-run. "It worked when I tried it" is not coverage. |
| "Deleting hours of work is wasteful" | Sunk cost. Keeping code you can't trust is the real waste. |
| "Need to explore first" | Fine. Throw the exploration away, then start with a test. |
| "Hard to test" | Hard to test means hard to use. Simplify the design. |
| "Existing code has no tests" | You are improving it. Add tests for the code you touch. |

## Red flags: stop and start over

- Code before the test, or a test added "later".
- A test that passes immediately, or a failure you can't explain.
- "Just this once", "it's about the spirit, not the ritual", "this case is different".
- "Keep it as a reference" or "adapt the existing code".

## When stuck

| Problem | What to do |
|---|---|
| Don't know how to test it | Write the API you wish you had. Write the assertion first. Ask the user. |
| Test is too complicated | The design is too complicated. Simplify the interface. |
| Must mock everything | The code is too coupled. Inject the dependencies. |
| Setup is huge | Extract helpers. Still huge? Simplify the design. |

## Checklist before calling it done

- [ ] Every new function or method has a test.
- [ ] I watched each test fail, for the expected reason, before implementing.
- [ ] I wrote the least code to pass each test.
- [ ] The full suite passes, and the output has no errors or warnings.
- [ ] Tests use real code (mocks only when unavoidable).
- [ ] Edge cases and error paths are covered.

Can't tick every box? TDD was skipped. Start over, unless the user agreed to an exception.
