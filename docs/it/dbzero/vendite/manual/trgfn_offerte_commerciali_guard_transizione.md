## 📘 Documentazione Concettuale – Funzione `vendite.trgfn_offerte_commerciali_guard_transizione()`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
> • [vendite.offerte_commerciali](/dbzero/vendite/tabelle/offerte_commerciali)
> • [config.stati_doc_offerte](/dbzero/config/tabelle/stati_doc_offerte)
> • [config.stati_doc_offerte_transizioni](/dbzero/config/tabelle/stati_doc_offerte_transizioni)
> • [vendite.listini_versioni](/dbzero/vendite/tabelle/listini_versioni)
>
Approfondimento funzioni:
> • [vendite.trgfn_preventivi_guard_transizione](/dbzero/vendite/funzioni/trgfn_preventivi_guard_transizione)
> • [script.fn_log_and_raise_error](/dbzero/script/funzioni/fn_log_and_raise_error)

---
### 🎯 Scopo Principale

(rev 2026-08-21 — funzione rev 2026-05-25)

Governa il workflow dell'offerta commerciale, e fa **tre cose in un trigger solo**:

1. **valida la transizione** contro la matrice `config.stati_doc_offerte_transizioni`
   (config-driven, nessun grafo hardcodato);
2. **presidia l'emissione**: passando `BOZZA → EMESSA`, l'offerta deve avere una versione di
   listino, e quella versione dev'essere `ATTIVA`;
3. **valorizza il timestamp** del passaggio (`data_emissione`, `data_accettazione`,
   `data_rifiuto`, `data_annullamento`).

Le tre cose stanno insieme perché condividono la parte costosa: la risoluzione dei codici
interni dei due stati. Separarle costerebbe tre volte la stessa lettura.

---

### Aggancio

Trigger `trg_offerte_commerciali_a10_guard_transizione_upd` — fase `_a10_`,
`BEFORE UPDATE OF stato_doc_offerta_id` su `vendite.offerte_commerciali`, `FOR EACH ROW`.

---

### Regole applicate

**No-op** se `OLD.stato_doc_offerta_id = NEW.stato_doc_offerta_id`.

**Regola 1 — transizione in matrice.** La coppia `(stato_da, stato_a)` deve esistere in
`config.stati_doc_offerte_transizioni` con `attivo = true`. Altrimenti
`E_OFFERTA_TRANSIZIONE_NON_AMMESSA`.

**Regola 2 — solo su `BOZZA → EMESSA`:**

* `listino_versione_id` deve essere valorizzato →
  `E_OFFERTA_EMISSIONE_SENZA_VERSIONE_LISTINO`;
* la versione dev'essere in stato `ATTIVA` →
  `E_OFFERTA_EMISSIONE_VERSIONE_LISTINO_NON_ATTIVA`.

Il senso: un'offerta emessa è un impegno di prezzo verso il cliente, e un impegno di prezzo
senza un listino fissato e vigente non è verificabile. Una versione `CHIUSA` o in
preparazione non basta.

**Regola 3 — timestamp.** In base al codice dello stato di destinazione valorizza `now()`
sulla colonna corrispondente. `ELSE NULL` per gli stati che non hanno un timestamp dedicato:
non è un errore, semplicemente non c'è niente da marcare.

---

### ⚠️ I timestamp si riscrivono a ogni passaggio

La regola 3 assegna `now()` **ogni volta** che si arriva a quello stato. Se un'offerta torna
in `BOZZA` e viene riemessa, `data_emissione` viene sovrascritta con la data nuova e la prima
emissione **sparisce**.

Per un documento commerciale è di norma il comportamento voluto — vale la data
dell'emissione corrente — ma va saputo: quelle colonne registrano **l'ultimo** passaggio, non
il primo. La storia completa dei passaggi non è lì.

---

### ⚠️ Un codice interno non risolto degrada il messaggio, non il controllo

I codici interni sono letti con un `max(CASE ...)` su entrambi gli stati. Se uno dei due id
non si risolve, la variabile resta `NULL` e il `coalesce` nel messaggio ripiega sull'**id
numerico**.

Il controllo della regola 1 non ne risente: confronta gli id, non i codici. Ma la regola 2
sì — `v_codice_da = 'BOZZA' AND v_codice_a = 'EMESSA'` con un codice nullo è falso, quindi
**il guard sul listino non scatta**. In pratica la FK verso `config.stati_doc_offerte`
rende il caso irraggiungibile; resta il verso in cui il ramo cede, che è fail-open.

---

### Codici errore

| Codice | Quando |
|--------|--------|
| `E_OFFERTA_TRANSIZIONE_NON_AMMESSA` | Coppia `(stato_da, stato_a)` assente o non attiva in matrice |
| `E_OFFERTA_EMISSIONE_SENZA_VERSIONE_LISTINO` | `BOZZA → EMESSA` con `listino_versione_id` nullo |
| `E_OFFERTA_EMISSIONE_VERSIONE_LISTINO_NON_ATTIVA` | `BOZZA → EMESSA` con versione in stato diverso da `ATTIVA` |

Tutti via `script.fn_log_and_raise_error` con `NEW.tx_id` propagato.

---

{% include-markdown "signature-core.md" %}
