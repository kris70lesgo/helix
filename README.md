# HELIX

### Coral-Powered Space Operations Intelligence Platform

HELIX is an AI-powered Space Operations Intelligence Platform that transforms fragmented orbital, launch, and space weather data into actionable mission intelligence.

Built on top of Coral's federated SQL runtime, HELIX enables operators, researchers, and analysts to investigate conjunction risks, correlate launch activity, monitor orbital congestion, and generate explainable operational assessments through multi-step AI investigations.

Unlike traditional satellite trackers, HELIX focuses on answering:

> What is happening in orbit?
>
> Why is it happening?
>
> What should operators pay attention to next?

---

## Why HELIX?

Earth's orbit is becoming increasingly congested.

Thousands of active satellites, frequent launches, and growing debris populations create a complex operational environment where understanding risk requires data from multiple disconnected systems.

Most tools can visualize orbital activity.

HELIX investigates it.

Using Coral as a unified intelligence layer, HELIX correlates:

* Satellite conjunction events
* Launch schedules and mission activity
* Space weather conditions
* Satellite metadata
* Historical orbital trends

to produce operational assessments that help explain elevated risk conditions and emerging orbital threats.

---

## Key Features

### AI Operations Investigation Engine

HELIX includes a deterministic multi-step investigation engine.

Instead of generating a simple summary, the system:

1. Detects operational anomalies
2. Builds an investigation strategy
3. Executes approved Coral queries
4. Correlates evidence across sources
5. Generates operational assessments
6. Produces recommendations

Every investigation is transparent, explainable, and traceable.

---

### Coral-Powered Intelligence Layer

HELIX uses Coral as its federated operational query engine.

Connected sources include:

* HELIX Orbital Intelligence Database
* NOAA Space Weather
* Launch Library
* Space-Track

Coral enables:

* Query Anything as SQL
* Cross-Source Joins
* Federated Query Execution
* Source Discovery
* Local-First Intelligence Workflows

---

### Multi-Step Operational Investigations

HELIX investigates questions such as:

* Why are conjunction risks elevated today?
* Which satellites repeatedly appear in high-risk events?
* Are upcoming launches contributing to orbital congestion?
* Is space weather affecting operational risk?
* Which orbital regions are becoming increasingly congested?

Investigations execute through a structured reasoning workflow rather than a single query-and-summary approach.

---

### Interactive Mission Control Interface

HELIX combines:

* Real-time orbital visualization
* Conjunction monitoring
* Operational alerts
* AI investigations
* Coral query tracing
* Mission intelligence summaries

into a unified mission-control experience.

---

### Passive Operational Monitoring

HELIX continuously surfaces:

* High-risk conjunctions
* Elevated conjunction density
* Launch pressure indicators
* Space weather conditions
* Operational anomalies

Operators can immediately launch AI investigations directly from surfaced alerts.

---

## Architecture

```text
Space-Track
      │
      ▼
NOAA Space Weather
      │
      ▼
Launch Library
      │
      ▼
HELIX Orbital Database
      │
      ▼
┌─────────────────────────────┐
│           Coral             │
│ Federated SQL Query Engine  │
└─────────────┬───────────────┘
              │
              ▼
┌─────────────────────────────┐
│ Multi-Step Investigation    │
│ Engine                      │
│                             │
│ • Query Planning            │
│ • Correlation               │
│ • Assessment Generation     │
│ • Recommendations           │
└─────────────┬───────────────┘
              │
              ▼
┌─────────────────────────────┐
│ HELIX Mission Control       │
│ Intelligence Console        │
│ 3D Operational Globe        │
└─────────────────────────────┘
```

---

## Example Investigation

User asks:

```text
Why are conjunction risks elevated today?
```

HELIX performs:

```text
[1] Querying conjunction database
[2] Detecting orbital clustering
[3] Identifying repeated satellite involvement
[4] Correlating recent launch activity
[5] Evaluating NOAA space weather
[6] Comparing historical density trends
[7] Generating operational assessment
[8] Producing recommendations
```

Result:

```text
Assessment:
Elevated conjunction density appears correlated with
recent deployment activity within large satellite
constellations.

Space weather conditions remain nominal and are
unlikely to be a significant contributing factor.

Recommendation:
Continue monitoring congestion clusters over the
next 12–24 hours.
```

---

## Built With

### Frontend

* Next.js
* React
* TypeScript
* Three.js
* react-globe.gl

### Backend

* FastAPI
* Python
* SQLite

### Intelligence Layer

* Coral
* Coral SQL Runtime
* Coral MCP
* Federated Query Engine

### Orbital Computation

* SGP4
* SciPy KDTree

### AI

* Gemini 2.5 Flash
* OpenRouter
* Structured Investigation Planner


## Mission

HELIX was built to move beyond satellite visualization and toward operational understanding.

As orbital activity continues to increase, operators need systems that can investigate, correlate, and explain emerging risks across multiple data sources.

HELIX combines aerospace analytics, AI investigations, and Coral-powered data federation into a single operational intelligence platform.

Built for the Coral Hackathon.
Powered by Coral.
Designed for the future of space operations.
