# Brief DB — Un cliente manuale per soggetto e utility

## ⏭️ Chi riparte — aggiornato al 2026-10-13

**Riparte: il team DB**, con la consegna del §5: le decisioni del §4 sono tutte prese. Cantiere aperto, codice non iniziato.

| # | Chi | Che cosa | Dove | Aspetta |
| --- | --- | --- | --- | --- |
| 1 | Tid | ✅ decisioni C-1…C-5 prese il 2026-10-13 | §4 | — |
| 2 | DB | la regola a DB, il codice d'errore, il censimento dei doppioni di dbdev, il pgTAP | §5 | 1 |
| 3 | BE | il messaggio della creazione manuale; lo smoke `smoke-test-clienti.sh` esce dal registro dei rossi | §6 | 2 |

Decisioni aperte di Tid: nessuna. Lavoro da committare: questo documento.

> **Chi scrive:** team DB (`dev/db-tid`), 2026-10-13. **A chi:** Tid, poi il team DB.
> **Origine:** lo smoke `smoke-test-clienti.sh` del giro notturno (commit BE `b3e35f899`), il passo
> lasciato rosso come «DOMANDA APERTA» (registro `backend/scripts/tests/baseline-smoke.tsv`). Tid,
> 2026-10-13: **va impedito**. Registro: **D33** di
> [migliorie-generali-da-test-valutazione](migliorie-generali-da-test-valutazione.md).

## 1. Il caso

La creazione manuale del cliente (utility con `config.utilities.richiede_pdp = false`) crea **ogni
volta** un'istanza fittizia nuova (`ClientiRepository.create_istanza_fittizia`: un `INSERT` in
`anagrafiche.istanze_utilities` con `fittizia = true`), poi il suo billing account e il cliente. Con
lo stesso soggetto e la stessa utility, la seconda richiesta risponde 200 e nasce un **secondo
cliente**, indistinguibile dal primo.

## 2. Perché è un difetto del modello

* Per le utility con PDP l'identità della fornitura è il **punto fisico**: due GAS dello stesso soggetto
  sono due contatori, due istanze, due clienti, ed è giusto. La protezione è
  `ex_clienti_no_overlap_stesso_pdp`.
* L'istanza fittizia **non rappresenta niente di fisico**: è un «contenitore tecnico trasparente»
  ([gestione-delle-istanze-utility](../../guide/gestione-delle-istanze-utility.md), §Istanze fittizie
  nella creazione manuale). Senza punto fisico, ciò che distingue una fornitura resta soggetto, utility
  e azienda emittente: due istanze fittizie con gli stessi tre valori sono la stessa fornitura scritta
  due volte.
* La guida dice che il UNIQUE sul billing account «basta» per le fittizie
  (`uq_clienti_billing_account`). Basta contro due clienti sullo **stesso** BA, ma non contro una
  seconda istanza col suo BA nuovo, che è proprio quello che fa la creazione manuale.

## 3. I fatti di struttura (2026-10-13)

* `anagrafiche.istanze_utilities`: `soggetto_id`, `fittizia`, nessuna utility e nessun emittente;
  l'unico UNIQUE è `codice`.
* `anagrafiche.billing_account`: `istanza_utility_id`, `soggetto_ruolo_id`, `utility_id`, `validita`;
  `uq_billing_instance_utility (istanza_utility_id, utility_id)`.
* L'emittente del BA sta nel ponte `emittenti_fiscali_billing_account`; un'istanza non ha BA di due
  emittenti (`E_ISTANZA_EMITTENTI_DIVERSI`). Lo stesso soggetto può quindi essere cliente di due
  aziende per la stessa utility, su due istanze: la chiave deve contenere l'emittente.
* La regola tocca quattro tabelle (istanza per `fittizia`, cliente per `periodo` e utility, BA, ponte
  per emittente): non sta in un indice, si controlla **alla conferma** dell'operazione, come
  `E_ISTANZA_SENZA_BA`. È la sorella di `ex_clienti_no_overlap_stesso_pdp`: là il perno è il PDP, qui
  soggetto + utility + emittente.

## 3-bis. Analisi: chiudere, riaprire, «attivo» (2026-10-13)

> Fatti datati, letti dal codice e dalla doc auto-generata. Servono a trovare dove il codice si
> separa dal modello, non a decidere la forma.

### Chi chiude e chi riapre, oggi

| Passo | Dove | Che cosa fa |
| --- | --- | --- |
| disdetta | `script.fn_disdetta_cliente` | solo da `AT`: `data_chiusura` + stato `CH` |
| subentro | `script.fn_subentro_cliente` | chiude il cliente precedente **sul PDP**; il nuovo nasce su istanza, BA e cliente nuovi (`parent_istanza_id`) |
| sospensione e riattivazione | `pratiche` (`trgfn_sospensioni_riattiva`) | `data_sospensione` / `data_riattivazione`: il cliente resta lo stesso, il periodo non cambia |
| **riapertura di un chiuso** | — | **non esiste**: nessuna funzione DB, nessun endpoint BE (la PATCH del cliente non accetta stato e date) |

⚠️ Nemmeno disdetta e subentro hanno un chiamante nel backend o nel frontend: oggi l'app **crea**
clienti (sempre `AT` con la data operativa) ma non li chiude. La chiusura vive solo nelle due funzioni
DB.

La riapertura è quindi un passo del modello ancora da scrivere, non un comportamento da conservare.
Lo storico del cliente esiste già (`storico.clienti`): ogni versione della riga resta leggibile.

### Cinque definizioni di «cliente attivo»

| Lettore | Criterio | Dove si separa dal periodo |
| --- | --- | --- |
| `ex_clienti_no_overlap_stesso_pdp` | `periodo` (date; `AN` → NULL) | è il riferimento |
| `script.fn_subentro_cliente` | non `AN`, `data_attivazione < nuova`, `data_chiusura IS NULL OR >= nuova` | coerente con il periodo |
| `anagrafiche.trgfn_clienti_sync_stato_pdp` | **lo stato**, e solo `AT`/`CH` | `CW` (chiuso per switch) non libera il PDP; una chiusura con data futura lo libera subito |
| `script.fn_disdetta_cliente` | stato `AT` | un sospeso (`SF`/`SC`/`RS`) non si può disdire |
| BE `PraticheRepository.ha_ba_attivo` | `data_attivazione NOT NULL AND data_chiusura IS NULL` | una chiusura con data futura vale «non attivo» già oggi; un `CH` senza data vale «attivo» |

Sono tre misure diverse (periodo, stato, «data di chiusura vuota») per la stessa domanda. La regola di
questo brief deve usarne una, il periodo; le altre sono il debito da riallineare (vedi §5).

### Chi legge «il cliente del BA» (per C-5)

I documenti non portano un `cliente_id`: preventivi, ordini, DDT, contratti, fatture e commesse puntano
al **BA**. Il cliente si ritrova dal BA, contando su `uq_clienti_billing_account`:

* DB (doc auto-generata): `vendite.fn_resolve_termini_pagamento` (termine e modalità di pagamento
  della fattura), `script.fn_get_cliente_testata_documento`, `script.fn_get_search_detail`,
  `vendite.fn_get_contratto_attivo`, `fn_contratto_sovrapposto`, `fn_get_commessa_stato`,
  `fn_get_or_create_commessa`, `fn_list_commesse_emittibili`, `fn_list_consumi_da_pushare`,
  `fn_list_contratti_da_pushare`, `anagrafiche.fn_guard_ba_gestore_globale_storia`; le viste
  `vw_clienti_lista`, `vw_clienti_codice_ba`, `vw_pdp`, `vw_contratti_lista`,
  `vw_dash_fatturazione_contratti`, `dbops.vw_diag_v_clienti_links`;
* BE: `preventivi_repository`, `pricing_diagnose_repository`.

Con la decisione C-5 (strada c) nessuno di questi lettori cambia: un BA resta con un cliente solo.

## 4. Decisioni di Tid

* ✅ **C-1 — la chiave** (Tid, 2026-10-13): **soggetto + utility + azienda emittente**, fra le istanze
  fittizie. Due clienti con la stessa chiave e periodi sovrapposti sono un doppione; con un'altra
  utility o un'altra azienda emittente sono due forniture.
* ✅ **C-2 — nel tempo** (Tid, 2026-10-13): **non ne possono essere attivi due**. La misura è quella
  che il modello usa già per il PDP: **`clienti.periodo`** (`[data_attivazione, data_chiusura)`,
  scritto da `anagrafiche.trgfn_clienti_set_periodo`), non lo stato e non la `validita` del BA. Lo
  stato entra attraverso il periodo:

  | Stato | Periodo | Occupa la chiave? |
  | --- | --- | --- |
  | `AT`, `RS`, `SF`, `SC` (attivo, sospeso) | `[attivazione, ∞)` | sì: un sospeso è ancora la fornitura |
  | `CH`, `CW` (chiuso) | `[attivazione, chiusura)` | solo fino alla chiusura: dopo si apre una catena nuova (C-5) |
  | `AN` (annullato) | `NULL` (il trigger azzera date e periodo) | no |
  | `PR` (pre-contrattuale) | `NULL` finché non c'è `data_attivazione` | no: vedi C-4 |

* ✅ **C-5 — un cliente chiuso non si riapre** (Tid, 2026-10-13). Vale per tutte le utility, con e
  senza PDP. Sullo stesso cliente si ammettono **solo sospensione e riattivazione**. Per tornare si
  apre una **catena nuova**: istanza nuova (collegata alla precedente con `parent_istanza_id`), BA
  nuovo, cliente nuovo, come nel subentro sul PDP. Scartate: (a) riaccendere lo stesso cliente; (b) un
  cliente nuovo sullo stesso BA, che avrebbe tolto «un BA, un cliente» (R-8 di
  [brief-db-istanza-nasce-col-ba](../work-done/brief-db-istanza-nasce-col-ba.md)) e costretto ogni
  lettore del §3-bis a scegliere fra più clienti. Conseguenze:
  * `uq_clienti_billing_account` resta com'è; il vecchio BA vive per fatture finali e conguagli;
  * **chiuso è uno stato finale**: da `CH`/`CW` non si esce, e `data_chiusura` di un chiuso non si
    cambia. Oggi nessuno lo impedisce (non c'è un grafo delle transizioni del cliente): la riapertura
    non esiste perché nessuno la scrive, non perché il DB la vieti;
  * la guida «Policy sul billing account dopo la disdetta» cita «eventuali riattivazioni future» del
    BA: va riscritta (il BA chiuso non si riattiva; restano fatture finali e conguagli).
* ✅ **C-4 — il pre-contrattuale** (Tid, 2026-10-13): **non blocca**. Un cliente `PR` non ha periodo:
  si può preparare anche mentre un altro con la stessa chiave è attivo (è il caso della catena nuova
  preparata prima della chiusura della vecchia), e il blocco scatta all'**attivazione**. Ma quando lo
  si prepara serve un **avviso, solo avviso**: «esiste già un cliente per questo soggetto, servizio e
  azienda», col codice del suo BA.
  * ⚠️ Un avviso `W_` del catalogo **non basta**: va solo nel log (`script.fn_log_error_only`),
    l'operatore non lo vede. Serve una **lettura** che il BE chiama e il FE mostra, sul modello del
    controllo degli indirizzi duplicati (`useIndirizzoDuplicato`).
  * ⭐ Il DB consegna **una** funzione «clienti con la stessa chiave» (codice BA, stato, periodo), e la
    usano **tutti e due**: il guard che rifiuta (C-2) e la lettura che avvisa. Un predicato solo: se
    fossero due, prima o poi l'avviso direbbe una cosa e il guard un'altra.
* ✅ **C-3 — la creazione manuale davanti a un doppione** (Tid, 2026-10-13): il rifiuto porta nel
  messaggio il **codice del cliente esistente**, cioè il codice del suo BA (il cliente non ha un codice
  suo: lo identifica il BA, `vw_clienti_codice_ba`). Il segnaposto lo riempie il DB; il BE non
  aggiunge niente. Il pulsante «Apri il cliente esistente» resta un possibile passo FE successivo,
  senza ricadute sul DB.

### ⚠️ Il buco sotto la regola: un chiuso senza data di chiusura

`chk_clienti_date_coerenti` controlla solo `data_chiusura >= data_attivazione` quando ci sono
entrambe, e `trgfn_clienti_set_periodo` dice nel commento che in `CH` la data di chiusura «deve
essere valorizzata» ma non lo controlla. Un cliente `CH` con `data_chiusura` NULL ha periodo
`[attivazione, ∞)`: per la regola resta **attivo per sempre** e impedisce la catena nuova. Vale già
oggi per il PDP (`ex_clienti_no_overlap_stesso_pdp`). Si chiude in questo cantiere: stato chiuso
⇒ `data_chiusura` obbligatoria (censire prima i chiusi senza data).

## 5. Consegna DB (dopo le decisioni)

* la regola (guard alla conferma, sul modello di `E_ISTANZA_SENZA_BA`) e un codice d'errore registrato;
* ⛔ **censimento prima del vincolo**: lo smoke ha creato doppioni su dbdev a ogni giro. Il vincolo
  nuovo va provato contro i dati esistenti e la bonifica scritta prima, altrimenti l'apply si ferma;
* chiuso stato finale (C-5): da `CH`/`CW` non si esce, `data_chiusura` immutabile;
* `CH`/`CW` ⇒ `data_chiusura` obbligatoria (§4, il buco), col censimento dei chiusi senza data;
* le cinque definizioni di «attivo» (§3-bis) riallineate sul periodo, o dichiarate come debito in un
  brief loro;
* la funzione «clienti con la stessa chiave» (C-4), letta dal guard e dall'avviso;
* pgTAP: un secondo cliente manuale con la stessa chiave è rifiutato; con un altro emittente o
  un'altra utility passa; un sospeso blocca; dopo la chiusura la catena nuova (istanza, BA, cliente)
  passa; riportare un chiuso ad attivo è rifiutato; l'annullato non blocca; un `CH` senza data è
  rifiutato.

## 6. Ricaduta BE/FE

* `ClienteService`: il codice nuovo arriva come 409 col messaggio del DB, che porta già il codice
  del cliente esistente (C-3); nessun lavoro BE oltre alla mappatura del codice (§Tassonomia errori di
  `api.md`).
* **avviso del pre-contrattuale (C-4)**: dove si prepara un cliente `PR` (oggi dalla pratica), il BE
  legge la funzione «clienti con la stessa chiave» e il FE mostra l'avviso senza bloccare, come per
  gli indirizzi duplicati;
* **nessun percorso di riapertura** (C-5): se un giorno il BE esporrà disdetta e subentro, il «torna»
  del cliente è una catena nuova (istanza, BA, cliente), mai un cambio di stato del chiuso;
* `smoke-test-clienti.sh`: il passo oggi in «DOMANDA APERTA» si aspetta il rifiuto, ed esce da
  `baseline-smoke.tsv`.
