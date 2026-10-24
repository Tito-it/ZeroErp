## 📘 Documentazione Concettuale – Funzione `script.fn_check_esclusione_articolo_documento`

> 👀 **Vedi anche**
>
> **Consumatori:**
>
> • [script.fn_check_articolo_riga](/dbzero/script/manual/fn_check_articolo_riga) — la check per tipo di riga, che la **compone** come primo motivo dell'ESCLUSIONE (dal 2026-10-13); il guard di tabella [script.trgfn_righe_guard_articolo_ammesso](/dbzero/script/manual/trgfn_righe_guard_articolo_ammesso) ne solleva il primo motivo
> • [vendite.fn_documento_righe_preview](/dbzero/vendite/funzioni/fn_documento_righe_preview) — la lista delle righe, che **spegne «Escludi»** (`escludi_blocco_codice`)
>
> **Sorgenti:** [vendite.fn_documento_listino_operativo](/dbzero/vendite/funzioni/fn_documento_listino_operativo) · [vendite.listini_righe_componenti](/dbzero/vendite/tabelle/listini_righe_componenti)
>
> **Verifica:** `db/pgtap/vendite/test-contratto-righe-lista-v1.sql` · `db/pgtap/vendite/test-righe-esclusione-solo-non-si-vende-v1.sql`

---

### 🎯 Scopo Principale

(funzione nata il 2026-10-04, `20261004-43`)

**I motivi per cui un articolo NON si può escludere da un contratto o da
un'offerta.** Ritorna `[]` se si può, altrimenti l'array **ordinato** dei
motivi: `[{codice, reason, reason_key, dettaglio, valori}, …]`
(linee-guida-sql §12.5). Il documento si sceglie col primo argomento
(`CONTRATTO`, `OFFERTA`).

Prende il posto di `script.fn_check_esclusione_articolo_contratto` (nata il
2026-09-28 per spegnere «Escludi» prima del click invece di rifiutarlo dopo),
che valeva per il solo contratto. Ritirata nello stesso giro: due check della
stessa regola un giorno risponderebbero in due modi diversi.

---

### I motivi

| # | `reason` | Codice | Quando |
| --- | --- | --- | --- |
| 1 | `FIGLIO_DI_BUNDLE` | `E_CONTRATTO_ESCLUSIONE_FIGLIO_BUNDLE_VIETATA` | l'articolo è componente di un bundle nella versione del listino che vale per il documento |

`reason_key`: `vendite.contratti.escludi_blocco.figlio_di_bundle` (la chiave che
il frontend traduce già; resta quella anche per l'offerta). `valori`:
l'articolo. `dettaglio`: documento, id, articolo, listino e versione.

**Quale versione del listino**: la dice
[`vendite.fn_documento_listino_operativo`](/dbzero/vendite/funzioni/fn_documento_listino_operativo)
— la fissata, o in bozza quella in vigore oggi. Senza versione: nessun bundle,
nessun motivo. Il componente deve essere valido **oggi** nella versione.

---

### Forma

- Prende i **valori** (documento, articolo), non l'id di una riga: una riga
  «dal listino» non esiste fra le eccezioni finché non la si esclude.
- `STABLE`, `SECURITY INVOKER`, come il guard che la chiama.

---

{% include-markdown "signature-core.md" %}
