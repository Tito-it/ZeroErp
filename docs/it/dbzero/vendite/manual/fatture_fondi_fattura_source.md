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

* La generazione è vincolata alla **fattura sorgente**, che deve rientrare nella
  **banda** delle due soglie di `anagrafiche.emittenti_fiscali_utilities`
  (`minimo_soglia_min` / `minimo_soglia_max`). La banda **contiene lo zero**:
  ⭐ un `importo` **negativo** è quindi legittimo — è un credito riportato
  avanti, non un difetto.
* L’applicazione avviene solo per record `DISPONIBILE`.
* La tabella è pensata anche per scenari di **compensazione** tra insoluti
  e crediti cliente (tipici nei processi utilities).
* Stato `ANNULLATO`: usato quando la source non è più eseguibile
  (es. documento sorgente già saldato/compensato o reset bloccato da movimenti contabilizzati).

### Reset e riapertura

* In caso di reset tecnico della fattura figlia, i fondi applicati vengono
  **ripristinati** a stato `DISPONIBILE` e la relazione con la fattura figlia
  viene rimossa.
* La logica di reset è centralizzata in `vendite.fn_reset_fondi_fattura()`.
* ⚠️ È un'operazione **tecnica sulla figlia** (ritorno del lotto in bozza),
  **non una reazione ai pagamenti**: nessun incasso riapre o chiude un fondo.

### 🔴 ~~Storni e riapertura per tipologia~~ — concetto ritirato (2026-08-15)

> ~~«In caso di storni, la policy di riapertura va gestita per tipologia fondo»~~
> e ~~«Reset per tipologie non standard (WIP): funzioni specifiche di
> ripristino»~~ **non si faranno**, per due ragioni indipendenti:
>
> 1. **lo storno non esiste più come concetto**: una correzione è una
>    contabile con importi negativi (cantiere incassi, decisione D3-d);
> 2. una riapertura automatica sarebbe **un automatismo che riscrive uno stato
>    in reazione a un pagamento**, e sono stati esclusi tutti: *i fatti si
>    aggiungono, i saldi si leggono, le decisioni le prende una persona.*
>
> Un fondo esistente **resta com'è**; se non è più giustificato, semplicemente
> **non viene applicato**.

### 🟠 Che cosa cambia con il piano in corso

Piano completo: [brief-db-fondo-fattura…](/dev/work-in-progress/brief-db-fondo-fattura-ricalcolo-e-governo) §8.

| Oggi | Diventerà |
| --- | --- |
| l'importo di una source non assegnata viene **riallineato** dai giri di fatturazione successivi | **si congela**: una fattura sorgente `DEFINITIVA` ha un fondo definitivo (lock di colonna su `importo`) |
| la sorgente può essere in **qualunque** stato, `ANNULLATA` compresa | solo sorgenti **`DEFINITIVA`** |
| nessun vincolo impedisce **due fondi vivi** sulla stessa sorgente | indice unico parziale sugli atti automatici |
| `stato` è un `varchar` **senza CHECK**: il vocabolario vive solo nelle funzioni | CHECK sul vocabolario + guard di transizione |
| l'`importo` non ha **nessun CHECK** | `importo <> 0` + guard di **corrispondenza con la sorgente** (stesso segno del totale, non superiore in valore assoluto) |

---

{% include-markdown "signature-core.md" %}
