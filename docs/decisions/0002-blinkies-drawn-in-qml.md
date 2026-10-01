# 0002: Blinkies drawn natively in QML, not exported from Grok_bot

**Status:** accepted
**Date:** 2026-10-01

## Context
The blinkies should look like Grok-bot avatars (soft body, capsule eyes, no mouth), one distinct
look per session. Reference: github.com/Eyadkelleh/Grok_bot, an SVG avatar studio
(Vue) that recreates bloub. Its README and engine sources were read, the app was not run.

## Options
- Export SVGs from Grok_bot: needs running a third-party npm toolchain; the repo has no
  licence file, so its output and geometry cannot safely ship in a public repo; static SVGs
  cannot blink, look around or hop without one file per frame.
- Draw them in QML: body outline from a radius function per shape, eyes as rounded rectangles
  or arches, motion as functions of time. No assets, no licence question, any size.

## Decision
Native QML in `quickshell/Blinky/BlinkyFace.qml`; the ten looks are data in `src/blinky/skins.py`.
Shapes and constants are our own, not copied from Grok_bot.

## Consequences
- New looks are one line in `skins.py`; a new shape or eye style is one case in `BlinkyFace.qml`.
- Rendering is checked by offscreen screenshots, not pixel goldens.
