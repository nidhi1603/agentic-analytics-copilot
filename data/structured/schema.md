# Structured Data Model

This project starts with four core business tables:

## 1. `daily_kpis`

Daily KPI summary by region and metric. This is the fastest table for KPI trend and anomaly questions.

## 2. `shipment_events`

Shipment-level operational events. This is the deeper table for investigation and SQL generation.

## 3. `incident_log`

Known incidents and operational disruptions that may explain KPI movement.

## 4. `metric_definitions`

Business definitions for metrics, owners, grain, and investigation hints.

This is a simple analytics-first model that keeps the first version easy to understand while still reflecting how enterprise teams organize trustworthy business data.

