## 📘 Documentazione Concettuale – Tabella `vendite.fatture_fondi_fattura_source`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
• [vendite.fatture](/dbzero/vendite/tabelle/fatture)  
> • [vendite.tipi_fondi_fattura](/dbzero/vendite/tabelle/tipi_fondi_fattura)  
> • [vendite.fatture_fondi_fattura](/dbzero/vendite/tabelle/fatture_fondi_fattura)  
>
### 🎯 Scopo Principale
(latest review 11-02-2026)  
`vendite.fatture_fondi_fattura_source` registra la **sorgente** dei fondi
fattura derivati da documenti precedenti. Serve a garantire idempotenza e
selezione deterministica dei fondi disponibili per l’addebito/accredito.

---

### Campi chiave (semantica)

* `fattura_sorgente_id`: fattura che genera il fondo.
* `tipo_fondo_fattura_id`: tipologia fondo.
* `importo`: valore del fondo.
* `stato`: `DISPONIBILE` / `ASSEGNATO` / `ANNULLATO`.
* `fattura_figlia_id`: fattura che utilizza il fondo (opzionale).
* `data_assegnazione`, `user_assegnazione`: audit assegnazione.
* Chiavi denormalizzate: `billing_account_id`, `utility_id`, `tipo_doc_fiscale_id`,
  `emittente_soggetto_ruolo_id`, `valuta_id`.

---

### Note operative

* La generazione e` vincolata alla **fattura sorgente**.
* L’applicazione avviene solo per record `DISPONIBILE`.
* In caso di storni, la policy di riapertura va gestita per tipologia fondo.
* La tabella e` pensata anche per scenari di **compensazione** tra insoluti
  e crediti cliente (tipici nei processi utilities).
* Stato `ANNULLATO`: usato quando la source non e` piu` eseguibile
  (es. documento sorgente gia` saldato/compensato o reset bloccato da movimenti contabilizzati).

### Reset e riapertura

* In caso di reset tecnico della fattura figlia, i fondi applicati vengono
  **ripristinati** a stato `DISPONIBILE` e la relazione con la fattura figlia
  viene rimossa.
* La logica di reset e` centralizzata in `vendite.fn_reset_fondi_fattura()`.

### Reset per tipologie non standard (WIP)

* Alcune tipologie di fondo (es. canone RAI o altri addebiti esterni)
  possono richiedere reset su **tabelle dedicate**.
* Per queste tipologie saranno previste funzioni specifiche di ripristino,
  richiamate dal reset tecnico della fattura solo se applicabili.

---

{% include-markdown "signature-core.md" %}
