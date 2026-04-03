# Runbook: Delivery Disruption Investigation

## Purpose

Use this runbook when regional delivery KPIs drop sharply or when support teams report broad last-mile disruption.

## Triage Signals

- delivery success rate below target by more than 5 percentage points
- on-time delivery rate below target by more than 8 percentage points
- repeated shipment failures with the same reason
- incident log entries with medium or high severity

## Investigation Workflow

1. Confirm the affected region and time window.
2. Review KPI summary tables to identify which metric moved and by how much.
3. Break down shipment events by failure reason, event type, and delivery-hour distribution.
4. Review incident logs for weather alerts, carrier outages, or routing interventions.
5. Compare with prior-day baseline to estimate whether the issue is isolated or persistent.

## Common Root Causes

- carrier capacity shortage during peak dispatch periods
- weather-related delays affecting route completion
- route reassignment mistakes during manual intervention
- backlog spillover from previous operational disruptions

## Recommended Response

- notify regional operations lead for high-severity drops
- assign backup carrier capacity if partner outage is confirmed
- trigger manual route review if reassignment error rates rise
- keep analyst in the loop when evidence is incomplete or conflicting

