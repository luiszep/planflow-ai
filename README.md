# PlanFlow AI — Floor Plan Iteration Demo

Single-file desktop demo for AI-assisted floor-plan iteration in 2D and 3D.

## Overview

PlanFlow explores how a user can iterate on a simple residential floor plan through prompt-like changes — for example swapping a flex room for an office or expanding a kitchen — and immediately see the layout update.

The application is intentionally lightweight: the full demo lives in `planflow_app.py`.

## What it demonstrates

- PyQt5 desktop UI design with tabbed 2D/3D iteration views
- Rule-based interpretation of simple layout-change prompts
- Matplotlib-based plan rendering embedded in a desktop application
- Rapid prototyping of an AI-assisted design workflow without a backend

## Run it

```bash
python planflow_app.py
```

Requirements are the Python packages imported at the top of `planflow_app.py`, principally PyQt5, NumPy, and Matplotlib.

## Repository contents

- `planflow_app.py` — complete demo application: room model, prompt rules, and 2D/3D UI.

## Status

Prototype/demo. Included as a compact example of product prototyping and human-in-the-loop design tooling, not as a production CAD system.
