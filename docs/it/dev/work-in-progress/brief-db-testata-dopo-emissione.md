# Brief DB — Il documento dopo la bozza: che cosa si cambia ancora

> **Chi scrive:** team DB (`dev/db-tid`), 2026-10-10. **A chi:** Tid; poi BE (§7).
> **Origine:** §8 di [brief-db-esecutivi-ba-coppia](brief-db-esecutivi-ba-coppia.md) e il suo §10.3
> («quali colonne di testata si riscrivono in fase chiusa»), ripreso dal §7 di
> [brief-db-guard-emittente-ba-unico](../work-done/brief-db-guard-emittente-ba-unico.md).
> **Assorbe (2026-10-10):** brief-db-ordine-data-consegna-confermata-capability (scritto dalla
> sessione backend il 2026-10-09, archiviato in `work-done/` con un rimando qui). Era la stessa domanda
> («fuori bozza, quali colonne si cambiano e in quale stato?») su una colonna di riga, e i due brief
> fissavano la stessa forma per stato: ora è la **fase 1** di questo (§5-bis).
> **Stato:** 📝 **aperto, decisioni tutte chiuse da Tid il 2026-10-10 (§5-bis.4, §6), nessun codice.**
> ⛔ **Si comincia dalla fase 1** (§5-bis): il lettore del montaggio e la capability della data di
> consegna confermata. È consegnabile da sola, e **il BE la aspetta** per il suo verbo: non attende
> il resto del giro. Poi la fase 2: le colonne decise nel montaggio del BB fuori bozza di ogni
> documento, un codice per famiglia, la forma per stato (§5); infine il BE toglie i suoi «solo in
> DRAFT» (§7).
> **Nel registro dei difetti DB:** voce **D23** di `migliorie-generali-da-test-valutazione.md`, che
> rimanda qui.

## 1. La domanda

Un documento emesso è un foglio stampato, consegnato, numerato sul registro di un'azienda. Alcuni suoi
dati, dopo, non devono più cambiare: cambiarli vorrebbe dire che il foglio dice una cosa e il database
un'altra. Altri invece **arrivano dopo** (il codice di tracciamento del corriere) o sono note interne.

La domanda è, documento per documento e colonna per colonna: **dopo la bozza, che cosa si cambia
ancora?**

## 2. ⭐ Che cosa succede oggi: la regola c'è, ma sta nel backend

| Documento | Backend (service) | Database |
| --- | --- | --- |
| ordine | testata modificabile **solo in DRAFT** (`ordini_service._STATI_MODIFICABILI`) | bloccati: cliente (sempre), numero, emittente fuori bozza, fatturazione immediata, canale d'origine |
| DDT | **solo in DRAFT** (`ddt_service._STATI_MODIFICABILI`) | cliente, causale, magazzini, emittente fuori bozza; numero, fatturazione immediata |
| reso | **solo in DRAFT** (`resi_service._STATI_MODIFICABILI`) | magazzino ed emittente fuori bozza; numero |
| preventivo | **solo in DRAFT** (`preventivi_service._STATI_MODIFICABILI`) | numero; emittente fuori bozza; fatturazione immediata |
| offerta | **solo in BOZZA** (`offerte_service._STATI_EDITABILI`) | codice, catena delle revisioni; emittente fuori bozza |
| contratto | **una tabella per stato** (`_CONTRATTO_PATCH_ALLOWED_BY_STATE`): DRAFT tutto; ATTIVO solo `valido_al`, `meta`, CIG/CUP/codice commessa; CESSATO e ANNULLATO niente | numero; emittente fuori bozza; listino e variazioni bloccati in ATTIVO (`trgfn_contratti_lock_post_attivazione`); fatturazione immediata |
| commessa | nessun controllo di stato trovato in `aggiorna_commessa_testata` | termine e modalità di pagamento bloccati quando ha attività collegate |

Due conseguenze, sul modello:

* **La regola completa vive solo nel backend.** Il database ne dice dei pezzi. Chi scrive senza
  passare dai service — un verbo DB, un job, una scrittura diretta — cambia la valuta di un ordine
  confermato o la data di una bolla emessa, e nessuno lo ferma. È la stessa asimmetria che il progetto
  chiude altrove: *la logica sta nel DB, il backend non la ripete*.
* **La decisione D-1 sulla bolla allarga cosa si può fare**: oggi, dall'applicazione, a bolla emessa
  non si cambia niente, nemmeno il codice di tracciamento. Con D-1 le famiglie 2, 3 e 4 diventano
  modificabili: per vederlo a video, anche il backend deve cambiare (§7, e D-0).

## 3. Le famiglie di colonne

Le colonne di testata si raggruppano per **che cosa sono**, e la regola si decide per famiglia:

| # | Famiglia | Che cosa contiene | Proposta generale |
| --- | --- | --- | --- |
| **1** | **Identità** | numero, anno, serie, registro, data, valuta, tasso di cambio | **bloccata** fuori bozza: è con questi dati che il documento è registrato |
| **2** | **Stampato** | quello che il foglio porta e chi lo riceve firma: colli, pesi, vettore, porto… | da decidere per documento |
| **3** | **Arriva dopo** | tracciamento, targa, autista, date di partenza e consegna, scadenze | **modificabile**: si sa solo dopo |
| **4** | **Note interne** | `meta` | **modificabile** |
| **5** | **Condizioni commerciali** | pagamento, listino, variazioni di prezzo, validità, agente, condizioni di fatturazione | da decidere per documento: decidono **quanto** e **quando** si fattura |
| **6** | **Già bloccate** | cliente, azienda che emette, causale, magazzini, catene di revisione, sorgente | nessuna decisione: le dicono già il giro di ba-coppia e quello dell'emittente |
| **7** | **Scritte dal DB** | totali, istantanee (`*_snapshot`), date dei cambi di stato | nessuna decisione: non le scrive una persona |

## 4. Documento per documento

Nelle tabelle: **«oggi DB»** è il blocco esistente dopo la bozza; ✅ = bloccata, — = nessun blocco.

### 4.1 DDT — ✅ deciso (D-1)

| Famiglia | Colonne | Oggi DB | Decisione |
| --- | --- | --- | --- |
| 1 Identità | `data`, `valuta_id`, `anno`, `serie`, `registro_id` | — | **bloccate** (Tid) |
| 1 Identità | `numero` | ✅ (`trgfn_v_ddt_protect_num`) | resta |
| 2 Stampato | `mittente_soggetto_ruolo_id`, `vettore_soggetto_ruolo_id`, `aspetto_bene_id`, `modalita_addebito_trasporto_id`, `num_colli`, `peso_lordo`, `peso_netto`, `volume` | — | **modificabili** (Tid) |
| 3 Arriva dopo | `targa`, `autista`, `data_ora_partenza`, `data_ora_consegna_prev`, `tracking_code` | — | **modificabili** (Tid) |
| 4 Note | `meta` | — | **modificabile** (Tid) |
| 6 Già bloccate | `billing_account_id`, `utility_id`, `destinatario_soggetto_ruolo_id`, `causale_trasporto_id`, `magazzino_id`, `magazzino_arrivo_id`, `emittente_fiscale_id`, `fatturazione_immediata` | ✅ | — |
| 6 Sorgente | `sorgente_tipo_id`, `sorgente_uid` | — | ⚠️ da decidere: **D-5** |

⚠️ Anno, serie, numero e registro li scrive la numerazione **all'emissione**, cioè nell'UPDATE che
esce dalla bozza: il blocco guarda lo stato **di prima** (BB `trgfn_doc_testata_lock_fuori_bozza`),
quindi non lo intralcia.

### 4.2 Reso

| Famiglia | Colonne | Oggi DB | Proposta |
| --- | --- | --- | --- |
| 1 Identità | `data`, `valuta_id`, `anno`, `registro_id` | — | bloccate, come la bolla |
| 1 Identità | `numero` | ✅ | resta |
| 4 Note | `meta` | — | modificabile |
| 6 Già bloccate | `magazzino_id`, `emittente_fiscale_id`; cliente (dal DDT, `trgfn_resi_guard_cliente_ddt`) | ✅ | — |
| 6 Sorgente | `sorgente_tipo_id`, `sorgente_uid` | — | D-5 |

Il reso non ha colonne delle famiglie 2 e 3.

### 4.3 Ordine

| Famiglia | Colonne | Oggi DB | Proposta |
| --- | --- | --- | --- |
| 1 Identità | `data`, `valuta_id`, `tasso_cambio`, `anno`, `serie`, `registro_id` | — | bloccate |
| 1 Identità | `numero` | ✅ | resta |
| 5 Commerciali | `modalita_pagamento_id`, `termine_pagamento_id`, `agente_soggetto_ruolo_id`, `fatturazione_trigger` | — | **D-3** |
| 4 Note | `meta` | — | modificabile |
| 6 Già bloccate | cliente (`billing_account_id`, `soggetto_ruolo_id`: sempre), `utility_id` (FK col BA), `emittente_fiscale_id`, `fatturazione_immediata`, `canale_origine` | ✅ | — |
| 6 Sorgente | `sorgente_tipo_id`, `sorgente_uid`, `documento_origine_tipo`, `documento_origine_id` | — | D-5 |
| 7 Dal DB | `imponibile_tot`, `sconto_tot`, `iva_tot`, `totale_doc` | — | — |

La data di consegna confermata sta sulle **righe**, e ha già la sua regola per stato (BB delle righe,
argomenti `[4]` e `[5]`).

### 4.4 Preventivo

| Famiglia | Colonne | Oggi DB | Proposta |
| --- | --- | --- | --- |
| 1 Identità | `data`, `valuta_id`, `rev` | — | bloccate |
| 1 Identità | `numero` | ✅ | resta |
| 5 Commerciali | `termine_pagamento_id`, `validita_dal`, `validita_al`, `competenza_mese` | — | D-3 |
| 4 Note | `meta` | — | modificabile |
| 6 Già bloccate | `emittente_fiscale_id`, `fatturazione_immediata` | ✅ | — |
| 6 Cliente | `billing_account_id`, `istanza_utility_id`, `utility_id` | — (in bozza si sceglie) | **bloccato fuori bozza**: è il cliente del documento, come sulla bolla |
| 7 Dal DB | `totale_imponibile`, `totale_iva`, `totale_documento` | — | — |

### 4.5 Offerta

| Famiglia | Colonne | Oggi DB | Proposta |
| --- | --- | --- | --- |
| 1 Identità | `valuta_id` | — | bloccata |
| 1 Identità | `codice`, `revisione_padre_id`, `revisione_radice_id` | ✅ | resta |
| 5 Commerciali | `listino_id`, `listino_versione_id`, `tipo_variazione_globale`, `valore_variazione_globale`, `validita_dal`, `validita_al` | — | D-3 |
| 4 Note | `meta`, `motivazione_rifiuto` | — | modificabili |
| 6 Già bloccate | `emittente_fiscale_id` | ✅ | — |
| 6 Cliente | `billing_account_id`, `istanza_utility_id`, `utility_id` | — | bloccato fuori bozza |
| 7 Dal DB | `data_emissione`, `data_accettazione`, `data_rifiuto`, `data_annullamento`, `revisione_numero` | — | — (le scrivono i cambi di stato) |

### 4.6 Contratto

Il contratto ha già la regola **per stato** nel backend: è il modello per gli altri.

| Famiglia | Colonne | Oggi DB | Backend in ATTIVO | Proposta |
| --- | --- | --- | --- | --- |
| 1 Identità | `data`, `valuta_id` | — | no | bloccate |
| 1 Identità | `numero` | ✅ | no | resta |
| 3 Arriva dopo | `valido_al` | — | **sì** | modificabile (la chiusura del contratto) |
| 2 Stampato (PA) | `codice_cig`, `codice_cup`, `codice_commessa` | — | **sì** | modificabili |
| 5 Commerciali | `listino_id`, `listino_versione_id`, `tipo_variazione_globale`, `valore_variazione_globale` | ✅ in ATTIVO | no | restano |
| 5 Commerciali | `ambito`, `valido_dal`, `validita`, `parent_contratto_id` | — | no | D-3 |
| 4 Note | `meta` | — | **sì** | modificabile |
| 6 Già bloccate | `emittente_fiscale_id`, `fatturazione_immediata` | ✅ | no | — |
| 6 Cliente | `billing_account_id`, `istanza_utility_id`, `utility_id` | — | no | bloccato fuori bozza |
| 6 Sorgente | `offerta_id`, `sorgente_tipo_id`, `sorgente_uid` | — | no | D-5 |
| 7 Dal DB | `*_snapshot` | — | no | — |

### 4.7 Commessa

La commessa **non si emette**: è il contenitore del lavoro da fatturare, nasce dal push e non ha una
bozza. La sua fase che conta è «ha attività collegate», e lì il DB blocca già termine e modalità di
pagamento (`trgfn_commesse_guard_chiave_immutabile`). Proposta: **fuori da questo brief** (D-4).

## 5. Che cosa costa

Il pezzo tecnico c'è già: il BB `vendite.trgfn_doc_testata_lock_fuori_bozza` blocca fuori bozza le
colonne che gli si passano, ognuna col suo codice. Bloccare una famiglia vuol dire **aggiungere colonne
al montaggio** del documento (un changeSet per documento), un codice per famiglia (per esempio
`E_DOC_IDENTITA_FUORI_BOZZA`), e i pgTAP. Per il contratto, che ha regole diverse in ATTIVO e in
CESSATO, serve la forma per stato del BB delle righe (argomenti «colonne» + «stati»), portata sulla
testata.

🔗 **Il lettore del montaggio:** se il form deve spegnere i campi prima dell'errore (§7), serve
una capability che legga **dal montaggio** quali colonne restano modificabili in quale stato. È il
lettore che nasce nella fase 1 (§5-bis), **generico** sui due BB (righe e testata): qui si riusa
(regola del 2). La forma degli argomenti per stato portata sulla testata è quella che quel lettore
sa leggere, e si fissa una volta sola, nella fase 1.

🔎 **Una terza copia, da ritirare in questo giro (trovata il 2026-10-10):** le capability di
ordine, DDT, contratto e offerta portano già una lista dei campi bloccati scritta a mano
(`non_editable_fields`: `c_non_edit_tutti`, `c_non_edit_attivo`…), accanto al trigger e al backend.
Il lettore della fase 1 è la sede che la sostituisce.

🔗 **Ereditati da [brief-db-offerta-emissione-ed-erogazione](brief-db-offerta-emissione-ed-erogazione.md)
(2026-10-10), da fare in questo giro:**

* **Il posto del lock del contratto** (terzo trovato del §F.4.3 di quel brief). Su un contratto
  ATTIVO un cambio di listino incoerente risponde «listino di un'altra utility/azienda»
  (`a10_guard_listino…`) prima di «campi bloccati» (`a10_lock_post_attivazione`): l'operatore
  corregge il listino e poi trova il lock. Rimontando il lock del contratto nella forma per stato, lo
  si mette **prima** del guard del listino (`_a05_`, linee-guida-trigger), così «bloccato» arriva
  per primo.
* **Il congelamento del listino all'uscita dalla bozza** (pgTAP). D-3 blocca `listino_versione_id`
  fuori bozza, ma è proprio l'UPDATE che esce dalla bozza a scriverla: l'emissione dell'offerta
  (BOZZA → EMESSA) e l'attivazione del contratto (DRAFT → ATTIVO) la congelano. Il BB guarda lo stato
  **di prima** e non la intralcia, come per il numero (§4.1): un caso costruito per documento lo
  prova, e un secondo prova che dopo, fuori bozza, cambiarla è rifiutato.

## 5-bis. Fase 1 — il lettore del montaggio e la data di consegna confermata

> Dal brief assorbito (sessione backend, 2026-10-09). **Origine:** §4.4 di
> [brief-db-righe-e-componenti-debiti-residui](../work-done/brief-db-righe-e-componenti-debiti-residui.md)
> (D-1 di Tid, 2026-10-08) e la voce «La promessa di consegna dopo la conferma» di PROJECT_CONTEXT
> (decisione di Tid del 14-09). **Decisione di forma (Tid, 2026-10-09):** verbo dedicato **sopra una
> capability letta dal DB**. Prima la capability, poi BE e FE. Il BE attende.

### 5-bis.1 Il punto

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

### 5-bis.2 Cosa si chiede

| # | Cosa | Tipo | Bloccante per il BE |
| --- | --- | --- | --- |
| R-1 | Il **lettore del montaggio** e una **check** che dica se `data_consegna_confermata` si può cambiare fuori bozza su un ordine, e perché no. La regola si legge **dalla stessa sede del lock**, non da una copia | `20_code` + pgTAP | sì |
| R-2 | La capability del documento in `script.fn_available_actions_ordine`: terna di famiglia 1 `can_edit_data_consegna_confermata` · `can_edit_data_consegna_confermata_reason` · `can_edit_data_consegna_confermata_reason_key`, prodotta da R-1 | `20_code` + pgTAP | sì |

**R-1 — una sede sola per «in quali stati».** Strada decisa (D-F2): **leggere il montaggio**, cioè
un lettore delle colonne e degli stati ammessi fuori bozza di un adottante, da `pg_trigger.tgargs`.
Capability e lock leggono lo stesso dato: non possono divergere. Il lettore nasce **generico** sui
due BB (righe e testata), non cucito su `vendite.ordini_righe`:

* serve ai prelievi della bolla (`ubicazione_arrivo_id` in `EMESSO`/`SPEDITO`, `20261008-93`), che
  hanno lo stesso problema senza un consumatore;
* serve alla fase 2: la forma per stato portata sulla testata (D-8) è quella che questo lettore sa
  leggere, e si fissa **qui**, una volta per entrambi.

Scartate: (b) spostare la regola in una tabella letta da trigger e check (cambierebbe due montaggi);
⛔ e una check con i due codici di stato scritti accanto a quelli del montaggio.

**R-2 — cosa emette la capability.**

* `true` quando lo stato dell'ordine è fra quelli ammessi da R-1;
* `false` con un motivo negli altri stati. In `DRAFT` la data si scrive dalla riga
  (`can_edit_righe`), quindi il motivo dice quello e non «non si può»; in `EVASO`, `ANNULLATO`
  e negli altri, il motivo dice che lo stato non lo ammette più. I codici dei motivi e le
  chiavi i18n li sceglie il team DB, sotto `vendite.ordini.*`: le chiavi nei `locales` le
  aggiunge il FE (debito dichiarato, come per le altre `reason_key`).

La capability è **di documento**, non di riga: la regola dipende solo dallo stato della
testata, e il lock non guarda nient'altro della riga (nemmeno `attivo`).

### 5-bis.3 Cosa farà il BE/FE, dopo la fase 1

Per sapere cosa serve, non da fare ora. È la parte della fase 1 nel §7.

* **BE:** un verbo `POST /api/v1/vendite/ordini/<ordine_id>/righe/<riga_id>/data-consegna-confermata/`,
  corpo `{"data_consegna_confermata": "AAAA-MM-GG" | null}` (`null` toglie la promessa: la colonna
  è nullable). Scrive la **sola** colonna; **nessun** pre-check di stato in Python: il cancello è il
  lock, il 409 `E_RIGA_DOC_NON_BOZZA` passa com'è. `aggiorna_riga` resta «solo in bozza» per tutte
  le colonne. Il dettaglio porta la terna sotto `capabilities` (forma annidata).
* **FE:** nel drawer dell'ordine fuori bozza, un'azione sulla riga che apre un dialog col
  DatePicker; spenta col motivo quando la capability è `false` (`npm run guard:capability` legge
  la chiave dalla doc auto-generata).

### 5-bis.4 Decisioni della fase 1

| # | Domanda | Decisione |
| --- | --- | --- |
| **D-F1** | La conferma d'ordine già stampata porta la data vecchia: cambiarla dopo genera un documento nuovo? | ✅ **No, la stampa resta quella** (Tid, 2026-10-10): la ristampa riproduce il documento di allora, la data nuova vive a video (righe, situazione merce) |
| **D-F2** | R-1: leggere il montaggio, o spostare la regola in una tabella? | ✅ **Si legge il montaggio** (Tid, 2026-10-10): una funzione legge colonne e stati da `pg_trigger.tgargs`, generica sui due BB; nessuna tabella nuova |

La terza decisione presa nello stesso giro (documenti chiusi: tutto fermo) riguarda la forma per
stato di tutti e due i BB: è **D-8** nel §6.

## 6. Decisioni per Tid

| # | Domanda | Proposta | Decisione di Tid |
| --- | --- | --- | --- |
| **D-0** | Con D-1 le famiglie 2-4 della bolla si cambiano **anche dall'applicazione** a bolla emessa? Oggi `aggiorna_ddt` rifiuta qualunque modifica fuori DRAFT | **Sì**: la regola la dice il DB, colonna per colonna; il backend toglie il suo «solo in DRAFT» sulla testata e lascia decidere il DB (§7) | ✅ **Sì, decide il DB** (Tid, 2026-10-10) |
| **D-1** | Bolla: che cosa si blocca dopo l'emissione? | famiglia 1 bloccata, 2-4 modificabili | ✅ **Tid, 2026-10-10: identità bloccata (data, valuta, anno, serie, registro), le altre no** |
| **D-2** | Reso | come la bolla: identità bloccata, note libere | ✅ **Come la bolla** (Tid, 2026-10-10) |
| **D-3** | Condizioni commerciali (famiglia 5) di ordine, preventivo, offerta, contratto | **bloccate fuori bozza**: decidono quanto e quando si fattura, e il cliente le ha viste sul documento | ✅ **Bloccate** (Tid, 2026-10-10): si cambiano annullando e rifacendo, o con una nuova revisione. Restano modificabili `valido_al` e CIG/CUP/codice commessa del contratto (famiglie 2 e 3) |
| **D-4** | Commessa | fuori da questo brief: non ha bozza né emissione | ✅ **Fuori** (Tid, 2026-10-10) |
| **D-5** | La sorgente (`sorgente_tipo_id`, `sorgente_uid`, i legami d'origine) | **bloccata fuori bozza** su tutti: decide il cliente ereditato (D-6 di ba-coppia) e la catena del documento | ✅ **Bloccata** (Tid, 2026-10-10) |
| **D-6** | Il cliente di preventivo, offerta e contratto | **bloccato fuori bozza**, come sulla bolla | ✅ **Bloccato** (Tid, 2026-10-10) |
| **D-7** | L'identità (famiglia 1) di ordine, preventivo, offerta e contratto | **bloccata fuori bozza**, come sulla bolla | ✅ **Bloccata** (Tid, 2026-10-10) |
| **D-8** | Documento chiuso (annullato, contratto cessato): le colonne che restano aperte dopo l'emissione (famiglie 2-4, `valido_al`, CIG/CUP) si cambiano ancora? | **no, tutto fermo** | ✅ **Tutto fermo** (Tid, 2026-10-10): il BB della testata impara gli stati in cui una colonna resta aperta fuori bozza, come quello delle righe (`[4]`/`[5]`); la forma si fissa nella fase 1 (§5-bis, R-1) |

## 7. Ricaduta BE (dopo la consegna DB)

**Dopo la fase 1:** il verbo della data di consegna confermata e il dialog FE (§5-bis.3).

**Dopo la fase 2:**

* **I «solo in DRAFT» della testata** di ordine, DDT, reso, preventivo e offerta, e la tabella per
  stato del contratto: con la regola nel DB sono una seconda copia. Si ritirano, e il backend mostra
  l'errore del DB (o legge la capability, se il form deve spegnere i campi prima).
* **Le whitelist `UPDATE_KEYS_*`** restano: dicono quali colonne il form espone, non quando.
* Con D-0, la bolla emessa mostra a video i campi delle famiglie 2-4 modificabili.

## 8. Fuori da questo brief

* **Le regole delle righe**: le righe hanno già la loro (BB `vendite.trgfn_doc_righe_lock_fuori_bozza`,
  con le eccezioni per stato) e qui non si ridecide. Ci entrano solo dalla fase 1: il lettore del
  montaggio le legge, e la capability della data di consegna confermata è una colonna di riga.
* **La commessa** (D-4).
