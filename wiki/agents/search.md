# Wiki Search

Use this workflow when the user wants to search, browse, or answer questions from the generated wiki.

## Goal

Interpret the query, let the backend delegate retrieval to `obsidian-cli search` when available or `rg` otherwise, then use `index.md` and category pages for browse context.

Use the active model from the invoking skill/session for answer synthesis. Retrieval remains delegated in `scripts/wiki.py`.

## Workflow

1. Run search first:

```bash
python wiki/scripts/wiki.py search "user query"
```

2. Read note matches from `obsidian-cli` or `rg`.
3. Read generated matches from `index.md` and `categories/`.
4. Use category-path context in the answer when it helps orient the user.
5. Prefer grounded synthesis over speculative inference.

## What Good Answers Include

- The most relevant concepts
- Their category paths or category pages
- The key distinction or pattern across top matches
- Direct mention of missing coverage when the wiki does not support the answer

## Do Not

- Do not do retrieval in the prompt alone.
- Do not ignore category-page hits if they explain the branch better than any single note.
