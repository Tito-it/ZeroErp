# Brief DB — Ordine: la capability della data di consegna confermata dopo la conferma

> **Chi scrive:** sessione backend (`dev/backend-tid`), 2026-10-09. **A chi:** team
> DB (`dev/db-tid`), tramite Tid.
> **Origine:** §4.4 di
> [brief-db-righe-e-componenti-debiti-residui](../work-done/brief-db-righe-e-componenti-debiti-residui.md)
> (D-1 di Tid, 2026-10-08), e la voce «La promessa di consegna dopo la conferma» di
> PROJECT_CONTEXT (decisione di Tid del 14-09).
> **Decisione di forma (Tid, 2026-10-09):** verbo dedicato **sopra una capability
> letta dal DB**. Prima la capability (questo brief), poi BE e FE. Il BE attende.
> **Stato:** 📝 da fare (DB).
> ⛔ **Da qui si parte.** R-1 viene **prima** di
> [brief-db-testata-dopo-emissione](brief-db-testata-dopo-emissione.md), che lo attende: il lettore
> del montaggio nasce generico sui due BB (righe e testata) e la forma per stato degli argomenti si
> fissa qui, una volta per entrambi (nota in fondo a R-1).

## 1. Il punto

Dal `20261008-90` il lock delle righe d'ordine (`vendite.trgfn_doc_righe_lock_fuori_bozza`)
lascia aperta fuori bozza una sola porta: un UPDATE della sola `data_consegna_confermata`
quando l'ordine è in `CONFERMATO` o `PARZIALMENTE_EVASO` (argomenti `[4]` e `[5]` del
montaggio). Il backend deve costruirci sopra il verbo che cambia la data dopo la conferma.

Per proporre il verbo, il client deve sapere **quando** è ammesso. Oggi nessuna superficie lo
dice:

* `script.fn_available_actions_ordine` emette `can_edit_righe = (stato = 'DRAFT')`, che risponde
  a un'altra domanda;
* i due stati ammessi stanno **solo** negli argomenti del trigger.

Se il backend li ricopiasse in Python (`{"CONFERMATO", "PARZIALMENTE_EVASO"}`) ci sarebbero due
sedi della stessa regola, e al primo stato nuovo nella matrice risponderebbero in modo diverso
(api.md §«Capability di riga»: *il backend trasporta, non deduce*). Il §4.1 del brief d'origine
ha già scartato il flag di stato (`fase = IN_CORSO` comprende anche `SPEDITO` e `CONSEGNATO`).

## 2. Cosa si chiede

| # | Cosa | Tipo | Bloccante per il BE |
| --- | --- | --- | --- |
| R-1 | Una **check** che dica se `data_consegna_confermata` si può cambiare fuori bozza su un ordine, e perché no. La regola si legge **dalla stessa sede del lock**, non da una copia | `20_code` + pgTAP | sì |
| R-2 | La capability del documento in `script.fn_available_actions_ordine`: terna di famiglia 1 `can_edit_data_consegna_confermata` · `can_edit_data_consegna_confermata_reason` · `can_edit_data_consegna_confermata_reason_key`, prodotta da R-1 | `20_code` + pgTAP | sì |

### R-1 — una sede sola per «in quali stati»

La forma la decide il team DB. Le due strade che vediamo:

* **(a) leggere il montaggio.** Un lettore delle colonne e degli stati ammessi fuori bozza di
  un adottante del building block (da `pg_trigger.tgargs` del trigger montato su
  `vendite.ordini_righe`). Capability e lock leggono lo stesso dato: non possono divergere.
  Il lettore serve anche ai prelievi della bolla (`ubicazione_arrivo_id` in `EMESSO`/`SPEDITO`,
  `20261008-93`), che oggi hanno lo stesso problema senza un consumatore;
* **(b) spostare la regola in un dato** (per esempio una tabella di colonne ammesse per stato) e
  far leggere quel dato **sia** al trigger **sia** alla check. Cambia il montaggio del `-89`.

⛔ Non la terza strada: una check con i due codici scritti accanto a quelli del montaggio.

🔗 **Secondo consumatore (nota DB, 2026-10-10):**
[brief-db-testata-dopo-emissione](brief-db-testata-dopo-emissione.md) porta la regola fuori bozza
sulla **testata** (BB `vendite.trgfn_doc_testata_lock_fuori_bozza`), con la forma per stato
(«colonne» + «stati») presa da quella delle righe (§5 di quel brief). Il suo form dovrà sapere
quali campi restano modificabili (§7 di quel brief): è la stessa domanda di R-1. Con la strada (a), quindi, il
lettore nasce **generico** sui due BB (righe e testata), non cucito su `vendite.ordini_righe`, e
la forma degli argomenti per stato si fissa una volta per entrambi. È un motivo in più per la (a):
la (b) cambierebbe due montaggi. Ordine suggerito: R-1 prima, poi il giro della testata lo riusa.

### R-2 — cosa emette la capability

* `true` quando lo stato dell'ordine è fra quelli ammessi da R-1;
* `false` con un motivo negli altri stati. In `DRAFT` la data si scrive dalla riga
  (`can_edit_righe`), quindi il motivo dice quello e non «non si può»; in `EVASO`, `ANNULLATO`
  e negli altri, il motivo dice che lo stato non lo ammette più. I codici dei motivi e le
  chiavi i18n li sceglie il team DB, sotto `vendite.ordini.*`: le chiavi nei `locales` le
  aggiunge il FE (debito dichiarato, come per le altre `reason_key`).

La capability è **di documento**, non di riga: la regola dipende solo dallo stato della
testata, e il lock non guarda nient'altro della riga (nemmeno `attivo`).

## 3. Cosa farà il BE/FE, dopo

Per sapere cosa serve, non da fare ora.

* **BE:** un verbo `POST /api/v1/vendite/ordini/<ordine_id>/righe/<riga_id>/data-consegna-confermata/`,
  corpo `{"data_consegna_confermata": "AAAA-MM-GG" | null}` (`null` toglie la promessa: la colonna
  è nullable). Scrive la **sola** colonna; **nessun** pre-check di stato in Python: il cancello è il
  lock, il 409 `E_RIGA_DOC_NON_BOZZA` passa com'è. `aggiorna_riga` resta «solo in bozza» per tutte
  le colonne. Il dettaglio porta la terna sotto `capabilities` (forma annidata).
* **FE:** nel drawer dell'ordine fuori bozza, un'azione sulla riga che apre un dialog col
  DatePicker; spenta col motivo quando la capability è `false` (`npm run guard:capability` legge
  la chiave dalla doc auto-generata).

## 4. Domande aperte per Tid (non bloccano il DB)

* **D-1.** La conferma d'ordine già stampata porta la data vecchia. Cambiarla dopo genera un
  documento nuovo, oppure la stampa resta quella e la data nuova vive solo a video (situazione
  merce, lista righe)? Oggi la ristampa fedele riproduce il documento di allora.
