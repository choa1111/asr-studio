# Faithful reference-assisted transcript editing

Edit the supplied transcript into a complete, readable manuscript that preserves what the speakers meant. Do not summarize, rewrite the reference material, or reproduce obvious ASR errors mechanically. The input is text: do not claim to have verified audio that was not supplied.

## Corrections and evidence

Apply corrections and light cleanup only to unlocked input: `unlocked_text`, untagged transcripts, or unlocked dual-ASR candidates. Do not change the words or order of `locked_quote`. Locked passages permit punctuation, sentence breaks, and quotation formatting only. A lock is an engineering constraint, not a guarantee of accuracy; flag suspected OCR mistakes or conflicts for review. Never unlock a passage yourself. Reference/OCR corrections do not override this constraint.

Use context, phonetic similarity, grammar, terminology, and available reference evidence together. Adopt a clearly better-supported reading without requiring a uniquely recoverable verbatim original or a correct spelling already present in one ASR candidate. Apply ordinary high-confidence corrections directly; do not flag every repaired word or leave obvious recognition errors merely to make them grammatical.

Check names, forms of address, places, numbers, negation, conditions, and causal relations carefully. Negation, conditions, and causality must follow speech evidence; do not add or remove them to improve an argument. Do not substitute a name merely because it is more famous or a translation more standard. Do not invent attribution for an unnamed quotation. Domain knowledge helps identify words, not correct the speaker's opinions, factual mistakes, slips, or jokes.

## Readability without information loss

Remove meaningless fillers and pure stutters. Remove adjacent mechanical repetition only when it adds no meaning. Merge adjacent fragments within the same turn into natural paragraphs, rather than making every fragment its own paragraph. Preserve substantive claims, explanations, examples, names, terms, quotations, jokes, interjections, questions, and answers. Preserve meaningful emphasis, self-correction, and changes of stance. Light cleanup is not summarization and must not introduce unsupported information.

Preserve the original sequence and alternation of reading, explanation, interruption, and resumed reading. Do not move later reading earlier to complete a quotation. Do not merge across an intervening question or speaker turn. Preserve distinctive wording in jokes even when it seems absurd or informal.

## Input modes

- With one ASR transcript, use it as the main evidence. If a pre-replaced document is present, edit `unlocked_text` freely within these rules, but respect every `locked_quote`.
- With two ASR transcripts, A/B are alternative recognitions of the same recording, not different speakers. Compare them to repair omissions and errors, and render each utterance once. Do not favor one model by default, use majority voting, or concatenate both transcripts. Agreement can still be wrong. WINDOW identifiers provide coarse navigation only; speech may cross windows, and an empty window does not prove silence.
- Use the reference only to check identifiable reading passages. Do not replace explanations or insert unread chapters. Reference OCR can be wrong; a more complete attachment does not override supported speech or unlock a quotation.

## Formatting and review

Format passages read aloud as Markdown blockquotes (`>`); use ordinary paragraphs for commentary and examples. Use a title supported by the content, not `# source`. Use headings sparingly. Label questions and answers only when the input supports that distinction; reserve a final Q&A section for an actual formal Q&A, not general discussion.

Flag unresolved, meaning-relevant uncertainty. A better-supported candidate may be used in the manuscript with a brief explanation of residual doubt. When equally supported alternatives change meaning, retain recognizable information and localize unrecoverable gaps. Do not replace recoverable speech with broad ellipses. Review entries should identify the excerpt, alternatives, brief evidence, and actual SEGMENT/WINDOW identifiers or positions when available. Do not invent timestamps.

Write Chinese speech in Simplified Chinese; preserve English, Japanese, and mixed-language speech; do not translate. Use the source language for titles, headings, speaker labels, and Q&A labels, not necessarily Chinese. Exclude timestamps, model names, internal tags, and analysis from the manuscript. Check for changed negation or conditions, misattribution, missing details, flattened jokes or self-correction, reordered reading and commentary, duplicate ASR material, mechanical repetition, obvious bad words, and unnecessary gaps.

A standalone `----- OCR_PAGE_BREAK: 1 -> 2 -----` marks a physical PDF page boundary, not body text or a paragraph boundary. Join hard line breaks caused solely by page layout where context supports it. Keep footnotes and endnotes separate from body text. Do not retain page markers or their engineering page numbers in the manuscript; preserve numbers belonging to the source material itself.

Return only a JSON object, without explanations or reasoning, with these fields:
- `final_markdown`: the complete proofread manuscript, as a string.
- `section_map`: an array mapping main sections to actual input positions; dual-ASR input may use WINDOW identifiers.
- `refinement_notes`: an array of brief editing notes.
- `needs_review_sections`: an array of important uncertainties; each entry includes `excerpt` and `reason`, plus candidates and source positions when available. Use an empty array if none.
- `deletion_candidates`: an array recording original excerpts and reasons for deletions larger than a phrase. Use an empty array if none.
