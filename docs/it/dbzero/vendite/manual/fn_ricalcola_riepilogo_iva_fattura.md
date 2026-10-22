## 📘 Documentazione Concettuale – Funzione `vendite.fn_ricalcola_riepilogo_iva_fattura`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
• [vendite.fatture_righe](/dbzero/vendite/tabelle/fatture_righe)    
> • [vendite.fatture_riepiloghi_iva](/dbzero/vendite/tabelle/fatture_riepiloghi_iva)    
>
**Approfondimento funzioni:**
>
• [vendite.fn_ricalcola_riepiloghi_iva_lotto](/dbzero/vendite/funzioni/fn_ricalcola_riepiloghi_iva_lotto)    

---
### 🎯 Scopo Principale
(latest review 10-02-2026)  
La funzione **`vendite.fn_ricalcola_riepilogo_iva_fattura()`** ricalcola i riepiloghi
IVA per una singola fattura, eliminando i valori esistenti e rigenerandoli dalle
righe (`fatture_righe`).

---

### Regole principali

* `p_fattura_id` obbligatorio e `> 0`.
* ~~Ricalcolo ammesso solo se lo stato documento è `DRAFT` o `EMESSA`~~ ⛔ **non è
  più vero dal 2026-08-29**: la soglia si legge da
  `config.stati_doc_fiscale.congela_fiscale`, **non** da una lista di codici
  scritta qui dentro. ⭐ Una lista in una funzione e una colonna sulla tabella
  degli stati sono due verità sullo stesso fatto, e divergono in silenzio al
  primo stato nuovo. In caso di dubbio **non si ricalcola**: il valore è
  fail-closed.
* L’imponibile e` arrotondato a 2 decimali (half-up) prima del calcolo imposta.
* L’imposta e` calcolata come `round(imponibile_arrotondato * aliquota_iva / 100, 2)` con arrotondamento half-up.
* L’aliquota IVA e` risolta in base allo **stato fiscale dell’emittente**
  (override da `config.iva_stati` se presente), e da `20260829-39` viene
  **scritta anche sul riepilogo**, accanto a imponibile e imposta: chi ristampa
  un documento non deve più andarsela a ricalcolare.
* ⭐ **rev 2026-08-29: prima di aggregare, la funzione RIALLINEA l'aliquota delle
  righe** al catalogo di adesso. Questa funzione, per costruzione, vede **solo
  documenti non congelati** — il guard qui sopra rifiuta gli altri — e su un
  documento che può ancora cambiare la risposta giusta è la configurazione
  corrente. È la stessa regola che segue il trigger di riga.
  ⚠️ **Non si confonda con lo snapshot**: `fatture_righe.aliquota_iva` diventa una
  fotografia quando il documento **smette di essere scritto**, non perché
  qualcuno smette di leggerlo. Il riallineamento tocca solo ciò che è davvero
  cambiato.
* ⭐ **Riallinea anche `esigibilita` e `split_payment`** (dal 2026-10-01, D-8 di
  `brief-db-esigibilita-iva-per-cassa-emittente`), per la stessa ragione: la
  riga li deriva quando viene scritta, ma il regime dell'emittente, la scissione
  o la partita IVA del cliente possono cambiare dopo. La coppia esce da
  [vendite.fn_esigibilita_iva_fattura](/dbzero/vendite/funzioni/fn_esigibilita_iva_fattura),
  che usa il regime **congelato nello snapshot** dell'intestazione: il passo
  `ricalcola_iva_lotto` della fase EMESSA, l'ultimo prima del congelamento,
  lascia righe e testata sullo stesso regime.
* ⭐ **Una riga senza codice IVA non rompe il riepilogo** (rev 2026-10-22): entra nel
  riepilogo della bozza con l'aliquota vuota, invece di sollevare l'errore tecnico del
  catalogo. La fattura però **non si emette**: lo ferma
  [vendite.trgfn_fatture_guard_stato](/dbzero/vendite/manual/trgfn_fatture_guard_stato) con
  `E_FATTURA_RIGA_IVA_MANCANTE`. La guardia esiste solo insieme al cancello: da sola sarebbe
  uno zero muto su un documento fiscale.
* I riepiloghi sono ricreati aggregando per combinazione fiscale.

---

### Output

Ritorna una riga con:

* `deleted_rows` = numero righe rimosse da `fatture_riepiloghi_iva`
* `inserted_rows` = numero righe inserite

---

### Esempio d’uso

```sql
SELECT *
FROM vendite.fn_ricalcola_riepilogo_iva_fattura(
  p_fattura_id => 123
);
```

---

{% include-markdown "signature-core.md" %}
