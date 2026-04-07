## 📘 Documentazione Concettuale – Vista `vendite.vw_preventivi_list`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
>
[vendite.preventivi](/dbzero/vendite/tabelle/preventivi)
> [config.stati_doc_preventivi](/dbzero/config/tabelle/stati_doc_preventivi)
> [anagrafiche.billing_account](/dbzero/anagrafiche/tabelle/billing_account)
> [config.valute](/dbzero/config/tabelle/valute)
> [config.termini_pagamento](/dbzero/config/tabelle/termini_pagamento)

---
### 🎯 Scopo Principale

(latest review 07-04-2026)

`vendite.vw_preventivi_list` e' la vista denormalizzata principale per la **lista preventivi
vendita**. Espone tutti i dati necessari al frontend (tabella lista) e al backend (filtro
permessi per scope emittente).

---

> ### Nota sulla colonna `emittente_fiscale_id`
>
> Dalla revisione del **07-04-2026** la colonna espone la **PK numerica reale** di
> `anagrafiche.emittenti_fiscali.id`, derivata via [`fn_get_emittente_fiscale_pk`](/dbzero/anagrafiche/funzioni/fn_get_emittente_fiscale_pk).
>
> **In precedenza** la vista usava `fn_get_emittente_fiscale_id` che, nonostante il nome,
> restituisce un `soggetto_ruolo_id`: il valore esposto era quindi semanticamente
> incompatibile con `config.parameter_overrides.emittente_fiscale_id` (FK reale a
> `emittenti_fiscali.id`) usata dal filtro permessi backend.
>
> Il fix allinea i due valori e rende il filtro permessi corretto.

---

### JOIN principali

| Tabella                                                       | Dati esposti                                         |
|---------------------------------------------------------------|------------------------------------------------------|
| `config.stati_doc_preventivi`                                 | Codice e descrizione stato                           |
| `anagrafiche.billing_account` → `soggetti_ruoli` → `soggetti` | Denominazione cliente                                |
| `config.valute`                                               | Codice valuta                                        |
| `config.termini_pagamento`                                    | Descrizione termini                                  |
| `anagrafiche.fn_get_emittente_fiscale_pk()`                   | `emittente_fiscale_id` per scope permessi (PK reale) |

---

### 📑 Campi chiave esposti

* **Identificatori**: id, uid, numero, rev, is_revision_attiva, data
* **Stato**: stato_doc_preventivo_id, stato_codice, stato_descrizione
* **Controparte**: billing_account_id, ba_utility_id, soggetto_id, cliente_denominazione
* **Permessi**: emittente_fiscale_id (derivato da BA)
* **Contesto**: utility_id, istanza_utility_id
* **Importi**: totale_imponibile, totale_iva, totale_documento
* **Condizioni**: valuta_id, valuta_codice, termine_pagamento_id, termine_pagamento_descrizione
* **Validita'**: validita_dal, validita_al, competenza_mese
* **Flag**: fatturazione_immediata, storicizza

**Ordinamento default**: data DESC, numero DESC.

---

### Esempio d'uso

```sql
-- Lista preventivi per un emittente, filtro stato
SELECT id, numero, rev, data, stato_codice, cliente_denominazione,
       totale_documento, validita_al
FROM vendite.vw_preventivi_list
WHERE emittente_fiscale_id = 1
  AND stato_codice = 'EMESSO'
ORDER BY data DESC;
```

---

{% include-markdown "signature-core.md" %}
