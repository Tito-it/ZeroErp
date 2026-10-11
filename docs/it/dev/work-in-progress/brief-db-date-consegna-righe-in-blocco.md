# Brief DB — Le date di consegna delle righe, aggiornate in blocco

> **Chi scrive:** sessione DB (`dev/db-tid`), 2026-10-11, su decisione di Tid. **A chi:** team DB
> (§4), poi BE/FE (§5).
> **Stato:** 📝 **aperto.** Decisioni D-1 … D-7 prese da Tid il 2026-10-11 (§3); resta un punto
> aperto, P-1 (§6).
> **Storia:** la prima versione (sessione BE, stesso giorno, col nome
> `brief-db-data-consegna-proposta-in-testata`) proponeva due date sulla testata come **seme**
> delle righe. Tid l'ha **superata** (D-1): con la data in testata, cambiare la data di un ordine
> già scritto obbligava di nuovo a correggere le righe una per una, perché una riga che aveva preso
> il seme non si distingueva più da una scritta a mano. Al suo posto c'è una utility che scrive
> una data su più righe.
> **Non è un doppione di:**
> * [brief-db-modifiche-certe-ciclo-vendita-e-articolo](../work-done/brief-db-modifiche-certe-ciclo-vendita-e-articolo.md)
>   P-6: lì si è scartata una data di testata come riassunto delle righe. Qui di date in testata
>   non ce ne sono: P-6 resta com'è;
> * [brief-db-testata-dopo-emissione](../work-done/brief-db-testata-dopo-emissione.md): è la sede
>   della regola «fuori bozza, che cosa si cambia e in quale stato», anche per le righe (eccezione
>   `[4]`/`[5]` del lock). Qui non si riscrive: l'utility la **attraversa**, e si aggiunge una
>   regola di **riga** che quella regola di stato non sa dire (D-7).

## 1. La domanda

Su un documento di vendita la data di consegna sta solo sulle righe. Un ordine che si consegna
tutto insieme obbliga a scrivere la stessa data riga per riga, e a riscriverla riga per riga
quando il cliente la sposta. Tid chiede un gesto che scriva **una** data su più righe.

## 2. Il modello

* **La riga decide, sempre.** Non esiste una data di documento: nessuna colonna nuova in testata,
  nessuna lettura `COALESCE(riga, testata)`.
* **L'utility è una scrittura di massa sulle righe**, niente di più: l'operatore sceglie la
  colonna, la data e la modalità — **tutte le righe** o **solo quelle senza data**.
* **Il DB resta il giudice, riga per riga.** L'utility non porta regole sue: si accende dove la
  colonna si può scrivere (D-3) e scrive passando per i lock delle righe. Se una riga non si può
  toccare, la decisione è del DB, e il BE la legge da lì (§4.1), non la ricopia.

## 3. Decisioni di Tid (2026-10-11)

| # | Domanda | Decisione |
| --- | --- | --- |
| **D-1** | Data in testata come seme delle righe? | **No.** Superata la prima versione del brief: nessuna colonna nuova in testata |
| **D-2** | Che cosa fa l'utility? | Chiede una data e la scrive sulle righe del documento, in una delle due modalità: **tutte** / **solo non valorizzate** |
| **D-3** | Quando si accende? | Dove la colonna, oggi, si può scrivere: le regole di attivazione sono quelle di modificabilità della data di riga |
| **D-4** | Quali documenti? | **Ogni documento di vendita, per ogni colonna di data di consegna che la sua riga porta.** L'utility è parametrica per colonna: l'ordine le ha tutte e due, il preventivo la sola data richiesta |
| **D-5** | Acquisti? | **Fuori, per ora.** Senza lock e senza capability, non c'è ancora una regola da attraversare |
| **D-6** | Data **richiesta** su righe già evase? | Non si aggiorna. **Vale già**: il lock delle righe la lascia scrivere solo in bozza, e una riga di un documento in bozza non è evasa. Nessun lavoro |
| **D-7** | Data **confermata** su una riga già spedita? | **Non si cambia**: la data di consegna si scrive prima di spedire. Una riga che ha già un DDT confermato la tiene ferma. ⚠️ Oggi **non vale**: il lock decide sullo stato della **testata**, non sulla riga (§4) |

## 4. Lavoro DB — la sola regola nuova è D-7

Per D-6 e per l'attivazione (D-3) il DB ha già tutto: il lock delle righe
(`vendite.trgfn_doc_righe_lock_fuori_bozza`, eccezione `[4]`/`[5]` per
`data_consegna_confermata` in `CONFERMATO` e `PARZIALMENTE_EVASO`), `can_edit_righe` e
`can_edit_data_consegna_confermata` nelle capability. Manca solo la regola di riga di D-7.

### 4.1 Il predicato: «la data confermata di questa riga si cambia?»

* Una funzione **pura** `fn_check_*` per riga d'ordine (nome di lavoro
  `script.fn_check_ordine_riga_data_consegna_confermata(p_riga_id)`): `[]` se sì, i motivi se no,
  `NULL` se la riga non si vede.
* **Compone, non ricopia**: il motivo di stato viene da
  `script.fn_check_ordine_data_consegna_confermata` (che legge il montaggio del lock); il motivo
  nuovo è **riga già spedita**.
* «Riga già spedita» = esiste un `vendite.ordini_righe_fulfillment` verso una riga di DDT la cui
  testata è **uscita dalla bozza** e non è annullata. ⚠️ Prima di scriverlo si cerca chi lo dice
  già (`fn_situazione_merce_ordine`, `fn_documento_legami`, `fn_ordine_ha_residuo_evasione` e i
  lettori del fulfillment): una seconda definizione di «spedito» diverge dalla prima.
* Ha **tre** consumatori: il guard (§4.2), la capability per riga del verbo esistente, la
  selezione dell'utility (§5). Per questo è nel DB e non nel BE.

### 4.2 Il guard

* `BEFORE UPDATE` su `vendite.ordini_righe`, `WHEN (OLD.data_consegna_confermata IS DISTINCT FROM
  NEW.data_consegna_confermata)`, che rifiuta quando il motivo «riga già spedita» c'è.
* Fascia `_a10_`: dopo il lock di stato (`_a05_`), che deve parlare per primo.
* Codice nuovo, registrato con policy e frase di ripiego (nome di lavoro
  `E_ORDINE_RIGA_DATA_CONSEGNA_SPEDITA`): la frase dice che la riga è già partita con un DDT, e
  la data di consegna non si cambia più.
* Solo `UPDATE`: una riga che nasce non ha ancora un fulfillment.

### 4.3 La capability per riga

Il verbo per la singola riga che già esiste (`cambia_data_consegna_confermata` del BE) oggi si
accende per documento (`can_edit_data_consegna_confermata`). Con D-7 la risposta è anche **di
riga**: il team DB censisce dove le righe d'ordine espongono le capability di riga e ci aggiunge
la terna `can_edit_data_consegna_confermata` (`_reason`, `_reason_key`) letta dal predicato del
§4.1. ⚠️ La `reason_key` è un debito verso il frontend.

### 4.4 Che cosa **non** si fa nel DB

* Nessuna colonna, nessun trigger di seme, nessun verbo di massa: l'utility è un `UPDATE` del BE
  che i lock giudicano riga per riga (§5).
* Nessuna regola nuova per il preventivo: la data richiesta segue il suo lock delle righe.

### 4.5 pgTAP (fixture fabbricati)

* Riga d'ordine con fulfillment verso un DDT **emesso** → cambiare la data confermata è
  rifiutato col codice nuovo, e il predicato dà il motivo.
* Stessa riga con fulfillment verso un DDT **in bozza** → si cambia.
* Fulfillment verso un DDT **annullato** → si cambia (o si dichiara come il lettore esistente
  tratta l'annullato).
* Riga senza fulfillment, ordine `CONFERMATO` → si cambia; ordine in uno stato fuori
  dall'eccezione → rifiuta il lock di stato, **prima** del guard nuovo (ordine dei rifiuti).
* `UPDATE` di massa sull'ordine con il filtro del predicato → aggiorna le sole righe ammesse.

## 5. Ricaduta BE/FE (dopo la consegna DB)

* **Un'utility parametrica per colonna**, «Aggiorna date di consegna», sui documenti di vendita:
  ordine (data richiesta e data confermata), preventivo (data richiesta). L'elenco delle colonne
  per documento è l'unica cosa che l'utility sa del documento.
* **Attivazione** (D-3), dalle capability che il DB già manda:
  * data richiesta → `can_edit_righe` (solo bozza);
  * data confermata → `can_edit_righe` **oppure** `can_edit_data_consegna_confermata` (che è
    `false` in bozza di proposito: lì la data si scrive modificando la riga).
* **Un solo `UPDATE`, in una transazione**, non un ciclo di chiamate:
  `SET <colonna> = :data WHERE <fk_testata> = :id AND attivo`, più `AND <colonna> IS NULL` in
  modalità «solo non valorizzate», più — per la data confermata — il filtro del predicato del
  §4.1 (`= '[]'`). Le righe già spedite si **saltano**, non fanno fallire il gesto.
* **Fuori bozza si scrive solo la colonna confermata**: il lock lascia passare quella sola.
* **Ritorna** quante righe ha aggiornato e quante ha saltato perché già spedite: il FE lo dice.
* **«Tutte» sovrascrive** le date scritte: dialog di conferma col numero di righe.
* Il verbo per la singola riga e l'utility **scrivono dalla stessa funzione del repository**
  (regola del 2); il verbo per riga impara il codice nuovo del §4.2.
* Guide `gestione-ordini` e preventivi: l'utility, le due modalità, l'esempio «tutto il 20, poi
  il cliente sposta al 22».

## 6. Punto aperto per Tid

| # | Domanda | Note |
| --- | --- | --- |
| **P-1** | Una riga spedita **in parte** (o rientrata con un reso da riconsegnare) tiene ferma la data confermata? | D-7 alla lettera dice sì: basta un DDT confermato. Conseguenza: il **residuo** di quella riga non si può ripromettere con un'altra data. L'alternativa è fermarla solo quando la riga è **evasa per intero** (residuo zero, contando i rientri come `fn_ordine_ha_residuo_evasione`); allora però la data della riga torna a dire due cose — quella usata per la parte spedita e quella del residuo. Decide Tid prima che il team DB scriva il predicato |

## 7. Fuori da qui

* Acquisti (D-5): entra col cantiere acquisti, con lo stesso modello; la colonna
  `acquisti.ordini.data_ora_consegna_prev` (dato del trasporto, analisi-simmetria-ordini-acquisto
  ⑪) si guarda lì.
* Una data di testata, proposta o calcolata (D-1; P-6 per quella calcolata, che è già il `min` di
  `vw_ordini_lista`).
