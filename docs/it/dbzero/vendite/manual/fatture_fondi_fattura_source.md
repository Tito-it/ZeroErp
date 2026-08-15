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
(latest review 15-08-2026)  
`vendite.fatture_fondi_fattura_source` registra la **sorgente** dei fondi
fattura derivati da documenti precedenti. Serve a garantire idempotenza e
selezione deterministica dei fondi disponibili per l’addebito/accredito.

> ⭐ **Dal 2026-08-15 una riga è un ATTO, non un valore.** Si compie una volta e
> non si riscrive: l'importo, la sorgente, il tipo e l'origine sono immutabili
> (`E_FONDO_ATTO_IMMUTABILE`), e ciò che non è più dovuto **si annulla con una
> ragione** invece di essere aggiornato. Prima di allora ogni giro di
> fatturazione riallineava l'importo delle source non assegnate — anche di
> fatture già stampate.

---

### Campi chiave (semantica)

* `fattura_sorgente_id`: fattura che genera il fondo. **Immutabile.**
* `tipo_fondo_fattura_id`: tipologia fondo. **Immutabile.**
* `importo`: valore del fondo. **Immutabile**, e vincolato a *corrispondere* alla
  sorgente (stesso segno del `totale_a_pagare`, non superiore in valore assoluto).
* `stato`: `DISPONIBILE` / `ASSEGNATO` / `ANNULLATO` — vocabolario chiuso da
  `CHECK` e cammino presidiato da un guard; `ANNULLATO` è **terminale**.
* `origine`: `AUTOMATICA` / `MANUALE`. ⭐ Non dice *chi* ha creato il fondo: dice
  **quale regola si applica**. L'atto automatico è *vincolato* dal guard di
  corrispondenza, quello manuale è *governato* (motivo obbligatorio, e arriva dal
  processo rimborsi di `pagamenti`). **Immutabile.**
* `motivo`: la ragione dell'atto, **obbligatoria dove l'atto è straordinario** —
  su `MANUALE` e su ogni `ANNULLATO`. È il posto dove la ragione smette di essere
  un testo di diario in `fatture_log` e diventa un dato interrogabile.
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

### ✅ I presidi, e da dove vengono (applicati il 2026-08-15)

Piano completo: [brief-db-fondo-fattura…](/dev/work-in-progress/brief-db-fondo-fattura-ricalcolo-e-governo) §8.

| Prima | Adesso | Chi lo fa |
| --- | --- | --- |
| l'importo di una source non assegnata veniva **riallineato** dai giri successivi | **congelato**: la sorgente `DEFINITIVA` ha un fondo definitivo | `trg_..._a10_lock_atto_upd` |
| la sorgente poteva essere in **qualunque** stato, `ANNULLATA` compresa | solo sorgenti **`DEFINITIVA`**, e la generazione **crea soltanto** | `fn_genera_fondi_fattura_source` |
| nessun vincolo impediva **due fondi vivi** sulla stessa sorgente | un solo atto automatico vivo per (sorgente, tipo) | `uq_fondi_source_atto_vivo_automatico` |
| `stato` era un `varchar` **senza CHECK**: il vocabolario viveva solo nelle funzioni | vocabolario chiuso **e** cammino presidiato | `chk_fondi_source_stato` + `trgfn_fondi_source_guard_transizione` |
| l'`importo` non aveva **nessun CHECK** | `importo <> 0` + **corrispondenza con la sorgente** | `chk_fondi_source_importo_non_zero` + `trgfn_fondi_source_guard_importo` |
| un annullamento non lasciava una ragione sul dato | `motivo` obbligatorio su `ANNULLATO` e su `MANUALE` | `chk_fondi_source_motivo_obbligatorio` |

> ⚠️ **I due presidi sull'importo non sono in serie come sembra.** I trigger
> `BEFORE ROW` girano **prima** dei `CHECK`: su una sorgente con totale diverso
> da zero, un `importo = 0` lo intercetta il **guard**, e il `CHECK` non entra
> mai in gioco. Conta quando si scrive un test.

🔵 **Cosa non è ancora presidiato**: l'`ANNULLATO` che
[fn_sync_contabili_fondo_fattura](/dbzero/vendite/funzioni/fn_sync_contabili_fondo_fattura)
scrive da sé quando la sorgente non è più capiente. Ora almeno **dichiara la sua
ragione**, ma resta uno stato cambiato senza una persona: si toglie quando
`pagamenti` avrà il processo rimborsi.

---

{% include-markdown "signature-core.md" %}
