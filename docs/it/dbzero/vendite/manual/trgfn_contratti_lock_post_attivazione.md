## 📘 Documentazione Concettuale – Trigger Function `vendite.trgfn_contratti_lock_post_attivazione()`

> 👀 **Vedi anche**
>
> Tabelle correlate:
>
> [vendite.contratti](/dbzero/vendite/tabelle/contratti) — tabella guardata
>
> Funzioni correlate:
>
> [script.fn_log_and_raise_error](/dbzero/script/funzioni/fn_log_and_raise_error)
> [vendite.trgfn_contratti_freeze_listino_versione](/dbzero/vendite/funzioni/trgfn_contratti_freeze_listino_versione) — freeze versione all'attivazione
> [vendite.trgfn_doc_righe_lock_fuori_bozza](/dbzero/vendite/funzioni/trgfn_doc_righe_lock_fuori_bozza) — le righe: il building block «solo in bozza», che dal 2026-09-22 ha riassorbito il lock dedicato delle righe di contratto

La trigger function **`vendite.trgfn_contratti_lock_post_attivazione()`** impedisce la modifica dei campi pricing della testata contratto una volta che il contratto è in stato ATTIVO.

---

### 🎯 Scopo Principale

Il pricing di un contratto attivo è **immutabile per design** (§3-bis-A del brief): né listino, né variazione globale, né versione fissata possono essere cambiati dopo l'attivazione. Questo garantisce stabilità del calcolo prezzi per tutta la durata del contratto e coerenza dell'audit trail.

---

### Logica

Verifica lo stato del contratto leggendo `OLD.stato_doc_contratto_id` → `codice_interno` da `config.stati_doc_contratti`. Se `codice_interno = 'ATTIVO'`: raise `E_CONTRATTO_CAMPI_BLOCCATI_POST_ATTIVAZIONE`.

Il trigger usa `UPDATE OF` su colonne specifiche: **non scatta** per update di altri campi (`meta`, `note`, `valido_al`, `numero`, audit columns, ecc.).

---

### Applicazione

Trigger creato dalla migration `20260515-14`:

* **`trg_contratti_a10_lock_post_attivazione_upd`** su `vendite.contratti`
* Timing: **BEFORE UPDATE OF `listino_id, listino_versione_id, tipo_variazione_globale, valore_variazione_globale`**
* Fase: **_a10_**
* Scope: **FOR EACH ROW**

Il trigger NON scatta quando il freeze trigger (`trgfn_contratti_freeze_listino_versione`) imposta internamente `NEW.listino_versione_id` durante la transizione DRAFT→ATTIVO — perché quella è una modifica tramite trigger function, non una colonna nell'UPDATE statement dell'utente.

---

### Codice errore sollevato

**`E_CONTRATTO_CAMPI_BLOCCATI_POST_ATTIVAZIONE`** (id 452) — `config.messaggi_errore`.

HTTP mapping (BE): `409 Conflict`.

---

### Campi bloccati vs campi liberi

| Campo | Bloccato post-ATTIVO | Note |
| --- | --- | --- |
| `listino_id` | ✅ | Il listino di riferimento non può cambiare |
| `listino_versione_id` | ✅ | Snapshot immutabile fissato all'attivazione |
| `tipo_variazione_globale` | ✅ | Tipo variazione sul listino |
| `valore_variazione_globale` | ✅ | Percentuale/valore variazione |
| `valido_al` | ❌ libero | Cessazione programmata via PATCH |
| `meta` | ❌ libero | Metadati estendibili |
| `stato_doc_contratto_id` | ❌ libero | Gestito da `guard_transizione_stato` |

{% include-markdown "signature-core.md" %}

---
