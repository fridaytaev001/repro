# Repro

Turn vague website complaints into independently verified bug reproductions, runnable regression tests, and optional tested repairs.

Track: **Done Means Done**.

- [Technical design](Repro_Design_Doc.md)
- [Build plan](Repro_Tickets.md)
- [Linear project](https://linear.app/ali-madinovich/project/repro-308900fec3ae/issues)

Implementation is delivered in six chunks, each on a feature branch with a PR for owner approval before merging to main. Chunk 1 builds the original demo store, a disclosed seeded checkout defect, and durable report intake. Autonomous Crusoe investigation is a later milestone.

Never commit credentials, run artifacts, or customer data. `.env.example` documents server-only configuration.
