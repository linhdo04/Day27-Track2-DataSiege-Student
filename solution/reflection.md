# Reflection

**Which fault types were hardest to catch, and why?**

The hardest cases were subtle numeric drift and lineage topology faults. A
small distribution, feature, or embedding shift can overlap normal variance,
so lowering a threshold enough to catch every instance would also create false
alarms. Lineage required a different kind of reasoning: the event payload's
declared input list was not the complete dependency contract. Detection had to
compare the observed graph with the expected upstream set for the job, rather
than treating the payload itself as the source of truth.

**What would you change about your cost/coverage tradeoff, if you had another pass?**

I used exactly one domain-specific metered call per event. This gives complete
coverage while staying within every phase budget, and avoids redundant checks.
With another pass and more representative clean history, I would maintain
robust rolling distributions per asset and use adaptive thresholds for numeric
signals. That could improve recall on subtle faults without broadly lowering
the published three-sigma limits. I would retain immediate alerts for discrete
contract and lineage violations because their false-positive risk is low.
