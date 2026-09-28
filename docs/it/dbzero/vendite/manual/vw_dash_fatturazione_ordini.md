## 📘 Documentazione Concettuale – Vista `vendite.vw_dash_fatturazione_ordini`

> 👀 **Vedi anche**
>
Approfondimento tabelle e funzioni:
>
[vendite.ordini](/dbzero/vendite/tabelle/ordini)
> [vendite.ordini_righe](/dbzero/vendite/tabelle/ordini_righe)
> [vendite.commesse_attivita](/dbzero/vendite/tabelle/commesse_attivita)
> [config.stati_doc_ordini](/dbzero/config/tabelle/stati_doc_ordini)
> [vendite.fn_list_ordini_da_pushare](/dbzero/vendite/funzioni/fn_list_ordini_da_pushare) (predicato gemello)
>
Union e aggregata:
>
[vw_dash_fatturazione_documenti](vw_dash_fatturazione_documenti.md)
> [vw_dash_aperto_documenti](vw_dash_aperto_documenti.md)

---
### 🎯 Scopo Principale
(latest review 2026-07-18)
Resolver dell'area **ORDINI** per la Dashboard Fatturazione
(brief-design-dashboard-fatturazione §5, Fase 1): una riga per ordine con valore
**imponibile** totale vs **transitato a commessa** e il motivo del fermo.
Read-time, nessun mirror.

> ⚠️ **Dal 2026-07-18 il resolver è *trigger-aware*** (slice fatturazione DDT/resi,
> §4b/§4c). `ordini.fatturazione_trigger` decide **chi fattura**, e questo cambia
> due cose: il **motivo** del fermo e la **misura del valore**. Un ordine con
> trigger `SPEDITO`/`CONSEGNATO` non fattura da sé — lo fanno i suoi DDT.

---

### Semantica

| Aspetto | Regola |
|---------|--------|
| Transito riga | `EXISTS` attività con `segment_key = 'ORD:<uid>:R:<riga_id>'` e `stato_emissione = 'EMESSA'` — lo **stesso** `NOT EXISTS` che rende la riga non più eligible in `fn_list_ordini_da_pushare` (attività `NON_EMESSA` = riga ancora ferma, ri-pushabile) |
| Valore riga | `quantita × prezzo_unitario × (1 − sconto%/100)` — solo righe attive |
| **Valore totale (trigger-aware)** | **Trigger `CONFERMATO`** → valore **pieno** (fattura l'ordine: nessun doppio conteggio da evitare). **Trigger `SPEDITO`/`CONSEGNATO`** → **residuo da spedire**, per riga `GREATEST(0, quantita − Σ fulfillment.qta_evasa + fn_ordine_riga_qta_riconsegna(riga)) × prezzo scontato`: ciò che è già spedito lo porta il DDT, l'ordine porta il resto |
| Competenza | Mese di `ordini.data` (l'ordine non ha competenza nativa; quella puntuale nasce sulla commessa) |
| `is_abortito` | `esito = 'NEGATIVO'` da `config.stati_doc_ordini` |
| `motivo_fermo` | `DOC_BOZZA` (DRAFT) · **`IN_ATTESA_DDT`** (trigger `SPEDITO`/`CONSEGNATO`: il push spetta al DDT) · `PUSH_NON_ESEGUITO` (confermato, 0 righe transitate) · `PUSH_PARZIALE` |
| `cliente_display` | Ragione sociale del `soggetto_ruolo_id` (path `vw_ordini_lista`), nullable |

---

### Perché il trigger cambia le due cose

**Il motivo.** Un ordine a trigger `SPEDITO`/`CONSEGNATO` non avrà **mai** attività
sui segmenti `ORD:*` — fattureranno i suoi DDT su `DDT:*`. Prima risultava
`PUSH_NON_ESEGUITO` **per sempre**, con un'azione che il motore stesso rifiuta:
falso positivo perpetuo. Ora ha `IN_ATTESA_DDT`, che è **`FISIOLOGICO`** → l'ordine
**resta nel serbatoio** (è aperto e pre-commessa, giusto) e **sparisce dal backlog**
(non c'è nulla da fare su di lui, giusto). Nessun caso speciale nel FE: lo fa la
regola di classe.

**Il valore.** Ordine da 1.000 €, trigger `CONSEGNATO`, metà spedita: a valore pieno
il serbatoio mostrerebbe 1.000 € sull'ordine **più** 500 € sul DDT = 1.500 € per una
fattura che sarà di 1.000. Con la misura netta i due sommano correttamente.

> ⚠️ Perché **solo** per i trigger DDT: con `CONFERMATO` la misura netta creerebbe un
> buco cieco al posto di chiuderne uno — un ordine interamente spedito ma non ancora
> pushato mostrerebbe **0 €**, e il DDT non compenserebbe perché non fatturerà mai.
> E sarebbe sulla configurazione di **default** (`fatturazione_ordini` = `CONFERMATO`).
>
> ⚠️ La misura netta rende **l'area ORDINI l'unica a valore netto**; le altre restano
> lorde. Accettato consapevolmente (§4c).

---

### Esempio d'uso

```sql
-- Ordini con push a commessa assente o parziale nel mese.
SELECT codice, valore_totale, valore_transitato, motivo_fermo, stato_codice
FROM vendite.vw_dash_fatturazione_ordini
WHERE competenza_mese = DATE '2026-05-01'
  AND NOT is_abortito AND NOT is_transitato;
```

---

### Note operative

* **Non interrogarla dal BE**: il backend passa da
  `vw_dash_fatturazione_documenti` / `vw_dash_aperto_*` (layering).
* L'`EXISTS` su `segment_key` è assistito da `ix_commesse_attivita_segment_key`
  (90_end `20260703-58`): l'UNIQUE esistente ha `commessa_id` in testa e non serve
  il lookup puntuale.
* `EVASO` scatta solo a push completo: un ordine `CONFERMATO` con push parziale è
  il caso `PUSH_PARZIALE`.
* RLS emittente applicata automaticamente (vista invoker su `vendite.ordini`).
* Test: `db/pgtap/vendite/test-vw-dash-fatturazione-v1.sql`.

---

<!-- rev-2026-09-28-liste-righe -->
### 🔄 rev 2026-09-28 — brief-db-liste-righe-documento

L'imponibile di riga (`valore_riga` e `valore_riga_residua`, che passa alla funzione la quantità residua già calcolata) non è più scritto qui: viene da [script.fn_imponibile_riga](/dbzero/script/funzioni/fn_imponibile_riga), la sede unica della formula (`20260928-23`). Stesso valore — provato su una griglia di 252 casi e sui dati di dev — ma una regola sola: prezzo o quantità assenti danno **nessun valore**, mai zero; sconto assente è nessuno sconto; l'arrotondamento resta a chi consuma.

---

{% include-markdown "signature-core.md" %}
