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
(latest review 03-04-2026)
`vendite.vw_preventivi_list` e' la vista denormalizzata principale per la **lista preventivi
vendita**. Espone tutti i dati necessari al frontend (tabella lista) e al backend (filtro
permessi per scope emittente).

---

### JOIN principali

| Tabella | Dati esposti |
|---------|-------------|
| `config.stati_doc_preventivi` | Codice e descrizione stato |
| `anagrafiche.billing_account` → `soggetti_ruoli` → `soggetti` | Denominazione cliente |
| `config.valute` | Codice valuta |
| `config.termini_pagamento` | Descrizione termini |
| `anagrafiche.fn_get_emittente_fiscale_id()` | emittente_fiscale_id per scope permessi |

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
