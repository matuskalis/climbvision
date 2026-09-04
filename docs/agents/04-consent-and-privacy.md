# Consent and Privacy

**This is not legal advice.** When to get real advice, and the reasoning behind every rule below:
[`00-operating-manual.md`](00-operating-manual.md) Section 4.

---

## Decisions to record

Fill the right-hand column. Each recorded decision becomes its own file under `docs/adr/`.

| Decision | Slug | Your answer |
| --- | --- | --- |
| Who may appear on camera | `second-participant` | |
| Gym permission obtained, and by what means | - | |
| What happens to a clip with a bystander in it | - | |
| Retention period | `retention-policy` | |
| Deletion date | `retention-policy` | |
| Where consent records are stored | - | |

---

## Message to the gym

```
Subject: Filming myself climbing, on a tripod

Hello,

I would like to film myself climbing at <gym>, on a tripod, on <wall or facet>, during
<quiet time window>. Five questions:

  1. Is that acceptable, on that wall?
  2. Other members may occasionally appear in the background. Is that acceptable to you?
  3. Do you have your own filming policy or signage I should follow?
  4. May a clip ever be published, or should the footage stay private?
  5. When is that wall next reset?

The footage stays on my own machine and I am happy to work around your quiet hours.

Thank you,
<name>
```

---

## Consent record template

One record per participant, stored outside the repository.

```
consent_id:                       # opaque; the only part of this that enters the repository
date:
participant_pseudonym:
what_was_recorded:                # which sessions, which wall, what content
what_it_will_be_used_for:         # specific and narrow
retention_period:
deletion_date:
how_to_withdraw:                  # a concrete mechanism
stored_at:                        # ~/climbvision-data/consent/
signature_or_typed_confirmation:
```

---

## Hard rules

1. Raw footage stays on this machine. No upload, no attachment, no paste into a chat, no model API.
2. A frame shared for debugging: no third party in it, no face in it, and it is a derived
   artifact with its own identity. Never the master file.
3. The repository stores the opaque consent id, and nothing else from a consent record.
4. Participants appear as pseudonyms only, and never in a filename.
5. The master pseudonym-to-person mapping lives outside the repository and is never copied into it.
6. Audio is ingested unchanged, never shared, and never stripped after ingest.

---

## Withdrawal procedure

1. Delete the raw files.
2. Delete every artifact directory for those assets.
3. Remove the assets from the split manifest.
4. Re-freeze the splits under a new release id.
5. Mark every gate measured against the old split as invalidated in `docs/status.md`.
6. Record the deletion, with its date.

What this costs after a split freeze: manual 4.6.
