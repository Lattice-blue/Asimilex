# Asimilex

> **A note on how this was written:** The vision and ideas in this document are my own. I wrote the original draft myself (the problem, the Jarvis-style goal, what the system should know and do). I then used an AI assistant (Claude) to organize that draft into this structure, tighten the wording, and help work through technical design choices. The AI-assisted parts, including some of the code, were reviewed by me.

**Assimilating AI into a real life.**

Asimilex is an open-source personal AI system built around one idea: an AI can only help with a life it can see. Asimilex keeps a faithful, continuously updated model of a person's real life (goals, schedule, health, knowledge, finances) so an AI can reason about their actual situation instead of an average one.

In one sentence: *Jarvis from Iron Man, for a real person.*

> **Status:** early design / pre-alpha. This document is the specification. The implementation is being built in public; see the [Roadmap](#8-roadmap) and the `journal/` dev log.

---

## Table of contents

1. [Vision](#1-vision)
2. [Principles](#2-principles)
3. [Concepts: the Mirror and the Loop](#3-concepts-the-mirror-and-the-loop)
4. [What the Mirror knows](#4-what-the-mirror-knows)
5. [Behavior: how the AI thinks and acts](#5-behavior-how-the-ai-thinks-and-acts)
6. [Architecture and deployment](#6-architecture-and-deployment)
7. [Technical decisions and data model](#7-technical-decisions-and-data-model)
8. [Roadmap](#8-roadmap)
9. [Non-goals (for now)](#9-non-goals-for-now)
10. [Open questions](#10-open-questions)
11. [Privacy and repository layout](#11-privacy-and-repository-layout)

---

## 1. Vision

### The problem

Modern AI is capable of far more than it can currently deliver, because it knows nothing about the person it is helping. It does not know their goals, their schedule, their health, or their circumstances. It fills those gaps with generic guesses drawn from its training data. A person's life, meanwhile, is easy to let drift out of order, with no single place that holds the whole picture.

### The idea

Give the AI a complete, current record of a person's reality, and let its sole purpose be helping that person improve. With that record it can:

- **Know:** goals, commitments, health (vitals, labs, sleep), finances, and the person's accumulated knowledge.
- **Advise:** point out blind spots, prioritize, and optimize how time is spent.
- **Act digitally:** schedule, draft, organize files, build study plans, and (with approval) move money.
- **Act physically:** operate smart-home devices, and eventually robotics.
- **Sense:** wearables, home sensors, and anything else that can be connected.

It should be conversational, like Jarvis, with a personality that is more than a flat assistant: guiding, and a little cheeky.

### Three directions of growth

Everything on the wish list falls into one of three buckets, and the architecture is designed to grow along all three:

| Direction | Meaning | Examples |
|---|---|---|
| **Sensors** | More input from real life | Calendar, email, wearables, room sensors, lab results |
| **Mirror** | A richer, more accurate model of the person | Goals, schedule, knowledge, health history |
| **Actuators** | More things the system can do | Edit schedule, draft email, control devices |

---

## 2. Principles

- **Build for myself first, open-source second.** Scratch my own itch, then share it.
- **Fail fast.** Build in small iterations; no premature over-engineering or enterprise bloat.
- **The Mirror is the product; the AI is replaceable.** A smart AI on a stale model gives bad advice, and an ordinary AI on an accurate model gives useful advice. The AI provider sits behind one interface and can be swapped.
- **Engine and data are separate.** The code is public. The person's life data is private and never committed.
- **Autonomy is earned in stages.** See [Autonomy ladder](#autonomy-ladder).
- **Evidence over opinion.** Every recommendation cites what it saw in the Mirror.
- **Local-first.** The data lives on hardware the user controls.

---

## 3. Concepts: the Mirror and the Loop

The AI cannot observe the world; it can only see what the **Mirror** shows it. Asimilex is modeled as a living feedback loop rather than a static database.

```
 REALITY                 THE MIRROR                          THE ENGINE
 (the person, time,  ->  Goals        (attractors)       ->  observes the Mirror,
  devices, body,         Commitments  (planned vectors)      detects friction between
  actions)               History      (what happened)        current state and goals,
                         State        (computed snapshot)    proposes changes
        ^                                                            |
        +------------------- actions / proposals <-------------------+
```

- **Reality:** the person, their time, devices, actions, and biology.
- **The Mirror:** a structured, timestamped model of that reality.
  - **Goals** are high-level, independent targets (academic success, health baselines).
  - **Commitments** are planned blocks and tasks that bridge the present to the goals.
  - **History** is what actually happened (sleep logs, lab results, completed work).
  - **State** is the calculated picture of energy, capacity, and progress at a point in time. It is *computed* from the other layers and never typed in by hand.
- **The Engine:** reads the Mirror, detects friction between current state and goals, and rearranges future commitments (for example, moving deep work when sleep debt is high).

**Adherence is derived.** Whether the person is sticking to their schedule is simply planned commitments compared against recorded history. It is computed by the engine, not stored.

---

## 4. What the Mirror knows

| # | Domain | Description | Tier |
|---|---|---|---|
| 1 | **Goals** | What the person is aiming for, in their own words; changeable at any time | 1 |
| 2 | **Life context** | Roles and constraints: work, family, university, hobbies | 1 |
| 3 | **Schedule & commitments** | How time is allocated; tasks that serve goals | 1 |
| 4 | **Daily check-in** | Sleep, energy, mood, what the person is doing | 1 |
| 5 | **Knowledge** | What the person has learned and how well, linked to goals | 2 |
| 6 | **Health** | Labs, vitals, hydration | 2 |
| 7 | **Finances & properties** | Accounts, assets, spending | 2 |
| 8 | **Location & live telemetry** | Position, wearable streams, room sensors | 3 |
| 9 | **Physical control** | Smart-home actuators, robotics | 3 |

**Why life context matters.** The AI cannot build a realistic schedule from goals alone. It must also know the person has classes on certain days, a job, a family. Context is what makes a plan feasible.

**Knowledge as a model of the person.** Each thing learned is recorded with a date, a source, and a level. When a situation calls for a skill the person has (say, calculus), the AI can include it in its suggestions. A *blind spot* is a goal that needs a skill the Mirror says the person does not have.

**Autodidact goals.** A goal such as "learn from this book" is broken by the engine into scheduled reading blocks, using the same goal-to-commitment link as everything else.

---

## 5. Behavior: how the AI thinks and acts

### Always aware, rarely thinking

A person is always perceiving but only deliberates when something warrants it. Asimilex works the same way, in two layers:

- **A cheap, always-running loop.** Plain code that receives events (a sensor reading, an email, a check-in), writes them to the Mirror, and evaluates simple rules. It costs almost nothing and runs 24/7.
- **The LLM, woken only on triggers.** No activity means no model call and no cost.

### Three kinds of triggers

1. **Reactive:** the person speaks to it, or an external event arrives (a new email).
2. **Rule-triggered:** a cheap check flags friction, such as a deadline at risk.
3. **Reflective:** on a schedule (for example weekly), the AI steps back, reads the whole Mirror, and looks for patterns across weeks.

### Reflection and self-improvement

The system should do more than watch; it should think. For example: the Mirror shows scheduled deep-work blocks being missed, afternoon energy dropping, and days fragmented into many small commitments. The reflective pass diagnoses fragmented focus, brings in relevant outside knowledge (such as Cal Newport's work on deep work), and proposes a change *with the evidence attached*. If the person accepts, the schedule rules change.

Rules for reflection:

- **Evidence required.** Every proposal cites what it saw in the Mirror. No evidence, no proposal.
- **Two kinds of proposal.** *Actions* (add or move an event) and *policy changes* (alter how schedules are built). Policy changes always require approval.
- **Versioned and reversible.** Policy changes run as time-boxed experiments, with a before/after comparison so the system learns whether its advice worked.
- **Capped.** A limited number of proposals per period, ranked by strength of evidence, so the system advises rather than nags.

Outside knowledge (what the AI knows from training) is kept distinct from the person's own knowledge (stored in the Mirror). The Mirror's job is to tell the AI which general knowledge applies to *this* person.

### Autonomy ladder

Trust is built in stages, and the stage depends on how costly a mistake would be.

| Level | Behavior | Example |
|---|---|---|
| **Observe** | Records and reports only | Notes a sleep trend |
| **Suggest** | Offers a recommendation with evidence | "Consider an earlier bedtime" |
| **Ask** | Prepares an action and waits for approval | Draft of a schedule change |
| **Auto** | Acts without asking, for low-stakes, reversible things only | Adding an urgent email deadline to the calendar |

Health advice, moving money, and controlling water or power remain at *Suggest* or *Ask* until the system has earned more trust over a long period.

### Interaction and personality

The person converses with the AI by text, and eventually by voice. It can summarize, answer, and carry out tasks. Its personality (guiding, a little cheeky) is a short persona prompt supplied by the engine, kept in its own file so it can be tuned without touching the data.

---

## 6. Architecture and deployment

### Components

```
 Connectors (inputs)  ->  Mirror (SQLite)  <->  Engine  ->  Proposals / Actions
   manual CLI              single file          reducers       approve / reject / auto
   calendar, email         local, private       rules          rendered Mirror.md view
   wearables, sensors                           LLM (swappable)
```

- **Connectors** are small programs that fetch or receive something from the outside world and write it to the Mirror. Every record carries a source and a de-duplication key, so re-running a connector never creates duplicates. Each record stores both *when it happened* and *when the system learned about it*, so the engine can distinguish "I slept fine" from "I haven't logged sleep in four days."
- **The Engine** computes state, evaluates rules, builds a compact context snapshot, calls the LLM, and stores its output as proposals. The LLM never gets raw database access; it receives a summary assembled by code.
- **The LLM** sits behind a single function, so Gemini, Claude, or a local model can be swapped by changing one file.
- **The Mirror view** is a generated `Mirror.md`, readable in Obsidian or VS Code.

### Deployment topology

- **MVP:** everything runs on one laptop, driven by a command-line tool.
- **Target:** an always-on headless server (an old laptop is sufficient) hosts the Mirror, the loop, the scheduler, and the LLM calls. Laptop, phone, and watch are thin clients that send input to the server and show its output.
- **Single writer.** Only the server process opens the database file. Clients talk to that process, never to the file directly.
- **Private access.** The server is reachable only over a private network (such as a VPN mesh) and is never exposed to the public internet.

### Devices and sensors

Every device or sensor is a connector. Adding a room sensor means adding a connector; the engine does not change. High-frequency data is stored per sensor and downsampled over time to keep the database small.

---

## 7. Technical decisions and data model

### Stack

- **Language:** Python 3.11+
- **Storage:** SQLite via the standard-library `sqlite3` module, with plain SQL
- **Interface:** a generated Markdown file (`Mirror.md`), viewed in Obsidian or VS Code
- **LLM:** behind one interface; free-tier Gemini initially

### Why SQLite

| Requirement | SQLite |
|---|---|
| One machine now, a server later | A single file; moving it is copying it |
| Several programs reading and writing | Supported with write-ahead logging enabled |
| Mixed data: structured records, free-text notes | Tables plus built-in full-text search |
| Search by meaning (knowledge layer, later) | Available via the sqlite-vec extension, no migration |
| Privacy | Local file, protected by disk encryption |
| Fail fast, no infrastructure | Nothing to install or run |

**Alternatives considered.** A graph database was rejected because the queries are tabular and time-based ("what happened this week", "what is due soon"), not multi-hop relationship traversals. Postgres/TimescaleDB adds a server to maintain and is worth it only with many concurrent writers or heavy sensor streams. DuckDB suits large analytical workloads, not constant small writes. Plain files would mean reimplementing queries by hand. Data can be exported to a larger system later if needed.

### Data modeling rule

- Data where **only the present matters** (goals, commitments) is stored as rows updated in place.
- Data where **history matters** (sleep, labs, sensor readings) gets one table per topic, with a new row for each reading.
- **Derived values** (sleep debt, averages, progress) are computed on demand and never stored.

### Initial schema

```sql
CREATE TABLE IF NOT EXISTS goals (
  id INTEGER PRIMARY KEY,
  title TEXT NOT NULL,
  why TEXT,
  deadline TEXT,
  priority INTEGER DEFAULT 3,      -- 1 = most important
  status TEXT DEFAULT 'active',
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sleep (
  id INTEGER PRIMARY KEY,
  night TEXT NOT NULL,             -- date the person went to bed (YYYY-MM-DD)
  bed_ts TEXT NOT NULL,
  wake_ts TEXT NOT NULL,
  energy INTEGER,                  -- 1-5, how the person felt on waking
  source TEXT NOT NULL DEFAULT 'manual',
  note TEXT,
  recorded_at TEXT NOT NULL,       -- when it was logged
  UNIQUE (night, source)           -- re-logging a night replaces it
);
```

Planned next: `commitments` (tasks linked to goals) and `proposals` (what the engine suggests, with evidence and autonomy level).

---

## 8. Roadmap

**MVP definition.** Done when one command each morning produces a brief ("what should I focus on today, and what is at risk?") that the person would actually act on.

**Build order**

1. Goals table, with commands to add and list goals
2. Commitments table, linked to goals
3. Sleep and energy table, with a daily log command
4. Context snapshot, LLM call, and the daily brief
5. Generated `Mirror.md` view
6. First real connector (calendar)
7. Scheduler and always-on loop
8. Reflective weekly review
9. Move to a headless server

**Tiers.** Tier 1 (goals, context, schedule, daily check-in) is enough to test the whole idea. Tier 2 adds knowledge, labs, and finances. Tier 3 adds live telemetry, wearables, smart home, and physical control.

---

## 9. Non-goals (for now)

- Graph databases, cloud sync, or hosted services
- Email, calendar, and lab connectors in the first build
- The knowledge layer
- Autonomous actions of any kind
- Voice and physical control

---

## 10. Open questions

- Which history data should be tracked first, beyond sleep?
- What exactly should the daily brief contain?
- How often will manual updates realistically happen, and which inputs can be automated first?
- How proactive should the AI be: interrupt when it sees a problem, or wait until asked?
- Where should the line sit for each action on the autonomy ladder?

---

## 11. Privacy and repository layout

The repository contains the **engine** only. Real life data stays local and is excluded by `.gitignore`.

```text
asimilex/
├── .gitignore          # excludes the database and generated Mirror.md
├── engine/             # code: schema, database access, (later) rules and LLM
├── cli.py              # command-line tool for entering data
├── mirror/             # the person's data: asimilex.db (private, ignored)
├── journal/            # public dev log; decisions and design only, no personal data
├── SPEC.md
├── LICENSE
└── README.md
```

Rules of thumb: never commit `mirror/*.db` or `Mirror.md`; ship `.example` files where a template is useful; keep personal details (health numbers, real deadlines, names) out of the public journal.
