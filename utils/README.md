# Compatibility shims

`core/src/core` is the canonical implementation package.

This `utils` package exists only to keep legacy imports such as `utils.api` and
`utils.customize.*` working. New runtime code and new behavior tests should
import from `core.*` directly.

Do not add business logic here. Add implementation under `core/src/core/` and,
only when old import compatibility is required, add a thin alias module in this
package.
