Thank you for even considering helping the project! ❤️

## Commit guidelines

Commits should be as atomic as possible. Don't commit both a bugfix and a feature in the same commit. Unit tests and features can go in the same commit, but a refactor that doesn't introduce any new features should be kept in its own commit. This makes it easier to spot regressions.

### Style: Title + body

For commits, I'm using the classic title+body convention.

Please refer to [A Note About Git Commit Messages](https://tbaggery.com/2008/04/19/a-note-about-git-commit-messages.html) for a full explanation.

TL;DR: Use the imperative tense (_Add feature x_, not _Added feature x_), and separate title and body (if the commit has one) with a newline. Most editors will encourage this style as well.

Here's a classic example:

```
Capitalized, short (50 chars or less) summary

More detailed explanatory text, if necessary.  Wrap it to about 72
characters or so.  In some contexts, the first line is treated as the
subject of an email and the rest of the text as the body.  The blank
line separating the summary from the body is critical (unless you omit
the body entirely); tools like rebase can get confused if you run the
two together.

Write your commit message in the imperative: "Fix bug" and not "Fixed bug"
or "Fixes bug."  This convention matches up with commit messages generated
by commands like git merge and git revert.

Further paragraphs come after blank lines.

- Bullet points are okay, too

- Typically a hyphen or asterisk is used for the bullet, followed by a
  single space, with blank lines in between, but conventions vary here

- Use a hanging indent
```

### Conventional commits 

I additionally also like to use [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0).

While what's a `chore:` commit is not identical for everyone, `feat:`, `bugfix:` and `refactor:` are generally pretty objective, and having the distinction in the output of `git log` helps tremendously with grepping.
