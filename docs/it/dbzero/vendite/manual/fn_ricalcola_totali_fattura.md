## 📘 Documentazione Concettuale – Funzione `vendite.fn_ricalcola_totali_fattura`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
• [vendite.fatture](/dbzero/vendite/tabelle/fatture)  
> • [vendite.fatture_riepiloghi_iva](/dbzero/vendite/tabelle/fatture_riepiloghi_iva)  
> • [vendite.fatture_fondi_fattura](/dbzero/vendite/tabelle/fatture_fondi_fattura)  
> • [anagrafiche.emittenti_fiscali_utilities](/dbzero/anagrafiche/tabelle/emittenti_fiscali_utilities)  
>
**Approfondimento funzioni:**
>
• [vendite.fn_get_totale_fondi_fattura](/dbzero/vendite/funzioni/fn_get_totale_fondi_fattura)  
> • [vendite.fn_get_arrotondamento_scope](/dbzero/vendite/funzioni/fn_get_arrotondamento_scope)  
> • [vendite.fn_set_arrotondamento_scope](/dbzero/vendite/funzioni/fn_set_arrotondamento_scope)  
> • [vendite.fn_sync_contabili_fondo_fattura](/dbzero/vendite/funzioni/fn_sync_contabili_fondo_fattura)  
>
### 🎯 Scopo Principale
La funzione **`vendite.fn_ricalcola_totali_fattura()`** ricalcola i totali
sulla testata fattura a partire dai **riepiloghi IVA** e dai **fondi fattura**,
applicando le regole di arrotondamento definite per **emittente/utility**.

---

### Regole principali

* `p_fattura_id` obbligatorio.
* Totali calcolati da `fatture_riepiloghi_iva`.
* Totale fondi fattura via `vendite.fn_get_totale_fondi_fattura()`.
* Arrotondamento calcolato con i parametri **effettivi** di emittente e utility,
  da `anagrafiche.fn_parametri_importo_utility`: la riga di
  `anagrafiche.emittenti_fiscali_utilities` se c'è, altrimenti i valori di sistema
  dell'utility (`config.utilities`) e, per il metodo, la policy generale
  dell'emittente. Senza la riga la fattura **si chiude** (rev 21-10-2026,
  brief-db-modelli-documento-standard §10.3 K-7): `E_CONFIG_MANCANTE` resta solo
  per una fattura senza utility. L'arrotondamento lo fa `script.fn_arrotonda_importo`, la sede
  unica delle quattro regole (rev 21-10-2026, R-2: prima una copia delle formule).
* Aggiorna il saldo tecnico con `fn_set_arrotondamento_scope()`.
* Imposta `minimo = true` quando `totale_a_pagare` rientra nella soglia
  (`minimo_soglia_min`/`minimo_soglia_max`).

  ⭐ **È qui che si decide se una fattura si riporta sulla successiva**, e questa
  è l'unica pagina in cui la regola è scritta per intero: le due soglie sono i
  due capi di una **banda che contiene lo zero** (es. `−500` / `+10`), quindi ci
  rientrano sia le fatture troppo piccole da incassare sia i **crediti** troppo
  piccoli da rimborsare. Chi legge solo la doc del
  [fondo fattura](/dbzero/vendite/tabelle/fatture_fondi_fattura_source) non la
  trova, e ne deduce che un fondo sia sempre a debito.

  🔴 **Attenzione a una configurazione a metà.** La condizione è
  `(soglia_min NON vuota E totale >= soglia_min) E (soglia_max vuota O totale <= soglia_max)`:
  se manca **il minimo** il meccanismo è spento (corretto), ma se manca **il
  massimo** la seconda condizione è vera per tutti e **ogni** fattura sopra il
  minimo diventa «di minimo». Una configurazione incompleta oggi non chiude:
  **spalanca**. È previsto un vincolo «entrambe o nessuna»
  ([piano](/dev/work-done/brief-db-fondo-fattura-ricalcolo-e-governo) §8.2 D-0).
* Esegue la sincronizzazione contabile dei fondi assegnati alla fattura
  (`fn_sync_contabili_fondo_fattura`).

---

### Output

Non ritorna valori. Aggiorna la testata fattura.

---

### Esempio d’uso

```sql
SELECT vendite.fn_ricalcola_totali_fattura(
  p_fattura_id => 123
);
```

---

{% include-markdown "signature-core.md" %}
