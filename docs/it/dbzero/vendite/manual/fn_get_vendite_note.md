## 📘 Documentazione Concettuale – Funzione `vendite.fn_get_vendite_note`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
• [vendite.note](/dbzero/vendite/tabelle/note)  
> • [vendite.note_fatture](/dbzero/vendite/tabelle/note_fatture)  
>
**Approfondimento funzioni:**
>
• [script.fn_get_note](/dbzero/script/funzioni/fn_get_note)  

---
### 🎯 Scopo Principale
(latest review 10-02-2026)  
La funzione **`vendite.fn_get_vendite_note()`** e` un wrapper su
`script.fn_get_note('vendite.note')` per recuperare le note vendite
da tabella partizionata in modo uniforme.

---

### Regole principali

* `target_tipo` identifica il tipo documento col codice di `config.tipi_entita` (es. `FATTURA`,
  `ORDINE_VENDITA`, `DDT_VENDITA`; ultima revisione: 2026-10-25 (brief-db-grammatica-unica-documenti, lotto 3): fino ad allora `ORDINE`, `DDT`).
* `target_id` identifica la testata.
* `target_riga_id` opzionale per note di riga.
* `include_doc` e `include_righe` filtrano note di testata e riga.
* `only_visible` applica il filtro di visibilita`.

---

### Output

Ritorna le note con campi standard: target, anchor, posizione, testo, stile,
lingua, visibilita`, meta e audit.

---

### Esempio d’uso

```sql
SELECT *
FROM vendite.fn_get_vendite_note(
  _target_tipo => 'FATTURA',
  _target_id => 123,
  _target_riga_id => NULL,
  _include_doc => true,
  _include_righe => true,
  _only_visible => true
);
```

---

{% include-markdown "signature-core.md" %}
