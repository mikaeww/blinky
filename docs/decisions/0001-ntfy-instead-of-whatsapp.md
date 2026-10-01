# 0001: ntfy instead of WhatsApp for phone pushes

**Status:** accepted
**Date:** 2026-10-01

## Context
The original wish: the PC logs into WhatsApp as a linked device and writes into a group, so
the iPhone rings when an agent needs attention. Messages sent from your own account (including
from a linked device, including into a group) never trigger a notification on your own phone.
The message would arrive silently.

## Options
- WhatsApp with the user's own number: silent on the phone, defeats the purpose.
- WhatsApp with a second number as the sender: works, but needs a second SIM, an unofficial
  client library (whatsmeow or Baileys), and breaks WhatsApp's terms; the number can be banned.
- Telegram bot: official API, free, real push; needs the Telegram app and a bot token.
- ntfy: free, no account, iOS and Android apps, one HTTP POST, self-hostable.

## Decision
ntfy, via its JSON publish API and Python's `urllib`. No dependency, no account.

## Consequences
- Setup for other people is one command plus subscribing in the app.
- A topic name is the only secret; `setup` generates a long random one and pushes carry no
  agent output.
- Another channel later means a second sender in `phone.py`, not a plugin system.
