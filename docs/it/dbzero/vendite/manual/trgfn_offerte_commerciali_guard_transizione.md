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
> • [`script.fn_check_prezzi_autorizzati`](/dbzero/script/funzioni/fn_check_prezzi_autorizzati) — i prezzi non autorizzati (dal 2026-09-24)
> • [script.fn_available_actions_offerta](/dbzero/script/funzioni/fn_available_actions_offerta) — spegne i pulsanti con gli stessi motivi

---
### 🎯 Scopo Principale

(rev 2026-09-24 — il prezzo non autorizzato; rev 2026-08-21 — funzione rev 2026-05-25)

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

**Regola 2-bis — prezzi autorizzati (rev 2026-09-24), verso `EMESSA` e `ACCETTATA`.**
Un'eccezione o un suo componente **attivi** con il prezzo in attesa di approvazione o
rifiutato bloccano la transizione: solleva il primo motivo di [`script.fn_check_prezzi_autorizzati`](/dbzero/script/funzioni/fn_check_prezzi_autorizzati)
(`E_DOC_PREZZO_PENDENTE` / `E_DOC_PREZZO_RIFIUTATO`). ⛔ Non sul **rientro** automatico
`SUPERATA → EMESSA` (il padre che torna vivo quando si annulla la revisione): non manda niente
al cliente, e bloccarlo fermerebbe un annullamento. Vedi la sezione in fondo.

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
| `E_DOC_PREZZO_PENDENTE` | → `EMESSA` / `ACCETTATA` con un prezzo in attesa di approvazione (dal 2026-09-24) |
| `E_DOC_PREZZO_RIFIUTATO` | → `EMESSA` / `ACCETTATA` con un prezzo rifiutato (dal 2026-09-24) |

Tutti via `script.fn_log_and_raise_error` con `NEW.tx_id` propagato (i due `E_DOC_PREZZO_*`
attraverso `script.fn_raise_primo_motivo_se_presente`).

---

### Rev 2026-09-24 — un prezzo non autorizzato non esce

Regola decisa da Tid: *un prezzo che nessuno ha autorizzato non esce dalla bozza*. Fino a
questa revisione l'offerta **non guardava il prezzo per niente**: un'offerta con un'eccezione
in attesa di approvazione, o rifiutata, si emetteva e si accettava.

* Il predicato non è scritto qui: lo fa [`script.fn_check_prezzi_autorizzati`](/dbzero/script/funzioni/fn_check_prezzi_autorizzati), la sede unica per preventivi, contratti,
  offerte, ordini e DDT. Per l'offerta guarda le eccezioni
  (`offerte_commerciali_eccezioni`) e i loro componenti, solo se **attivi**, e sia il
  prezzo **in attesa** (`PENDING`) sia quello **rifiutato** (`REJECTED`).
* Vale verso `EMESSA` e verso `ACCETTATA`; non sul rientro da `SUPERATA` (letto dal flag
  di superamento, non da un codice). L'annullamento resta sempre possibile.
* Gli stessi motivi spengono «Emetti» e «Accetta» in
  [`script.fn_available_actions_offerta`](/dbzero/script/funzioni/fn_available_actions_offerta):
  pulsanti e database non possono dissentire.

(changeSet `20260924-27`, brief `brief-db-preventivi-congelamento-pricing`.)

---

{% include-markdown "signature-core.md" %}
