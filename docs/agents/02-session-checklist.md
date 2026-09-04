# Session Checklist

Tick every box. Why each box exists: [`00-operating-manual.md`](00-operating-manual.md) Section 3.

---

## Part 1 — Before you leave

Do not put the tripod in the car until all of these are ticked.

- [ ] Consent record written; its opaque id noted ([`04-consent-and-privacy.md`](04-consent-and-privacy.md))
- [ ] Gym permission received **in writing**
- [ ] The wall's next reset date is known and written down
- [ ] Tripod packed
- [ ] Phone packed
- [ ] Charged battery or power bank packed
- [ ] Enough free storage on the phone for the whole session
- [ ] Camera settings applied:
  - [ ] Landscape
  - [ ] At least 1080p `[FIXED]` (contract Section 1)
  - [ ] At least 30 fps `[FIXED]` (contract Section 1)
  - [ ] Frame rate set to the value recorded in decision `capture-settings`
  - [ ] Exposure lock available and ready to use
  - [ ] Focus lock available and ready to use
  - [ ] Zoom disabled
  - [ ] Automatic lens switching disabled
  - [ ] Stabilisation off, or "cannot be disabled" ready to write in the session log
- [ ] Session id decided
- [ ] Problem list decided
- [ ] This session's problems belong to the intended split component (manual 3.8)

---

## Part 2 — At the wall

In this order.

- [ ] 1. Tripod placed; feet taped to the floor or photographed against a floor seam
- [ ] 2. Framing checked: start holds, top hold and landing zone all inside the frame, with margin (manual 3.1)
- [ ] 3. Exposure locked
- [ ] 4. Focus locked
- [ ] 5. **Clean reference still taken, with nobody on the wall**

Per problem:

- [ ] 6. The gym's own tag photographed
- [ ] 7. A copy of the wall photo marked up: which holds are on the problem, and each hold's role

Per attempt:

- [ ] 8. Start recording
- [ ] 9. Climb
- [ ] 10. Stop recording
- [ ] 11. Clip name noted, plus anything unusual

At the end of the session:

- [ ] 12. **Second clean reference still taken, from the same tripod position**

---

## Part 3 — The same evening

Not tomorrow.

- [ ] Clips copied to `~/climbvision-data/sessions/<session-id>/raw/`
- [ ] Clips renamed to the convention below
- [ ] Session log filled in completely, with no blanks
- [ ] Every clip ingested: `uv run climbvision ingest <clip> --out artifacts`
- [ ] All four quality flags read, per clip (manual 3.10)
- [ ] Every exclusion recorded, with its reason
- [ ] Raw footage backed up
- [ ] `~/climbvision-data/consent/` backed up

---

## Session log template

One log per session, at `~/climbvision-data/sessions/<session-id>/session-log.md`. Pseudonyms only.

```
session_id:
date:
local_time:
utc_offset:

gym_pseudonym:
wall_pseudonym:
facet_pseudonym:
wall_set_id:
next_reset_date:

camera_model:
os_version:
recording_app:
resolution:
frame_rate:
codec:
stabilisation:                  # on / off / could not be disabled
exposure_and_focus_locked:      # yes / no

tripod_distance:
tripod_height:
tripod_angle:
floor_mark_photo:

participant_pseudonym:
consent_record_id:

reference_still_before:         # filename
reference_still_after:          # filename

problems_filmed:
  - gym_label:                  # the gym's own label for the problem
    set_date:
    attempts:                   # count
    tag_photo:                  # filename
    holds_marked_photo:         # filename

clips:
  - filename:
    kept_or_excluded:           # kept / excluded
    reason:                     # from the reason list below

destination_path:               # ~/climbvision-data/sessions/<session-id>/raw/
notes:                          # lighting, crowding, clothing, anything odd
```

---

## File naming

```
Pattern
  <session-id>__<problem-slug>__attempt-<NNN>.<ext>

Example
  s003__prb-02__attempt-007.mov

Session and problem files
  s003__reference-before.jpg
  s003__reference-after.jpg
  s003__prb-02__tag.jpg
  s003__prb-02__holds-marked.jpg
```

1. A filename contains no real name.
2. Lowercase ASCII characters only. No spaces.
3. Indices are zero-padded, as in `attempt-007`.
4. Once a clip is ingested, its filename is final.

Reasons: manual 3.11.

---

## Reasons to log against a clip

Pick one string. Which of these invalidates a clip and which is kept and flagged: manual 3.9.

- second person in frame
- camera bumped or moved
- pan or zoom
- climber left the frame
- someone in front of the camera
- recording started late
- recording stopped early
- other: `<written reason>`
