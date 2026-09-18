## 📘 Documentazione Concettuale – View `dbops.vw_articoli_a_magazzino_prontezza`

> 👀 **Vedi anche**
>
> • [catalogo.articoli](/dbzero/catalogo/tabelle/articoli) — `gestito_a_magazzino`
> • [dbops.presidi](/dbzero/dbops/tabelle/presidi), [dbops.fn_conta_presidio](/dbzero/dbops/funzioni/fn_conta_presidio)
>
Guide: [Presidi e registri del debito](/guide/presidi-e-registri-del-debito) · brief `brief-db-modifiche-certe-ciclo-vendita-e-articolo` (§7) · brief `brief-db-magazzino-lotto-2-motore` (§4.8, D-L2-k)

---
### 🎯 Scopo Principale

(rev 2026-09-18 — Lotto 2 del magazzino)

**Il magazzino è pronto?** Una riga sola: `stato = MARCATI` se esiste almeno un articolo
attivo con `gestito_a_magazzino`, altrimenti `NESSUNO_MARCATO` (e `n_marcati`).

Esiste per una ragione precisa: al rilascio **nessun articolo** è gestito a magazzino (il
default è `false`, per sicurezza) e senza una spia il magazzino resterebbe un mobile vuoto
senza che nessun rosso lo dica. In `dbops.presidi` è iscritta con natura `ZERO`, colonna di
stato `stato` e stato atteso `MARCATI`: il conteggio guarda le righe *diverse* dall'atteso —
**lo zero suona, il pieno tace** — senza una natura nuova per un caso solo. Cadenza
`SETTIMANALE`: è una condizione di prontezza, non un incidente, e un allarme quotidiano su
una cosa già saputa si spegne. `catalogo.articoli` non ha row level security: perimetro
`LIBERO`.

Presidio: `db/pgtap/dbops/test-articoli-a-magazzino-prontezza-v1.sql`.

---

### Storia

* 2026-09-14 — decisa (brief modifiche certe, §7): si scrive col primo carico, non prima.
* 2026-09-18 — nasce con il Lotto 2 (`20260918-25`).

---

{% include-markdown "signature-core.md" %}
