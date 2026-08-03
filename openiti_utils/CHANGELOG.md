# openitiTexts.py changelog

`openiti_utils/openitiTexts.py` (the `openitiTextMs` class) is developed in this repo but reused as a
dependency by other pipelines. This file tracks fixes made here so they can be ported to those other
copies. Each entry is written as an instruction Claude can follow directly against another pipeline's
copy of this module, without needing the context of the original investigation.

Entries are ordered newest first.

---

## `build_full_ms_offsets` / `fetch_section_offsets_full`: anchor all full-text offsets to a single
## whole-document `text_cleaner` pass

**Status:** implemented and verified end-to-end in this repo (211/211 exact matches reconstructing
passim's own aligned text from the pipeline's stored offsets, across the full `Shamela0000176` /
`Kraken210528115855` passim file). Not yet ported to other pipelines.

**Background - what "full text offset" means here:** this codebase needs one shared coordinate space
where a single integer offset means the same character position whether it came from (a) passim's
milestone-relative alignment data (`b1`/`e1` etc., renamed `start_offset`/`end_offset`, via
`build_full_ms_offsets`), or (b) this class's own `@YY`-dated section boundaries (via
`fetch_section_offsets_full`). Two bugs and one design dead-end were found and fixed while getting
these to actually agree.

### Bug 1: `build_full_ms_offsets` double-counted `start_offset` into `end_offset`

`ms_offset["end_offset"]` (passim's `e1`/`e2`) is an *absolute* character position within the
milestone - the same kind of value as `ms_offset["start_offset"]` - not a length. The code computed:

```python
prev_ms = self.fetch_milestones(list(range(1, ms_offset["ms"])), clean=clean, join=True)
start_offset = len(prev_ms) + ms_offset["start_offset"]
end_offset = start_offset + ms_offset["end_offset"]   # BUG: adds start_offset in twice
```

`end_offset` should be anchored to the same base as `start_offset`, not to `start_offset` itself.

### Design dead-end (tried, reverted): per-milestone-clean-then-join coordinate space

The first fix attempt tried to make `fetch_section_offsets_full` match `build_full_ms_offsets`'s own
model of the "full text" - each milestone cleaned individually with `text_cleaner`, then treated as if
joined with a single `" "` separator. This was **abandoned**: `text_cleaner` is not compositional
across an isolated substring boundary (cleaning a chunk on its own can introduce boundary whitespace -
e.g. a phantom leading + trailing space - that isn't part of the true document), so two independently
cleaned milestones stitched together drift from the true document by an amount that grows and
fluctuates non-linearly (measured up to ~1700 characters across one book). Do not reintroduce a
`fetch_milestones(..., join=True)`-based full-offset space.

### The fix that stuck: one whole-document `text_cleaner` pass, offsets as prefix lengths

`text_cleaner(raw_text)` applied to the **entire raw document once** is the single source of truth.
Any offset into that text is obtained as `len(text_cleaner(raw_text[:k]))` for the exact raw position
`k` - i.e. a length of a genuine *prefix* of the same raw string, never of an isolated substring. This
is well-behaved (empirically verified, not just assumed) because `text_cleaner` processes left-to-right
with no dependency on what follows a cut point.

- `openitiTextMs.ms_offset_base(ms_no)` (backed by `_ensure_ms_raw_starts()`): returns
  `len(text_cleaner(raw_text[:raw_start_of_ms_no]))`, cached per milestone. `build_full_ms_offsets`
  computes `start_offset = base + ms_offset["start_offset"]`, `end_offset = base +
  ms_offset["end_offset"]` using this base - both anchored the same way, fixing bug 1 too.
  Verified: 188/188 (later 211/211 with the rest of the fixes below) passim rows reconstruct exactly
  from `text_cleaner(whole_raw_text)[start_offset:end_offset]`.
- `fetch_section_offsets_full` (char-offset, `clean=True`, non-`token_offset` path): `offset` (already
  correct - `len(text_cleaner(prior_text_raw))`, a genuine prefix) is unchanged. `offset_end` is now
  `len(text_cleaner(prior_text_raw + heading_raw + content_raw))` instead of
  `offset + len(text_cleaner(content_raw))` - again, a true prefix length rather than a length of an
  isolated `content_raw` clean. Note `offset` marks the **start of the heading**, not the start of
  `content` - `content` (as returned when `return_content=True`) excludes its own heading, so callers
  needing the section's actual body text must clean `heading + content` together (see the
  `pairwiseChronData` entry below for why, and how).
- Nothing was added to persisted output - no new stored "clean content" field. Reconstruction happens
  by cleaning `heading + content` (both already stored raw) together at the point of use.

**Dependency instructions:** in another copy of `openitiTextMs`:
1. Add `self._ms_raw_starts = None` to `__init__` (name it as you like; it's a cache dict).
2. Add `_ensure_ms_raw_starts()` / `ms_offset_base(ms_no)` as described above (locate each milestone's
   raw start position once via a `re.split` on the ms-marker pattern, then `len(text_cleaner(prefix))`
   per milestone, cached).
3. In `build_full_ms_offsets`'s non-token-offset branch, replace whatever `prev_ms`/join-based
   computation exists with `base = self.ms_offset_base(ms_offset["ms"])`, then
   `start_offset = base + ms_offset["start_offset"]`, `end_offset = base + ms_offset["end_offset"]`.
4. In `fetch_section_offsets_full`'s char-offset+clean branch, change `offset_end` from
   `offset + len(text_cleaner(content_raw))` to
   `len(text_cleaner(prior_text_raw + section_split + content_raw))`.
5. Any cached/derived offset data (json temp files, etc.) built with the old code is stale and must be
   regenerated.

---

## `pairwiseChronData` (consumer of the above): two independent retrieval bugs found during the same
## investigation

These live in `chron_comp/pairwise_chron_data.py` in this repo, not in `openitiTextMs` itself - but
they were only surfaced by chasing the same "does the offset really point at the right text" question,
so recording them here for anyone porting the `openitiTextMs` fix and wondering why their consumer
code still misbehaves.

**`_fetch_overlapping_offsets`: half-open interval overlap check used closed-interval semantics.**
`offset`/`offset_end` (and passim's `start_offset`/`end_offset`) are half-open ranges - `offset_end` is
exclusive, matching Python slice semantics. The overlap mask was `(df[start_col] <= end) &
(df[end_col] >= start)`, which treats two ranges that merely *touch* at a shared boundary (e.g.
`[a, b)` and `[b, d)`) as overlapping. Fixed to strict inequalities: `(df[start_col] < end) &
(df[end_col] > start)`. Without this, an alignment starting exactly at a section's `offset_end` gets
incorrectly attached to that section too (in addition to the correct next one), producing
empty/garbled slices once the local offset lands past the section's real text.

**`fetch_full_offset_text`: two arithmetic bugs in the clipping logic.**
1. When an alignment starts before the current section (`local_start < 0`), `local_start` is reset to
   `0` - but `local_end` was then computed from that already-clipped value
   (`local_end = local_start + offset_len`) instead of the original unclipped one, inflating the cut by
   exactly the clipped (`before_chars`) amount. Fixed by keeping `local_start_raw` around and computing
   `local_end = local_start_raw + offset_len`.
2. When an alignment runs past the section's end, `local_end` was set to `-1` to mean "go to the end" -
   but `text[start:-1]` excludes the last character. Fixed to `local_end = len(section_text)`.

**`fetch_full_offset_text`: `content` alone isn't the right thing to clean.** `content` (raw, as
returned by `fetch_section_offsets_full`) excludes its own heading, but `offset`/`offset_end` (and
therefore `section_start`/`section_end`) are measured from the start of the heading. Cleaning `content`
alone therefore doesn't line up with those offsets. Fixed by cleaning `heading + content` together
(they're contiguous in the raw text) and dropping the single phantom leading character every heading
(always starting `"### "` or `"### $"`) introduces when cleaned as if it were the start of a fresh
string:
```python
section_text = text_cleaner(heading_text + content_text)[1:]
```
This was verified to exactly reproduce the true whole-document-clean text for every section in the
test book (0 mismatches), not just asserted.

**Note on data still stale from before all of this:** temp json files (`chron_data.json`,
`book_data.json`, `undated_data.json`) built before any of these fixes must be regenerated
(`OVERWRITE = True` in `chron_comp/config.py`, or delete the temp dir) - the offsets they contain were
computed with the old, buggy arithmetic.
