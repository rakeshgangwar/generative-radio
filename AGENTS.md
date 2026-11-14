# Repository workflow

- Create or update a GitHub pull request for each completed, cohesive change.
  The user has authorized committing and pushing validated work and opening PRs
  without asking for permission again.
- Use feature branches and preserve unrelated work in the checkout.
- Describe the concrete problem, resulting behavior, validation performed, and
  remaining limitations in each PR.
- Split independent changes into separate PRs. When a change depends on an
  unmerged PR, state the dependency and merge order in its description.
- The user has authorized merging ready PRs after CI clears them. Require real
  passing checks; an absence of checks is not clearance. Keep unfinished PRs in
  draft, merge dependencies first, and revalidate CI when a PR's base changes.
