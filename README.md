# ARGUS

### AI-Powered Space Operations Intelligence Platform

ARGUS is an AI-native Space Operations Intelligence Platform that transforms fragmented orbital, launch, and space weather data into actionable operational intelligence.

Built on top of Coral's federated SQL query engine, ARGUS enables mission operators, researchers, and analysts to investigate conjunction risks, correlate launch activity, monitor orbital congestion, and generate explainable operational assessments through a unified intelligence workflow.

---

## Overview

Earth's orbit is becoming increasingly congested.

With thousands of active satellites, frequent launches, and growing orbital debris, operators need more than visualization—they need intelligence.

ARGUS combines:

* Real-time satellite tracking
* Conjunction detection
* Orbital risk analysis
* Launch intelligence
* Space weather monitoring
* Multi-source operational investigations
* AI-assisted mission assessments

into a single operational platform.

Unlike traditional satellite trackers, ARGUS acts as an operational investigation system capable of correlating information across multiple aerospace data sources and producing explainable assessments.

---

## Why ARGUS?

Most space monitoring tools answer:

> "What is happening?"

ARGUS answers:

> "Why is it happening?"

and

> "What should operators pay attention to next?"

Using Coral as the intelligence layer, ARGUS performs cross-source investigations that connect:

* Conjunction events
* Launch activity
* Satellite metadata
* Orbital congestion
* Space weather conditions

into a unified operational picture.

---

## Key Features

### Real-Time Orbital Monitoring

Track and visualize thousands of objects orbiting Earth in real time.

* Active satellites
* Orbital debris
* Constellations
* Dynamic orbit propagation

---

### Conjunction Detection Engine

Identify close approaches between orbital objects using efficient spatial analysis.

Metrics include:

* Miss distance
* Relative velocity
* Time of Closest Approach (TCA)
* Risk classification

Risk levels:

* LOW
* MEDIUM
* HIGH
* CRITICAL

---

### AI Operations Agent

ARGUS includes a deterministic multi-step investigation engine.

Instead of generating a single summary, the system:

1. Detects operational anomalies
2. Builds investigation plans
3. Executes approved Coral queries
4. Correlates findings
5. Generates operational assessments
6. Produces recommendations

---

### Coral-Powered Intelligence Layer

ARGUS uses Coral as its federated operational query engine.

Connected sources include:

* AEGIS Core Orbital Data
* NOAA Space Weather
* Launch Library
* Space-Track

All sources become queryable through a unified SQL interface.

---

### Cross-Source Investigations

Example investigation:

> Why are conjunction risks elevated today?

ARGUS automatically:

* Analyzes conjunction density
* Identifies repeated satellite involvement
* Correlates recent launch activity
* Evaluates geomagnetic conditions
* Produces an operational assessment

---

### Investigation Timeline

Every investigation includes:

* Live progress tracking
* Query execution trace
* Source visibility
* Confidence scoring
* Recommendation generation

This provides a transparent and explainable operational workflow.

---

### Passive Operational Alerts

ARGUS continuously surfaces:

* Elevated conjunction density
* High-risk conjunction events
* Launch pressure indicators
* Space weather anomalies

Operators can immediately launch investigations from detected alerts.

---

## Architecture

```text
                    ┌────────────────────┐
                    │    Space-Track     │
                    └─────────┬──────────┘
                              │

                    ┌────────────────────┐
                    │ NOAA Space Weather │
                    └─────────┬──────────┘
                              │

                    ┌────────────────────┐
                    │   Launch Library   │
                    └─────────┬──────────┘
                              │

                    ┌────────────────────┐
                    │   AEGIS Core DB    │
                    └─────────┬──────────┘
                              │

                ┌──────────────────────────┐
                │       Coral Engine       │
                │ Federated SQL Runtime    │
                └────────────┬─────────────┘
                             │

                ┌──────────────────────────┐
                │ Investigation Engine     │
                │ Query Planner            │
                │ Assessment Generator     │
                └────────────┬─────────────┘
                             │

                ┌──────────────────────────┐
                │ ARGUS Intel Console      │
                │ Interactive 3D Globe     │
                └──────────────────────────┘
```

---

## Technology Stack

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
* Coral Source Federation
* Coral MCP

### Orbital Computation

* SGP4
* SciPy KDTree

### AI

* Gemini 2.5 Flash
* OpenRouter
* Structured Investigation Planner

---

## Data Sources

### AEGIS Core

Internal orbital intelligence database.

Includes:

* Satellites
* Conjunction events
* Risk classifications
* Relative velocity data

---

### NOAA Space Weather

Provides:

* Geomagnetic activity
* Solar storm information
* Environmental space conditions

---

### Launch Library

Provides:

* Upcoming launches
* Mission schedules
* Launch providers
* Vehicle information

---

### Space-Track

Provides:

* Orbital object metadata
* Satellite catalog information
* TLE data

---

## Example Operational Questions

ARGUS can investigate questions such as:

### Operational Risk

* Why are conjunction risks elevated today?
* Which satellites repeatedly appear in high-risk events?
* What are the highest-risk conjunctions in the next 48 hours?

### Launch Intelligence

* Which upcoming launches overlap with elevated conjunction pressure?
* Are launch windows contributing to orbital congestion?

### Environmental Analysis

* Are current space weather conditions contributing to risk?
* Is geomagnetic activity affecting orbital conditions?

### Historical Context

* Which satellites are frequent contributors to conjunction events?
* How has conjunction density changed over time?

---

## Sample Investigation Flow

User Prompt:

```text
Why are conjunction risks elevated today?
```

Investigation Steps:

```text
[1] Querying conjunction database
[2] Detecting orbital clustering
[3] Identifying repeated satellite involvement
[4] Correlating recent launch activity
[5] Evaluating space weather conditions
[6] Comparing historical density trends
[7] Generating operational assessment
[8] Producing recommendations
```

Result:

```text
Assessment:
Elevated conjunction pressure appears correlated
with increased Starlink deployment activity.

Space weather conditions remain nominal and are
unlikely to be a significant contributing factor.

Recommendation:
Continue monitoring congestion clusters over the
next 12–24 hours.
```

---

## Coral Usage

ARGUS demonstrates several core Coral capabilities:

* Query Anything as SQL
* Cross-Source Joins
* Federated Query Execution
* Local-First Intelligence
* Source Discovery
* Multi-Source Agent Workflows
* MCP Integration
* Operational Investigations

---

## Future Roadmap

Planned improvements include:

* Collision probability estimation
* Historical mission intelligence archives
* Advanced anomaly detection
* Real-time monitoring dashboards
* Investigation replay mode
* Automated alert escalation
* Enhanced orbital forecasting
* Multi-operator collaboration

---

## Mission

ARGUS aims to make space situational awareness more accessible, explainable, and actionable by combining orbital analytics, operational intelligence, and AI-assisted investigations into a single platform.

As orbital activity continues to grow, the need for intelligent monitoring systems becomes increasingly important.

ARGUS is built to help operators move beyond visualization and toward understanding.

---

Built for the Coral Hackathon.
Powered by Coral.
Designed for the future of space operations.
