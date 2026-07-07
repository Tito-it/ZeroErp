## 📘 Documentazione Concettuale – Vista `vendite.vw_dash_fatturazione_offerte`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
>
[vendite.offerte_commerciali](/dbzero/vendite/tabelle/offerte_commerciali)
> [vendite.contratti](/dbzero/vendite/tabelle/contratti) (figlio via `offerta_id`)
> [vendite.ordini](/dbzero/vendite/tabelle/ordini) (figlio via `documento_origine_*`)
> [config.stati_doc_offerte](/dbzero/config/tabelle/stati_doc_offerte)
>
Union e aggregata:
>
[vw_dash_fatturazione_documenti](vw_dash_fatturazione_documenti.md)
> [vw_dash_aperto_documenti](vw_dash_aperto_documenti.md)

---
### 🎯 Scopo Principale
(latest review 03-07-2026)
Resolver dell'area **OFFERTE** per la Dashboard Fatturazione
(brief-design-dashboard-fatturazione §5, Fase 1): una riga per offerta,
**a conteggi** (decisione D-2: niente valore in euro in v1 — le righe offerta
sono eccezioni al listino, non hanno totale di testata). `valore_* = NULL`,
`unita_totali = 1`, `unita_transitate = 0/1`.

---

### Semantica

L'offerta **non ha uno stato post-push** (resta `ACCETTATA`): il transito si
legge dai **figli**, in XOR permanente.

| Aspetto | Regola |
|---------|--------|
| Figlio contratto | `contratti.offerta_id` (UNIQUE `uq_contratti_offerta_id`); vivo se `NOT is_abortito_snapshot` |
| Figlio ordine | `ordini.documento_origine_tipo = 'OFFERTA'` + `documento_origine_id` (UNIQUE parziale); vivo se esito ≠ `NEGATIVO`. Il literale `'OFFERTA'` è un valore dell'enum CHECK di colonna, non un codice di catalogo (§6d) |
| `is_transitato` | Esiste un figlio **vivo** |
| Competenza | Mese di `COALESCE(validita_dal, data_emissione, data_insert)` |
| `is_abortito` | `esito = 'NEGATIVO'` (RIFIUTATA / ANNULLATA / SUPERATA secondo il seed D1) |
| `motivo_fermo` | `DOC_BOZZA` · `IN_ATTESA_ACCETTAZIONE` (EMESSA) · `SENZA_FIGLIO` (accettata, nessun figlio) · `FIGLIO_ABORTITO` (figlio generato ma annullato) |
| `cliente_display` | Ragione sociale intestatario istanza (`istanze_utilities → soggetti`, path `vw_offerte_commerciali_lista`), nullable |

---

### Esempio d'uso

```sql
-- Offerte "bloccate": figlio annullato, XOR permanente -> serve una revisione.
SELECT codice, stato_codice, competenza_mese
FROM vendite.vw_dash_fatturazione_offerte
WHERE motivo_fermo = 'FIGLIO_ABORTITO';
```

---

### Note operative

* **Non interrogarla dal BE**: il backend passa da
  `vw_dash_fatturazione_documenti` / `vw_dash_aperto_*` (layering).
* **`FIGLIO_ABORTITO` ≠ `SENZA_FIGLIO`**: la XOR contratto/ordine è permanente
  anche se il figlio viene annullato (capability spente) — non è rimediabile con
  un nuovo push, serve una **revisione** dell'offerta (brief §8.1).
* Il valore in euro dell'offerta (espansione listino + eccezioni) è rinviato a v2
  (decisione D-2).
* RLS emittente applicata automaticamente (vista invoker su `offerte_commerciali`).
* Test: `db/pgtap/vendite/test-vw-dash-fatturazione-v1.sql`.

---

{% include-markdown "signature-core.md" %}
