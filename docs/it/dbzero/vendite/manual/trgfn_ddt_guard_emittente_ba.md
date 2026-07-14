## 📘 Documentazione Concettuale – Funzione `vendite.trgfn_ddt_guard_emittente_ba()`

> 👀 **Vedi anche**
>
> Tabelle:
> [vendite.ddt](/dbzero/vendite/tabelle/ddt)
> [anagrafiche.emittenti_fiscali](/dbzero/anagrafiche/tabelle/emittenti_fiscali)
> [anagrafiche.emittenti_fiscali_billing_account](/dbzero/anagrafiche/tabelle/emittenti_fiscali_billing_account)
>
> Funzioni correlate:
> [anagrafiche.fn_get_emittente_fiscale_pk](/dbzero/anagrafiche/funzioni/fn_get_emittente_fiscale_pk)
> [vendite.trgfn_ddt_default_emittente](/dbzero/vendite/funzioni/trgfn_ddt_default_emittente)
> [vendite.trgfn_ddt_normalize](/dbzero/vendite/funzioni/trgfn_ddt_normalize)
>
> Pattern simmetrico (con differenza di piazzamento):
> [vendite.trgfn_ordini_guard_emittente_ba](/dbzero/vendite/funzioni/trgfn_ordini_guard_emittente_ba)
>
> Errori:
> [config.messaggi_errore E_DDT_EMITTENTE_BA_INCOERENTE (id=527)](/dbzero/config/tabelle/messaggi_errore)

---

### 🎯 Scopo Principale

(rev 2026-07-13)

Garantisce la **coerenza BA ↔ emittente fiscale** su `vendite.ddt`: quando il
`billing_account_id` è valorizzato, l'`emittente_fiscale_id` del DDT deve
coincidere con quello derivabile dal BA tramite
`anagrafiche.fn_get_emittente_fiscale_pk(billing_account_id)`. Logica identica a
`trgfn_ordini_guard_emittente_ba` (skip se BA NULL). Chiude il buco aperto
dall'apertura del payload emittente lato BE.

---

### ⚠️ Piazzamento post-normalize (differenza voluta da ordini)

Su **ordini** il BA arriva nel payload, quindi il guard sta in fascia `_a10_`
(prima della normalizzazione). **Sul DDT no**: il `billing_account_id` è spesso
**risolto** da `trgfn_ddt_normalize` (evasione: dall'ordine sorgente;
standalone: fallback), che fira **dopo** gli `a10`.

Un guard `a10` "mirror esatto" vedrebbe `billing_account_id = NULL` proprio nei
casi da controllare (evasione, BA-derived) e salterebbe. Per questo il guard è
piazzato **dopo** il normalize: il trigger `trg_ddt_z10_guard_emittente_ba_ins_upd`
(fase `z10`, `BEFORE INSERT OR UPDATE OF billing_account_id, emittente_fiscale_id`)
ordina dopo `trg_ddt_normalize_ins_upd` e prima di `z90`. Così controlla i
**valori finali** risolti:

- evasione / fallback-da-BA → coerenti per costruzione → **pass**;
- divergenza introdotta dal payload → **raise**.

---

### Logica

1. Se `NEW.billing_account_id IS NULL` → **skip** (RETURN NEW).
2. `v_ef_atteso_id := anagrafiche.fn_get_emittente_fiscale_pk(NEW.billing_account_id)`.
3. Se `NEW.emittente_fiscale_id IS DISTINCT FROM v_ef_atteso_id`:
   `script.fn_log_and_raise_error` con `E_DDT_EMITTENTE_BA_INCOERENTE` e contesto
   JSONB (`billing_account_id`, `emittente_fiscale_id`, `emittente_atteso_id`, `numero_ddt`).

---

### Casi d'uso

| Scenario | Comportamento |
|---|---|
| DDT da evasione (emittente+BA ereditati dall'ordine) | Passa: coerenti per costruzione |
| Standalone, BA→EF1, emittente EF1 (o fallback-da-BA) | Passa |
| Standalone, payload emittente EF2 ma BA→EF1 | **Errore** `E_DDT_EMITTENTE_BA_INCOERENTE` |
| DDT senza BA risolvibile (`billing_account_id NULL`) | Passa: check saltato |
| UPDATE `emittente_fiscale_id` divergente dal BA | **Errore** `E_DDT_EMITTENTE_BA_INCOERENTE` |

---

### Errori sollevati

| Codice | id | Quando | Contesto JSONB |
|---|---|---|---|
| `E_DDT_EMITTENTE_BA_INCOERENTE` | 527 | `emittente_fiscale_id ≠ fn_get_emittente_fiscale_pk(billing_account_id)` (con BA valorizzato, dopo il normalize) | `billing_account_id`, `emittente_fiscale_id`, `emittente_atteso_id`, `numero_ddt` |

---

### Note operative

- Distinto dal write-guard di scope RLS
  `trg_ddt_a10_guard_emittente_scope_ins_upd` (verifica lo **scope operatore**
  sull'emittente): questo verifica la **coerenza emittente↔BA** del documento.
- Per il BE è trasparente: mandando un emittente coerente col BA del cliente non
  si incontra l'errore.

---

{% include-markdown "signature-core.md" %}
