## 📘 Documentazione Concettuale – Funzione `vendite.trgfn_contratti_guard_emittente_ba()`

> 👀 **Vedi anche**
>
> Tabelle:
> [vendite.contratti](/dbzero/vendite/tabelle/contratti)
> [anagrafiche.emittenti_fiscali](/dbzero/anagrafiche/tabelle/emittenti_fiscali)
> [anagrafiche.emittenti_fiscali_billing_account](/dbzero/anagrafiche/tabelle/emittenti_fiscali_billing_account)
>
> Funzioni correlate:
> [anagrafiche.fn_get_emittente_fiscale_pk](/dbzero/anagrafiche/funzioni/fn_get_emittente_fiscale_pk)
> [script.trgfn_default_emittente_fiscale](/dbzero/script/funzioni/trgfn_default_emittente_fiscale) — il default (dal 2026-09-15 al posto di `trgfn_contratti_default_emittente`)
> [script.fn_log_and_raise_error](/dbzero/script/funzioni/fn_log_and_raise_error)
>
> Errori:
> [config.messaggi_errore E_CONTRATTO_EMITTENTE_BA_INCOERENTE (id=464)](/dbzero/config/tabelle/messaggi_errore)

---

### 🎯 Scopo Principale

(rev 2026-05-26)

Garantisce la **coerenza BA ↔ emittente fiscale** su `vendite.contratti`:
l'`emittente_fiscale_id` del contratto deve coincidere con quello
derivabile dal `billing_account_id` tramite
`anagrafiche.fn_get_emittente_fiscale_pk(billing_account_id)`.

**Motivazione**: un operatore assegnato all'emittente EF1 non può
creare un contratto per un BA che mappa a EF2. Il guard impedisce che
dati di scope diverso vengano mescolati nello stesso documento, anche in
caso di override esplicito nel payload.

Applicata dal trigger `trg_contratti_a10_guard_emittente_ba_ins_upd`
(fase `_a10_`, `BEFORE INSERT OR UPDATE OF billing_account_id, emittente_fiscale_id`).

---

### Firing order

Nella fase `_a10_` i trigger BEFORE si ordinano alfabeticamente. Su INSERT:

1. `trg_contratti_a10_default_emittente_ins` — setta `emittente_fiscale_id`
2. **`trg_contratti_a10_guard_emittente_ba_ins_upd`** — valida la coerenza
   (vede già `emittente_fiscale_id` valorizzato)
3. `trg_contratti_a10_guard_transizione_stato_upd` — solo UPDATE stato
4. `trg_contratti_a10_lock_post_attivazione_upd` — solo UPDATE post-attivazione

---

### Logica

1. Chiama `anagrafiche.fn_get_emittente_fiscale_pk(NEW.billing_account_id)`.
   - Risolve l'EF atteso via mapping specifico (`emittenti_fiscali_billing_account`)
     o fallback gestore globale (`billing_account_id IS NULL AND is_default = true`).
   - Solleva `E_EMITTENTE_DEFAULT_MISSING` se nessun EF è configurato per il BA
     (errore di configurazione del sistema, non scenario atteso in esercizio).
2. Confronta `NEW.emittente_fiscale_id` con `v_ef_atteso_id`.
3. Se diversi: `script.fn_log_and_raise_error` con `E_CONTRATTO_EMITTENTE_BA_INCOERENTE`
   e contesto JSONB (`billing_account_id`, `emittente_fiscale_id`, `emittente_atteso_id`).

---

### Casi d'uso

| Scenario | Comportamento |
|---|---|
| INSERT normale (operatore EF1, BA→EF1) | Passa: emittente default == emittente atteso dal BA |
| INSERT push da offerta (offerta EF1, contratto BA→EF1) | Passa: offerta già aveva BA e EF coerenti |
| INSERT con BA→EF2 (operatore EF1) | **Errore** `E_CONTRATTO_EMITTENTE_BA_INCOERENTE` |
| UPDATE `billing_account_id` → BA di EF2 (contratto in DRAFT) | **Errore** `E_CONTRATTO_EMITTENTE_BA_INCOERENTE` |
| UPDATE `billing_account_id` (post-attivazione) | Bloccato da `lock_post_attivazione` prima del guard |

---

### Errori sollevati

| Codice | id | Quando | Contesto JSONB |
|---|---|---|---|
| `E_CONTRATTO_EMITTENTE_BA_INCOERENTE` | 464 | `emittente_fiscale_id ≠ fn_get_emittente_fiscale_pk(billing_account_id)` | `billing_account_id`, `emittente_fiscale_id`, `emittente_atteso_id`, `numero_contratto` |

---

### Note operative

- Il guard salta su `trg_contratti_a10_lock_post_attivazione_upd`: per
  contratti già ATTIVI, `billing_account_id` ed `emittente_fiscale_id`
  sono campi locked e l'UPDATE viene bloccato prima di raggiungere
  questo guard.
- In contesti di backfill/migration data (Liquibase, DBA), il trigger è
  comunque attivo su UPDATE. Il backfill (migration 80_data/20260526-07)
  usa la stessa catena BA-derived, quindi i valori aggiornati soddisfano
  il guard per costruzione.

---

{% include-markdown "signature-core.md" %}
