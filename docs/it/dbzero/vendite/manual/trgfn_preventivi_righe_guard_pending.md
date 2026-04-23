## 📘 Documentazione Concettuale – Trigger Function `vendite.trgfn_preventivi_righe_guard_pending()`

> 👀 **Vedi anche**
>
> Tabelle correlate:
>
> [vendite.preventivi_righe](/dbzero/vendite/tabelle/preventivi_righe) — tabella guardata
> [pratiche.pratiche](/dbzero/pratiche/tabelle/pratiche) — pratica di richiesta approvazione (FK `pratica_approvazione_prezzo_id`)
>
> Funzioni correlate:
>
> [script.fn_log_and_raise_error](/dbzero/script/funzioni/fn_log_and_raise_error)
> [vendite.trgfn_preventivi_guard_transizione_approvazione](/dbzero/vendite/funzioni/trgfn_preventivi_guard_transizione_approvazione) — guard complementare lato preventivo
>
> Tipo ENUM:
>
> [config.stato_approvazione_prezzo](/dbzero/config/tabelle/stato_approvazione_prezzo) — PENDING/APPROVED/REJECTED
>
> Guide:
>
> [Sviluppo Listini v5 §14.6](/dev/work-in-progress/sviluppo-listini-v5) — workflow L3 approvazione out-of-policy

La trigger function **`vendite.trgfn_preventivi_righe_guard_pending()`** congela i **campi struttura** di una riga preventivo mentre la riga e' in `stato_approvazione_prezzo = 'PENDING'`. Ammette solo le modifiche di **workflow**, **payload esteso** e **audit**.

---

### 🎯 Scopo Principale

(latest revision 22-04-2026, Sprint E listini v5 §14.6)

- **Decisione L3 sulla riga esatta** — se l'approvatore L3 deve autorizzare un prezzo out-of-policy proposto, la riga che lui vede deve essere **identica** a quella su cui esprime il verdetto. Cambi di prezzo, quantita' o articolo tra richiesta ed esito romperebbero la catena decisionale (l'approvazione diventerebbe ambigua: su quale versione della riga?).
- **Coerenza con DB-E-4** — il trigger complementare [`trgfn_preventivi_guard_transizione_approvazione`](/dbzero/vendite/funzioni/trgfn_preventivi_guard_transizione_approvazione) impedisce di accettare il preventivo finche' ci sono righe PENDING. Insieme garantiscono l'invariante "nessuna decisione commerciale con pricing incerto".
- **Allowlist difensiva** — pattern esplicito: elenco completo delle colonne **struttura** (denylist) → se il refactor della tabella aggiunge una colonna, il trigger va aggiornato. Nota implementativa.

---

### Logica

**Guard attivo solo quando `OLD.stato_approvazione_prezzo = 'PENDING'`**. In tutti gli altri casi (stato NULL, APPROVED, REJECTED) il trigger fa early return senza vincoli — la riga non e' in workflow.

Quando il guard e' attivo:

- **Allowlist (ammessi)**: `stato_approvazione_prezzo`, `pratica_approvazione_prezzo_id`, `meta`, `data_update`, `user_update` (questi ultimi due sono comunque gestiti dal trigger framework `trgfn_audit_data_user_generic`).
- **Denylist (bloccati)**: qualsiasi modifica a `preventivo_id`, `articolo_id`, `descrizione`, `quantita`, `prezzo_unitario`, `sconto_percentuale`, `iva_id`, `ordine`, `attivo`, `qta_operativa`, `uom_operativa_id`, `factor_to_base` → raise `E_RIGA_PREZZO_PENDENTE`.

**Transizione workflow ammessa**: `PENDING → APPROVED`, `PENDING → REJECTED`, `PENDING → NULL` (reset richiesta). Queste passano perche' sono cambi su colonne allowlisted, non sulla struttura.

**Tentativo misto rilevato**: se l'UPDATE cambia **sia** lo stato_approvazione **sia** un campo struttura (es. "approva E riduci il prezzo"), il trigger **blocca**. La decisione deve essere atomica e preservare la riga originale — eventuali aggiustamenti post-approvazione richiedono un UPDATE separato dopo che lo stato e' transito.

Context payload JSONB:

- `riga_id` — l'id della riga bloccata
- `preventivo_id` — per tracciabilita' cross-tabella
- `hint` — suggerimento UX (attendi esito / rifiuta)

Il messaggio include `riga_id` formattato via `%s` dal CSV `messaggi_errore`.

---

### Applicazione

Trigger creato dalla migration `20260422-07-02`:

- **`trg_preventivi_righe_a10_guard_pending_upd`** su `vendite.preventivi_righe`

Specifiche:

- Timing: **BEFORE UPDATE**
- Fase: **_a10_** (guard/block)
- Scope: **FOR EACH ROW**
- **No `UPDATE OF <colonna>`**: il guard deve intercettare **qualsiasi UPDATE** su una riga PENDING per poter confrontare NEW vs OLD su tutte le colonne struttura. Limitare l'UPDATE OF a una sola colonna rischierebbe bypass via update combinati.

---

### Codice errore sollevato

**`E_RIGA_PREZZO_PENDENTE`** (id 390) — `config.messaggi_errore` CSV. Seminato in `20260422` con il trigger.

Messaggio: `"Riga preventivo <id> in attesa di approvazione prezzo: modifica dei campi struttura vietata."`.

Causa (CSV): quando una riga e' PENDING, solo workflow/payload/audit sono modificabili. I campi struttura sono frozen per preservare la catena decisionale L3.

Soluzione suggerita (CSV): attendere l'esito (APPROVED sblocca, REJECTED consente poi modifica), o usare endpoint di rifiuto/annullamento per liberare la riga.

---

### Quando NON scatta

- **OLD.stato_approvazione_prezzo != 'PENDING'**: early return. Righe senza workflow (NULL, la gran parte dei casi in produzione) o gia' decise (APPROVED/REJECTED) non hanno vincoli.
- **INSERT di una riga con stato = 'PENDING'**: scope `BEFORE UPDATE`, non scatta. L'apertura di una richiesta L3 e' normale.
- **DELETE**: scope `BEFORE UPDATE`, non scatta. La cancellazione di una richiesta (rifiuto) passa per altri meccanismi.
- **UPDATE di soli campi allowlisted su riga PENDING**: allowlist esplicita, pass-through.

---

### Note implementative

- `LANGUAGE plpgsql` — necessario per il confronto multi-colonna condizionale.
- **Pattern denylist enumerato**: elenco completo dei campi struttura. Se il refactor di `preventivi_righe` aggiunge una colonna nuova che dovrebbe essere frozen durante PENDING, il trigger va aggiornato. Questa scelta e' esplicita: postgres non ha un modo nativo di dire "tutte le colonne tranne N", e la denylist esplicita e' piu' verifiable di un approccio meta-reflection.
- **Nessuna variabile locale con `%TYPE`**: il trigger lavora solo con `NEW`/`OLD` (gia' tipati dalla tabella).
- Passaggio `OLD.id::text` come valore variadic per placeholder `%s` del messaggio errore.
- Il cast `'PENDING'::config.stato_approvazione_prezzo` e' necessario per il confronto ENUM: senza cast PostgreSQL tratterebbe `'PENDING'` come `text` e il `IS DISTINCT FROM` avrebbe risoluzione implicita meno efficiente.
