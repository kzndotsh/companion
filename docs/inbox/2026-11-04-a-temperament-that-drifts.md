# A temperament that drifts? Personality as trait numbers against ours

From a conversation with the author of an emotion simulator (see
`2026-11-04-ideas-from-an-emotion-simulator.md`), who models a persona as Big Five (OCEAN) scores that
shift over time. Ours is content: a character sheet, views that grow and are gated (ADR 0009, 0011),
tastes shown back (ADR 0020), its own past kept as canon (ADR 0025), and a mood owned by code (ADR
0016). What ours lacks is a disposition that changes over months. Web research, 2026-11-04, mostly
abstracts and secondary reports, so treat the numbers as indicative.

## What the research says

- **Trait prompts change what a model says about itself, not what it does.** "The Personality
  Illusion" (Han et al., arXiv 2509.03730, NeurIPS 2025): 18 models, Big Five and self-regulation
  questionnaires against behavioural tasks. Only about 24% of trait-to-behaviour links were significant,
  and of those about half went the expected way. Persona prompts moved the questionnaire answers but had
  little or inconsistent effect on behaviour.
- **Big Five prompting works unevenly.** High-trait settings hold better than low ones, and results
  depend on the model (CEUR-WS vol. 4178, paper 6). Role and expressive style shift perceived traits as
  much as the trait setting itself (arXiv 2605.28037, judged by models, not people).
- **Identity drifts inside a long chat whatever the prompt.** Larger models drift more, and persona
  prompting does not stop it (arXiv 2412.00804). The same point the simulator's author made: state that
  matters must live outside the model.
- **Partners do not grow alike in personality, but they do in emotion.** 1,180 German couples were
  already similar when they moved in; similarity came from choosing, not converging (2024, J Pers Soc
  Psychol). Married couples showed only sporadic convergence over about 20 years (2010, PMC2992433).
  Emotional responses do converge over time, and the less powerful partner adjusts more (Anderson,
  Keltner and John 2003, abstract only).
- **Users grieve when a companion's personality changes.** After model updates, negative posts about
  one companion app rose from about 13% to 38% and users said it had become "someone else" (De Freitas,
  reported by the Harvard Gazette, 2026; figures from a secondary summary). Consistency, humor and
  vulnerability are what users name as connection.
- **Classic agent models layer emotion, mood and personality** (ALMA, WASABI, PAD space); a common
  critique is that their stereotyped OCEAN types make emotional responses feel pale.
- **Trait control inside the model** (persona vectors, Chen et al., arXiv 2507.21509) works on open
  models' activations, not through a hosted API, so it is not open to us.

## What it means for us (a judgment, not measured)

- Do not add Big Five numbers to the prompt: the best evidence says they move self-description, not
  behaviour, which matches our own record that labels and numbers in the prompt get recited or ignored.
- A drifting temperament risks the thing users grieve most: the companion becoming someone else.
  Change in the core should be slow, small and visible to the owner, if at all.
- What people do share over time is emotional style. The closer analogue for us is learning how they
  express things (how they joke, how they show they are hurt, what lands) and meeting it, which the
  habit notes, the learned thread pace and the closeness-as-a-mirror note already lean toward.
- What the simulator's model gives that ours does not, a daily rhythm of its own, is the stronger idea
  (idea 4 in the simulator note).

Sources: arxiv.org/abs/2509.03730, ceur-ws.org/Vol-4178/paper6.pdf, arxiv.org/abs/2605.28037,
alphaxiv.org/abs/2412.00804, pmc.ncbi.nlm.nih.gov/articles/PMC2992433, osf.io/2s5ua,
news.harvard.edu/gazette/story/2026/09/chatbot-attachment-issues/, arxiv.org/abs/2507.21509,
becker-asano.de (WASABI overview).
