# 0003: Own character in the spirit of coucou, looks as editable slots

**Status:** accepted
**Date:** 2026-10-01

## Context
The blinkies should feel like coucou's companion: shaded body, cheeks, a status bubble, eyes
that follow the cursor, distinct expressions for thinking, searching and so on. coucou's code
is MIT, but its LICENSE-ASSETS.md reserves the Mochi character (design, look, expressions,
animations) and forbids shipping it in other projects. Blinky is meant to be published.
The user also wants to change the looks.

## Options
- Port Mochi's drawing: closest look, not allowed in a public repo.
- Own character with the same kinds of behaviour: soft gradient, shine, optional cheeks,
  capsule eyes, a bubble at the shoulder, gaze and motion as functions of time.
- Looks stored per session versus a slot number resolved at display time.

## Decision
Own character (BlinkyFace, BlinkyEyes, BlinkyBadge); nothing is traced or ported from Mochi's
sources or captures. Sessions store a slot; `blinky watch` resolves the slot against
`skins.json` (or the defaults) on every snapshot, so edits show up on running blinkies.

## Consequences
- The settings page only writes `skins.json`; there is one writer and one reader.
- A broken `skins.json` must not break hooks: hooks and watch fall back to the defaults and
  watch reports the error for the bar.
