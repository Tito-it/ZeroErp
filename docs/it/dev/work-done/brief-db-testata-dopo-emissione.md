# Brief DB — Il documento dopo la bozza: che cosa si cambia ancora

> **Chi scrive:** team DB (`dev/db-tid`), 2026-10-10. **A chi:** Tid; poi BE (§7).
> **Origine:** §8 di [brief-db-esecutivi-ba-coppia](../work-done/brief-db-esecutivi-ba-coppia.md) e il suo §10.3
> («quali colonne di testata si riscrivono in fase chiusa»), ripreso dal §7 di
> [brief-db-guard-emittente-ba-unico](../work-done/brief-db-guard-emittente-ba-unico.md).
> **Assorbe (2026-10-10):** brief-db-ordine-data-consegna-confermata-capability (scritto dalla
> sessione backend il 2026-10-09, archiviato in `work-done/` con un rimando qui). Era la stessa domanda
> («fuori bozza, quali colonne si cambiano e in quale stato?») su una colonna di riga, e i due brief
> fissavano la stessa forma per stato: ora è la **fase 1** di questo (§5-bis).
> **Stato:** ✅ **chiuso e archiviato il 2026-10-11** (DB, BE/FE e collaudo a video di Tid; `E_CONTRATTO_NON_MODIFICABILE` ritirato dal team DB lo stesso giorno). Decisioni tutte chiuse da Tid il 2026-10-10 (§5-bis.4, §6).
> ✅ **Fase 1, lato DB: applicata il 2026-10-10 su dbdev e zeroerp_ci, pgTAP di Tid senza
> regressioni** (`20261010-60 … -67`, `script/test-doc-lock-montaggio-v1`). Il BE può partire col
> suo verbo (§5-bis.6).
> ✅ **Fase 2, lato DB: applicata il 2026-10-10 su dbdev e zeroerp_ci, pgTAP di Tid verdi**
> (`20261010-68 … -76` e i
> due CSV dei codici): **da leggere per primo il §9.4**. D-9 e D-10 decise da Tid lo stesso giorno.
> ⚠️ Il BE toglie i suoi «solo in DRAFT» **nello stesso rilascio** (§9.5, R-BE-2): da questo apply
> le capability accendono la testata negli stati in cui una colonna resta aperta.
> ✅ **Giro R-DB (2026-10-11): `-21 … -33` e `-40`/`-41` (la nascita, D-13) applicati, pgTAP di Tid verdi.**
> ✅ **Lato DB non resta niente** (§11.8). ✅ **BE/FE del §11.4 fatti e committati il 2026-10-11** (§12). ✅ **Collaudo a video di Tid superato il 2026-10-11** (§12.1). Archiviato in `work-done/` il 2026-10-11.
> `20261011-21 … -33`, CSV dei codici, pgTAP nuovo `test-testata-dopo-emissione-rdb-v1` (34/34 sullo
> scratch) e tre pgTAP adeguati. Decisioni D-11 e D-12 di Tid. Apply e corsa pgTAP di Tid.
> **Resta (prima del giro R-DB):** lato DB il pgTAP del congelamento del listino all'uscita dalla bozza (§9.4, «Non fatto»)
> e le richieste **R-DB-1 … R-DB-4** del §10.1 (trovate dal BE/FE, tenute qui per decisione di Tid);
> poi i ritocchi BE/FE che ne discendono e il collaudo a video. ✅ Lato BE/FE le richieste del
> §5-bis.6 e del §9.5 sono fatte (§10, 2026-10-10, non committate). Poi l'archivio.
> ⚠️ (superato: fasi 1 e 2 fatte) ⛔ **Si comincia dalla fase 1** (§5-bis): il lettore del montaggio e la capability della data di
> consegna confermata. È consegnabile da sola, e **il BE la aspetta** per il suo verbo: non attende
> il resto del giro. Poi la fase 2: le colonne decise nel montaggio del BB fuori bozza di ogni
> documento, un codice per famiglia, la forma per stato (§5); infine il BE toglie i suoi «solo in
> DRAFT» (§7).
> **Nel registro dei difetti DB:** voce **D26** di `migliorie-generali-da-test-valutazione.md`, che
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

### 5-bis.5 ⭐ Fase 1, lato DB: che cosa è stato scritto (2026-10-10)

> ✅ **Applicato il 2026-10-10** (dbdev e zeroerp_ci, `databasechangelog` letto), pgTAP di Tid:
> nessuna regressione.

**L'idea.** D-F2 dice «si legge il montaggio». Leggere lo stesso dato però non basta: se il
trigger capisse gli argomenti a modo suo e il lettore a modo suo, le **grammatiche** sarebbero
due, e così le **regole** («in bozza tutto; fuori, le colonne ammesse negli stati ammessi»). Per
questo grammatica e decisione sono uscite dal trigger in due funzioni, che il trigger stesso
chiama e che il lettore riusa. Lock e capability non possono rispondere in due modi.

| changeSet | Oggetto | Che cosa |
| --- | --- | --- |
| `20261010-60` | `script.fn_doc_lock_regola` (nuova) | **la grammatica**: dagli argomenti (`TG_ARGV` o `tgargs`) alla regola, per i due BB |
| `20261010-61` | `script.fn_doc_lock_colonna_bloccata` (nuova) | **la decisione**: in questo stato, quale di queste colonne il montaggio ferma |
| `20261010-62` | `script.fn_doc_lock_montaggi` (nuova) | **il lettore** (R-1): i lock di una tabella con la loro regola, da `pg_trigger.tgargs` |
| `20261010-63` | `script.fn_doc_colonna_modificabile` (nuova) | la domanda generica di una capability: questa colonna, da sola, in questo stato? |
| `20261010-64` | `vendite.trgfn_doc_righe_lock_fuori_bozza` | il lock delle righe legge e decide con `-60`/`-61` |
| `20261010-65` | `vendite.trgfn_doc_testata_lock_fuori_bozza` | il lock della testata legge e decide con `-60`/`-61` |
| `20261010-66` | `script.fn_check_ordine_data_consegna_confermata` (nuova) | **la check** (R-1) della promessa di consegna |
| `20261010-67` | `script.fn_available_actions_ordine` | **la terna** (R-2) |

**La check (R-1).** `NULL` se l'ordine non si vede; `[]` se il lock lascia cambiare la sola data
(anche in DRAFT, dove si modifica la riga intera); altrimenti un motivo: codice
`E_RIGA_DOC_NON_BOZZA` (quello che il lock solleva, nessun codice nuovo), reason
`STATO_NON_AMMETTE`, i valori della frase del lock. Gli stati li legge dal montaggio: il pgTAP 30
prova che nel codice della check, della capability e dei lettori non c'è scritto nessuno stato.

**La terna (R-2).** `can_edit_data_consegna_confermata` · `_reason` · `_reason_key`:

| Stato | flag | reason | reason_key |
| --- | :---: | --- | --- |
| `DRAFT` | `false` | `ORDINE_IN_BOZZA` | `vendite.ordini.data_consegna_confermata_reason.in_bozza` |
| stati dell'eccezione del lock (oggi `CONFERMATO`, `PARZIALMENTE_EVASO`) | `true` | `null` | `null` |
| gli altri (`ALLOCATO`, `SPEDITO`, `CONSEGNATO`, `EVASO`, `FATTURATO`, `ANNULLATO`) | `false` | `STATO_NON_AMMETTE` | `vendite.ordini.data_consegna_confermata_reason.stato_non_ammette` |

Il motivo della bozza sta nella capability e non nella check: in bozza il lock lascia passare la
data (la riga intera si modifica), quindi «in bozza non è il verbo giusto» è una scelta di
presentazione, non una regola del database.

**Che cosa cambia per i lock: niente, per gli adottanti di oggi.** Stessi codici, stesse frasi,
stesso contesto. L'eccezione delle righe è la stessa, detta per colonna. Due sole differenze:
una lista di sole virgole in `[4]` o `[5]` accanto a una piena ora è un montaggio a metà (nessun
adottante la ha); la frase del montaggio sbagliato della testata dice l'evento («si monta BEFORE
UPDATE») o gli argomenti attesi, separatamente.

**La prova (2026-10-10, su `zeroerp_ci`, SQL estratto dagli YAML in transazione ritirata, come
owner `zeroerp`).**

* `script/test-doc-lock-montaggio-v1` (nuovo, 30 test): **30/30**.
* **Regressione**, 29 pgTAP lanciati senza e con l'SQL estratto, esiti identici file per file:
  i quindici che toccano i due lock (fra cui `test-trgfn-doc-righe-lock-fuori-bozza-v1` 21/21,
  `test-righe-e-componenti-debiti-residui-v1` 24/24, `test-esecutivi-ba-coppia-v1`,
  `test-guard-emittente-ba-unico-v1`), i sei della capability dell'ordine e i presidi trasversali
  (`test-riferimenti-morti-v1`, `test-rubinetto-primo-motivo-v1`,
  `test-catalogo-messaggi-errore-completo`, `test-vw-codici-errore-motivo-nominato`,
  `test-security-definer-search-path-v1`, `test-catalogo-presidi-v1`). I rossi presenti sono gli
  stessi con e senza (fixture e owner sullo scratch), non di questo giro.
* `plpgsql_check` sulle funzioni nuove e sui due trigger: nessun errore. Resta un avviso sulla
  check («STABLE ma chiama una VOLATILE»: è la `PERFORM` dell'errore sul parametro, come nelle
  check sorelle).
* Firme: una funzione per nome, identità e volatilità attese. Guardrail statici (letterali,
  `runOnChange`, preCondition) verdi.
* ⚠️ Come owner la RLS non c'è: l'esito come app arriva dalla corsa di Tid. Il file non è marcato
  `pgtap-runner: owner`: monta i lock di prova su tabelle temporanee, che l'app può fare.

**Presidi da guardare alla corsa di Tid.** `scripts/check_i18n_keys.py` vedrà le due chiavi
nuove (`'reason_key', '…stato_non_ammette'` nella check, `v_dcc_reason_key := '…in_bozza'` nella
capability) appena la doc auto-generata è rigenerata, e sarà rosso finché il FE non le aggiunge
(§5-bis.6).

**Documentazione.** Manuali nuovi in `docs/it/dbzero/script/manual/` per le cinque funzioni (la
pagina concettuale è `fn_doc_lock_montaggi.md`); aggiornati quelli dei due lock e della capability.

### 5-bis.6 Richieste a BE e FE, dopo l'apply della fase 1

| # | A chi | Cosa |
| --- | --- | --- |
| R-BE-1 | BE | il verbo del §5-bis.3, e la terna nel dettaglio sotto `capabilities` (forma annidata). Nessun pre-check di stato in Python: il motivo arriva dalla capability, il rifiuto dal lock (`E_RIGA_DOC_NON_BOZZA`, 409) |
| R-FE-1 | FE | le due chiavi nei `locales` (it, en): `vendite.ordini.data_consegna_confermata_reason.in_bozza` («In bozza la data si cambia modificando la riga.») e `vendite.ordini.data_consegna_confermata_reason.stato_non_ammette` («In questo stato la data di consegna non si cambia più.») |
| R-FE-2 | FE | l'azione sulla riga e il dialog del §5-bis.3, spenta col motivo quando il flag è `false` |

### 5-bis.7 La forma per stato della testata (D-8), fissata qui per la fase 2

D-8 vuole che le colonne che restano aperte dopo l'emissione (famiglie 2-4, `valido_al`,
CIG/CUP) si chiudano quando il documento si chiude. Il lock della testata deve quindi sapere,
colonna per colonna, **in quali stati** resta aperta fuori bozza.

* **L'uscita della grammatica è già quella giusta**: ogni colonna della testata porta
  `stati_ammessi`, e la decisione lo usa (una colonna nominata si ferma se lo stato non è fra i
  suoi). Oggi è sempre vuoto, perché le coppie dicono «bloccata fuori bozza».
* **Gli argomenti — ✅ proposta del team DB accettata da Tid il 2026-10-10**: le coppie *(colonna, codice)* diventano **terne**
  *(colonna, codice, stati)*, con `stati` vuoto = bloccata fuori bozza (le colonne di oggi) e una
  lista = aperta solo in quegli stati (le famiglie 2-4). Le colonne che la testata non nomina
  restano libere: sono quelle che scrive il database (totali, istantanee, date dei cambi di
  stato, lo stato stesso).
* **Che cosa costa nella fase 2**: la grammatica cambia in un punto solo
  (`script.fn_doc_lock_regola`), e trigger e lettore la seguono insieme. I sei montaggi della
  testata si rimontano nello stesso giro: andava fatto comunque, per aggiungere le famiglie 1, 5
  e 6. Con le terne si aggiorna anche la «soluzione» di `E_DOC_RIGHE_LOCK_MONTAGGIO`, che
  descrive gli argomenti.

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

## 9. Fase 2 — la testata: censimento e due domande (2026-10-10)

### 9.1 Chi scrive le testate fuori bozza (letto dal catalogo e dal codice, 2026-10-10)

**Nel database.** Le funzioni che fanno `UPDATE` sulle sei testate scrivono lo **stato** (cambi di
stato, resi, riconsegne, revisioni dell'offerta, push), i **totali** (`fn_ricalcola_totali_ordine`,
`…_preventivo`) e un solo dato di dominio: `valido_al` del contratto in
`vendite.fn_chiudi_contratto_per_successione`. Nessuna di queste colonne è fra quelle da bloccare,
tranne `valido_al`, che resta aperta in `ATTIVO`.

I trigger `BEFORE` che scrivono colonne derivate (`gen_numero`/`gen_codice`, `normalize`,
`freeze_listino_versione`, la data di emissione dell'offerta) stanno **dopo** il lock, che è in
fascia `_a05_`: il lock giudica la **richiesta**, non le derivazioni. E scrivono all'uscita dalla
bozza, quando lo stato vecchio è ancora la bozza.

⛔ **Una colonna generata non si nomina nel lock**: dentro un `BEFORE` `NEW.validita` vale `NULL`
(linee-guida-sql §7b), quindi sembrerebbe cambiata a ogni `UPDATE`. `validita` del contratto, che il
§4.6 elencava nella famiglia 5, **esce dall'elenco**: segue `valido_dal` (bloccata) e `valido_al`.
Stesso discorso per `partecipa_overlap_snapshot`.

**Nel backend.** Le testate si aggiornano solo nei verbi «solo in DRAFT» (§2), con quattro
eccezioni:

| Dove | Cosa scrive | Stato vecchio | Con il lock della fase 2 |
| --- | --- | --- | --- |
| `ordini_service._crea_testata_ordine_da_origine` | `documento_origine_tipo`, `documento_origine_id` | `DRAFT` (l'ordine è appena nato) | passa |
| `offerte_repository.update_stato` | `motivazione_rifiuto`, con lo stato | `EMESSA` (verso `RIFIUTATA`/`ANNULLATA`) | passa se `EMESSA` è fra gli stati aperti della famiglia 4 |
| `contratti_service` (cessazione) | `valido_al`, prima dello stato | `ATTIVO` | passa (`valido_al` aperta in `ATTIVO`) |
| ⚠️ `preventivi_service.cambia_stato` | `competenza_mese`, `fatturazione_immediata` | **`EMESSO`** (verso `ACCETTATO`), e `ACCETTATO` | **rifiutato**, se `competenza_mese` è bloccata fuori bozza come dice D-3 → domanda D-9 |

E una precisazione al §2/§4: `fatturazione_immediata` **non** è bloccata fuori bozza. Il suo guard
(`trgfn_guard_fatturazione_immediata_immutabile`) la blocca quando il documento è **entrato in una
commessa**: è un'altra regola, e resta.

### 9.2 Le due domande

**D-9 — Il preventivo: le condizioni di fatturazione si scelgono all'accettazione.**
`competenza_mese` e `fatturazione_immediata` non si scelgono in bozza: si scelgono **accettando**
(`EMESSO → ACCETTATO`), e si possono ancora cambiare in `ACCETTATO` finché il preventivo non è in
commessa. D-3 le metteva fra le condizioni bloccate fuori bozza, ma bloccarle romperebbe
l'accettazione.
*Proposta*: `competenza_mese` aperta in `EMESSO` e `ACCETTATO`, chiusa negli altri stati (terna
con quegli stati); `fatturazione_immediata` non nominata, la governa il suo guard di commessa.
✅ **Decisa da Tid il 2026-10-10: come la proposta.** Corregge D-3 per il preventivo.

**D-10 — Che cosa vuol dire «documento chiuso» (D-8), documento per documento.**
D-8 chiude le colonne aperte dopo l'emissione quando il documento è chiuso. Il catalogo ha la
`fase` `CHIUSO`, ma non coincide col senso di D-8: il **reso** ha un solo stato vivo dopo la bozza,
`CONFERMATO`, che è già `CHIUSO` (con quella regola le sue note — D-2: «libere» — si fermerebbero
alla conferma); la **bolla** `CONSEGNATO` è `CHIUSO` (tracciamento e data di consegna non si
correggerebbero più dopo la consegna).
*Proposta* (gli stati si scrivono nel montaggio, per `codice_interno`, come per le righe):

| Documento | Colonne aperte fuori bozza | Aperte negli stati | Chiuse in |
| --- | --- | --- | --- |
| DDT | famiglie 2, 3, 4 | `EMESSO`, `SPEDITO`, `CONSEGNATO` | `RESO`, `ANNULLATO` |
| reso | `meta` | `CONFERMATO` | `ANNULLATO` |
| ordine | `meta` | `CONFERMATO`, `PARZIALMENTE_EVASO`, `ALLOCATO`, `SPEDITO`, `CONSEGNATO`, `EVASO` | `FATTURATO`, `ANNULLATO` |
| preventivo | `meta` (e `competenza_mese`, D-9) | `EMESSO`, `ACCETTATO` | `EVASO`, `RIFIUTATO`, `SCADUTO`, `ANNULLATO` |
| offerta | `meta`, `motivazione_rifiuto` | `EMESSA`, `ACCETTATA` | `RIFIUTATA`, `SUPERATA`, `ANNULLATA` |
| contratto | `valido_al`, CIG, CUP, `codice_commessa`, `meta` | `ATTIVO` | `CESSATO`, `ANNULLATO` |

Il criterio: chiuso è il documento **annullato** o **arrivato in fondo** (fatturato, cessato,
superato, rifiutato, scaduto, reso, evaso dal preventivo); una consegna o una conferma del reso
no. ⚠️ L'ordine `EVASO` resta aperto perché può tornare `CONFERMATO` (rientro da reso).
✅ **Decisa da Tid il 2026-10-10: la tabella qui sopra (modo B), senza tabelle nuove.** Gli stati
si scrivono nel montaggio, colonna per colonna (terne del §5-bis.7). Scartato il flag per stato sui
cataloghi `config.stati_doc_*`: sei colonne nuove, e dice «aperto/chiuso» per documento, non per
colonna (D-9 apre `competenza_mese` in stati suoi).

### 9.3 Cosa si scrive dopo le risposte

1. La grammatica della testata a terne (`script.fn_doc_lock_regola`, §5-bis.7) e la frase di
   `E_DOC_RIGHE_LOCK_MONTAGGIO`.
2. I codici per famiglia: `E_DOC_IDENTITA_FUORI_BOZZA` (1), `E_DOC_CONDIZIONI_FUORI_BOZZA` (5),
   `E_DOC_CLIENTE_FUORI_BOZZA` (cliente di preventivo, offerta, contratto), `E_DOC_SORGENTE_FUORI_BOZZA`
   (D-5), `E_DOC_CHIUSO` (le colonne aperte, a documento chiuso: D-8). I codici della bolla e del
   reso che esistono già restano.
3. I sei montaggi rimontati a terne, con le colonne del §4 (meno `validita`); per il contratto il
   lock assorbe `trgfn_contratti_lock_post_attivazione` (quattro colonne di pricing, regola del 2)
   e parla prima del guard del listino (§5, ereditati).
4. La terza copia: `non_editable_fields` delle capability di ordine, DDT, contratto e offerta si
   ricava dal montaggio.
5. pgTAP: per documento, una colonna per famiglia in uno stato aperto e in uno chiuso; il
   congelamento del listino all'uscita dalla bozza (offerta, contratto).

### 9.4 ⭐ Fase 2, lato DB: che cosa è stato scritto (2026-10-10)

> ✅ **Applicato su dbdev il 2026-10-10 alle 17:43** (`databasechangelog` letto: `-68 … -76`; i file erano
> nella forma finale, ultimo ritocco 17:37; sul vivo ci sono la categoria del contratto, i cinque codici e il
> ritiro). ✅ Poi anche su `zeroerp_ci`; pgTAP di Tid verdi (2026-10-10).

| changeSet / file | Che cosa |
| --- | --- |
| `20261010-68` | la grammatica della testata a **terne** (`script.fn_doc_lock_regola`), i commenti del lock, e i **sei montaggi** rimontati con le colonne del §4 e gli stati del §9.2 — in un changeSet solo, perché grammatica nuova e montaggi vecchi non convivono |
| `20261010-69` | ritirati `vendite.trgfn_contratti_lock_post_attivazione` e il suo trigger: le quattro colonne di pricing le ferma il lock di testata, in ogni stato fuori bozza e prima del guard del listino |
| `20261010-70` | `script.fn_doc_testata_in_stato` (nuova): colonne non modificabili e `can_edit_testata` letti dal montaggio |
| `20261010-71 … -76` | le capability di ordine, DDT, contratto, offerta, preventivo e reso leggono la testata da lì: **ritirate le liste a mano** (`c_non_edit_tutti`, `c_non_edit_attivo`, `c_non_edit_extra`) e gli stati scritti di `can_edit_testata`. Restano le liste «sempre» (campi di sistema e lock assoluti, valide anche in bozza) |
| `80_data/sql/config/codici_errore.csv`, `messaggi_errore.csv` | cinque codici nuovi (`E_DOC_IDENTITA_FUORI_BOZZA`, `E_DOC_CONDIZIONI_FUORI_BOZZA`, `E_DOC_CLIENTE_FUORI_BOZZA`, `E_DOC_SORGENTE_FUORI_BOZZA`, `E_DOC_CHIUSO`, CONFLITTO_STATO, id messaggi 1249-1253); `E_CONTRATTO_CAMPI_BLOCCATI_POST_ATTIVAZIONE` ritirato (`obsoleto_dal`); la soluzione di `E_DOC_RIGHE_LOCK_MONTAGGIO` descrive le terne |

**Rispetto al §4 e al §9.2, tre precisazioni prese scrivendo:**

* la **utility dell'ordine** è nominata come cliente (`E_DOC_CLIENTE_FUORI_BOZZA`): il billing
  account ha già il lock assoluto, la utility no, e dopo `brief-db-esecutivi-ba-coppia` non è più
  legata al BA. Il §4.3 la dava per bloccata, ma non lo era;
* `categoria_cliente_id_snapshot` del **contratto** è nominata fra le condizioni: il backend la
  scrive dal form, decide la categoria di prezzo, e la lista a mano della capability la fermava
  fuori bozza;
* `validita` del contratto **non** è nominata (colonna generata, §9.1).

**Censimento dei campi del form** (`TESTATA_UPDATE_COLUMNS` dei sei repository del backend,
2026-10-10): tutti nominati nel montaggio, tranne `fatturazione_immediata`, che ha il suo guard
(scelta del §9.1). Nessun campo resta libero a documento chiuso.

**⚠️ Che cosa cambia nelle capability.** `can_edit_testata` ora vuol dire «in questo stato almeno
un campo della testata si cambia»: vero su un ordine confermato (le note), su una bolla emessa
(trasporto, tracciamento), su un contratto attivo; falso a documento chiuso. Quello che non si
riscrive lo dice `non_editable_fields`, che ora porta identità, condizioni, cliente e sorgente.
Il test 10 di `test-fn-available-actions-ordine-v1` pinnava apposta `can_edit_testata = false` su
un ordine confermato («se diventasse true, è qui che si deve accorgere qualcuno»): adeguato, ora
prova che i campi che contano sono fra i non modificabili. Stessa cosa per il test 5 di quello
dell'offerta e il test 5 di quello del preventivo.

**La prova (2026-10-10, `zeroerp_ci`, SQL estratto in transazione ritirata, come owner).**

* `vendite/test-testata-dopo-emissione-v1` (nuovo, 26 test): **26/26**. Il test 3 è la matrice
  colonna × stato di tutti e sei i documenti, scritta dal brief e confrontata col montaggio; il
  21 prova, colonna per colonna sul preventivo, che capability e lock rispondono uguale.
* `script/test-doc-lock-montaggio-v1` portato alle terne: **30/30**.
* **Regressione** su 144 pgTAP (i due lock, i sei documenti, le capability, i presidi
  trasversali), senza e con il giro: identici, salvo i quattro adeguati qui sopra
  (`test-contratti-step23-v1` test 2 verificava il trigger ritirato; ora verifica le quattro
  colonne nel lock di testata).
* ⚠️ **Un buco della regressione, trovato da Tid dopo l'apply (2026-10-10).** Anche il test 13 di
  `vendite/test-ddt-read-side-v1` pinnava `can_edit_testata = false` su una bolla `EMESSO`, ed è
  diventato rosso alla corsa di Tid. Nella mia regressione risultava «uguale senza e con», ma
  **troncato al test 5 in tutte e due le corse**: sullo scratch la sua fixture cerca i dati nel
  database e si ferma, quindi il 13 non girava mai. Uguale non vuol dire verificato: un file che
  si ferma prima dell'asserzione è cieco, e va contato come non provato. Adeguato come gli altri
  tre (testata modificabile, identità, causale, cliente e numero fra i non modificabili, il
  tracciamento no); il predicato nuovo è vero sulla lettura dal montaggio per `EMESSO` (dbdev,
  come app). Gli altri pgTAP che nominano `can_edit_testata` o `non_editable_fields`, cercati per
  nome: sono quelli già adeguati più `dbops/test-fn-non-editable-fields-conditional`, che parla
  degli articoli.
* ⚠️ **Secondo rosso alla corsa di Tid: `vendite/test-resolve-termini-livello-sorgente-v1`.** Il
  file prendeva attività reali già spinte in commessa e cambiava termine e modalità di pagamento
  sul loro ordine e preventivo, cioè su documenti fuori bozza: dopo D-3 il modello non lo ammette
  da nessun percorso (`E_DOC_CONDIZIONI_FUORI_BOZZA`). **Riscritto in modo costruttivo** (scelta
  di Tid, 2026-10-10): ordine e preventivo nascono in bozza col loro termine, escono dalla bozza
  con le transizioni vere, passano dal push come lo fa il backend (lista da pushare →
  `fn_get_or_create_commessa` con termine e modalità del documento → `fn_link_commessa_sorgente` →
  `fn_upsert_commessa_attivita`) e dal pull (`fn_emit_attivita_fatturabili_da_commessa`). Al
  preventivo un articolo servizio con natura `SERVIZIO_UNA_TANTUM`: la merce andrebbe all'ordine.
  Il test non dipende più dai dati del database; il 7 (sorgente bolla, tipo non gestito) resta
  sui dati e, dove non ce ne sono, è uno `skip` dichiarato. Su zeroerp_ci 9/9 (il 7 in skip).
* **Censimento per nome** dei pgTAP che scrivono una colonna di testata ora bloccata (55 file).
  Su zeroerp_ci nessuno solleva i codici nuovi; 30 si fermano prima della fine per i loro fixture
  sui dati, e lì lo scratch è cieco. Di quelli che scrivono una colonna bloccata **da questa
  fase**, letto il contesto: `fatturazione_trigger` è sempre rimesso su un ordine appena creato in
  bozza; `ddt.data` in `test-documenti-numerazione-trasloco-v1` prima dell'emissione; i dati di
  trasporto in `test-fn-genera-ddt-riconsegna-eredita-v1` sulla bolla appena generata; `meta`
  dell'ordine pushato in `test-fatturazione-immediata-simmetria-sorgenti-v1` (aperta in
  `CONFERMATO`); `codice_cig` in `test-fatture-atti-v1` su un contratto che deve essere `ATTIVO`
  (l'unico che dipende dallo stato del contratto nel test). Da guardare alla corsa intera di Tid.
* I due CSV caricati per intero (upsert di 1034 codici e 1030 messaggi) dopo l'SQL estratto:
  nessun rifiuto.
* `plpgsql_check`: nessun avviso nuovo; firme delle capability invariate (il reso ora ancorato
  a `vendite.resi.id%TYPE`, stessa identità). Guardrail statici verdi.

**Non fatto, dichiarato.** Il congelamento del listino **all'uscita dalla bozza** (offerta e
contratto, ereditato dal §5) non ha un caso costruito: la matrice prova che fuori bozza
`listino_versione_id` è ferma, non che l'emissione la scrive. Serve una fixture di offerta
emessa e di contratto attivato, che i builder pgTAP non hanno; resta da fare in questo brief.

### 9.5 Richieste a BE e FE, dopo l'apply della fase 2

| # | A chi | Cosa |
| --- | --- | --- |
| R-BE-2 | BE | ⚠️ **nello stesso rilascio dell'apply**: togliere i «solo in DRAFT» della testata (`_STATI_MODIFICABILI` di ordini, DDT, resi, preventivi; `_STATI_EDITABILI` delle offerte) e la tabella per stato del contratto (`_CONTRATTO_PATCH_ALLOWED_BY_STATE`). Decide il DB (D-0); il 409 del lock passa com'è. Le whitelist `TESTATA_UPDATE_COLUMNS` restano |
| R-BE-3 | BE | le policy dei cinque codici nuovi (CONFLITTO_STATO → 409; il presidio `test_error_codes_db_policy_guardrail` è rosso finché mancano) e il ritiro di `E_CONTRATTO_CAMPI_BLOCCATI_POST_ATTIVAZIONE` in `contratti_service.py` e nei file di policy e messaggi generati |
| R-BE-4 | BE | i test che pinnano `can_edit_testata = false` fuori bozza o le liste di `non_editable_fields`; `docs/it/backend/vendite/manual/modello-contratti.md` nomina ancora il lock post-attivazione |
| R-FE-3 | FE | i form di testata seguono `can_edit_testata` e `non_editable_fields` anche fuori bozza: la bolla emessa mostra trasporto e tracciamento modificabili (D-0), il preventivo emesso e accettato la competenza, il contratto attivo fine validità e CIG/CUP |


## 10. Lato BE/FE (sessione backend, 2026-10-10)

> Non committato. Prove: suite `apps.core` + `apps.vendite` con `ZEROERP_TEST_DB_E2E=1`
> 4154 verdi; mypy a cricchetto e ruff verdi; FE 790 test (con i due presidi nuovi, provati per mutazione), `npm run guards`, lint e build verdi;
> sonda sul DB di sviluppo in transazione annullata (sotto).

| # | Fatto |
| --- | --- |
| R-BE-1 | `POST /vendite/ordini/<id>/righe/<riga_id>/data-consegna-confermata/` (`ordini_service.cambia_data_consegna_confermata`): scrive la sola colonna, `null` toglie la promessa, ogni altra chiave è un 400; nessun pre-check di stato. La terna arriva già sotto `capabilities` (il dettaglio trasporta il blob intero). Doc: `api_ordini.md` §Righe |
| R-BE-2 | Ritirati i «solo in DRAFT» della testata in `aggiorna_ordine`, `aggiorna_ddt`, `aggiorna_reso`, `aggiorna_preventivo`, `aggiorna_offerta` e la tabella `_CONTRATTO_PATCH_ALLOWED_BY_STATE`: resta la lettura della testata (404 fuori perimetro), il 409 del lock passa com'è. Le costanti restano dove servono ad altro (elimina, conferma, indirizzi, righe/eccezioni dell'offerta) |
| R-BE-3 | `error_policies_generated.py` rigenerato (diff: i cinque codici e il ritiro, nient'altro), ripieghi dei cinque codici in `error_messages_fallback.py`, tolto il marker di `E_CONTRATTO_CAMPI_BLOCCATI_POST_ATTIVAZIONE` in `contratti_service.py` |
| R-BE-4 | Test riscritti sul contratto nuovo («fuori bozza decide il DB»: il service passa la scrittura) e 6 test del verbo; `modello-contratti.md` §7 e `api_contratti.md` riscritti sul lock di testata; `api_ddt/resi/preventivi/offerte/ordini.md` allineati |
| R-FE-1 | Le due chiavi `vendite.ordini.data_consegna_confermata_reason.*` (it, en): `check_i18n_keys.py` pulito |
| R-FE-2 | Azione di riga «Cambia la data di consegna confermata» in `OrdiniRigheTable` (icona `MANAGE_ICONS.PROMESSA_CONSEGNA`), accesa o spenta col motivo dalla terna; nascosta solo in readonly da permessi. Dialog `OrdineRigaDataConsegnaDialog` (DatePicker, vuoto = toglie la promessa, conferma all'uscita) |
| R-FE-3 | BB `useTestataDocumento` (ok Tid, regola del 2) nei sei drawer: la testata è modificabile se almeno un campo che il form MOSTRA è aperto nella capability (`CAMPI_FORM_TESTATA_*`, presidio `campiFormTestata.spec.js`); i campi si spengono uno per uno da `non_editable_fields`, il form esce dal corpo protetto con `app-escape`, il Salva si libera (`footer-readonly`). Il corpo (righe, indirizzi, sub-drawer) resta sul readonly di stato. A video: la bolla emessa/spedita/consegnata cambia trasporto e tracciamento (D-0, D-1); il contratto ATTIVO CIG/CUP/commessa (ritirata la copia degli stati `codiciAttoEditabili`); l'ordine confermato l'interruttore «fatturazione immediata» (non nominato dal lock, §9.1). Preventivo, offerta e reso: nessun campo del form aperto fuori bozza, come prima. `valido_al` del contratto resta sul dialog «Cessa» (scelta di interfaccia) |

**La sonda (dbdev, transazione annullata, contesto operatore).** Verbo e capability rispondono uguale in
`CONFERMATO`/`PARZIALMENTE_EVASO` (scrive), `EVASO`/`ANNULLATO` (`E_RIGA_DOC_NON_BOZZA`, motivo
`stato_non_ammette`), `DRAFT` (scrive; capability spenta con `in_bozza`). Testata: note dell'ordine e
tracciamento della bolla passano fuori bozza, `data` dà `E_DOC_IDENTITA_FUORI_BOZZA`, a documento annullato
`E_DOC_CHIUSO`. Un payload intero con i campi bloccati **invariati** passa (ordine confermato, bolla emessa):
il form può continuare a mandarlo tutto.

### 10.1 Aperto — richieste al team DB (tutte qui, decisione di Tid del 2026-10-10)

> Trovate dal lato BE/FE facendo il §10. Restano in questo brief, che si chiude quando sono fatte
> insieme al pgTAP del congelamento del listino (§9.4, «Non fatto») e al collaudo a video di Tid.

| # | Cosa | Perché | Ricaduta BE/FE quando è fatta |
| --- | --- | --- | --- |
| **R-DB-1** | `fn_available_actions_ddt`: in bozza `billing_account_id` fermo **solo se la bolla ha una sorgente** (ordine o reso), aperto sulla bolla standalone. ⚠️ **Corretta il 2026-10-10** (collaudo di Tid): la prima stesura diceva «togliere da `c_non_edit_draft`» sempre, ma un DDT da ordine o da reso ha il cliente della sorgente (D-6, `trgfn_ddt_guard_cliente_sorgente`) e il cliente a video si cambiava per poi essere rifiutato al salvataggio. La regola che la capability deve leggere e' quella del guard, non una copia | La capability lo dice fermo **anche in bozza**, il lock lo ferma solo fuori bozza e D-2 (brief-db-esecutivi-ba-coppia) vuole che la bolla nata senza cliente lo riceva in bozza. Terza copia scritta a mano, rimasta indietro | Togliere l'eccezione dichiarata in `DdtDrawer` (`nonEditableFields`), che dal 2026-10-10 vale gia' solo per la bolla senza sorgente |
| **R-DB-2** | `fn_available_actions_offerta`: `motivazione_rifiuto` fuori dalle «sempre» | È fra le colonne ferme in ogni stato, mentre D-10 la vuole aperta in `EMESSA`/`ACCETTATA`. Oggi non pesa: la scrive il cambio di stato e il form non la mostra | Nessuna |
| **R-DB-3** | Un lock a DB per il satellite `vendite.offerte_commerciali_utilities` e per gli indirizzi dei documenti | Nessun lock li nomina: quando si cambiano lo dice solo la capability (`can_edit_utility`) o il BE (`_INDIRIZZI_CFG`, «solo in bozza»). Chi scrive senza passare dal BE cambia la fornitura di un'offerta emessa o gli indirizzi di un documento emesso. Il BE, tolto il «solo in BOZZA» della testata, per il sotto-oggetto `utility` legge `can_edit_utility` | Il BE toglie i suoi «solo in bozza» degli indirizzi e la lettura di `can_edit_utility` in `aggiorna_offerta`: il 409 del lock passa com'è |
| **R-DB-4** | Portare nel DB, dopo il lock di testata, le due regole del contratto che oggi vivono solo in Python: cambio di `listino_id` con righe (`E_CONTRATTO_CAMPI_BLOCCATI_CON_RIGHE`) e rimozione del listino con eccezioni (`E_CONTRATTO_LISTINO_RIMOZIONE_CON_ECCEZIONI`) | Su un contratto ATTIVO che cambia listino il rifiuto Python arriva prima di `E_DOC_CONDIZIONI_FUORI_BOZZA`, mentre il §5 voleva «bloccato» per primo. E una regola in una sede sola, quella del DB | Il BE toglie i due controlli da `update_contratto` |

**Da sapere, non da fare:** `fatturazione_immediata` non è nominata dal lock (§9.1). Dopo R-FE-3
l'interruttore resta acceso fuori bozza (ordine, bolla, contratto) finché il documento non entra in
commessa, e lì lo ferma il suo guard. È la decisione del DB: a video si vedrà.

## 11. Il giro delle richieste R-DB (team DB, dal 2026-10-11)

### 11.1 Censimento prima di scrivere (letto dal catalogo e dalla doc auto-generata)

* **R-DB-3, chi scrive i satelliti.** Nessuno dei sette satelliti di documento ha un lock:
  `vendite.{ddt,ordini,preventivi,offerte_commerciali,contratti}_indirizzi`,
  `vendite.offerte_commerciali_utilities` e anche `vendite.contratti_utilities`, che R-DB-3 non
  nominava ma ha lo stesso buco. Le funzioni DB che li scrivono (`fn_crea_revisione_offerta`,
  `fn_crea_revisione_preventivo`, `fn_push_offerta_a_contratto`, `fn_push_preventivo_a_ordine`,
  `fn_genera_ddt_da_ordine`, `fn_genera_ddt_riconsegna`, `fn_create_contratto`,
  `trgfn_contratti_snapshot_precontrattuali`, AFTER INSERT) scrivono tutte su un documento **appena
  nato in bozza**: il BB delle righe (`vendite.trgfn_doc_righe_lock_fuori_bozza`) si monta senza
  rompere le cascate. Le fatture (`fatture_indirizzi`) restano fuori: non sono di questo brief.
* **R-DB-4.** Le due regole vivono solo in `contratti_service.update_contratto`; l'offerta, che ha le
  stesse righe ed eccezioni, non ne ha nessuna (in bozza cambia listino sotto righe già caricate).
  Fuori bozza `listino_id` è già fermo dal lock di testata (`_a05_`): le due regole contano in bozza.

### 11.2 Decisioni di Tid (2026-10-11)

| # | Domanda | Decisione |
| --- | --- | --- |
| **D-11** | R-DB-4 vale solo per il contratto o anche per l'offerta? | ✅ **Contratto e offerta**: un BB guard montato su tutti e due, con codici di documento al posto di `E_CONTRATTO_*` (regola del 2: contratto e offerta hanno le stesse regole sulle righe) |
| **D-12** | R-DB-3: la frase di `E_RIGA_DOC_NON_BOZZA` parla di «righe»; va bene per indirizzi e fornitura? | ✅ **Codice nuovo per i satelliti**: il BB delle righe impara un argomento col codice da sollevare (default `E_RIGA_DOC_NON_BOZZA`), e i satelliti montano un codice con una frase loro |

### 11.3 ⭐ Che cosa è stato scritto (2026-10-11, non applicato)

> Numerazione: `20261011-21 … -33` (Tid: «parti da -21, lasciamo spazio all'altro cantiere»,
> `brief-db-ddt-righe-evase-dall-ordine`, che sta in `-05 … -20`).

| changeSet / file | Che cosa | Richiesta |
| --- | --- | --- |
| `20261011-21` | `script.fn_doc_lock_regola`: il BB delle righe legge un settimo argomento, il **codice** del rifiuto (default `E_RIGA_DOC_NON_BOZZA`) | R-DB-3, D-12 |
| `20261011-22` | `vendite.trgfn_doc_righe_lock_fuori_bozza` solleva il codice del montaggio | R-DB-3 |
| `20261011-23` | `script.fn_doc_riga_modificabile` (nuova): la riga intera, in uno stato, passa il lock? Sorella di `fn_doc_colonna_modificabile` | R-DB-3 |
| `20261011-24` | il lock «solo in bozza» sui **sette satelliti** (cinque `*_indirizzi`, le due utility 1:1), codice `E_DOC_DATI_COLLEGATI_NON_BOZZA` | R-DB-3 |
| `20261011-25` | `vendite.fn_ddt_vincoli_cliente` (nuova): da dove viene il cliente della bolla (sorgente ordine/reso, righe d'ordine evase) | R-DB-1 |
| `20261011-26` | `vendite.trgfn_ddt_guard_cliente_sorgente` legge i vincoli da `-25`; comportamento invariato | R-DB-1 |
| `20261011-27` | `script.fn_check_listino_cambiabile` (nuova): i due motivi per cui il listino non cambia | R-DB-4, D-11 |
| `20261011-28` | `script.trgfn_doc_guard_listino_con_righe` (nuovo) montato su contratti e offerte, fascia `_a10_`, prima di `guard_listino_documento` | R-DB-4, D-11 |
| `20261011-29` | `fn_available_actions_ddt`: il cliente fermo solo se un vincolo lo tiene (da `-25`); + `can_edit_indirizzi` | R-DB-1, R-DB-3 |
| `20261011-30` | `fn_available_actions_offerta`: `motivazione_rifiuto` fuori dalle «sempre»; `can_edit_utility` e `can_edit_indirizzi` dal montaggio | R-DB-2, R-DB-3 |
| `20261011-31 … -33` | `fn_available_actions_ordine`, `_preventivo`: + `can_edit_indirizzi`; `_contratto`: + `can_edit_utility`, `can_edit_indirizzi` | R-DB-3 |
| `80_data/sql/config/codici_errore.csv`, `messaggi_errore.csv` | tre codici nuovi (`E_DOC_DATI_COLLEGATI_NON_BOZZA` CONFLITTO_STATO, id 1280; `E_DOC_LISTINO_CAMBIO_CON_RIGHE` e `E_DOC_LISTINO_RIMOZIONE_CON_ECCEZIONI` NON_ESEGUIBILE, id 1281-1282); ritirati (`obsoleto_dal`) `E_CONTRATTO_CAMPI_BLOCCATI_CON_RIGHE` ed `E_CONTRATTO_LISTINO_RIMOZIONE_CON_ECCEZIONI` | R-DB-4 |
| `db/pgtap/vendite/test-testata-dopo-emissione-rdb-v1.sql` (nuovo, 34 test) | i quattro R-DB e il **congelamento del listino all'uscita dalla bozza** (il «Non fatto» del §9.4: offerta BOZZA → EMESSA e contratto DRAFT → ATTIVO congelano la versione in vigore, e dopo non si cambia) | §9.4, R-DB-1…4 |
| `db/pgtap/script/test-doc-lock-montaggio-v1.sql` | test 1 adeguato: la regola delle righe porta anche `codice` | — |

**Scelte prese scrivendo.**

* **`contratti_utilities` entra nel montaggio** anche se R-DB-3 nominava solo l'offerta: il
  backend la scrive solo in DRAFT (`_assert_contratto_draft`), è lo stesso buco.
* **`can_edit_indirizzi` su cinque capability.** Gli indirizzi non avevano una capability: il
  FE li spegneva col suo «readonly di stato» e il BE li rifiutava fuori DRAFT, due copie della
  regola. Ora la capability la legge dal lock.
* **Le id dei messaggi partono da 1280**, lasciando 1270-1279 all'altro cantiere che sta
  scrivendo lo stesso CSV.
* **`fn_check_listino_cambiabile` non emette `reason_key`**, come la gemella
  `fn_check_listino_documento`: oggi la legge solo un guard, e non apre un debito verso i
  locales.
* ⚠️ **Un contratto inserito direttamente in ATTIVO** (seed, import: la matrice non vincola
  l'INSERT, linee-guida-sql §7c punto 6) con dati precontrattuali ora fallisce: lo snapshot
  `trgfn_contratti_snapshot_precontrattuali` (AFTER INSERT) scrive `contratti_utilities` su un
  padre fuori bozza, e il lock lo ferma. È coerente con le righe, che su un contratto nato
  ATTIVO già non si scrivono; nessuna funzione DB crea contratti fuori bozza. Da sapere, e
  da confermare con Tid.

### 11.4 Richieste a BE e FE, dopo l'apply di questo giro

| # | A chi | Cosa |
| --- | --- | --- |
| R-BE-5 | BE | ⚠️ **nello stesso rilascio dell'apply**: togliere da `contratti_service.update_contratto` i due controlli del listino (`E_CONTRATTO_CAMPI_BLOCCATI_CON_RIGHE`, `E_CONTRATTO_LISTINO_RIMOZIONE_CON_ECCEZIONI`, ritirati) con `count_righe_attive` e `count_eccezioni_bloccanti` del repository se restano senza lettori; il 422 arriva dal DB coi codici `E_DOC_LISTINO_CAMBIO_CON_RIGHE` ed `E_DOC_LISTINO_RIMOZIONE_CON_ECCEZIONI` (NON_ESEGUIBILE, campo `listino_id`), anche sull'offerta. Policy dei tre codici nuovi (`E_DOC_DATI_COLLEGATI_NON_BOZZA` è CONFLITTO_STATO → 409), `error_policies_generated.py` rigenerato, ripieghi in `error_messages_fallback.py` |
| R-BE-6 | BE | i «solo in bozza» dei satelliti: `stati_modificabili` di `_INDIRIZZI_CFG` (ordini, DDT, preventivi, offerte, contratti), `_assert_contratto_draft` di `create_utility`/`update_utility` del contratto, la lettura di `can_edit_utility` in `aggiorna_offerta`. Decide il DB (D-0): il 409 `E_DOC_DATI_COLLEGATI_NON_BOZZA` passa com'è. La capability porta ora `can_edit_indirizzi` (cinque documenti) e `can_edit_utility` (offerta, contratto) |
| R-FE-4 | FE | il DDT: togliere l'eccezione dichiarata in `DdtDrawer` (`nonEditableFields` sul cliente): dal DB `billing_account_id` arriva fra i non modificabili solo sulla bolla da ordine o da reso (R-DB-1) |
| R-FE-5 | FE | gli indirizzi e la fornitura seguono `can_edit_indirizzi` e `can_edit_utility` invece del readonly di stato (regola del 2: lo stato scritto nel FE è una copia) |

### 11.5 La prova (2026-10-11, `zeroerp_ci`, SQL estratto in transazione ritirata, come owner `zeroerp`)

* I corpi di partenza delle otto funzioni modificate coincidono con quelli vivi su `zeroerp_ci`
  (`pg_get_functiondef` contro la doc auto-generata).
* L'SQL estratto dei tredici changeSet, in ordine di id, più l'upsert **completo** dei due CSV
  (1053 codici, 1049 messaggi): nessun rifiuto.
* `vendite/test-testata-dopo-emissione-rdb-v1` (nuovo, 34 test): **34/34** con l'estratto;
  senza, rosso dal test 1 e fermo al 4 (le funzioni non ci sono): il file vede ciò che deve
  vedere.
* **Regressione** su 88 pgTAP (chi scrive i sette satelliti, le cinque capability, i due lock,
  il guard del cliente, il listino del contratto, i presidi trasversali), senza e con il giro:
  identici, salvo:
  * `script/test-doc-lock-montaggio-v1` — il test 1 adeguato (la regola delle righe porta
    `codice`): 30/30 con, 29/30 senza, come atteso;
  * `offerte_commerciali/test_fn_crea_revisione_offerta` e `test_fn_push_offerta_a_contratto`
    — **adeguati**: la fixture scriveva la fornitura su un'offerta già EMESSA o ACCETTATA, che il
    modello ora rifiuta; la fornitura nasce in bozza, prima delle transizioni (come le
    eccezioni dal 2026-10-04). 7/7 e 10/10, con e senza;
  * `script/test-rubinetto-primo-motivo-v1` — test 5, il conteggio esatto delle funzioni che
    chiamano l'helper: **37** (il 36 è dell'altro cantiere, `fn_ddt_riga_correggi_qta_evasa`;
    il 37 è `script.trgfn_doc_guard_listino_con_righe`). Su `zeroerp_ci` senza i due giri vale
    35: il numero torna solo con entrambi applicati;
  * `vendite/test-ddt-righe-evase-dall-ordine-v1` — dell'altro cantiere, fermo sulla colonna
    `evasa` che arriva coi suoi changeSet non applicati: lo scratch non lo può giudicare.
* ⚠️ **Trovato nella prova e corretto prima della consegna**: il presidio C2
  (`test-punti-canale-campo-v1`, test 2) legge un `->> 'codice'` dentro la chiamata a
  `fn_log_and_raise_error` come un sito «primo motivo» cieco. Il lock delle righe passa ora il
  codice in una variabile (`v_codice`), come il gemello di testata.
* `plpgsql_check` sulle quattro funzioni nuove e sulle otto modificate: nessun errore. Un
  avviso su `fn_check_listino_cambiabile` («STABLE ma chiama una VOLATILE»: la `PERFORM`
  dell'errore di chiamante, come nelle check sorelle); quello su `fn_available_actions_ordine`
  c'era già prima del giro.
* Guardrail statici verdi sui file del giro (letterali, `runOnChange`, preCondition, trigger di
  automazione, `GRANT` batch, timestamp, v1). `guardrail_pgtap_preambolo` segnala
  `vendite/test-push-list-stato-obbligatorio-v1.sql` (manca `SET CONSTRAINTS ALL IMMEDIATE`):
  file già committato, non di questo giro.
* ⚠️ Come owner la RLS non c'è: l'esito come app arriva dalla corsa di Tid.

### 11.6 Dopo l'apply: la nascita del documento (2026-10-11, D-13 di Tid)

> ✅ `20261011-21 … -33` applicati da Tid su dbdev e zeroerp_ci. Alla corsa pgTAP, sette rossi nuovi.

**I rossi.** Sei sono la stessa causa: `test_fn_successione_contratti`, `test-fn-resolve-iva-riga`,
`test-fn-resolve-prezzo-listino-v2-classe-da-contratto-v1`, `test-vw-dash-aperto-v1`,
`test-vw-dash-backlog-v1`, `test-vw-dash-fatturazione-v1`. Inseriscono un contratto direttamente
ATTIVO o ANNULLATO (lecito, linee-guida-sql §7c punto 6), e `trgfn_contratti_snapshot_precontrattuali`
(AFTER INSERT) gli scrive la fornitura, che il lock dei satelliti rifiutava. È il caso dichiarato
«da confermare» nel §11.3. Su dbdev succede perché l'istanza pescata ha dati precontrattuali; in CI
quei fixture non li trovano. Il buco però è nel modello. Il settimo,
`test-trgfn-doc-righe-lock-fuori-bozza-v1`, pinna l'elenco esatto dei montaggi del lock: mancavano
i sette satelliti (**adeguato**, test 2).

**D-13 di Tid.** Prima scelta: «la nascita è la transazione». Ripresa quando è emerso che acceca
ogni pgTAP dei lock (il test è una transazione sola). Decisione finale: **passa ciò che un
trigger scrive su un documento nato in questa transazione**. Scartato anche il lock della
fornitura senza INSERT, che lascia un buco.

| changeSet | Che cosa |
| --- | --- |
| `20261011-40` | `script.fn_get_stato_testata_documento`: + `nata_in_transazione` (`data_insert = transaction_timestamp()`: la scrive il default, nessun UPDATE la tocca; `xmin` no, lo cambia anche l'emissione). Cambia `RETURNS TABLE`: DROP e CREATE, poi il GRANT all'app. I chiamanti leggono le colonne per nome |
| `20261011-41` | `vendite.trgfn_doc_righe_lock_fuori_bozza`: `CONTINUE WHEN v_nata AND pg_trigger_depth() > 1`. Una scrittura diretta resta rifiutata |
| `vendite/test-testata-dopo-emissione-rdb-v1` | + test 35 (un contratto inserito ATTIVO riceve lo snapshot) e 36 (la fornitura scritta direttamente su un contratto attivo nato nella stessa transazione è rifiutata) |
| `vendite/test-trgfn-doc-righe-lock-fuori-bozza-v1` | test 2: i sette satelliti nell'elenco atteso dei montaggi |

> Numerazione: `-36 … -39` lasciati all'altro cantiere (che è a `-35`).

**La prova** (`zeroerp_ci`, che ha già `-21 … -35`; SQL estratto di `-40`/`-41` in transazione
ritirata, come owner, log dblink spento). `test-testata-dopo-emissione-rdb-v1` **36/36**; senza i
due changeSet cade esattamente il test 35, con il rosso di Tid (`E_DOC_DATI_COLLEGATI_NON_BOZZA`).
Regressione su 18 pgTAP (lock delle righe, montaggi, consumatori del lettore, satelliti, offerte,
presidi): identici con e senza. I sei file di Tid su `zeroerp_ci` cadono prima, sui loro fixture
che pescano dati: lo scratch non li giudica, il caso è costruito nei test 35-36. `plpgsql_check`
pulito (l'avviso sul lettore è la `PERFORM` dell'errore di chiamante, c'era già). Dopo il DROP e
CREATE la funzione ha gli stessi grant (app e batch, quest'ultimo dai privilegi di default).

### 11.7 Due fixture che scrivevano la fornitura di un contratto attivo (2026-10-11)

Dopo `-40`/`-41` (applicati da Tid) due file cadono ancora, e non per la nascita: la fixture
**modifica** o **cancella** la fornitura di un contratto già ATTIVO, cioè proprio ciò che il lock
dei satelliti vieta. Adeguati sul modello:

| File | Prima | Ora |
| --- | --- | --- |
| `vendite/test-fn-resolve-iva-riga` | UPDATE di tipo e classe della fornitura del contratto ATTIVO | legge il tipo d'uso che lo snapshot ha scritto alla nascita, e mette il codice IVA su quello (catalogo); se lo snapshot non c'è, la fixture lo dice nel test 1 |
| `vendite/test-fn-resolve-prezzo-listino-v2-classe-da-contratto-v1` | contratto nato ATTIVO, poi DELETE e INSERT della fornitura (due volte) | il contratto nasce DRAFT, riceve la fornitura, poi si attiva con la transizione vera (il listino costruito ha una versione in vigore oggi) |

Censiti per nome gli altri pgTAP che scrivono `contratti_utilities` / `offerte_commerciali_utilities`
con UPDATE o DELETE: solo `test-contratti-utilities-guard-tipo-classe-v1`, che lavora in DRAFT.
⚠️ Lo scratch non li giudica: le due fixture pescano dati che su `zeroerp_ci` non ci sono. L'esito
è della corsa di Tid su dbdev.

### 11.8 Stato (2026-10-11)

✅ `20261011-40`/`-41` applicati da Tid, pgTAP verdi (con le fixture adeguate del §11.7).

**Lato DB non resta niente.** Le richieste R-DB-1 … R-DB-4 sono fatte (§11.3, §11.6), e il
pgTAP del congelamento del listino all'uscita dalla bozza c'è (test 13-14 e 18-19 di
`test-testata-dopo-emissione-rdb-v1`). Il brief resta aperto per:

* **BE/FE**: le richieste del §11.4. R-BE-5, il ritiro dei due controlli del listino da
  `update_contratto`, va nello stesso rilascio. Poi R-BE-6 (i «solo in bozza» dei satelliti),
  R-FE-4 (l'eccezione del cliente in `DdtDrawer`) e R-FE-5 (`can_edit_indirizzi`, `can_edit_utility`);
* il **collaudo a video** di Tid;
* poi l'**archivio** in `work-done/`.

Da sapere: D27 (`brief-db-indirizzi-documento-seguono-il-cliente`) scrive gli indirizzi dei
documenti in bozza; il lock dei satelliti (`-24`) lo lascia fare, e un riempimento automatico
fatto da un trigger alla nascita passa per D-13.

## 12. Lato BE/FE del giro R-DB (sessione backend, 2026-10-11)

> Committato il 2026-10-11. Prove: suite `apps.core` + `apps.vendite` 3927 verdi (al commit l'intera
> suite backend, 6136); con
> `ZEROERP_TEST_DB_E2E=1` 4154, rossi i soli due presidi del codice di D27 (sotto); mypy a
> cricchetto e ruff verdi; FE 795 test, `npm run guards`, lint e build verdi;
> `check_i18n_keys.py` pulito.

✅ **Fatta dal team DB il 2026-10-11** (`obsoleto_dal` in `codici_errore.csv`). **Richiesta al team DB (2026-10-11, dalla revisione del giro):** `E_CONTRATTO_NON_MODIFICABILE`
è ancora **vivo** nel catalogo (`config.codici_errore`), ma dopo R-BE-6 non lo solleva più nessuno,
né il backend né una funzione del DB. Va marcato **ritirato** come i due codici del listino (R-DB-4),
così entra in `CODICI_RITIRATI` alla prossima rigenerazione delle policy; il ripiego resta, come per
gli altri ritirati.

| # | Fatto |
| --- | --- |
| R-BE-5 | Tolti da `contratti_service.update_contratto` i due controlli del listino e da `ContrattiRepository` `count_righe_attive` / `count_eccezioni_bloccanti` (nessun altro lettore): il 422 arriva dal DB (`E_DOC_LISTINO_CAMBIO_CON_RIGHE`, `E_DOC_LISTINO_RIMOZIONE_CON_ECCEZIONI`). Policy rigenerate; ripieghi dei tre codici nuovi e, nello stesso giro, dei cinque di `brief-db-ddt-righe-evase-dall-ordine` già nel catalogo in git |
| R-BE-6 | Il BB `_indirizzi_documento_helpers` non giudica più lo stato (`stati_modificabili` e `stato_error_code` ritirati dalla config dei cinque domini): resta il guard di esistenza, il 409 `E_DOC_DATI_COLLEGATI_NON_BOZZA` passa com'è. Contratto: ritirato `_assert_contratto_draft` (create/update utility). Offerta: tolta la lettura di `can_edit_utility` in `aggiorna_offerta` e, oltre al §11.4, i «solo in BOZZA» di `crea_utility` / `aggiorna_utility` (stesso satellite, stessa copia). `E_CONTRATTO_NON_MODIFICABILE` non ha più chi lo solleva: tolto il suo override UI |
| R-FE-4 | Tolta l'eccezione del cliente in `DdtDrawer`: il form legge `non_editable_fields` com'è |
| R-FE-5 | `DocumentoIndirizziSection` prende dal chiamante i permessi (`readonly`) e il blob (`capabilities`) e legge lei `can_edit_indirizzi` (regola del 2: l'OR era ricopiato nei cinque drawer; presidio `DocumentoIndirizziSection.spec.js`), non dalla catena di stato del corpo, ed esce dal corpo protetto (`app-escape`): fuori bozza gli indirizzi si consultano in sola lettura. Cinque drawer. La fornitura del contratto non ha un'interfaccia: tolte le azioni `addUtility`/`updateUtility` dello store e le due API senza consumatori (ok di Tid); `can_edit_utility` serve all'offerta, che già la leggeva |
| i18n | Le quattro chiavi `vendite.ddt.correggi_qta_evasa_reason.*` (it, en) di `fn_check_ddt_riga_correggi_qta_evasa`, dell'altro cantiere, importate qui (decisione di Tid) |

⚠️ **Il DB di sviluppo è avanti rispetto a git** di un codice, `E_INDIRIZZO_DOC_NON_DEL_CLIENTE`
(`brief-db-indirizzi-documento-seguono-il-cliente`, non pushato): è stato tolto da
`error_policies_generated.py`, che resta allineato al catalogo in git. Rossi attesi in locale
`test_error_codes_db_policy_guardrail` e `test_error_policies_divergenza_db`, finché quel giro non
arriva in git; allora si rigenera e si scrive il ripiego.

### 12.1 Collaudo a video (Tid, 2026-10-11): superato

Percorso: listino sotto le righe su contratto e offerta in bozza (cambio con righe, rimozione con
eccezioni, rimozione con sole AGGIUNTE, cambio senza righe); indirizzi dei cinque documenti in bozza
(modificabili) e fuori bozza (consultabili in sola lettura); fornitura dell'offerta in bozza ed
emessa; cliente della bolla standalone, da ordine ed emessa; le fasi 1-2 (data di consegna
confermata dell'ordine, testata della bolla emessa e annullata, riferimenti dell'atto del
contratto attivo, contratto cessato o annullato fermo).
