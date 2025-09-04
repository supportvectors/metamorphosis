
# Role Overview

I’m a Software Engineer on the Data Platform team doing a lot of Spark/SQL/Airflow/Kafka and also some ad‑hoc analysis when folks need it. My day‑to‑day is keeping the pipelines green and adding features that people request. Sometimes I jump into production issues. I also write some documentation although I’m not sure who reads it. I think the role is mostly about making sure the data lands so others can do their work.

# Key Projects (possibly not in order)

## Customer 360 (Batch, Delta/SCD)

- I worked on the Customer 360 thing again. The main part was redoing the SCD logic so it handles late records better. I used Spark SQL with ROW_NUMBER() and MERGE INTO and some window functions. We also changed partitioning to something that is more stable (ingest date + customer id). I think it made reads faster for BI.
- I refactored a big UDF that was doing parsing into a regular SQL expression. This was mostly about simplicity because UDFs can be slow. The job ran faster after this but I didn’t measure it as precisely as I should have. My rough estimate was “noticeably quicker,” maybe 20–30% on average runs, but I’d need to double‑check the dashboards.
- There was a dedup step that used to drop some valid records occasionally (edge cases when the same key showed up in different partitions). I changed the logic to be more deterministic. I think it’s better now and less confusing for on‑call.
- I wrote a long doc on how SCD2 works in our setup. It might be too long; I didn’t have time to trim it down. Also there are a few screenshots that probably don’t add much.

## Streaming Ingestion Stabilization (Kafka → Delta)

- We had issues with duplicate events and some lag spikes. I set up dropDuplicates with a composite key (event id + timestamp Bucket), and added a dead‑letter table for malformed events. This should make things cleaner for downstream teams.
- I tweaked the trigger to micro‑batch more frequently during high traffic and less during off hours. This seemed to help, although I haven’t fully documented the thresholds. We may still see lag when a partner sends a dump at once.
- Checkpointing was getting out of sync on occasion (mostly due to deploys overlapping with high volume). I moved the checkpoint path and added some guardrails to avoid concurrent writers. We haven’t had the same incident since, to my knowledge.
- I wanted to add auto‑scaling based on lag, but didn’t finish. I started a draft proposal but then other work came in. It’s still on my list.

## Data Quality / Expectations

- I added Great Expectations tests to a few tables that kept getting questions (nulls, uniqueness, referential stuff). The idea is to fail fast before consumers see bad data. Some of these tests might be too strict; a few times we had false alarms and I had to tune them down.
- I wrote a basic playbook that says who owns which test and what to do when things fail. It’s a Google Doc and probably should be moved to the repo. I have not added CI to verify the suites yet.
- Schema changes from upstream still surprise us occasionally. I began documenting a simple “contract” (just a YAML with fields and a change process), but it’s early and not fully enforced.

## Orchestration / Airflow

- I own (co‑own) some Tier‑1 DAGs. Most days it’s fine, but we get random breaks when a secret rotates or a vendor makes a change. I added some quick pre‑checks for credentials which at least fail fast instead of 40 minutes into a run.
- I also added a small compaction DAG that merges small files in off‑peak windows. It runs nightly but sometimes it runs too aggressively; I still need to fine‑tune the thresholds so we don’t spend extra compute.

# Impact (some of this needs better numbers)

- Customer 360 job overall runtime: I think it’s faster than before. I saw a drop on a couple of weekly reports (maybe ~30% on those days), but I didn’t create a formal baseline vs. after. I should have created a dashboard or at least pinned the timeframe and cluster configs. I will do that next cycle.
- Streaming duplicates: anecdotal reports say there are fewer. Analytics said things “look cleaner.” I did a sample check over two days and saw almost none, but it wasn’t a statistically significant test. I need to define what “duplicate” means too (depending on field set).
- Incidents/MTTR: feels lower this half, but I don’t have the exact number. We had two noticeable incidents that were fix‑forward quickly. I should track this better.
- Costs: We migrated some jobs to Photon which probably helps. I don’t want to overstate the savings. My guess is we shaved some percent, but I didn’t tie it to a clean A/B. I plan to add job‑level cost tags so I can prove this in the future.

# Collaboration and Communication

- I worked closely with analysts when they were blocked by slow queries. Sometimes I rewrote SQL for them (mostly CTEs and window functions to be more efficient). I probably spent too much time on “quick wins” and context switching.
- I offered to mentor a junior teammate on Spark partitioning and joins. We met a few times and went through examples. I think it helped, but I didn’t ask for feedback yet, so I’m not sure.
- I wrote long docs on SCD2 and the streaming changes. Feedback was that they are helpful but “dense.” I will try to put a TL;DR and some diagrams at the top next time. Right now the good stuff is buried.
- I could have been more proactive in socializing the auto‑scaling idea before letting it sit in a draft. Lesson learned: share early even if it’s not perfect.

# Reliability and On‑Call

- I was primary on‑call for a couple of weeks and secondary a few other times. We had a schema drift issue that broke a job. I added a pre‑ingest schema check to catch it earlier. That seemed to prevent a repeat.
- There was also a secret rotation that caused a silent failure. I added a check for credentials before doing the heavy lifting. It’s a basic thing but it avoids wasted compute.
- I think we handled pages reasonably fast. Sometimes I spent too long trying to find the “best fix” instead of the quickest mitigation. I’m working on balancing that better.

# Things I’m Proud Of (even if small)

- Removing two Python UDFs from a hot path and replacing them with SQL. The code looks simpler and it runs faster (again, I should have measured more rigorously).
- Making dedup rules easier to explain to others – now there’s a clear tie‑breaker instead of “it depends.”
- Setting up a dead‑letter table for events – it’s not fancy, but having a place to put bad data helps a lot.

# What Didn’t Go Well / Mistakes

- I chased a few optimizations (like Bloom filters) before verifying whether they mattered for our queries. It didn’t hurt, but it probable wasn’t the best use of time.
- I left the auto‑scaling proposal unfinished. It kept slipping behind “urgent” tasks and now it’s just a draft. I should have asked for help or split it smaller.
- Documentation length: my SCD2 doc is longer than necessary. It repeats itself and explains basics that the audience already knows. I need to be more concise and front‑load the decisions.
- I sometimes forgot to add owners to expectation suites, which meant alerts went nowhere. We fixed a couple of those, but I should codify this in the pipeline templates.

# Feedback I Heard (paraphrased)

- “Your code is readable but your docs are heavy; a summary up front would be nice.”
- “The streaming changes helped a lot; fewer duplicates and better latency, but please measure and publish the before/after.”
- “Thanks for jumping on incidents quickly.”
- “Spend less time doing small query rewrites for teams and push reusable examples or office hours.”

# Goals for Next Cycle (not fully SMART yet)

- Finish and ship the auto‑scaling for Kafka consumer lag. Define thresholds, a rollback plan, and a simple test harness.
- Add an actual dashboard for job runtime and cost by job, with before/after markers for meaningful changes (Photon, partitioning, etc.).
- Trim large docs by ~30% and put a TL;DR + diagrams at the top so people can skim. I might add an appendix for the deep dives so the main doc is shorter.
- Improve expectation suite ergonomics: a CLI to scaffold tests with owners + CI checks to block unowned suites.
- Be more explicit with trade‑offs in intake forms (latency vs. cost vs. freshness) to push back on scope creep earlier.

# Extra Details (probably too much, but keeping for completeness)

- On the SCD2 job, I changed the partitioning to ingest_date and Z‑ORDER by customer_id. We might be over‑optimizing here. Some tables get optimized weekly, others nightly. I still need to write down a policy instead of guessing.
- I tested ROW_NUMBER() vs. DENSE_RANK() for dedup and ROW_NUMBER() seemed easier to reason about. DENSE_RANK() could also work. I don’t think this matters much for end users but I wanted to note it.
- For streaming, I used dropDuplicates with an hour bucket. If we get events outside that window it could still duplicate or drop; we should revisit the bucket size. It’s a trade‑off between memory and correctness.
- The dead‑letter table has a basic error code system (like JSON_PARSE_ERROR), but I didn’t normalize it across pipelines yet. Also, some errors are lumped into “UNKNOWN.” I need to fix that taxonomy.

# Random Notes (duplicated in places)

- I think overall costs went down after Photon but I don’t have the hard number. I should collect it. I think overall costs went down after Photon but I don’t have the hard number. I should collect it. (Yes, repeating myself here to remember.)
- Backfills are easier now because the reprocess window is smaller. Still need to confirm behavior when two sources disagree within the same window.
- On‑call: when in doubt, mitigate first (pause, rerun smaller slice), then root cause. I sometimes flip that order.

# Another Pass at Impact (still fuzzy)

- Customer 360: faster by something like a third on average (rough estimate). Better determinism for dedup. Fewer “where did this record go?” questions, I think.
- Streaming: duplicates appear lower and latency is lower, but I need to define latency buckets (p90/p95) and measure across a consistent week, not cherry‑picked days.
- Data quality: expectations are in place but coverage is low (maybe 10–20% of key tables). Alerting improved but still uneven.

# Conclusion (could be shorter)

This cycle I kept the pipelines moving forward, made Customer 360 more reliable and faster, stabilized streaming somewhat, and started better data quality habits. The biggest gaps were around measurement, documentation style/length, and finishing the auto‑scaling work. I want to do a better job socializing proposals earlier and pushing for tight, clear metrics (and also saying “no” or “later” when small requests pile up). Overall, I feel I met expectations and in some areas was above, but it’s not uniform. Next cycle I plan to make the work more measurable and more shareable so others can benefit from it without me having to jump in each time.



