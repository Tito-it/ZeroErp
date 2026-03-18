## 📘 Documentazione Concettuale – Funzione `vendite.fn_close_giornaliero_lotto`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
• [vendite.fatturazione_lotti](/dbzero/vendite/tabelle/fatturazione_lotti)  
> • [vendite.fatturazione_lotti_fatture](/dbzero/vendite/tabelle/fatturazione_lotti_fatture)  
> • [vendite.fatture](/dbzero/vendite/tabelle/fatture)  
>
**Approfondimento funzioni:**
>
• [vendite.fn_sync_lotto_fatture_stato](/dbzero/vendite/funzioni/fn_sync_lotto_fatture_stato)  
> • [vendite.fn_set_fatturazione_lotto_stato](/dbzero/vendite/funzioni/fn_set_fatturazione_lotto_stato)  
>
### 🎯 Scopo Principale
(latest review 03-02-2026)
La funzione **`vendite.fn_close_giornaliero_lotto()`** chiude operativamente
un lotto di tipo **GIORNALIERO** e allinea lo stato documentale delle fatture
collegate al valore passato (tipicamente stato `INVIATA`).

---

### Regole principali

* `p_lotto_id` obbligatorio.
* `p_inviata_stato_doc_fiscale_id` obbligatorio.
* Il lotto deve esistere.
* Il lotto deve essere di tipo `GIORNALIERO`.
* Aggiorna il lotto:
  * `stato_operativo = 'CHIUSO'`
  * `stato_doc_fiscale_id = p_inviata_stato_doc_fiscale_id`
* Aggiorna tutte le fatture collegate in `vendite.fatturazione_lotti_fatture`
  impostando `stato_doc_fiscale_id = p_inviata_stato_doc_fiscale_id`.

---

### Output

Ritorna una riga con:

* `updated_lotti` = numero lotti aggiornati (atteso: 1)
* `updated_fatture` = numero fatture aggiornate

---

### Esempio d’uso

```sql
SELECT *
FROM vendite.fn_close_giornaliero_lotto(
  p_lotto_id => 123,
  p_inviata_stato_doc_fiscale_id => 3
);
```

---

{% include-markdown "signature-core.md" %}
