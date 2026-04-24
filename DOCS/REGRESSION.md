# {{PROJECT_DISPLAY_NAME}} — Regression Tests

Cross-step smoke test definitions. Run at the start of Phase 6 for every pipeline step.
Agents add tests here during Phase 7F after each step merges.

---

## Step 0 smoke tests

- [ ] `GET /health` returns 200
- [ ] Frontend loads at localhost:3000 without console errors
- [ ] Docker compose starts cleanly (`docker compose ps` shows all services healthy)

---

*(Add smoke tests here as steps complete)*
