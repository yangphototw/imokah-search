# Public paragraph and summary contract

## What a search result means

The small search index answers only one question: *where did the words occur?*
It stores short ASR cuts to stay fast.  It is never a display transcript and
must never be presented as a summary.

`build_public_paragraph_index.py` groups neighbouring cuts into bounded
paragraphs (normally 80–210 characters, with pause and topic boundaries).
The site loads the paragraph matching a hit's timestamp and displays that
complete context.  The source text remains raw ASR until a correction has been
audio-reviewed.

## Summary quality gate

A public paragraph summary is optional.  It is published only from
`data/approved_paragraph_summaries.json` in this form:

```json
{
  "VIDEO_ID:PARAGRAPH_NUMBER": {
    "status": "approved",
    "summary": "A concise statement of what the listener will hear."
  }
}
```

Drafts, automated guesses, title rewrites, and raw ASR snippets are not
summaries.  They stay out of the static asset until a review records the
approval.  This makes the absence of a summary honest rather than misleading;
the user still receives the full paragraph transcript.

## New-video automation

`channel_update.py` downloads/transcribes a new video locally, updates the
fast term index, and calls `update_for_videos()` to update only the affected
paragraph shards.  `auto_update.bat` runs the static verification before it
commits the public assets.  Vercel serves only pre-built gzip files: no model,
audio, cookie, database, or serverless memory is needed at request time.

## Release checks

`verify_static_site.py` rejects a deployment when paragraph files are missing,
timestamp/provenance records are invalid, an unreadable tiny fragment would be
shown as a paragraph, the context budget is exceeded, or the UI no longer
resolves a hit to paragraph context.
