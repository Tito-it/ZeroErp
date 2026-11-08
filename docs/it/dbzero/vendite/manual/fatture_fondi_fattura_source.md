## 📘 Documentazione Concettuale – Tabella `vendite.fatture_fondi_fattura_source`

> **Ultimo aggiornamento**: 4 novembre 2026

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
• [vendite.fatture](/dbzero/vendite/tabelle/fatture)  
> • [vendite.tipi_fondi_fattura](/dbzero/vendite/tabelle/tipi_fondi_fattura)  
> • [vendite.fatture_fondi_fattura](/dbzero/vendite/tabelle/fatture_fondi_fattura)  
>
### 🔴 rev 31-08-2026 — LA ROW SECURITY SI ACCENDE (D-20)

Due policy, le stesse della famiglia dei satelliti della fattura:

| Policy | Comando | Chi | Scope |
| --- | --- | --- | --- |
| `rls_fatture_fondi_fattura_source_ef_whitelist` | `FOR ALL` | `OPERATORE` | `fn_scope_ef_whitelist_via_sr` |
| `rls_fatture_fondi_fattura_source_ba_ownership` | `FOR SELECT` | `CLIENTE_PORTALE` | `fn_scope_ba_ownership` |

⚠️ **Non era cambiata la conclusione: era scaduta la PREMESSA.** Quando si decise
«niente RLS, il perimetro passa dalla fattura», l'unico accesso era **la lista**,
protetta dal `JOIN INNER` con `vendite.fatture`. Oggi la tabella ha un lettore
applicativo, una pagina aperta agli operatori, uno scrittore in un **altro
schema** (`pagamenti.fn_conferma_sistemazione`) e un accesso **per id** — e un id
non ha nessun `JOIN` davanti.

⭐ **Qui è più semplice che sugli altri satelliti**: `emittente_soggetto_ruolo_id`
e `billing_account_id` sono **in colonna e NOT NULL**, quindi la `WITH CHECK` li
legge da `NEW` invece di cercare il legame che l'`INSERT` sta scrivendo — che è
precisamente l'errore corretto su `pagamenti.enti_incasso`.

> ⭐ **E la misura ha trovato più della domanda.** Guardando *quali* satelliti
> della fattura hanno i presidi, il fondo era l'assente di **due** famiglie:
> niente congelamento oltre `EMESSA` e niente RLS. Erano la stessa dimenticanza
> vista da due lati, discussa in due posti diversi — e quell'oggetto è l'unico
> che muove denaro. L'altra metà la chiude `fn_check_fondo_cancellabile`.

ℹ️ Niente `FORCE ROW LEVEL SECURITY`, come tutta la famiglia: l'owner non è un
ruolo applicativo. Il giro notturno non attraversa la RLS: dal 2026-10-15 gira come
l'applicazione, con un utente tecnico per azienda, e vede le righe della sua azienda.
Il ruolo `zeroerp_batch_fatturazione`, che aveva `BYPASSRLS`, è ritirato.

---

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
* `stato`: `DISPONIBILE` / `ASSEGNATO` / **`ESEGUITO`** / `ANNULLATO` —
  vocabolario chiuso da `CHECK` e cammino presidiato da un guard; `ESEGUITO` e
  `ANNULLATO` sono **terminali**.
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
  (es. documento sorgente già saldato/compensato, o reset bloccato da una
  distinta contabile già chiusa).
* ⭐ Stato **`ESEGUITO`** (dal 21-08-2026): il trasferimento è stato
  **registrato in contabilità**. Non lo scrive una persona: lo scrive un
  trigger, quando la riga contabile nata dal fondo entra in uno stato
  registrato.

> ⭐ **Perché sono quattro e non tre.** `ANNULLATO` portava **tre** significati
> diversi — «non si deve fare più», «non si è più capienti», «è già stato
> eseguito» — e il terzo produceva un record che si contraddiceva: stato
> `ANNULLATO` con la fattura figlia **ancora agganciata**. Dare una parola al
> terzo caso non è cosmesi: i tre lettori dei fondi filtrano tutti sullo stato,
> quindi un atto che passa a `ESEGUITO` **esce da tutti e tre** senza che
> nessuno di loro cambi.
>
> ⚠️ **`ESEGUITO` è terminale**, per la ragione opposta e simmetrica di
> `ANNULLATO`: là si è tolto denaro dal tavolo, qui lo si è **mosso**. In
> entrambi i casi tornare indietro non disfa niente. Un fondo eseguito che si
> rivelasse sbagliato si corregge con un **atto nuovo**, ed è la ragione per cui
> i rimborsi sono un processo e non un `UPDATE`.

### Reset

* In caso di reset tecnico della fattura figlia, l'atto **non eseguito** viene
  **cancellato** insieme alle sue righe: è una *proposta*, non un fatto, e il
  giro successivo ne fa una nuova letta sul residuo **di adesso**.
* Un atto **`ESEGUITO` non si tocca mai**: il reset lo segnala nel diario della
  fattura e prosegue con gli altri.
* La logica di reset è centralizzata in `vendite.fn_reset_fondi_fattura()`.
* ⚠️ È un'operazione **tecnica sulla figlia** (ritorno del lotto in bozza),
  **non una reazione ai pagamenti**: nessun incasso riapre o chiude un fondo.

> ⚠️ **Prima del 21-08-2026 il reset riapriva** (`stato = 'DISPONIBILE'`) con
> l'importo vecchio congelato. Il passaggio `ASSEGNATO → DISPONIBILE` resta
> *ammesso* dalla matrice, ma **non lo percorre più nessuno**: è rimasto come
> unica strada per disfare l'assegnazione senza cancellare l'atto.

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

Piano completo: [brief-db-fondo-fattura…](/dev/work-done/brief-db-fondo-fattura-ricalcolo-e-governo) §8.

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
