---
name: project-offerte-commerciali-status
description: Stato sviluppo DB offerte commerciali — Steps 1-9 completati + fn_available_actions_offerta
metadata:
  type: project
---

Sviluppo dominio `vendite.offerte_commerciali` su branch `dev/db-tid`.

**Why:** Introdurre il predecessore tracciato del contratto (offerta → contratto 1:1 mono-utility, §5.1 analisi).

**How to apply:** Prima di proseguire verificare lo stato applicato sul DB; fare riferimento a `docs/it/dev/work-in-progress/analisi-offerta-commerciale-db.md` §8 per lo stato aggiornato.

| Step | Stato       | Migration / File                                             |
|------|-------------|--------------------------------------------------------------|
| 1    | APPLICATO   | CSV seeds sorgenti, stati, errori, fk_policy                 |
| 2    | APPLICATO   | `20260524-03`, `20260524-10`                                 |
| 3    | APPLICATO   | `20260524-05` .. `20260524-09`                               |
| 4    | APPLICATO   | `20260524-21`, `20260524-22`, `20260524-23`                  |
| 5    | APPLICATO   | CSV `sistema_codici.csv` (id=17)                             |
| 6    | APPLICATO   | `20260524-26`                                                |
| 7    | YAML PRONTO | `20260524-27` — fn_crea_revisione_offerta                    |
| 8    | YAML PRONTO | `20260525-01` (ALTER contratti) + `20260525-02` (fn_push_offerta_a_contratto) |
| 9    | YAML PRONTO | `20260526-01` (fn_available_actions_offerta) + CSV aggiornato + pgTAP 9 test |

**Step 9 — fn_available_actions_offerta (2026-05-26):**
- CSV `stati_doc_offerte_transizioni.csv` aggiornato: `requires_motivazione` su tutte le transizioni, `severity success` su emetti, `requires_confirm true` su accetta.
- Migration `20260526-01-create-fn-available-actions-offerta-mctit.yaml` (20_code/script, `runOnChange:true`).
- pgTAP: `db/pgtap/script/test-fn-available-actions-offerta-v1.sql` (9 test: NULL, BOZZA, EMESSA, ACCETTATA±contratto, RIFIUTATA).
- Doc: `docs/it/dbzero/script/manual/fn_available_actions_offerta.md`.

**Prossimo:** BE cabla `offerte_repository.py` + `offerte_service.py` + `OffertaDrawer.vue` (drop computed drawerActions).
