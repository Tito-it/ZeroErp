## 📘 Documentazione Concettuale – Funzione `vendite.trgfn_preventivi_guard_emittente_ba()`

> 👀 **Vedi anche**
>
> Tabelle:
> [vendite.preventivi](/dbzero/vendite/tabelle/preventivi)
> [anagrafiche.emittenti_fiscali](/dbzero/anagrafiche/tabelle/emittenti_fiscali)
>
> Funzioni correlate:
> [anagrafiche.fn_get_emittente_fiscale_pk](/dbzero/anagrafiche/funzioni/fn_get_emittente_fiscale_pk)
> [script.trgfn_default_emittente_fiscale](/dbzero/script/funzioni/trgfn_default_emittente_fiscale) — il default (dal 2026-09-15 al posto di `trgfn_preventivi_default_emittente`)
>
> Pattern simmetrico:
> [vendite.trgfn_ordini_guard_emittente_ba](/dbzero/vendite/funzioni/trgfn_ordini_guard_emittente_ba)
>
> Errori:
> [config.messaggi_errore E_PREV_EMITTENTE_BA_INCOERENTE (id=528)](/dbzero/config/tabelle/messaggi_errore)

---

### 🎯 Scopo Principale

(rev 2026-07-13)

Chiude la **simmetria piena** (brief indirizzi/emittente §1.3): i preventivi
avevano il `default_emittente` ma **non** il guard di coerenza. Ora, quando il
`billing_account_id` è valorizzato, l'`emittente_fiscale_id` del preventivo deve
coincidere con `anagrafiche.fn_get_emittente_fiscale_pk(billing_account_id)`.

Applicata dal trigger `trg_preventivi_a10_guard_emittente_ba_ins_upd`
(fase `_a10_`, `BEFORE INSERT OR UPDATE OF billing_account_id, emittente_fiscale_id`).

> **Piazzamento standard `_a10_`**: sui preventivi il BA arriva dal payload
> (niente normalize che lo risolve tardi, a differenza dei DDT), quindi il
> guard può stare in fascia `a10` come su ordini/contratti.

---

### Logica

1. Se `NEW.billing_account_id IS NULL` → **skip** (`preventivi.billing_account_id`
   è nullable).
2. `v_ef_atteso_id := anagrafiche.fn_get_emittente_fiscale_pk(NEW.billing_account_id)`.
3. Se `NEW.emittente_fiscale_id IS DISTINCT FROM v_ef_atteso_id`:
   `E_PREV_EMITTENTE_BA_INCOERENTE` con contesto JSONB
   (`billing_account_id`, `emittente_fiscale_id`, `emittente_atteso_id`, `numero_preventivo`).

---

### Errori sollevati

| Codice | id | Quando | Contesto JSONB |
|---|---|---|---|
| `E_PREV_EMITTENTE_BA_INCOERENTE` | 528 | `emittente_fiscale_id ≠ fn_get_emittente_fiscale_pk(billing_account_id)` (con BA valorizzato) | `billing_account_id`, `emittente_fiscale_id`, `emittente_atteso_id`, `numero_preventivo` |

---

### Note operative

- Complementare al default dell'emittente (`script.trgfn_default_emittente_fiscale`, user-derived; fino al 2026-09-15 la copia `trgfn_preventivi_default_emittente`) e al
  write-guard di scope `trg_preventivi_a10_guard_emittente_scope_ins_upd`.

---

{% include-markdown "signature-core.md" %}
