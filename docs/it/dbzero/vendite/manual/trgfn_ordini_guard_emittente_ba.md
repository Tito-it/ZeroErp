## 📘 Documentazione Concettuale – Funzione `vendite.trgfn_ordini_guard_emittente_ba()`

> 👀 **Vedi anche**
>
> Tabelle:
> [vendite.ordini](/dbzero/vendite/tabelle/ordini)
> [anagrafiche.emittenti_fiscali](/dbzero/anagrafiche/tabelle/emittenti_fiscali)
> [anagrafiche.emittenti_fiscali_billing_account](/dbzero/anagrafiche/tabelle/emittenti_fiscali_billing_account)
>
> Funzioni correlate:
> [anagrafiche.fn_get_emittente_fiscale_pk](/dbzero/anagrafiche/funzioni/fn_get_emittente_fiscale_pk)
> [vendite.trgfn_ordini_default_emittente](/dbzero/vendite/funzioni/trgfn_ordini_default_emittente)
> [script.fn_log_and_raise_error](/dbzero/script/funzioni/fn_log_and_raise_error)
>
> Pattern simmetrico:
> [vendite.trgfn_contratti_guard_emittente_ba](/dbzero/vendite/funzioni/trgfn_contratti_guard_emittente_ba)
>
> Errori:
> [config.messaggi_errore E_ORDINE_EMITTENTE_BA_INCOERENTE (id=468)](/dbzero/config/tabelle/messaggi_errore)

---

### 🎯 Scopo Principale

(rev 2026-06-01)

Garantisce la **coerenza BA ↔ emittente fiscale** su `vendite.ordini`:
quando il `billing_account_id` è valorizzato, l'`emittente_fiscale_id`
dell'ordine deve coincidere con quello derivabile dal BA tramite
`anagrafiche.fn_get_emittente_fiscale_pk(billing_account_id)`.

**Motivazione**: un operatore assegnato all'emittente EF1 non può creare un
ordine per un BA che mappa a EF2.

> **Differenza da contratti**: `ordini.billing_account_id` è **nullable**.
> Se il BA è `NULL` il guard **salta** (nessun BA su cui ancorare la coerenza)
> e l'emittente resta quello user-derived senza vincolo. Su `contratti` il BA
> è NOT NULL, quindi il check è sempre attivo.

Applicata dal trigger `trg_ordini_a10_guard_emittente_ba_ins_upd`
(fase `_a10_`, `BEFORE INSERT OR UPDATE OF billing_account_id, emittente_fiscale_id`).

---

### Logica

1. Se `NEW.billing_account_id IS NULL` → **skip** (RETURN NEW).
2. Risolve l'EF atteso: `anagrafiche.fn_get_emittente_fiscale_pk(NEW.billing_account_id)`.
3. Confronta `NEW.emittente_fiscale_id` con `v_ef_atteso_id`.
4. Se diversi: `script.fn_log_and_raise_error` con
   `E_ORDINE_EMITTENTE_BA_INCOERENTE` e contesto JSONB
   (`billing_account_id`, `emittente_fiscale_id`, `emittente_atteso_id`, `numero_ordine`).

---

### Casi d'uso

| Scenario | Comportamento |
|---|---|
| INSERT operatore EF1, BA→EF1 | Passa: emittente == emittente atteso dal BA |
| INSERT operatore EF1, BA→EF2 | **Errore** `E_ORDINE_EMITTENTE_BA_INCOERENTE` |
| INSERT senza BA (`billing_account_id NULL`) | Passa: check saltato (emittente user-derived) |
| UPDATE `billing_account_id` → BA di EF2 | **Errore** `E_ORDINE_EMITTENTE_BA_INCOERENTE` |

---

### Errori sollevati

| Codice | id | Quando | Contesto JSONB |
|---|---|---|---|
| `E_ORDINE_EMITTENTE_BA_INCOERENTE` | 468 | `emittente_fiscale_id ≠ fn_get_emittente_fiscale_pk(billing_account_id)` (con BA valorizzato) | `billing_account_id`, `emittente_fiscale_id`, `emittente_atteso_id`, `numero_ordine` |

---

### Note operative

- Distinto dal write-guard di scope RLS
  `trg_ordini_a10_guard_emittente_scope_ins_upd`: quest'ultimo verifica che
  l'**operatore corrente** abbia scope sull'emittente (canonica
  `fn_check_user_emittente_scope`), mentre questo guard verifica la
  **coerenza emittente↔BA** del documento.
- In backfill/migration data il trigger è attivo su UPDATE; il backfill
  (`80_data/20260601-24`) usa la stessa catena BA-derived nel tier 2, quindi
  i valori aggiornati soddisfano il guard per costruzione.

---

{% include-markdown "signature-core.md" %}
