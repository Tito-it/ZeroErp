## 📘 Documentazione Concettuale – Vista `vendite.vw_dash_fatturazione_contratti`

> 👀 **Vedi anche**
>
Approfondimento tabelle e funzioni:
>
[vendite.contratti](/dbzero/vendite/tabelle/contratti)
> [config.stati_doc_contratti](/dbzero/config/tabelle/stati_doc_contratti)
> [vendite.fn_list_contratti_da_pushare](/dbzero/vendite/funzioni/fn_list_contratti_da_pushare)
>
Union e stock:
>
[vw_dash_fatturazione_documenti](vw_dash_fatturazione_documenti.md)
> [vw_dash_aperto_documenti](vw_dash_aperto_documenti.md)

---
### 🎯 Scopo Principale
(latest review 07-07-2026)
Resolver dell'area **CONTRATTI** per la famiglia dash fatturazione / Situazione
aperta (brief `brief-db-situazione-aperta` SA-1, decisione **DL-12**): **una riga
per contratto vivo**, **de-esplosa** (fino al 2026-07-07 era una riga per
contratto × mese coperto — l'asse mensile serviva alla 5-card, dismessa).
Area **a conteggi** (D-3), con **giudizio di transito SOSPESO** finché non
esiste il push ricorrente dei canoni.

---

### Semantica

| Aspetto | Regola |
|---------|--------|
| Grana | 1 riga per contratto con `esito IS DISTINCT FROM 'NEGATIVO'` (D-6 alla fonte) |
| **Giudizio sospeso (DL-12)** | `is_transitato` / `unita_transitate` / `motivo_fermo` = **NULL** — non "fermo", non "transitato": senza push ricorrente ogni contratto risulterebbe fermo in eterno (falso-allarme perenne). La bozza resta leggibile da `fase`/`stato_codice_interno` |
| `competenza_mese` | `NULL` (senza asse mese non ha significato) |
| `data_riferimento` | `valido_dal` = "in essere da" |
| Valori | `NULL` (area a conteggi, D-3); `unita_totali = 1` |
| `cliente_display` | Ragione sociale intestatario BA (`billing_account → soggetto_ruolo → soggetti`), nullable |

---

### Esempio d'uso

```sql
-- Stock contratti vivi per fase.
SELECT fase, count(*)
FROM vendite.vw_dash_fatturazione_contratti
GROUP BY fase;
```

---

### Note operative

* **Non interrogarla dal BE**: il backend passa da
  `vw_dash_fatturazione_documenti` (drill-down) / `vw_dash_aperto_*` (stock).
* **Backlog (Lente 2)**: i contratti **non vi compaiono** (`motivo_fermo NULL`
  → esclusi dal filtro `motivo_fermo IS NOT NULL`). Già prima erano fuori
  (entrambi i motivi erano `FISIOLOGICO`).
* **Riaccensione futura**: quando esisterà il push ricorrente, il predicato
  "canone del mese corrente generato" (EXISTS su `commesse_attivita` per
  `sorgente CONTRATTO + sorgente_uid + competenza_mese`, assistito da
  `ix_commesse_attivita_sorgente_competenza`) torna su
  `is_transitato`/`motivo_fermo` (`CANONE_NON_GENERATO` è **rimasto nel seed**
  di `config.motivi_fermo` apposta) e i contratti entrano anche in Lente 2 —
  contratto colonne identico, si riempie.
* RLS emittente applicata automaticamente (vista invoker su `vendite.contratti`).
* Test: `db/pgtap/vendite/test-vw-dash-fatturazione-v1.sql` (test 12-14) e
  `test-vw-dash-aperto-v1.sql`.

---

{% include-markdown "signature-core.md" %}
