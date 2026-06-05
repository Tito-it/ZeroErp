## 📘 Documentazione Concettuale – Vista `vendite.vw_ordini_righe_iva_base`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
> [vendite.ordini](/dbzero/vendite/tabelle/ordini)
> [vendite.ordini_righe](/dbzero/vendite/tabelle/ordini_righe)
> [vendite.ordini_righe_componenti](/dbzero/vendite/tabelle/ordini_righe_componenti)
> [anagrafiche.emittenti_fiscali](/dbzero/anagrafiche/tabelle/emittenti_fiscali)
> [config.iva](/dbzero/config/tabelle/iva)
>
Approfondimento funzioni e viste:
> [config.fn_get_aliquota_iva](/dbzero/config/funzioni/fn_get_aliquota_iva)
> [vendite.vw_ordini_riepilogo_iva_dettaglio](/dbzero/vendite/views/vw_ordini_riepilogo_iva_dettaglio)
> [vendite.fn_ricalcola_totali_ordine](/dbzero/vendite/funzioni/fn_ricalcola_totali_ordine)

---

### 🎯 Scopo Principale

(latest review 05-06-2026)

`vendite.vw_ordini_righe_iva_base` e' la sorgente normalizzata per il calcolo
IVA degli ordini vendita. Espone solo righe ordine **attive** con
`quantita > 0`, calcolando gli imponibili a **precisione piena** e risolvendo
l'aliquota effettiva tramite `config.fn_get_aliquota_iva`.

La vista non produce il riepilogo finale: prepara i dati per
`vendite.vw_ordini_riepilogo_iva_dettaglio` e per
`vendite.fn_ricalcola_totali_ordine`.

---

### Regole

* Include solo `vendite.ordini_righe` con `attivo IS TRUE`.
* Include solo righe con `quantita > 0`.
* Non arrotonda gli imponibili di riga: gli importi `*_full` restano a
  precisione piena.
* Se `iva_id IS NULL`, non invoca `config.fn_get_aliquota_iva` e restituisce
  `aliquota_effettiva = NULL`.
* Se `iva_id` e' valorizzata, l'aliquota effettiva e' risolta con lo stato del
  soggetto emittente:

  ```text
  ordini.emittente_fiscale_id
    -> anagrafiche.emittenti_fiscali.soggetto_ruolo_id
    -> anagrafiche.soggetti_ruoli.soggetto_id
    -> anagrafiche.soggetti.stato_id
  ```

* Non legge direttamente `vendite.ordini_righe_componenti`: i componenti BoM
  confluiscono nel prezzo della riga padre tramite trigger dedicati. Questo
  evita il doppio conteggio IVA.
* E' definita con `WITH (security_invoker = on)`.

---

### Campi calcolati

| Campo | Formula | Note |
| --- | --- | --- |
| `imponibile_lordo_full` | `quantita * prezzo_unitario` | Lordo riga, senza sconto |
| `sconto_riga_full` | `quantita * prezzo_unitario * COALESCE(sconto_percentuale, 0) / 100` | Sconto riga full precision |
| `imponibile_riga_full` | `quantita * prezzo_unitario * (1 - COALESCE(sconto_percentuale, 0) / 100)` | Imponibile netto full precision |
| `aliquota_effettiva` | `config.fn_get_aliquota_iva(iva_id, stato_emittente_id)` | Override aliquota da stato emittente |

---

### Uso previsto

La vista e' un building block tecnico:

* alimenta il riepilogo IVA live dell'ordine;
* consente a `fn_ricalcola_totali_ordine` di calcolare `sconto_tot` come
  `lordo righe - imponibile aggregato`;
* mantiene una sola sorgente per formule e rounding.

Non deve essere usata per calcolare direttamente l'IVA per riga: l'imposta va
calcolata sull'imponibile aggregato per aliquota.

---

### Esempio

```sql
SELECT ordine_id, riga_id, iva_id, aliquota_effettiva,
       imponibile_lordo_full, sconto_riga_full, imponibile_riga_full
  FROM vendite.vw_ordini_righe_iva_base
 WHERE ordine_id = 42
 ORDER BY riga_nr;
```

---

{% include-markdown "signature-core.md" %}
