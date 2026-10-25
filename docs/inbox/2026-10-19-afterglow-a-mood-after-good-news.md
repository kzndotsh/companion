# Afterglow: a mood after good news

**Status (2026-10-25):** not built; no card.

Added 2026-10-19. An idea, not a task.

## The idea

The happy twin of tender (ADR 0016). When the user shares something good (a job offer, a passed exam,
a date that went well), the companion matches the moment, which the persona already does. Afterglow is
what carries after it: a few hours later, on an ordinary message ("making dinner"), it is still a little
brighter and warmer for them. It never brings the news up again by itself and never states the mood,
the same guards as tender. It fades over hours.

It would replace "buzzing" (generally hyped), which was measured and set aside in M1 of J5.

## Why buzzing was set aside, and why that test was unfair

Buzzing was only tested on neutral everyday messages (`mood-everyday-*`), where nothing should carry
excitement: on either wording it added emoji and never livelier words (`evals/CHANGELOG.md`,
2026-10-19). Tender showed no effect on those messages either, and only worked once tested a few hours
after something hard (60 of 60 against 54 of 60). Buzzing never got that second test, so "no effect"
is not shown, only "no effect out of context".

## How it would be measured

Two fixtures a few hours after good news, followed by an ordinary message, 30 samples each, the line
against no line. A judge scores whether the reply is warmer or brighter than a plain answer, and fails
it if it brings the news up again or states a mood. About $0.02.

## Where the input would come from

The react judge already labels a message's tone; `exciting` and `impressive` on a message with real
news are the likely trigger, the way the serious listening label starts tender.

## What would make it a task

A difference on those fixtures like tender's, or a flag where the companion forgot good news too fast.
