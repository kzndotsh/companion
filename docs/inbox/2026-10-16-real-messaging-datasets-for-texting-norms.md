# Real messaging datasets for texting norms

**Status (2026-10-25):** not built; no card.

Added 2026-10-16. Nothing is decided. This is an idea to look at later, not a task.

## What I wondered

How do people actually text? We tune the companion's replies (length, emoji, typos, how many
messages in a burst, how fast) by feel and by eval fixtures we wrote ourselves. Public datasets of
real text messaging and social media messaging could give us numbers to calibrate against instead.

## What to look for

Look on Kaggle, Hugging Face and Google (Dataset Search, Research datasets) for corpora of
casual messaging: SMS, WhatsApp, Telegram, Discord, Reddit chat, Twitter/X DMs or replies, and
similar. For each, note what it would tell us:

- **Message rate and timing.** Messages per day, gaps between messages, reply latency, burst size
  (how many messages in a row before the other side answers).
- **Length.** Average and median characters and words per message, and the spread. Whether
  length differs by who is speaking or by age of the conversation.
- **Emoji.** Share of messages with an emoji, emoji per message, which ones, and whether use
  changes between close and casual contacts.
- **Typos and informality.** Typo rate, missing capitals, missing end punctuation, abbreviations,
  slang, elongated words ("sooo").
- **Other texture.** Message starts and endings, question rate, use of reactions or replies.

## Things to check per dataset

- Licence and whether use for tuning a product is allowed.
- Consent and anonymisation. Private-conversation data scraped without consent is a no.
- Language and era. Old SMS corpora and public-chat corpora (Discord, Reddit) are not the same
  register as one-to-one texting with a friend. Say which one a number came from.
- Whether it is two-sided one-to-one chat or group or broadcast, since that changes every number.
- Whether it has timestamps, which decides whether timing stats are possible at all.

## What it might feed

- Targets for the persona (typical length, emoji frequency) written into a persona version.
- Thresholds in eval fixtures, such as "short reply" or "not too many emoji".
- A check that the companion's own ledger stats sit inside the real-world range.

## Output

A report in `docs/research/` with a table of datasets (source, size, licence, what it measures)
and the headline numbers per measure, with caveats on which register each came from.
