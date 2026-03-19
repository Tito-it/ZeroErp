## 📘 Documentazione Concettuale – Funzione `vendite.fn_prepare_sdi_payload`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
• [vendite.fatturazione_lotti](/dbzero/vendite/tabelle/fatturazione_lotti)  
> • [vendite.fatture_sdi](/dbzero/vendite/tabelle/fatture_sdi)  
> • [vendite.fatture_sdi_eventi](/dbzero/vendite/tabelle/fatture_sdi_eventi)  
> • [config.stati_sdi](/dbzero/config/tabelle/stati_sdi)  

---
### 🎯 Scopo Principale
(latest review 16-02-2026)  
Preparare il payload SDI di un lotto:

* apre (o riusa) i tentativi in `vendite.fatture_sdi`
* registra l'evento tecnico `PREPARED` in `vendite.fatture_sdi_eventi`
* restituisce il dataset fatture pronto per generazione file di invio

---

### Regole principali

* `p_lotto_id` obbligatorio e > 0.
* Stato SDI risolto da `config.stati_sdi.codice_interno` (default `DA_INVIARE`).
* Idempotenza:
  * se esiste tentativo aperto (`data_invio IS NULL`) viene riusato;
  * altrimenti viene creato nuovo tentativo incrementale.
* `p_force_new_tentativo = true` forza l'apertura di un nuovo tentativo.

---

### Nota su `p_force_new_tentativo`

* `false` (default): comportamento consigliato. Se il tentativo aperto esiste, la funzione lo riusa.  
  Utile per rilanciare un processo interrotto senza creare duplicati.
* `true`: forza sempre un nuovo tentativo (`tentativo_num` incrementale), anche se ne esiste uno aperto.  
  Da usare solo quando si vuole esplicitamente una nuova estrazione (retry controllato / nuova revisione payload).

---

### Esempio

```sql
SELECT *
FROM vendite.fn_prepare_sdi_payload(
  p_lotto_id => 123,
  p_stato_sdi_codice_interno => 'DA_INVIARE',
  p_force_new_tentativo => false
);
```

---

{% include-markdown "signature-core.md" %}
