# Brief DB — La testata di un documento dopo l'emissione: che cosa si cambia ancora

> **Chi scrive:** team DB (`dev/db-tid`), 2026-10-10. **A chi:** Tid; poi BE (§7).
> **Origine:** §8 di [brief-db-esecutivi-ba-coppia](brief-db-esecutivi-ba-coppia.md) e il suo §10.3
> («quali colonne di testata si riscrivono in fase chiusa»), ripreso dal §7 di
> [brief-db-guard-emittente-ba-unico](brief-db-guard-emittente-ba-unico.md).
> **Stato:** 📝 **aperto, decisioni tutte chiuse da Tid il 2026-10-10 (§6), nessun codice.** Il
> prossimo passo è il giro DB: le colonne decise nel montaggio del BB fuori bozza di ogni documento,
> un codice per famiglia, la forma per stato sul contratto (§5); poi il BE toglie i suoi «solo in
> DRAFT» (§7).
> ⛔ **Si parte da un altro brief.** Questo giro **non comincia** finché non è chiuso R-1 di
> [brief-db-ordine-data-consegna-confermata-capability](brief-db-ordine-data-consegna-confermata-capability.md):
> lì nasce il lettore generico del montaggio e si fissa la forma per stato degli argomenti, che qui si
> riusano (nota in fondo al §5). Cominciare da qui vorrebbe dire fissare quella forma due volte.
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

🔗 **Il lettore del montaggio (nota DB, 2026-10-10):** se il form deve spegnere i campi prima
dell'errore (§7), serve una capability che legga **dal montaggio** quali colonne restano
modificabili in quale stato. Lo stesso lettore lo chiede R-1 di
[brief-db-ordine-data-consegna-confermata-capability](brief-db-ordine-data-consegna-confermata-capability.md)
per la data di consegna confermata sulle righe: lì nasce **generico** sui due BB (righe e
testata), e qui si riusa (regola del 2). La forma degli argomenti per stato portata sulla testata
è quella che quel lettore sa leggere: si fissa una volta per entrambi.

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

## 7. Ricaduta BE (dopo la consegna DB)

* **I «solo in DRAFT» della testata** di ordine, DDT, reso, preventivo e offerta, e la tabella per
  stato del contratto: con la regola nel DB sono una seconda copia. Si ritirano, e il backend mostra
  l'errore del DB (o legge la capability, se il form deve spegnere i campi prima).
* **Le whitelist `UPDATE_KEYS_*`** restano: dicono quali colonne il form espone, non quando.
* Con D-0, la bolla emessa mostra a video i campi delle famiglie 2-4 modificabili.

## 8. Fuori da questo brief

* **Le righe**: hanno già la loro regola (BB `vendite.trgfn_doc_righe_lock_fuori_bozza`, con le
  eccezioni per stato).
* **La commessa** (D-4).
