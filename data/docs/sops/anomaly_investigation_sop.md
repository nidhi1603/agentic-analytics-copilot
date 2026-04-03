# SOP: KPI Anomaly Investigation

## Goal

Provide a standard process for investigating KPI anomalies using both metric tables and operational context.

## Standard Steps

1. Confirm that the KPI movement exceeds the anomaly threshold.
2. Identify whether the movement is isolated to one region, one metric, or multiple metrics.
3. Pull supporting evidence from shipment-level operational data.
4. Check for known incidents, policy exceptions, or recent operational changes.
5. Form one or more hypotheses and rank them by evidence strength.
6. Escalate when the evidence does not support a clear conclusion.

## Evidence Standard

Analysts should not claim a root cause unless at least two forms of evidence align, such as:

- shipment failure pattern plus incident log
- KPI movement plus documented runbook guidance
- repeated operational issue plus historical pattern

## Escalation Rule

Escalate to analyst review when:

- evidence is missing
- evidence conflicts across sources
- the confidence of the explanation is low
- the metric impact crosses a high-severity threshold

