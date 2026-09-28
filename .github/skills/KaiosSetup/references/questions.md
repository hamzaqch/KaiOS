---
version: 1.0.0
last_updated: 2026-09-28T00:00:00Z
convention: kaios-freshness-v1
---

# Setup question bank

Every question here is optional and every one can be answered "skip". The interview is worth doing because the answers change how KaiOS behaves for months; it is not worth doing all at once. A partial config is a working config.

How to ask: one topic at a time, in the order below, with what was already detected stated first so nobody is asked for something the machine already knows. Never ask two unrelated questions in one turn. Never ask for a secret value.

## Phase 1 — What the machine already has

Nothing is asked here. Run the detection and report it as a table: found or missing for the runtime, version control, the editor, the shell version, the platform CLI, and whether an MCP config already exists. Then ask one question:

- Anything in that list you expected to see and do not?

That question catches a broken install before it becomes a confusing session an hour later.

## Phase 2 — You

- What should I call you in a response? First name or handle is enough.
- What is your role, in the words your team would use?
- What team are you on, and what does that team own?
- What is in your daily stack? Languages, platforms, the tools you actually open.
- What are you usually doing when you open the editor? Writing new code, fixing production, reviewing, or exploring data?
- Anything I should know about how you like to be talked to? Short answers, more context, push back harder, ask before changing files.

The last one is worth asking even though it feels soft, because the answer changes every response afterwards.

## Phase 3 — Models

The picker shows whichever models the organisation has enabled, and that list is different in every company. So ask rather than assume:

- Which models does your picker actually offer? Read them off the list.
- Of those, which is the strongest reasoner, and which is the fastest cheap one?
- Is more than one vendor represented? Which vendors?

Then map them to roles and write the registry. The mapping rule: the strongest reasoner goes to **max**, the solid workhorse to **high**, the fast cheap one to **medium**, a model from a *different vendor than max* to **cross**, a third vendor if one exists to **third**, and whichever handles long documents best to **research**.

If only one vendor is enabled, say so plainly: the cross-family second look degrades to a fresh-context review from the same family, which is weaker, and the engineer should know that rather than discover it.

## Phase 4 — Optional integrations

Each of these is asked separately, and each answer of "skip" is recorded as a skip rather than left blank, so a later session does not ask again.

**GitHub MCP server**

- Do you want KaiOS to reach GitHub directly for issues and pull requests?
- If yes: an entry is written into the workspace MCP config. The token is read from an environment variable; I will not ask for the value and will not write one.

**Platform CLI**

- Is the platform CLI installed and already authenticated?
- If it is not authenticated: the login is interactive and belongs in your own terminal, not here. Run it yourself, then tell me the profile name.
- What is the profile name I should use by default?
- Is there a second profile for a different environment? Which one is production?

That last question matters more than it looks: knowing which profile is production is what lets the approval gate fire on the right target.

**Platform MCP server**

- Do you want a platform MCP entry as well? This is a placeholder unless your organisation actually runs one.

**API keys**

- Any APIs you want KaiOS to know about? Ticketing, docs, monitoring.
- For each: what is the *name* of the environment variable that holds the key?

Say the rule out loud when asking: the name of the variable is written to config, the value never is. If someone offers a key, stop them and ask for the variable name instead.

## Phase 5 — Your projects

Once per project, and stop when the engineer says that is all of them. Two or three projects is a normal answer; asking for a complete inventory of thirty repositories is how an interview gets abandoned.

- What is the project called, and where is it checked out?
- What is it for, in one or two sentences? Say it as you would to a new teammate.
- What is the stack?
- How do you deploy it, or run it? The literal command if there is one.
- What do you call it in conversation? Nicknames, so a later request routes to the right repository.
- Is there a repository URL or a board?
- When you finish a piece of work here, what has to be true before you would call it done?
- What goes wrong in this project more than once?

The last two questions produce the most useful output in the whole interview. The done-definition becomes the project's ISA seed and its instructions file. The recurring problems become the rules that stop them recurring, and they are the reason the project instructions are worth having at all.

## Phase 6 — Close

- Which project should I assume when you do not name one?
- Want me to grill the first project's ideal state properly now, or leave the seed and come back to it?

Then write everything, render the files, and report each path that was created with what is in it. A setup that ends without showing the engineer what it wrote leaves them unable to correct it.

## Questions never to ask

- Any secret value: a token, a password, a connection string, a key.
- Anything already detectable: versions, installed tools, the contents of a repository.
- Anything about the person outside work: this is a work-only system and the interview stays inside that boundary.
- A question whose answer would not change a file. Curiosity costs the engineer's attention.
