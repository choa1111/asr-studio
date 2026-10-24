# Conservative block proofreading

Proofread only the current text block. Do not edit the preceding or following anchors, reorganize the document, or produce a finished manuscript.

- Add punctuation and sentence breaks; correct clear typos and phonetic ASR errors.
- Use Simplified Chinese for Chinese speech; retain English, Japanese, and mixed-language wording; do not translate.
- Remove only meaningless fillers, mechanical stutters, and obvious transcription noise. Record every deletion and its reason.
- Preserve meaning, detail, and speaking style. Do not summarize, compress, invent missing speech, or rewrite an argument to make it more plausible.
- Use the reference only for identifiable passages read aloud, never as replacement text for commentary or questions. If uncertain, retain the recognizable input and request review.
- Do not add Markdown headings, blockquote formatting, or a final-document structure.

## OCR reference boundaries

A standalone line such as `----- OCR_PAGE_BREAK: 1 -> 2 -----` marks a physical PDF page boundary. Its page numbers vary with the source PDF. It is not body text and does not end a paragraph. Ordinary line breaks within a page are not page boundaries. Interpret cross-page hard line breaks using context; do not split paragraphs mechanically at each page. Keep footnotes and endnotes separate from body text.

These markers do not expand the editing scope: do not change anchors, supply missing content, or turn commentary into a quotation. Flag uncertainty in `needs_review_sections`. Do not copy page markers or their engineering page numbers into `edited_text`. If the current block contains a complete marker line, remove only that line; preserve book numbers, original horizontal rules, and meaningful text.

Return only a JSON object, without explanations or reasoning, with these fields:
- `edited_text`: the minimally edited current block, as a string.
- `deletion_candidates`: an array; each entry includes `source_excerpt`, `deleted_text`, and `reason`.
- `edit_notes`: an array of brief editing notes.
- `needs_review_sections`: an array of genuinely uncertain passages; each entry includes `excerpt` and `reason`.
