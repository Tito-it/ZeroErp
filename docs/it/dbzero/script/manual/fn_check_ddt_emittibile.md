## 📘 Documentazione Concettuale – Funzione `script.fn_check_ddt_emittibile`

> **Ultimo aggiornamento**: 3 novembre 2026

> 👀 **Vedi anche**
>
**Consumatori (guard, sollevano):**
>
• [vendite.trgfn_ddt_guard_transizione](/dbzero/vendite/funzioni/trgfn_ddt_guard_transizione)
> • [vendite.trgfn_ddt_guard_causale_emissione](/dbzero/vendite/funzioni/trgfn_ddt_guard_causale_emissione)
> • [vendite.trgfn_ddt_guard_indirizzi_obbligatori](/dbzero/vendite/funzioni/trgfn_ddt_guard_indirizzi_obbligatori)
> • [vendite.trgfn_ddt_guard_transizione_approvazione](/dbzero/vendite/funzioni/trgfn_ddt_guard_transizione_approvazione)
>
**Consumatore (capability, disabilita+motiva):**
>
• [script.fn_available_actions_ddt](/dbzero/script/funzioni/fn_available_actions_ddt)

### 🎯 Scopo Principale

(creata 2026-07-19 — brief-db-guard-righe-avanzamento-stato §1a-bis Rev 2)

**Single source dei motivi che impediscono l'emissione (EMESSO) di un DDT.**
Ritorna `[]` se il DDT è emittibile, altrimenti l'array **ordinato** dei motivi
ostativi: `[{codice, reason, reason_key, dettaglio}, ...]`.

Nasce da un difetto reale: le cinque condizioni di emissione vivevano sparse in
quattro trigger, e la capability (`fn_available_actions_ddt`) ne conosceva una
sola — il pulsante «Emetti» risultava abilitato e il click falliva con 409.
Con questa funzione capability e guard leggono **lo stesso verdetto** e non
possono più divergere: al prossimo vincolo aggiunto, si aggiunge QUI e basta.

### Le sei condizioni (in ordine di restituzione)

| # | asse | codice | quando |
|---|---|---|---|
| 1 | struttura | `E_DDT_EMISSIONE_SENZA_RIGHE` (543) | nessuna riga attiva — zero righe = niente da trasportare; il "solo trasporto" è righe **senza prezzo**, non zero righe |
| 2 | intento | `E_DDT_CAUSALE_OBBLIGATORIA` (544) | `causale_trasporto_id` NULL — in bozza il NULL è legittimo (DL-28): il vincolo è all'emissione |
| 3 | dati riga | `E_DDT_PREZZO_NON_RISOLVIBILE` (545) | causale **fatturabile** e almeno una riga attiva senza prezzo risolvibile (proprio o ereditato dall'ordine via fulfillment) |
| **3-bis** | **valore riga** | **`E_DDT_RIGA_IVA_MANCANTE`** (1009) | ⭐ **rev 2026-08-28**: una riga attiva che porta un **prezzo** e non ha `iva_id`. ⚠️ **Non** condizionato alla causale — vedi il riquadro qui sotto |
| 4 | testata | `E_INDIRIZZO_DOC_OBBLIGATORIO` | mancano indirizzi marcati obbligatori per l'ambito DDT |
| 5 | componenti | `E_DOC_PREZZO_PENDENTE` / `E_DOC_PREZZO_RIFIUTATO` / `E_DOC_COMPONENTI_PENDING_VALORIZZAZIONE` | ⚠️ **solo se la causale è fatturabile** (rev 2026-08-19): componenti BoM CASO A attivi con il prezzo in attesa o rifiutato (dal building block [`fn_check_prezzi_autorizzati`](/dbzero/script/funzioni/fn_check_prezzi_autorizzati), rev 2026-09-24), o senza prezzo |

> ## ⭐ Rev 2026-08-28 — chi porta un prezzo porta anche l'aliquota
>
> **La domanda che l'ha decisa**, posta da Tid: *«una riga di DDT senza `iva_id`
> è ammessa a regime?»*. Risposta: **no** — e «impossibile» si traduce in **non
> emittibile**. In bozza il NULL resta legittimo, esattamente come per la
> causale al punto 2: il documento si lavora, e si dichiara completo quando esce.
>
> **Il difetto che chiude, ed era silenzioso.** `vendite.vw_ddt_righe_iva_base`
> filtra `prezzo_unitario IS NOT NULL` e **non** filtra `iva_id`;
> `vw_ddt_riepilogo_iva_dettaglio` aggrega per `(iva_id, aliquota_effettiva)` e
> calcola l'imposta con `COALESCE(aliquota, 0)`. Una riga con prezzo e senza
> aliquota produceva quindi una **riga di riepilogo con imponibile pieno, codice
> IVA vuoto e imposta zero** — su un documento che si emette e si **stampa**.
> Nessuno lo fermava: nessun altro punto guarda `iva_id`, e su
> `vendite.ddt_righe` non esiste alcun trigger di default (l'unico che nomina la
> colonna verifica soltanto che l'aliquota citata sia **attiva**, non che ci sia).
>
> ### ⭐ Il discrimine è il PREZZO, non la causale
>
> Per questo il controllo sta **fuori** dal ramo `IF COALESCE(v_fatturabile,
> false)`, dove invece stanno i punti 3, 5 e 6. Metterlo dentro è la cosa che
> *sembra ordinata*, e sarebbe sbagliata: la vista del riepilogo la causale **non
> la guarda affatto**, quindi anche su un conto visione una riga valorizzata
> entrerebbe nel conto con l'imposta a zero.
>
> > **Un vincolo deve avere lo stesso perimetro del consumatore che protegge.**
>
> In una riga: *c'è un prezzo, quindi c'è un valore, quindi serve un'aliquota* —
> ed è lo stesso discrimine già scelto al punto 1, dove il «DDT di solo
> trasporto» è dichiarato legittimo perché è fatto di righe **senza prezzo**.
>
> ### ⚠️ Si guarda `dr.prezzo_unitario`, non il `COALESCE` col fulfillment
>
> Il punto 3 risale il prezzo alla riga d'ordine; qui **no**, di proposito. Una
> riga dal prezzo solo **derivato** non entra in `vw_ddt_righe_iva_base` (che
> legge la sola colonna), quindi non ha il difetto: pretendere lì l'aliquota
> bloccherebbe un documento sano.
>
> ⚠️ Che poi la vista **non conosca** il fulfillment è un'asimmetria vera — un
> DDT da evasione ordine supera questo gate e stampa un riepilogo IVA vuoto — ma
> è un'altra voce, di un altro perimetro: si cura insegnando il `COALESCE` alla
> vista, non allargando questo punto.
>
> ### ⛔ Perché non un `NOT NULL` sulla colonna
>
> Sarebbe la forma letterale, e **non è disponibile in un passo**:
> `vendite.ordini_righe.iva_id` è **nullable**, e `fn_genera_ddt_da_ordine` copia
> quel valore tale e quale. Un `NOT NULL` su `vendite.ddt_righe.iva_id` avrebbe
> fatto **fallire l'evasione di un ordine** ogni volta che la riga d'ordine non
> ha l'aliquota — con un `23502`, cioè un errore tecnico muto, su un percorso che
> funziona. Il NULL è ammesso lungo **tutta** la catena (`ordini_righe`,
> `ddt_righe_componenti`, `ddt_righe`): chiudere l'ultimo anello senza chiudere i
> primi non rende il dato obbligatorio, sposta il punto di rottura su chi non
> c'entra.
>
> ⭐ *Un vincolo si mette dove il dato **si può fornire**, non dove il difetto si
> vede.*
>
> ### ⛔ E non si riusa `fn_check_ddt_riga_richiede_prezzo`
>
> Risponde a un'altra domanda — *«questa riga appartiene a un documento che
> **vende**?»* — che qui non si pone: riusarla condizionerebbe il controllo alla
> causale, cioè il difetto descritto sopra.
>
> Piano: `brief-db-ddt-riconsegna-eredita-testata`, Fase C.

---

> ## ⚠️ Rev 2026-08-19 — anche i componenti seguono la causale
>
> I due motivi del punto 5 erano **incondizionati**, e il secondo era
> **irraggiungibile**: cercava un prezzo `NULL` su una colonna `NOT NULL` in
> tutte e quattro le tabelle gemelle — un presidio davanti a una porta murata,
> dentro questa funzione.
>
> Da quando il prezzo dei componenti DDT può mancare, quel ramo **è tornato
> vivo**. Senza condizionarlo alla causale avrebbe bloccato all'emissione ogni
> DDT con un kit non valorizzato, **compresi quelli che non si fatturano** —
> cioè proprio i documenti che si voleva rendere possibili: il conto visione di
> un kit sarebbe passato da «impossibile da caricare» a «impossibile da
> emettere».
>
> ⭐ È la regola del punto 3 applicata un livello più sotto: **padre e figli
> obbediscono alla stessa dichiarazione**, la causale.

> ## Rev 2026-09-24 — il prezzo non autorizzato dal building block
>
> Il punto 5 non scrive più da sé la domanda *«c'è un componente col prezzo in
> attesa?»*: la chiede a
> [`script.fn_check_prezzi_autorizzati`](/dbzero/script/funzioni/fn_check_prezzi_autorizzati),
> la sede unica della regola *«un prezzo che nessuno ha autorizzato non esce dalla
> bozza»*, comune a preventivi, contratti, offerte, ordini e DDT.
>
> Cosa cambia per il DDT:
>
> * conta anche il prezzo **rifiutato** (`REJECTED`), non solo quello in attesa;
> * contano solo i componenti **attivi** di righe attive: un componente spento
>   resterebbe rifiutato per sempre e bloccherebbe il documento senza rimedio;
> * il motivo cambia codice: `E_DOC_PREZZO_PENDENTE` / `E_DOC_PREZZO_RIFIUTATO`
>   (reason `PREZZO_PENDENTE` / `PREZZO_RIFIUTATO`) invece di
>   `E_COMPONENTE_PREZZO_PENDENTE` (reason `COMPONENTI_PREZZO_PENDENTE`).
>   `E_COMPONENTE_PREZZO_PENDENTE` resta il codice del guard **per riga** dei
>   componenti ([`trgfn_ddt_righe_componenti_guard_pending`](/dbzero/vendite/funzioni/trgfn_ddt_righe_componenti_guard_pending)).
>
> La **politica** resta qui: la domanda si fa solo se la causale vende. Il motivo
> «componente senza prezzo» (`E_DOC_COMPONENTI_PENDING_VALORIZZAZIONE`) non cambia.
> Il guard che solleva i due codici nuovi è
> [`trgfn_ddt_guard_transizione_approvazione`](/dbzero/vendite/funzioni/trgfn_ddt_guard_transizione_approvazione),
> aggiornato nello stesso giro (changeSet `20260924-31` e `-32`).

### Gli oneri della bolla (rev 2026-11-03)

Dal `20261103-41` (brief-db-addebito-trasporto-ordine §8.3, K-2/K-7/K-8) due motivi in più; riga-onere
= `script.fn_natura_e_merce(natura_vendita_id)` falso sulla natura congelata.

| Punto | Codice | reason / reason_key | dettaglio |
| --- | --- | --- | --- |
| 1-bis | `E_DDT_EMISSIONE_SOLO_ONERI` — righe attive, nessuna di merce | `DOCUMENTO_SOLO_ONERI` / `vendite.ddt.azione_reason.solo_oneri` | — |
| 3-ter | `E_DDT_ONERE_NON_FATTURABILE` — la prima riga-onere che non verrebbe mai fatturata | `ONERE_NON_FATTURABILE` / `vendite.ddt.azione_reason.onere_non_fatturabile` | `{riga_id, riga_nr}` |
| 3-quater | `E_DDT_TRASPORTO_NON_DOVUTO` — un onere di causale `TRASPORTO` su una bolla in porto `ASSEGNATO` o con addebito a `TERZI` (`20261103-47`, T-3 bis): il cliente non ci deve il trasporto. `FRANCO` o modalità assente: nessun motivo | `TRASPORTO_NON_DOVUTO` / `vendite.ddt.azione_reason.trasporto_non_dovuto` | `{riga_id, riga_nr, modalita, modalita_descrizione}` |

Il 3-ter scatta in due casi: (a) qualunque onere, anche copiato dall'ordine, su una bolla con causale
**non fatturabile** (la colonna `fatturabile` del punto 3); (b) un onere **senza legame** su una bolla il
cui ordine sorgente di testata fattura **alla conferma** (il trigger di testata dal building block
`vendite.fn_ddt_trigger_ordine_testata`, `20261103-45`, lo stesso della diagnosi del push). La copia dall'ordine ha il legame ed è lecita
(la fattura l'ordine); un onere a mano su una bolla senza ordine, o di un ordine alla consegna, è
ammesso se la causale è fatturabile (K-9). All'emissione e non all'inserimento: nella copia la riga
nasce prima del suo legame. Li solleva `vendite.trgfn_ddt_guard_causale_emissione`; la capability legge
il primo motivo.

### Regole

- **Pura** (convenzione `fn_check_*`): nessun raise, nessuna scrittura, STABLE.
  Chi solleva sono i guard, ognuno per i codici di propria competenza.
- **Il parametro è una riga `vendite.ddt`, non un id** — scelta deliberata:
  i guard sono `BEFORE UPDATE` e devono valutare i valori **candidati** (`NEW`).
  Con un id la funzione rileggerebbe da tabella i valori ancora vecchi, e un
  UPDATE che imposta insieme stato e causale verrebbe bloccato a torto.
  Le condizioni sulle righe figlie leggono comunque da tabella (un UPDATE di
  testata non le sta cambiando).
- La capability mostra come `reason`/`reason_key` il **primo** motivo
  dell'array, ed espone l'array completo nel campo `reasons` dell'azione.
- ⚠️ `vw_ddt_righe_iva_base` NON è riusabile per la condizione 3: filtra
  `prezzo_unitario IS NOT NULL`, perdendo proprio le righe da esaminare.
  ⭐ Per la **3-bis** vale l'opposto, ed è coerente: lì la vista è il
  **consumatore da proteggere**, quindi il controllo ne copia il perimetro
  (`prezzo_unitario IS NOT NULL`) invece di ignorarlo.
- ⚠️ **L'ordine dell'array è il contratto**: la capability mostra il **primo**
  motivo. La 3-bis sta fra il prezzo e gli indirizzi — struttura, intento,
  valore della riga, testata, componenti. Un ordine non scritto è un ordine che
  il prossimo cambia senza accorgersene.
- ⛔ **Aggiungere un motivo qui non basta**: va aggiunto anche il ramo nel guard
  che lo solleva (per la 3-bis è
  [`trgfn_ddt_guard_causale_emissione`](/dbzero/vendite/funzioni/trgfn_ddt_guard_causale_emissione)),
  il codice nel catalogo `config.codici_errore` + `messaggi_errore`, **e la
  `reason_key` nei locales del frontend** — che è la sede che si dimentica, e
  che `scripts/check_i18n_keys.py` fa fallire in CI.

### Dipendenze DB

`vendite.ddt_righe`, `config.causali_trasporto` (`fatturabile`),
`vendite.ordini_righe_fulfillment` + `vendite.ordini_righe` (eredità prezzo),
`vendite.ddt_indirizzi` + `script.fn_indirizzi_obbligatori_mancanti`,
`vendite.ddt_righe_componenti`.

### Test

`db/pgtap/vendite/test-fn-genera-ddt-riconsegna-eredita-v1.sql` (asserzioni
13, 14, 15, 16) copre la condizione **3-bis** in tutte e quattro le
combinazioni. ⭐ La **16** è quella che vale: *causale **non** fatturabile, riga
**con** prezzo senza aliquota → rifiuta lo stesso.* È l'unica asserzione che si
accorgerebbe se qualcuno spostasse la 3-bis dentro il ramo `fatturabile`.
