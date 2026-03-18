## 📘 Documentazione Concettuale – Funzione `vendite.fn_upsert_commessa_attivita`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
• [vendite.commesse_attivita](/dbzero/vendite/tabelle/commesse_attivita)  
> • [vendite.commesse](/dbzero/vendite/tabelle/commesse)  
> • [vendite.stati_commessa](/dbzero/vendite/tabelle/stati_commessa)  
>
**Approfondimento funzioni:**
>
• [vendite.fn_get_commessa_stato](/dbzero/vendite/funzioni/fn_get_commessa_stato)  
>
### 🎯 Scopo Principale
(latest review 26-02-2026)  
Effettua upsert idempotente di una riga `commesse_attivita` su chiave `(commessa_id, segment_key)`, con controlli di validita` e blocchi coerenti con lo stato della commessa.

---

### Regole principali

* Parametri obbligatori: `p_commessa_id`, `p_segment_key`, `p_uom_id`, `p_istanza_utility_id`, `p_quantita`, `p_prezzo_snapshot`.
* `p_quantita` deve essere diversa da `0` (valori negativi ammessi).
* `p_prezzo_snapshot` obbligatorio (anche valori negativi ammessi).
* Normalizza `p_competenza_mese` al primo giorno del mese.
* Valida classificazione operativa:
  * `tipo_movimento`: `NORMALE` o `RETTIFICA`
  * `tipo_consumo`: `ACCONTO`, `CONGUAGLIO`, `STORNO`
* Salva `tipo_movimento` e `tipo_consumo` nel campo `meta`.
* Guard stato commessa:
  * consente upsert solo se `stati_commessa.modificabile = true`
* Se la riga esiste con `stato_emissione <> NON_EMESSA`, update bloccato.
* In update mergea il `meta` esistente con quello in input.

---

### Output

Ritorna l'`id` della riga `vendite.commesse_attivita` inserita o aggiornata.

---

### Esempio d'uso

```sql
SELECT vendite.fn_upsert_commessa_attivita(
  p_commessa_id => 12345,
  p_segment_key => 'ORD-1001-RIGA-1',
  p_articolo_id => '8c5ce3a9-8f52-4d07-ae36-884c5f8d4a1f',
  p_istanza_utility_id => 10,
  p_data_attivita => DATE '2026-02-01',
  p_uom_id => 1,
  p_quantita => 1,
  p_competenza_mese => DATE '2026-02-01',
  p_competenza_dal => DATE '2026-02-01',
  p_competenza_al => DATE '2026-02-28',
  p_prezzo_snapshot => 100
);
```

---

{% include-markdown "signature-core.md" %}
