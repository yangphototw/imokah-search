# Local transcript review pipeline

This pipeline improves existing ASR cautiously. It never replaces the raw transcript or publishes a correction automatically.

1. Build paragraph-sized review units from the raw timestamped index:

   ```powershell
   python build_paragraph_audit.py
   ```

2. Inspect only flagged paragraphs first. Use `--ids` for a targeted case; for an ID beginning with `-`, use the `--ids=<id>` form.

   ```powershell
   python review_audio_paragraphs.py --ids 'VIDEO_ID:12' --models small,medium,large-v3
   ```

   The review tool loads one model at a time, saves after each clip, and resumes missing model outputs on the next run. Its local data is deliberately ignored by Git:
   `data/transcript_paragraph_audit.json.gz` and `data/transcript_audio_reviews.json`.

3. Run the deterministic quality gate:

   ```powershell
   python evaluate_transcript_reviews.py --write
   ```

The gate classifies each suggestion as one of:

- `all_models_support_candidate`: all requested ASR models contain the corrected term; it is eligible for editorial acceptance.
- `channel_identity_supported`: a known channel identity correction, such as 道慈, with explicit provenance; models may still hear a homophone.
- `ambiguous`: audio evidence is incomplete or disagrees; an editor must decide from the wider context.
- `incomplete`: a required model output or provenance field is missing.

Only accepted decisions should later feed public summaries or the search index. Keep the raw text, candidate text, model outputs, and decision together so every published wording can be traced back to its audio evidence.
