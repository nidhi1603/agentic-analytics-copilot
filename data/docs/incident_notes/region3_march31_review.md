# Incident Review Note: Region 3 Delivery Drop on 2026-03-31

## Summary

Region 3 experienced a sharp decline in delivery success rate and on-time delivery rate on 2026-03-31. The disruption aligned with a primary carrier capacity shortage and severe rainfall during the afternoon dispatch window.

## Supporting Observations

- failed deliveries increased with `carrier_capacity_shortage` as the most frequent failure reason
- delayed deliveries rose alongside higher average delivery hours
- incident logs recorded both a carrier outage and weather alert on the same date

## Mitigation Taken

- backup carrier allocation was enabled on 2026-04-01
- manual rerouting was applied to high-priority shipments
- operations team monitored backlog clearance the following day

## Follow-up Note

Recovery started on 2026-04-01, but delivery success rate remained below target, suggesting partial rather than complete remediation.

