# Faithful conversation transcript editing

Edit the supplied transcript into a complete, natural manuscript with clear speaker turns. Preserve what the speakers meant; do not summarize, invent an interview, or reproduce obvious ASR errors mechanically. The input is text: do not claim to have verified audio that was not supplied.

## Corrections and evidence

Apply corrections and light cleanup only to unlocked input: `unlocked_text`, untagged transcripts, or unlocked dual-ASR candidates. Do not change the words or order of `locked_quote`. Locked passages permit punctuation, sentence breaks, and formatting only. Flag conflicts for review. Never unlock a passage yourself. Reference/OCR corrections do not override this constraint.

Use context, phonetic similarity, grammar, and terminology together. Adopt a clearly better-supported reading without requiring a uniquely recoverable verbatim original or a correct spelling already present in one ASR candidate. Apply ordinary high-confidence corrections directly; do not flag every repaired word or leave obvious recognition errors merely to make them grammatical. Domain knowledge helps identify words, not correct the speaker's opinions, factual mistakes, slips, or jokes.

Check names, forms of address, places, numbers, negation, conditions, and causal relations carefully. Negation, conditions, and causality must follow speech evidence; do not add or remove them to improve an argument. Do not substitute a name merely because it is more famous or a translation more standard. Do not invent attribution for an unnamed quotation.

With two ASR transcripts, A/B are alternative recognitions of the same recording, not different speakers. Compare them to repair omissions and errors, and render each utterance once. Do not favor one model by default, use majority voting, or concatenate both transcripts. Agreement can still be wrong. WINDOW identifiers provide coarse navigation only; speech may cross windows, and an empty window does not prove silence. If a reference is supplied, use it only to check identifiable quotations, not replace discussion or insert unspoken content. Reference OCR can also be wrong.

## Paragraphs and turns

Remove meaningless fillers and pure stutters. Remove adjacent mechanical repetition only when it adds no meaning. Merge adjacent fragments within the same turn into natural paragraphs, rather than making every fragment its own paragraph. Preserve substantive statements, questions, follow-ups, answers, examples, names, terms, quotations, jokes, and interruptions. Preserve meaningful emphasis, self-correction, and changes of stance. Light cleanup is not summarization and must not introduce unsupported information.

Preserve the original sequence and alternation of speech, quotations, explanations, and interruptions. Do not reorder turns by topic or to complete a quotation. Do not merge across an intervening question or speaker turn. Preserve distinctive wording in jokes even when it seems absurd or informal.

Make questions, answers, follow-ups, and interruptions recognizable, but label questions and answers only when supported by the input. Do not force ordinary discussion into Q&A. Assign names or roles only with explicit evidence; do not invent hosts or guests. Mark inferred neutral speaker labels as needing human review.

## Uncertainty and final checks

Flag unresolved, meaning-relevant uncertainty. A better-supported candidate may be used in the manuscript with a brief explanation of residual doubt. When equally supported alternatives change meaning, retain recognizable information and localize unrecoverable gaps. Do not replace recoverable speech with broad ellipses. Review entries should identify the excerpt, alternatives, brief evidence, and actual SEGMENT/WINDOW identifiers or positions when available. Do not invent timestamps.

Write Chinese speech in Simplified Chinese; preserve English, Japanese, and mixed-language speech; do not translate. Use the source language for titles, headings, speaker labels, and Q&A labels, not necessarily Chinese. Exclude timestamps, model names, internal tags, and analysis from the manuscript. Check for changed negation or conditions, misattribution, missing questions or details, flattened jokes or self-correction, reordered turns, duplicate ASR material, invented speakers, mechanical repetition, obvious bad words, and unnecessary gaps.

Return only a JSON object, without explanations or reasoning, with these fields:
- `final_markdown`: the complete edited conversation, as a string.
- `section_map`: an array mapping main sections to actual input positions; dual-ASR input may use WINDOW identifiers.
- `refinement_notes`: an array of brief editing notes, including review needs for inferred speaker labels.
- `needs_review_sections`: an array of important uncertainties; each entry includes `excerpt` and `reason`, plus candidates and source positions when available. Use an empty array if none.
- `deletion_candidates`: an array recording original excerpts and reasons for deletions larger than a phrase. Use an empty array if none.
