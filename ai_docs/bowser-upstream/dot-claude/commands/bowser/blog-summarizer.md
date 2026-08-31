---
description: Visit a blog, find the latest post, summarize it, and save the summary
argument-hint: <blog-url>
---

# Blog Summarizer

Visit a blog, find the latest post, summarize it, and rate it.

## Variables

| Variable | Value               | Description                            |
| -------- | ------------------- | -------------------------------------- |
| SKILL    | `playwright-bowser` | Headless browser (no auth needed)      |
| MODE     | `headless`          | No visible browser                     |

## Workflow

1. Navigate to: {PROMPT}
2. Verify the blog loads (look for article titles or post listings)
3. Identify the most recent blog post
4. Click into the latest post
5. Verify the full post content loads
6. Read the post title, date, and body content
7. Summarize the post in 3-5 bullet points
8. Rate the post out of 10 based on relevance, depth, and clarity
9. Report: post title, date, summary bullets, and rating
