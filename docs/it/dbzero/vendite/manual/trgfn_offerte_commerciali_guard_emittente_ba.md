## 📘 Documentazione Concettuale – Funzione `vendite.trgfn_offerte_commerciali_guard_emittente_ba()`

> 👀 **Vedi anche**
>
> Tabelle:
> [vendite.offerte_commerciali](/dbzero/vendite/tabelle/offerte_commerciali)
> [anagrafiche.emittenti_fiscali](/dbzero/anagrafiche/tabelle/emittenti_fiscali)
>
> Funzioni correlate:
> [anagrafiche.fn_get_emittente_fiscale_pk](/dbzero/anagrafiche/funzioni/fn_get_emittente_fiscale_pk)
> [vendite.fn_push_offerta_a_contratto](/dbzero/vendite/funzioni/fn_push_offerta_a_contratto)
>
> Pattern simmetrico:
> [vendite.trgfn_ordini_guard_emittente_ba](/dbzero/vendite/funzioni/trgfn_ordini_guard_emittente_ba)
>
> Errori:
> [config.messaggi_errore E_OFFERTA_EMITTENTE_BA_INCOERENTE (id=529)](/dbzero/config/tabelle/messaggi_errore)

---

### 🎯 Scopo Principale

(rev 2026-07-13)

Chiude la **simmetria piena** (brief indirizzi/emittente §1.3): le offerte
commerciali non avevano né default né guard emittente. Questo guard verifica che
l'`emittente_fiscale_id` dell'offerta coincida con
`anagrafiche.fn_get_emittente_fiscale_pk(billing_account_id)`.

Applicata dal trigger `trg_offerte_commerciali_a10_guard_emittente_ba_ins_upd`
(fase `_a10_`, `BEFORE INSERT OR UPDATE OF billing_account_id, emittente_fiscale_id`).

> **`offerte_commerciali.billing_account_id` è NOT NULL** → il check è di fatto
> sempre attivo (il ramo skip-se-NULL è difensivo).

---

### Logica

1. Se `NEW.billing_account_id IS NULL` → skip (difensivo).
2. `v_ef_atteso_id := anagrafiche.fn_get_emittente_fiscale_pk(NEW.billing_account_id)`.
3. Se `NEW.emittente_fiscale_id IS DISTINCT FROM v_ef_atteso_id`:
   `E_OFFERTA_EMITTENTE_BA_INCOERENTE` con contesto JSONB
   (`billing_account_id`, `emittente_fiscale_id`, `emittente_atteso_id`, `codice_offerta`).

Nota: le offerte usano `codice` (non `numero`) come chiave documento, quindi il
contesto d'errore riporta `codice_offerta`.

---

### Errori sollevati

| Codice | id | Quando | Contesto JSONB |
|---|---|---|---|
| `E_OFFERTA_EMITTENTE_BA_INCOERENTE` | 529 | `emittente_fiscale_id ≠ fn_get_emittente_fiscale_pk(billing_account_id)` | `billing_account_id`, `emittente_fiscale_id`, `emittente_atteso_id`, `codice_offerta` |

---

### Note operative

- L'invariante era già rispettata a valle: `fn_push_offerta_a_contratto` copia
  l'emittente sul contratto, che ha già `trgfn_contratti_guard_emittente_ba`.
  Questo guard la rende esplicita **in ingresso** sull'offerta.

---

{% include-markdown "signature-core.md" %}
