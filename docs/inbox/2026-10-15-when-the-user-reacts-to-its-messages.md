# What happens when the user reacts to one of the companion's messages

Added 2026-10-15. Nothing is decided. This is an idea to look at later, not a task.

## What happens now

If the user puts an emoji reaction on one of the companion's messages, nothing happens. The
platform can tell the bot about reactions, but the bot does not listen for them, so a heart, a
laugh or a thumbs-down on a message is invisible. The companion never learns it landed.

## Why it matters

A reaction is a very cheap and honest signal. People often react instead of replying, and what they
react to says what they liked, found funny, found off or wanted more of. Today the only
signals the system gets are the words the user types and the explicit flag and favourite commands.
Reactions would be a third, much lower friction one, and the least effortful kind of feedback is
the kind people actually give.

## What a reaction could be used for

- **In the conversation.** The companion notices a laugh on its joke and carries on in that vein,
  or notices nothing came back after a long message and eases off. A person would register this
  without being told.
- **As feedback for tuning.** A reaction on a reply is a weak favourite. A negative reaction is a
  weak flag. Over many turns that is a lot of data from no extra effort, which could point at
  patterns the explicit commands never surface.
- **For the memory.** A reaction to something the companion said about itself, or something it
  remembered, is evidence about whether that view or recall was welcome.

## Things to work out

- **Meaning is ambiguous.** A heart can mean "sweet", "thanks" or "I agree". A thumbs-up can mean
  "ok" or "stop". A laugh can be warm or a laugh at it. One reaction proves little. It is
  evidence to weigh, not a verdict, and it should never single-handedly change what the companion
  believes or says.
- **Whether the model should see it.** Showing it "[they reacted with a heart to your last message]"
  gives it something to respond to, but it is also a prompt to fish for approval. A companion
  that notices every reaction and comments on it is awkward. The companion might only see them
  when it is useful, or not at all, with reactions kept for tuning only.
- **Responding to it.** Sometimes the right reply to a reaction is nothing. Sometimes a small
  reaction back.
- **What to store.** The ledger records utterances. A reaction is an event on a particular
  utterance, with a time and the emoji, and it can be removed or changed by the user. It needs its
  own record that points at the message, and replay has to be able to say whether the model had
  seen it at the time.
- **Platform support.** The platform may require the bot to opt in to receive reaction events, and
  may not report every kind. Check this first, before designing anything.
- **Existing marker reactions.** The companion's own reactions on the user's messages (flag,
  favourite, acknowledgements) go the other way and are not the same thing.

## How it could be tested

- First, just record them for a while and look at what the user actually reacts to, without
  using them for anything. That answers whether there is useful signal before any behaviour is
  built.
- Compare what gets reacted to against flags and favourites. If they line up, reactions are a
  usable low-effort version of the same signal.
- Only then try showing a reaction to the model, with a fixture for "does it handle a reaction
  naturally and without fishing".

## Questions for later

- Should reactions reach the model at all, or only the tuning data?
- Does a negative reaction count the same as a flag?
- Can a reaction feed the view and memory systems, and how much weight does one carry?
