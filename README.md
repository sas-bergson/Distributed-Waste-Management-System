# Distributed Waste Management System (DWMS)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Contributions Welcome](https://img.shields.io/badge/contributions-welcome-brightgreen.svg)](CONTRIBUTING.md)
[![Capstone Project](https://img.shields.io/badge/Capstone-Distributed%20Systems%20%26%20Cloud-blue)]()

> A cloud‑native, microservices‑based platform that **geolocates waste in real time**, renders it on a **color‑coded map** encoding waste volume and road accessibility, and exposes a **cloud service to view, update, and dispatch SPF collection requests** from any device.

---

## Table of Contents

- [Project Objectives](#project-objectives)
- [Glossary](#glossary)
- [Architecture Overview](#architecture-overview)
- [Map & Color Palette Specification](#map--color-palette-specification)
- [Key Features](#key-features)
- [Technology Stack](#technology-stack)
- [Repository Structure](#repository-structure)
- [Getting Started](#getting-started)
- [Usage & Scenarios](#usage--scenarios)
- [How to Contribute (Students & Forks)](#how-to-contribute-students--forks)
- [Roadmap & Milestones](#roadmap--milestones)
- [Scaling Limits & Where This Breaks](#scaling-limits--where-this-breaks)
- [License](#license)
- [Acknowledgements](#acknowledgements)

---

## Project Objectives

This capstone is defined by three objectives. Every service, endpoint, and map style must trace back to at least one of them.

| # | Objective | What it means in practice | Primary deliverables |
|---|-----------|---------------------------|----------------------|
| **1** | **Collect waste‑location information** | Capture the geographic position of waste deposits plus descriptive attributes (estimated volume/amount, waste type, timestamp, reporter) from multiple sources: field agents, citizens, and IoT/smart‑bin sensors. | Location Reporting Service, mobile/web reporting form, ingestion API, PostGIS storage |
| **2** | **Produce a color‑coded map of waste volume and road condition** | Render all reported waste locations on an interactive map using a **defined, documented color palette** that encodes *how much* waste is present and *how accessible* the road leading to it is. | Map Service (GeoJSON/tiles), styling spec, legend component, road‑condition data model |
| **3** | **Provide a cloud service to view, update the map and request the SPF in real time** | A multi‑tenant cloud API + live channel allowing clients to (a) view the current map, (b) create/modify waste and road reports, and (c) submit a collection request to the **SPF** for a specific waste location and track its status without page refresh. | API Gateway, SPF Request Service, real‑time channel (WebSocket/SSE), dashboard |

> **Traceability rule:** every pull request should state which objective(s) it advances. Use the PR template field *"Objective(s): 1 / 2 / 3"*.

---

## Glossary

| Term | Meaning |
|------|---------|
| **Waste location** | A georeferenced point (or small polygon) where waste has been deposited or accumulated, with attributes: estimated amount, waste type, reporter, timestamp, status. |
| **Road condition** | The accessibility of the road/path serving a waste location (e.g., *good/paved*, *degraded*, *unpaved*, *impassable*). Determines which vehicle can service it. |
| **SPF** | The **waste‑collection service provider** — the operator responsible for physically collecting waste (e.g., the municipal cleansing service). Requests are dispatched to the SPF from this platform. |
| **SPF request** | A formal, timestamped dispatch of the SPF to a specific waste location, with a lifecycle: `REQUESTED → ASSIGNED → IN_PROGRESS → COLLECTED` (or `REJECTED` / `CANCELLED`). |
| **Amount / volume bucket** | A coarse classification of waste quantity (see [palette spec](#map--color-palette-specification)) rather than a precise measurement, to keep field reporting fast. |

---

## Architecture Overview

DWMS is a **cloud‑hosted microservice platform** with an optional edge tier for sensor capture. Services are independently deployable so ingestion volume, map rendering load, and request‑tracking traffic can scale separately.

```mermaid
flowchart LR
    subgraph Clients
        C1["Citizen / Field Agent<br/>Mobile + Web"]
        C2["Operations Dashboard"]
        C3["IoT Smart Bins"]
    end

    subgraph Cloud ["Cloud Platform (Microservices)"]
        GW["API Gateway<br/>Auth · Rate limiting"]
        LOC["Location Reporting<br/>Service (Obj. 1)"]
        GEO["Geo Store<br/>PostGIS"]
        MAP["Map Service<br/>GeoJSON / tiles (Obj. 2)"]
        STYLE["Palette & Style<br/>Config (Obj. 2)"]
        SPF["SPF Request Service<br/>Dispatch lifecycle (Obj. 3)"]
        RT["Real‑Time Channel<br/>WebSocket / SSE (Obj. 3)"]
        NTF["Notification Worker<br/>Email / SMS / push"]
    end

    C1 -->|HTTPS| GW
    C2 <-->|HTTPS + WS| GW
    C3 -->|MQTT| GW

    GW --> LOC
    LOC --> GEO
    GEO --> MAP
    STYLE --> MAP
    GW --> SPF
    SPF --> NTF
    LOC --> RT
    MAP --> RT
    SPF --> RT
    RT <-->|live updates| C2
    RT <-->|live updates| C1
