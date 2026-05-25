---
name: project-offerte-commerciali-status
description: Stato sviluppo DB offerte commerciali (vendite schema) — Steps 1-8 applicati/pronti
metadata:
  type: project
---

Sviluppo dominio `vendite.offerte_commerciali` su branch `dev/db-tid`.

**Why:** Introdurre il predecessore tracciato del contratto (offerta → contratto 1:1 mono-utility, §5.1 analisi).

**How to apply:** Prima di proseguire verificare lo stato applicato sul DB; fare riferimento a `docs/it/dev/work-in-progress/analisi-offerta-commerciale-db.md` §8 per lo stato aggiornato.

| Step | Stato         | Migration / File                                             |
|------|---------------|--------------------------------------------------------------|
| 1    | APPLICATO     | CSV seeds sorgenti, stati, errori, fk_policy                 |
| 2    | APPLICATO     | `20260524-03`, `20260524-10`                                 |
| 3    | APPLICATO     | `20260524-05` .. `20260524-09`                               |
| 4    | APPLICATO     | `20260524-21`, `20260524-22`, `20260524-23`                  |
| 5    | APPLICATO     | CSV `sistema_codici.csv` (id=17)                             |
| 6    | APPLICATO     | `20260524-26`                                                |
| 7    | YAML PRONTO   | `20260524-27` — fn_crea_revisione_offerta(p_offerta_id, p_user) |
| 8    | YAML PRONTO   | `20260525-01` (ALTER contratti: offerta_id+UNIQUE, sorgente_tipo_id, sorgente_uid) + `20260525-02` (fn_push_offerta_a_contratto(p_offerta_id, p_pratica_id)) |
| 9    | TODO          | Suite pgTAP in `db/pgtap/vendite/offerte_commerciali/`       |

**Nota Step 8:** Il trigger `trgfn_contratti_snapshot_precontrattuali` si attiva AFTER INSERT su contratti e può creare un record in `contratti_utilities` dai precontrattuali. La funzione usa UPSERT (ON CONFLICT DO UPDATE) per sovrascrivere con i dati negoziati dell'offerta.

**Prossimo:** Step 9 — suite pgTAP completa in `db/pgtap/vendite/offerte_commerciali/`.
