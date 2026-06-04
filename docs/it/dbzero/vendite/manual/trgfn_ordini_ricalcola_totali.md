## 📘 Documentazione Concettuale – Trigger Function `vendite.trgfn_ordini_ricalcola_totali()`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
> [vendite.ordini](/dbzero/vendite/tabelle/ordini)
> [anagrafiche.emittenti_fiscali](/dbzero/anagrafiche/tabelle/emittenti_fiscali)
>
Approfondimento viste e funzioni:
> [vendite.fn_ricalcola_totali_ordine](/dbzero/vendite/funzioni/fn_ricalcola_totali_ordine)
> [vendite.vw_ordini_righe_iva_base](/dbzero/vendite/views/vw_ordini_righe_iva_base)
> [config.fn_get_aliquota_iva](/dbzero/config/funzioni/fn_get_aliquota_iva)

---

### 🎯 Scopo Principale

(latest review 05-06-2026)

`vendite.trgfn_ordini_ricalcola_totali()` ricalcola i totali dell'ordine quando
cambia `vendite.ordini.emittente_fiscale_id`.

Il cambio emittente puo' cambiare lo stato fiscale usato da
`config.fn_get_aliquota_iva`, e quindi l'aliquota effettiva del riepilogo IVA.
Senza questo trigger, i totali persistiti in testata potrebbero restare stantii.

---

### Trigger associato

| Nome | Timing | Evento | Condizione |
| --- | --- | --- | --- |
| `trg_ordini_z90_ricalcola_totali_upd` | AFTER ROW | `UPDATE OF emittente_fiscale_id` | valore realmente cambiato |

Il trigger usa:

```sql
WHEN (OLD.emittente_fiscale_id IS DISTINCT FROM NEW.emittente_fiscale_id)
```

La funzione ripete lo stesso controllo prima di invocare il ricalcolo.

---

### Logica

1. Verifica che `NEW.emittente_fiscale_id` sia diverso da
   `OLD.emittente_fiscale_id`.
2. Invoca:

   ```sql
   PERFORM vendite.fn_ricalcola_totali_ordine(NEW.id);
   ```

3. Ritorna `NEW`.

---

### Perche' solo `emittente_fiscale_id`

La vista base ricava lo stato fiscale dalla catena:

```text
ordini.emittente_fiscale_id
  -> emittenti_fiscali.soggetto_ruolo_id
  -> soggetti_ruoli.soggetto_id
  -> soggetti.stato_id
```

Tra i campi della testata ordine, `emittente_fiscale_id` e' quello che puo'
modificare direttamente la catena usata per l'aliquota effettiva. Gli altri
cambi di importo dipendono dalle righe e sono gestiti dai trigger su
`vendite.ordini_righe`.

---

### Ricorsione

Non c'e' ricorsione: `fn_ricalcola_totali_ordine` aggiorna solo
`imponibile_tot`, `sconto_tot`, `iva_tot` e `totale_doc`, non
`emittente_fiscale_id`.

---

{% include-markdown "signature-core.md" %}
