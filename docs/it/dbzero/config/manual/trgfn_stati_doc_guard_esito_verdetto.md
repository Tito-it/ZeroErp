## 📘 Documentazione Concettuale – Funzione `config.trgfn_stati_doc_guard_esito_verdetto()`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
> • [config.stati_doc_preventivi](/dbzero/config/tabelle/stati_doc_preventivi)
> • [config.stati_doc_ordini](/dbzero/config/tabelle/stati_doc_ordini)
> • [config.stati_doc_contratti](/dbzero/config/tabelle/stati_doc_contratti)
> • [config.stati_doc_offerte](/dbzero/config/tabelle/stati_doc_offerte)
> • [config.esiti_flussi_pratiche](/dbzero/config/tabelle/esiti_flussi_pratiche)
>
Approfondimento funzioni:
> • [script.fn_log_and_raise_error](/dbzero/script/funzioni/fn_log_and_raise_error)

---
### 🎯 Scopo Principale

(rev 2026-08-21)

Presidia la colonna `esito` delle tabelle `config.stati_doc_*` — la **proiezione di stato
dominio** introdotta dal brief *proiezione-stato-dominio*. Quella colonna serve a dire
«questo stato del documento corrisponde a un **verdetto**» (accettato, rifiutato…), non a
un passaggio intermedio.

Il guard impone che, se valorizzata, `esito` punti a un esito che è davvero un verdetto:
`config.esiti_flussi_pratiche.is_verdetto = true`. Gli esiti di puro instradamento — quelli
che spostano la pratica senza chiuderla — non possono essere usati come proiezione di uno
stato documento.

**È una funzione sola per quattro tabelle.** Legge solo `NEW.esito` e `NEW.codice_interno`,
quindi è riusabile su ogni dominio del roll-out senza modifiche: il nome della tabella lo
ricava a runtime da `TG_TABLE_NAME`.

---

### Aggancio

`BEFORE INSERT OR UPDATE`, `FOR EACH ROW`, su quattro tabelle:

| Trigger | Tabella |
|---------|---------|
| `trg_stati_doc_preventivi_a10_guard_esito_verdetto_ins_upd` | `config.stati_doc_preventivi` |
| `trg_stati_doc_ordini_a10_guard_esito_verdetto_ins_upd` | `config.stati_doc_ordini` |
| `trg_stati_doc_contratti_a10_guard_esito_verdetto_ins_upd` | `config.stati_doc_contratti` |
| `trg_stati_doc_offerte_a10_guard_esito_verdetto_ins_upd` | `config.stati_doc_offerte` |

Estendere il presidio a un dominio nuovo significa **solo** aggiungere il trigger: la
funzione non va toccata.

---

### Regole applicate

1. `NEW.esito IS NULL` → **passa**. Nessun verdetto è una risposta legittima: la maggior
   parte degli stati non proietta niente.
2. Cerca `NEW.esito` in `config.esiti_flussi_pratiche` per `codice_interno`.
3. Blocca se `is_verdetto IS DISTINCT FROM true`.

Il confronto `IS DISTINCT FROM true` copre in un colpo solo **tre** casi diversi:
il codice non esiste (`SELECT INTO` senza righe → variabile `NULL`), esiste con
`is_verdetto = false`, esiste con `is_verdetto = NULL`.

---

### Il codice inesistente viene fermato qui, non dalla FK

La colonna ha anche una FK verso `config.esiti_flussi_pratiche`, che da sola rifiuterebbe un
codice inventato — ma con un errore di integrità referenziale (`23503`), muto sul piano del
dominio.

Il guard, girando `BEFORE`, arriva **prima** e restituisce lo stesso errore parlante che
userebbe per un esito non-verdetto. Chi legge il log vede `E_STATO_DOC_ESITO_NON_VERDETTO`
con il codice e la tabella nel context, non un messaggio di violazione FK.

⚠️ Il rovescio: **codice inesistente e codice non-verdetto arrivano con lo stesso codice
errore.** Per distinguerli serve il `context` JSONB, non il solo codice.

---

### Codici errore

| Codice | Quando |
|--------|--------|
| `E_STATO_DOC_ESITO_NON_VERDETTO` | `esito` valorizzato ma non corrispondente a un esito con `is_verdetto = true` (compreso il codice inesistente) |

Sollevato via `script.fn_log_and_raise_error` con `area = 'config'`; nel context finiscono
`tabella`, `codice_interno` e `esito`.

---

{% include-markdown "signature-core.md" %}
