# Racing Times: tone rules for every script

These apply to Pixie, Byte and anything else on screen.

1. **Facts are sacred, style is free.** Every factual claim comes from the edition's sources or from a sourced anecdote. Jokes, opinions and metaphors can be as playful as you like, as long as they are obviously jokes or opinions.
2. **Label each line in the script.** Every sentence has a `kind`:
   - `fact`: a claim taken from the edition. The fact-checker verifies it against the edition's sources.
   - `opinion`: the character's own view. Must be recognisably opinion when spoken. Never contains a new factual claim.
   - `anecdote`: history or a statistic. Must have `source` (URL from the anecdote-finder). The fact-checker verifies it against that source.
   - `link`: greetings, hand-offs, sign-offs, jokes with no claims in them.
3. **Opinion budget:** Pixie gives at most one opinion per story, and not on every story. Byte gives at least one opinion per fact.
4. **Sensitive stories** (deaths, serious injuries, illness, accidents, anything off-track and personal): no jokes and no hot takes. A respectful tone, facts only. A sourced career memory is welcome. Edition 1 examples: Alan Jones's death and Jack Harvey's cancer diagnosis.
5. **Respect real people.** Opinions criticise decisions and driving, never a person's character, appearance, nationality or private life. No nicknames for real people that they don't use themselves.
6. **Quotes:** real quotes only, attributed, under fifteen words, at most one per source.
7. **Balance:** in a ten-minute episode, roughly two-thirds news and one-third colour (opinions, anecdotes, banter).

## House style: fast, exciting, human (producer's standard, 17 Nov 2026)
The reference is `episodes/2026-11-16/script.json`. Read it before writing; every episode should feel like it.
- **Pace.** Most lines are under 20 words. Lists build to a payoff ("Nine wins, seven podiums. Not bad for a second season, is it?").
- **Talk to a friend.** Contractions, rhetorical questions, reactions. Each story opens with a hook and ends on a beat (a quip, a reaction, a hand-off). Never on a flat fact.
- **Every line has a `delivery`,** and it changes often. No more than two lines in a row share one. Sensitive stories use only `serious` and `warm`.
- **Banter is real conversation.** Pixie and Byte interrupt, tease and hand over with jokes.
- **Read it out loud.** If it sounds like a press release or an essay, rewrite it.

## Not AI slop: banned
Rejected by `validate.py --strict`:
"delve", "testament to", "in a stunning turn", "a rollercoaster", "buckle up", "it's worth noting", "needless to say",
"in the world of", "navigate the", "a true masterclass", "showcasing", "game-changer", "unprecedented", "tapestry",
"embark", "a whirlwind", "nail-biting finish", "edge-of-your-seat", "only time will tell", "the stage is set",
"without further ado", "let's dive in", "in conclusion".
Also avoid: three adjectives in a row, "not only X but also Y", ending a story on a summary of itself, and exclamation marks on every line.
