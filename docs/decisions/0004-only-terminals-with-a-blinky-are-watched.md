# 0004: Only terminals with a blinky are watched

**Status:** accepted
**Date:** 2026-10-01

## Context
Until now every interactive agent session got a blinky and pushes automatically. The user wants
to place blinkies on terminals by drag and drop, see them in the terminal's corner, switch them
on and off, and know at a glance which terminals are covered.

## Options
- Everything automatic, dragging only pins a blinky visibly.
- Only covered terminals count: a blinky placed on a terminal window watches the agents in it.

## Decision
Only covered terminals count (chosen by the user). A placement is (blinky slot, terminal pid,
window address, awake). An agent is covered when the terminal pid is one of its ancestor
processes. Pushes need an awake blinky plus the global phone switch. Placements live in the
runtime directory and are pruned when the terminal process is gone.

## Consequences
- Agents in uncovered terminals are still tracked and listed on the board, without pushes.
- Matching by process means a terminal that owns several windows (kitty single-instance)
  counts as one terminal; marked with `ponytail:` in placement.py.
- Without a bar that places blinkies (no Quickshell), `blinky place on` must be called by hand.
