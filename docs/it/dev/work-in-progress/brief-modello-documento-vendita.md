# Brief — Il modello del documento di vendita, scritto una volta

## ⏭️ Chi riparte — aggiornato al 2026-10-25 (giro 7: DB e BE fatti, §9.7; difetto DB X → X, §9.8)

**Riparte: Tid**, col commit del giro BE (§9.7, §9.8) e il dato `emetti_ordine` ai profili; poi il **team DB** sul difetto emerso nel §9.8 (il verbo comune accetta il passaggio allo stesso stato: un secondo «Emetti» passa), prima del giro 8, il contratto. Giro 7 (l'ordine): DB applicato e verde (Tid, 2026-10-25). Giro 6, il preventivo (§8): DB applicato e verde, BE fatto (§8.10) tranne il ritiro di `STATO_EMESSO`, che aspetta il lettore. Il giro 5 è chiuso e committato su DB e BE (`4351164c1`, PR #1943).

| # | Chi | Che cosa | Dove | Aspetta |
| --- | --- | --- | --- | --- |
| 1 | ✅ team DB | Bozza: il modello com'è oggi, le divergenze, le decisioni già prese | §2, §3 | — |
| 2 | ✅ **Tid** | M-1 … M-6, decise il 2026-10-24 | §4 | 1 |
| 2-bis | ✅ **Tid** | N-1 … N-3 (un documento nasce nel suo stato iniziale), decise il 2026-10-24 | §4-bis | 2 |
| 2-ter | ✅ team DB | Censimento di chi crea documenti gia' avanti (DB, backend, test Django, pgTAP), 2026-10-24 | §4-ter | 2-bis |
| 2-quater | ✅ **Tid** | P-1 … P-3, decise il 2026-10-24; e il modo di procedere (§5) | §4-ter | 2-ter |
| 2-quinquies | ✅ team DB | Primo giro scritto e provato: il BB della nascita su vendite e acquisti, 9 funzioni e 3 builder senza copie, 48 pgTAP portati, la richiesta al team BE | §4-quinquies | 2-quater |
| 2-sexies | ✅ **Tid** | Apply di `20261024-07` … `-25` e corsa pgTAP: verdi (2026-10-24); Q-1 decisa (B) | §4-quinquies | 2-quinquies |
| 2-sexies-bis | ✅ **Tid** | Q-2 … Q-4, decise il 2026-10-24 | §4-quinquies | — |
| 2-sexies-ter | ✅ team DB | Q-2 (tre builder estesi, non nuovi: Tid), Q-3, Q-4: `20261024-26` … `-28`, 28 pgTAP portati, presidi estesi | §4-sexies | 2-sexies-bis |
| 2-sexies-quater | ✅ **Tid** | Corsa pgTAP (come app) del secondo giro; R-1 (Q-3: la «definitiva» ferma nel lotto); i candidati e i residui | §4-sexies | 2-sexies-ter |
| 2-septies | ✅ team BE | Richiesta 1-5 fatta il 2026-10-24: policy e ripiego del codice nuovo, i 5 service e i loro repository senza lo stato iniziale, test e smoke portati alla nascita in bozza; revisione critica dello stesso giro (punto 6) | §4-quinquies | 2-sexies |
| 2-octies | ✅ team BE | Le sonde `richiedi_db_provvisto` sulle firme FINALI dei builder: le due della richiesta **e una terza** (articolo) rotta da prima; policy rigenerata; suite completa sul DB reale verde (2026-10-25) | §4-octies | 2-nonies |
| 2-octies-bis | ✅ **Tid** / team BE | BE-1 e BE-2 accettate da Tid e fatte (2026-10-25): il BB delle sonde fallisce sull'oggetto mancante; il runner del lotto tiene il codice del DB | §4-octies | 2-octies |
| 2-nonies | ✅ team DB / **Tid** | Terzo giro: debiti emersi chiusi, R-1 … R-6 e R-9 (`-29` … `-36`); applicati | §4-septies | 2-sexies-quater |
| 2-decies | ✅ team DB / **Tid** | Quarto giro: il pezzo comune (nessun cliente in più nei builder) e i builder delle fixture ripetute (`-37` … `-42`); applicati da Tid alle 23:50, corsa come app verde | §4-octies | 2-nonies |
| 3 | ✅ team DB | Il §2, corretto con le decisioni, diventa la guida `docs/it/guide/modello-documento-di-vendita.md`; le otto guide dei documenti rimandano lì (2026-10-25) | §6 | 2 |
| 3-bis | ✅ **Tid** | Rilettura della guida: le sei regole sono scritte come le ha decise (Tid, 2026-10-25: «sì, ok») | §6 | 3 |
| 4 | ✅ team DB / **Tid** · team BE | Giro 5 (bolla e reso): DB scritto, applicato e verde il 2026-10-25 (§7); tocca al BE (§7.6). Il piano: ogni documento portato al modello **tutto in una volta**, un documento per giro. ✅ Primo documento (Tid, 2026-10-25): **il DDT, col DDT d'acquisto** — il più vicino al modello; lì nascono i pezzi comuni di S-1 e S-2. S-1 (b) e S-2 (a) decise | §5, §6 | 3-bis |
| 4-bis | ✅ team BE | Giro 5 lato BE: §7.6 punti 1-5 (EMESSO solo da «Emetti», il 403 dalla riga del passaggio col BB `PassaggioDocumento`, codici, test DB); committato `4351164c1` | §7.9 | 4 |
| 4-bis-bis | ✅ **Tid** | Giro 6 = il preventivo; lettore in due pezzi, `fn_doc_stato_id` + `fn_doc_azione_passaggio` (2026-10-25) | §8 | 4-bis |
| 4-bis-ter | ✅ **Tid** | U-1 (a), U-2, U-3 come da proposta, e il via (2026-10-25) | §8.3 | 4-bis-bis |
| 4-bis-quater | ✅ team DB / **Tid** | Giro 6 scritto; `-37` … `-48` applicati da Tid (11:37); `-49` … `-52` scritti e provati in transazione; 22 pgTAP portati, regressione senza differenze | §8.4, §8.5 | 4-bis-ter |
| 4-bis-quinquies | ✅ **Tid** | Apply di `-49` … `-52` e corsa pgTAP: verdi (2026-10-25) | §8.4 | 4-bis-quater |
| 4-bis-quinquies-bis | ✅ team DB / **Tid** | Anticipati (Tid, 2026-10-25): concessioni trasferite a `emetti_preventivo` su dbdev (script del §8.9), `cambia_stato_preventivi` spenta nel CSV, migrate applicato | §8.9 | — |
| 4-bis-sexies | ✅ team BE | Richiesta §8.7 fatta: firma del verbo, 403 dalla riga (anche dalla pratica e su «Emetti»), lettori nuovi, rifiuto dell'emissione dal vocabolario su bolla, preventivo, contratto e ordine, controesempio. Non fatto il ritiro di `STATO_EMESSO`: manca il lettore del codice (richiesta al DB) | §8.10 | 4-bis-quinquies |
| 4-bis-sexies-bis | ✅ **Tid** | Commit del giro BE 6 (con la revisione critica, §8.10 punto 8) | §8.10 | 4-bis-sexies |
| 4-bis-sexies-ter | ✅ **Tid** | V-1 (lettore generico), V-2 (contratto, ordine e offerta nello stesso passaggio BE), V-3 (brief della nascita archiviato) | §8.11 | 4-bis-sexies |
| 4-bis-septies | ✅ team DB | Via di Tid (2026-10-25); giro DB di chiusura K-1 … K-6 scritto, provato in transazione su dbdev (8/8, presidio dei riferimenti morti 9/9) | §8.11 | 4-bis-sexies-ter |
| 4-bis-septies-bis | ✅ **Tid** | Apply di `20261025-70`, `-71` (dbdev, 15:27) e corsa pgTAP: verdi (2026-10-25) | §8.11 | 4-bis-septies |
| 4-bis-septies-ter | ✅ team DB | Censimento di cosa resta al cantiere, lato DB: elenco chiuso | §8.12 | 4-bis-septies-bis |
| 4-bis-septies-quater | ✅ **Tid** | W-1: l'ordine, **senza** l'ordine d'acquisto (acquisti tutti insieme, quando parte quel cantiere); ordine dei giri dopo: contratto, offerta, commessa, fattura, listino. W-2 e W-3: non ancora decise (W-2 torna come Z-3) | §8.12 | 4-bis-septies-ter |
| 4-bis-septies-quinquies | ✅ team DB | Giro 7, l'ordine: ricognizione, piano, domande | §9 | 4-bis-septies-quater |
| 4-bis-septies-sexies | ✅ **Tid** | Z-1 … Z-4 come da proposta, W-3 in un brief suo, via allo sviluppo | §9.3 | 4-bis-septies-quinquies |
| 4-bis-septies-septies | ✅ team DB / **Tid** | Giro 7 scritto (`-72` … `-82`, CSV), provato, applicato da Tid (15:59); 11 pgTAP portati, regressione letta | §9.4, §9.5 | 4-bis-septies-sexies |
| 4-bis-septies-octies | ✅ **Tid** | Migrazione applicata e corsa pgTAP verde (2026-10-25). Resta un dato: `emetti_ordine` ai profili su dbdev | §9.5, §9.6 | 4-bis-septies-septies |
| 4-bis-octies | ✅ team BE | Un passaggio solo, B-1 … B-6 del §8.11 e C-1 … C-6 del §9.6, fatto il 2026-10-25 | §9.7 | 4-bis-septies-bis |
| 4-bis-octies-bis | ✅ team BE | I due residui del §9.7: l'annullo dal vocabolario fatto; il «solo da DRAFT» sospeso su un difetto DB | §9.8 | 4-bis-octies |
| 4-bis-octies-ter | **Tid** ⏭️ | Commit del giro BE (`dev/backend-tid`); `emetti_ordine` ai profili su dbdev; via al team DB per il difetto X → X | §9.8 | 4-bis-octies-bis |
| 4-bis-octies-quater | team DB | Il verbo comune rifiuta il passaggio allo stesso stato (difetto del modello, priorità alta); il verbo della bolla risponde a uno stato sconosciuto come i gemelli | §9.8, §9.9 | 4-bis-octies-ter |
| 4-bis-nonies | **Tid** → team DB | Il via al giro 8: il contratto (ordine dei giri di W-1). Non aspetta il BE (§5) | §5 | 4-bis-septies-octies |
| 4-ter | ✅ team DB | Il lettore codice → id dello stato e la domanda intera, la colonna `emissione` col suo lettore: fatti nel giro 6 (`-37` … `-41`) | §8.4 | 4-bis |
| 4-quater | ✅ team BE | Ritirata la composizione SQL del repository, sui lettori nuovi; `STATO_EMESSO` passa a 4-bis-octies | §8.10 | 4-ter |
| 5 | ✅ **Tid** | Fermo dei temi trasversali **allentato** (2026-10-25, scelta C): ammesso il tema che poggia su un pezzo comune già fatto, fermo quello da ricopiare documento per documento; scritto in PROJECT_CONTEXT | — | 3-bis |
| 5-bis | **Tid** | Ereditati dalla grammatica unica (chiusa il 2026-10-25): D-G1, il blocco «origine» della stampa della fattura, da decidere nel giro della fattura; D-G2, la prova a video del lotto 2b | §10 | — |

Decisioni aperte di Tid: nessuna in questo brief (W-3 è passata a [brief-db-scadenza-preventivi](brief-db-scadenza-preventivi.md), E-1 … E-3); il difetto X → X va al team DB (§9.8). Da sapere (§8.10, §9.7): il cambio stato generico dell'ordine rifiuta CONFERMATO (M-2); `POST /ordini/<id>/conferma/` non c'è più (Z-2); senza `emetti_ordine` nessuno conferma un ordine. Lavoro da committare (`dev/backend-tid`): il giro BE del §9.7, §9.8 e §9.9.
Committati: il giro DB del §8.11 e il giro 7 (`2f66ca7bc`), il giro BE 6 (`dad26c37b`), il giro BE 5 (`4351164c1`), il giro DB 5 (`c3e34be02`), i giri 2-4 lato DB (`498cc8275`).

> **Chi scrive:** team DB (`dev/db-tid`), 2026-10-21. **A chi:** Tid; poi team DB e BE.
> **Origine:** D2 e D3 di [brief-be-verifica-documentazione-api](../work-done/brief-be-verifica-documentazione-api.md)
> (azioni di processo mancanti fra gemelli; permesso del cambio stato del DDT). Analizzandole sono
> uscite due proposte che, senza saperlo, contraddicevano una decisione viva e ne revocavano
> un'altra (§3.2). Tid: «non mi sto più fidando… una volta in un modo, poi in un altro, poi si torna
> al precedente». Da qui la ricostruzione della storia (§1) e questo brief.
> **Brief vicini verificati:**
> [brief-db-documento-nasce-nello-stato-iniziale](../work-done/brief-db-documento-nasce-nello-stato-iniziale.md)
> (stato iniziale e verbo: candidato a confluire qui, M-6);
> [brief-db-grammatica-unica-documenti](../work-done/brief-db-grammatica-unica-documenti.md) (solo i nomi dei
> tipi: resta suo); [brief-db-magazzino-tutte-le-scritture-dal-verbo](brief-db-magazzino-tutte-le-scritture-dal-verbo.md)
> (magazzino; rimanda «`vendite`, brief suo»: è **questo**).

---

## 1. Perché questo brief — i fatti, con la data

Ricostruzione del 2026-10-21 su git, brief chiusi e guide (finestra 2026-09-01 → 2026-10-21).
Sono fatti datati: servono a capire, non decidono la forma (Regola zero).

* **I ritorni indietro veri sono pochissimi** (1-3: partite merce per riga, ritirata lo stesso
  giorno per prestazioni; icona e severity nelle capability, aggiunte ad aprile e tolte il 27-28/09;
  la firma con `%TYPE` persa e rimessa). Nessun brief della finestra ha disfatto il lavoro di un
  altro.
* **La sensazione di girare in tondo ha un'altra causa: ogni concetto del documento esiste in una
  copia per documento.** 11 funzioni di capability (`script.fn_available_actions_*`), 11 guard di
  transizione, 8 verbi d'annullo (`fn_annulla_*`). Ogni regola nuova che vale per tutti i documenti
  va ricopiata in 6-9 posti.
* Nella finestra sono arrivati **27 temi trasversali** (perimetro emittente, congelamento prezzi,
  icone, fuso aziendale, cache dei piani, indirizzi, annullo con legami, testata dopo l'emissione,
  articoli ammessi, grammatica unica, modelli standard…), ciascuno applicato **un documento alla
  volta**: il 61% dei changeSet sui documenti. `fn_available_actions_offerta` è stata riscritta 12
  volte, ogni volta per una ragione diversa.
* **Non esiste un documento che fissi il modello comune.** Ci sono sei guide per documento
  (`gestione-preventivi.md`, `-ordini`, `-ddt`, `-contratti`, `-offerte-commerciali`, `-commesse`)
  che si dichiarano «gemelle», ma la gemellanza non è scritta da nessuna parte.

Rimedio deciso da Tid il 2026-10-21: il fermo dei temi trasversali (PROJECT_CONTEXT), la regola
«un tema, un brief» (AGENTS.md) e questo modello, scritto **una volta**.

---

## 2. Il modello com'è oggi (bozza della guida)

> Descrive lo stato attuale. Dove i documenti fanno in modo diverso, la differenza è nel §3.

### 2.1 Stati e transizioni

* Ogni documento ha un vocabolario di stati (`config.stati_doc_*`) e una **matrice delle
  transizioni** in tabella (`config.transizioni_stati_*`): una riga = un passaggio ammesso.
* Un trigger `trgfn_*_guard_transizione` rifiuta ogni passaggio che non è nella matrice.
* La stessa matrice, con il suo `meta` (`action_key`, `label_key`, `requires_confirm`, `manuale`),
  alimenta i bottoni: la funzione di capability del documento la legge e dice quali azioni sono
  disponibili e perché le altre sono spente.

### 2.2 Chi scrive lo stato: il verbo

* Direzione decisa il 2026-09-24 (D-1/D-2 di
  [brief-db-permesso-nel-verbo-di-scrittura](../work-done/brief-db-permesso-nel-verbo-di-scrittura.md),
  guida `architettura-permessi-e-autorizzazioni.md` §7.4): **una scrittura = un verbo**. I domini
  nuovi nascono così; quelli esistenti ci passano «quando un cantiere tocca le loro scritture».
* Per `vendite` il passaggio era rimandato a «un brief suo», mai scritto: è questo.

### 2.3 Chi può: il permesso

* Le operazioni CRUD chiedono il livello sull'area; le operazioni di **processo** (emetti, cambia
  stato, annulla, genera…) chiedono un'**azione di processo** (`config.azioni_processo`).
* La regola ha **una sede sola**, nel DB (`script.fn_check_azione_processo`), e **due punti in cui
  si applica**, voluti (guida §7.4, «il backend chiede, non decide due volte»): l'endpoint
  (`post_permission`, risponde 403 subito) e il verbo (`script.fn_guard_azione`).

### 2.4 L'emissione

* L'emissione è il passaggio che dà il numero e, dove il documento si stampa, genera il PDF
  (rotta `/emetti/`, fabbrica `build_documenti_sorgente_views`).

### 2.5 L'annullo

* Ogni documento ha un verbo d'annullo; un documento con **legami** a valle si annulla solo se chi
  conferma dichiara quanti legami ha visto (guard comune `trgfn_doc_guard_annullo_con_legami`,
  [brief-db-annullo-documento-con-legami](../work-done/brief-db-annullo-documento-con-legami.md)).

---

## 3. Dove i documenti divergono oggi

### 3.1 Tabella per documento (censimento del 2026-10-21)

| Documento | Cambio stato | Matrice | Azione di processo | Emissione | Annullo |
| --- | --- | --- | --- | --- | --- |
| Preventivo | verbo `fn_cambia_stato_preventivo` (senza guard d'azione) | tabella | `cambia_stato_preventivi`, solo backend | solo da `/emetti/` | `fn_annulla_preventivo` → verbo generale |
| Contratto | UPDATE dal backend | **nel codice del trigger**; la tabella la legge solo la capability | nessuna | solo da `/emetti/` | `fn_annulla_contratto`, UPDATE dentro di sé |
| Offerta | UPDATE dal backend; gli stati di partenza ripetuti in Python | tabella (nome fuori serie `stati_doc_offerte_transizioni`) | nessuna | `/emetti/` | da ACCETTATA via guard (`fn_check_offerta_annullabile`), forma diversa dall'annullo con legami |
| Ordine | UPDATE dal backend | tabella | nessuna | `/emetti/`, ma `/conferma/` e `cambia-stato` accettano CONFERMATO (scelta del 2026-06-05) | `fn_annulla_ordine`, UPDATE dentro di sé |
| DDT | verbo `fn_cambia_stato_ddt` per ogni transizione (dal 2026-10-13) | tabella | `emetti_ddt` (emissione, annullo dell'emesso) e `registra_magazzino` (consegna di un trasferimento): **nel corpo del verbo**; emissione controllata anche dal backend | `/emetti/`, ma `cambia-stato` accetta EMESSO (copiato dall'ordine) | `fn_annulla_ddt` → verbo generale |
| Reso | verbi `fn_conferma_reso` / `fn_annulla_reso` | tabella | `conferma_reso`, backend + verbo | conferma | verbo |
| Commessa | verbo `fn_cambia_stato_commessa` (senza guard d'azione) | tabella | `cambia_stato_commessa`, solo backend | push | `fn_annulla_commessa` → verbo generale |
| Versione di listino | UPDATE dal backend | **nel codice del trigger** e ricopiata in Python (`_validate_versione_state_transition`); stato testo con CHECK, senza vocabolario | nessuna | — | — |
| Fattura | funzioni della pipeline; stato del lotto con UPDATE | tabella | azioni della pipeline, solo backend | pipeline | reset del lotto |

Fuori vendita, stessa domanda: pagamenti (stato di distinte e righe, abbinamenti, sistemazioni:
nessuna azione; i verbi di registrazione senza guard) e magazzino (conferma/annullo dei documenti
interni: nessuna azione; la registrazione col guard nel verbo).

### 3.2 Due proposte del 2026-10-21 ritirate, e perché

* **«Il backend toglie `post_permission`, niente controllo doppio»**: contraddiceva §7.4 della
  guida dei permessi, decisione viva. Ritirata.
* **«EMESSO solo da `/emetti/` anche per il DDT»**: non è una regola nuova, **revoca** l'opzione (i)
  di [brief-ordini-stampa](../work-done/brief-ordini-stampa.md) §6.2 (2026-06-05), che il DDT ha
  copiato il 2026-07-11. Torna come decisione M-2.

### 3.3 Altro emerso dal censimento

* Azioni a catalogo che nessuno usa: `genera_fattura`, `approva_fattura`, `emetti_fattura`;
  `approva_rimessa` già spenta.
* Pratica: il cambio stato generico (`cambia_stato_pratica`) accetta ogni passaggio della matrice,
  compreso APERTA ↔ SOSPESA: si potrebbe sospendere senza `sospendi_pratica` e senza la riga di
  sospensione. **Da verificare**: non è ancora provato.
* Il commento di `listini_service._validate_versione_state_transition` cita un brief che non esiste
  (`brief-db-listini-stato-chiusa-sync.md`).

---

## 4. Decisioni per Tid — una volta, per tutti i documenti

| # | Domanda | Oggi | Note |
| --- | --- | --- | --- |
| M-1 | Ogni cambio di stato passa da un verbo DB con il guard d'azione (completare D-1/D-2 su vendite)? | 4 modelli diversi (§3.1) | ✅ **Deciso da Tid il 2026-10-24: A** — sì, come cantiere, un documento per giro e tutto intero; **dopo** M-2 … M-5, che dicono come dev'essere fatto il verbo |
| M-2 | L'emissione si fa **solo** da `/emetti/` (con PDF) per tutti i documenti che si stampano? | sì per preventivo e contratto (2026-05-28); no per ordine (2026-06-05) e DDT (copiato) | ✅ **Deciso da Tid il 2026-10-24: A** — solo da `/emetti/`, per tutti: numero e PDF nascono insieme, in una transazione (il DDT prende il numero al passaggio a EMESSO, trigger `trg_ddt_z10_gen_numero_emesso`). **Revoca** l'opzione (i) del 2026-06-05 (ordine) e la copia del DDT (2026-07-11). Primo passo del cantiere: censire chi emette o conferma senza passare da `/emetti/` (import, passaggi da altri documenti) e decidere per ognuno |
| M-3 | L'azione richiesta da un passaggio si dichiara **sulla riga della matrice**, letta dal verbo, dall'endpoint e dalla capability? | nel DDT è scritta nel corpo del verbo; altrove solo sulla view | ✅ **Deciso da Tid il 2026-10-24: A** — l'azione sta sulla riga del passaggio (riga senza azione = solo il permesso sul documento); la leggono il verbo (controllo), il backend (403 subito, senza deciderla da sé: il doppio punto di applicazione del 2026-09-24 resta) e le capability (bottone nascosto). Motivo di Tid: un punto unico è ciò che rende configurabili i permessi; sparso in nove documenti sarebbe ingestibile. **Supera** «gate per `action_key` nel service» (2026-07-27) e «permesso fuori dalle capability» (2026-08-04). Risponde a D3 |
| M-4 | Quante azioni per documento: una «cambia stato X» (come preventivo e commessa) o separate (emetti / annulla come DDT e reso)? | miste | ✅ **Deciso da Tid il 2026-10-24: A** — per ogni documento UNA azione sui passaggi pesanti (emissione e annullo di un emesso), «chi fa disfa», come DDT e reso; gli altri passaggi (spedito, accettato, rifiutato…) chiedono solo il permesso sul documento. **Il preventivo non fa eccezione** (Tid): accetta e rifiuta perdono `cambia_stato_preventivi`; lo stesso vale per la commessa. Separare l'annullo dall'emissione, se servira', e' un cambio di riga (M-3), non un cantiere |
| M-5 | Le matrici scritte nel codice (contratto, versione di listino) passano in tabella, e le copie Python si ritirano? | contratto e listino fuori dal modello | ✅ **Deciso da Tid il 2026-10-24: A** — il guard del contratto legge `config.transizioni_stati_contratti` (gli IF si ritirano); la versione di listino prende vocabolario degli stati e matrice dei passaggi come gli altri; si ritirano le copie Python (`listini_service._validate_versione_state_transition`, gli stati di partenza di `offerte_service._cambia_stato_manuale`). Condizione di M-3: senza righe in tabella l'azione non ha dove stare. Si fa nel giro del documento (M-1) |
| M-6 | [brief-db-documento-nasce-nello-stato-iniziale](../work-done/brief-db-documento-nasce-nello-stato-iniziale.md) confluisce qui? | aperto, non iniziato, stesso tema (stato e verbo) | ✅ **Deciso da Tid il 2026-10-24: A** — confluisce (§4-bis). Nascere già avanti e' un passaggio «dal nulla» che nessuna matrice ammette. Va **all'inizio** del cantiere: chiude un buco gia' provato (la bolla emessa, numerata e vuota) |

### 4-bis. Confluito: un documento nasce nel suo stato iniziale (ex D32, M-6)

Da [brief-db-documento-nasce-nello-stato-iniziale](../work-done/brief-db-documento-nasce-nello-stato-iniziale.md)
(2026-10-13), confluito il 2026-10-24. Il caso, la prova e il censimento da fare restano scritti
là (§1-§3); le decisioni si prendono qui.

* **Il caso.** Le regole per uscire dalla bozza stanno tutte sul passaggio di stato (`BEFORE
  UPDATE`). Nessuna dice in che stato un documento puo' NASCERE: un `INSERT` gia' avanti le salta.
  Provato il 2026-10-13 sulla bolla: nasce EMESSA, numerata e senza righe, e dopo le righe non si
  aggiungono piu'.
* **Le sue decisioni**, ora di questo brief:

| # | Domanda | Note |
| --- | --- | --- |
| N-1 | La regola: (a) un documento nasce solo nello stato iniziale e il resto passa dal verbo; (b) all'INSERT si applicano le condizioni della transizione dall'iniziale allo stato chiesto | ✅ **Deciso da Tid il 2026-10-24: (a)** — nasce solo nello stato iniziale (letto dal vocabolario degli stati, non scritto nel codice); chi ha bisogno di un documento gia' avanti lo crea in bozza e chiama il verbo nella stessa transazione. Coerente con M-1; (b) avrebbe due copie dei controlli. Prima: il censimento di §3 del brief d'origine (funzioni DB, backend, fixture pgTAP → `dbops.fn_pgtap_porta_a_stato`) |
| N-2 | Il perimetro e l'ordine | ✅ **Deciso da Tid il 2026-10-24: A** — **primo giro del cantiere**, su tutti i documenti con la matrice dei passaggi insieme: UNA funzione (building block) che legge lo stato iniziale dal vocabolario di ogni documento, montata su ciascuno. Non e' una regola ricopiata nove volte (la causa del §1): e' una sede sola. Prima, il censimento su tutti i documenti |
| N-3 | Il codice | ✅ **Deciso da Tid il 2026-10-24: A, un codice unico** — `E_DOC_STATO_INIZIALE_NON_VALIDO` (nome di Tid: dice quale regola e' violata; nessun codice simile nel catalogo, verificato), classe **TECNICO**: nessuna maschera crea un documento gia' avanti, e' un difetto di chi scrive. Frase che dice qual e' lo stato giusto, coi nomi che legge l'operatore (etichette, non codici di colonna): «Il %s non può nascere nello stato %s: un documento nuovo nasce in %s.». ⚠️ Se il censimento trova un'API che accetta lo stato dal client in creazione, li' e' DATO_ERRATO col campo `stato`, dichiarato |

### 4-ter. Censimento: chi crea un documento, e in che stato (2026-10-24)

Letto dal codice (corpi delle funzioni su dbdev, `backend/`, `db/pgtap/`), non dai dati. Perimetro:
le testate che hanno un vocabolario di stati in tabella — preventivo, offerta, contratto, ordine,
DDT, reso, commessa, fattura di vendita; e `acquisti.ordini` / `acquisti.ddt`, che usano gli stessi
vocabolari degli ordini e dei DDT di vendita.

**Scrittori DB: nessuno crea un documento già avanti.** Le 11 funzioni che inseriscono una testata
nascono tutte nello stato iniziale: `fn_create_contratto`, `fn_push_offerta_a_contratto`,
`fn_genera_ordine_da_offerta`, `fn_push_preventivo_a_ordine`, `fn_genera_ddt_da_ordine`,
`fn_genera_ddt_riconsegna`, `fn_crea_revisione_preventivo`, `fn_crea_revisione_offerta`,
`fn_get_or_create_fattura_header`, `fn_get_or_create_commessa` (dal DEFAULT di colonna) e
`script.fn_scrivi_riga_da_jsonb` (lo usa `fn_create_contratto`). Nessuno scrittore di `acquisti`.

**Backend: nessuna API accetta lo stato dal client in creazione** (`CREATE_KEYS_*` di ordini, DDT,
resi, offerte, preventivi, contratti). Il caso DATO_ERRATO di N-3 non si presenta. Lo stato
iniziale lo scrive il service, cercandolo **per nome** (`_STATO_BOZZA`, `StatoOfferta.BOZZA`,
`get_stato_bozza_id`) in cinque service; le versioni di listino nascono `BOZZA` (DEFAULT, e
letterale nel clone).

**Lo stato iniziale è scritto in 16 posti, e nessuno lo legge dal vocabolario:** i letterali `'DRAFT'`/
`'BOZZA'` nelle funzioni DB, i 5 service, il DEFAULT `1` (un id) di `vendite.commesse`. Il
vocabolario non lo dichiara: `fase = 'APERTO'` cade oggi su una riga sola per vocabolario, ma
nessun vincolo lo garantisce e la colonna dice un'altra cosa (la frontiera della genealogia).
Diversi pgTAP lo trovano come «il primo per id» o «il primo per `ordine`»: funziona per caso,
come dice la Regola zero. → **P-1**.

**`vendite.fatture.stato_doc_fiscale_id` è nullable e senza DEFAULT.** Una fattura può nascere
senza stato: lo fanno 27 INSERT pgTAP e 4 test Django di `pagamenti`. Le altre sette testate hanno
la colonna NOT NULL. → **P-2**.

**pgTAP: 52 file creano almeno un documento già avanti** (contratti 10, preventivi 17,
fatture 12, offerte 8, commesse 7, ordini 4; un file può contare per più documenti). Con la regola
diventano rossi.

* **Tre builder** fanno l'INSERT direttamente nello stato chiesto: `dbops.fn_pgtap_crea_ordine`,
  `fn_pgtap_crea_preventivo`, `fn_pgtap_crea_fattura`. Si riscrivono come
  `fn_pgtap_crea_contratto`, che crea in DRAFT e poi fa il passaggio, cioè la forma di N-1. I loro
  chiamanti fuori bozza: i tre presidi `dbops/test-fn-pgtap-crea-*` e
  `pagamenti/test-sistemazione-annullo-riporto.sql`.
* **`dbops.fn_pgtap_porta_a_stato`** conosce solo ordine e preventivo: va esteso a tutti i
  documenti, leggendo vocabolario e matrice. Passare dalla matrice vuol dire soddisfare le
  condizioni d'uscita dalla bozza (righe, indirizzi, causale…). È il lavoro grosso del giro: un
  preventivo «EMESSO» di fixture oggi nasce vuoto, e dovrà avere quello che un'emissione vera
  pretende.
* Un test **fissa il comportamento di oggi**:
  `vendite/test-contratto-attiva-spento-se-sovrapposto-v1.sql` riga 288 fa nascere un contratto
  ATTIVO e si aspetta `23P01`. Con la regola l'errore diventa quello di N-3.

I 52 pgTAP, per documento:

| Documento | File (sotto `db/pgtap/`) |
| --- | --- |
| Contratto | `dbops/test-fn-apply-chiusura-scadenze-v1`, `vendite/contratti/test_fn_successione_contratti`, `vendite/test-contratti-guard-transizione-stato-v1`, `vendite/test-contratto-attiva-spento-se-sovrapposto-v1`, `vendite/test-fn-list-contratti-da-pushare-v1`, `vendite/test-fn-resolve-iva-riga`, `vendite/test-testata-dopo-emissione-rdb-v1`, `vendite/test-vw-dash-aperto-v1`, `vendite/test-vw-dash-backlog-v1`, `vendite/test-vw-dash-fatturazione-v1` |
| Preventivo | `dbops/test-fn-pgtap-crea-preventivo-v1`, `pratiche/test-guida-avanza-esito-proiettato`, `pratiche/test-proiezione-stato-sorgente`, `pratiche/test-reconcile-tie-break-flusso-origine`, `script/test-fn-available-actions-preventivo-v1`, `script/test-trgfn-default-emittente-fiscale-v1`, `vendite/test-emissione-mirata-gruppi-fatturabili-v1`, `vendite/test-fatturazione-immediata-simmetria-sorgenti-v1`, `vendite/test-fn-crea-revisione-preventivo`, `vendite/test-fn-list-preventivi-da-pushare-v1`, `vendite/test-fn-list-preventivi-da-pushare-v2`, `vendite/test-fn-preventivo-ha-residuo-commessa-v1`, `vendite/test-vw-dash-aperto-v1`, `vendite/test-vw-dash-competenza-gruppi-riferimento-sorgente-v1`, `vendite/test-vw-dash-competenza-gruppi-v1`, `vendite/test-vw-dash-preventivi-revisione-attiva`, `vendite/test-vw-preventivi-superata-vs-abortito-v1` |
| Fattura | `dbops/test-fn-pgtap-crea-fattura-v1`, `pagamenti/test-sistemazione-annullo-riporto`, `vendite/test-fattura-guard-uscita-draft-v1`, `vendite/test-fattura-satelliti-lock-congelamento-v1`, `vendite/test-fondi-fattura-governo`, `vendite/test-fondi-fattura-lotto`, `vendite/test-fondi-fattura`, `vendite/test-fondo-fattura-cancellazione`, `vendite/test-fondo-fattura-eseguito`, `vendite/test-genera-scadenze-fattura-v1`, `vendite/test-snapshot-indirizzi-lotto-v1`, `vendite/test-snapshot-intestazione-fattura-v1` |
| Offerta | `script/test-fn-available-actions-offerta-v1`, `vendite/offerte_commerciali/test_fn_crea_revisione_offerta`, `vendite/offerte_commerciali/test_fn_push_offerta_a_contratto`, `vendite/offerte_commerciali/test_offerte_commerciali_state_machine`, `vendite/test-righe-esclusione-solo-non-si-vende-v1`, `vendite/test-testata-dopo-emissione-rdb-v1`, `vendite/test-vw-dash-backlog-v1`, `vendite/test-vw-dash-fatturazione-v1` |
| Commessa | `vendite/test-af-emessa-non-lockata-reset-e-riporto-v1`, `vendite/test-diagnostica-gruppi-fatturabili-v1`, `vendite/test-ordini-guard-transizione-v1`, `vendite/test-pull-non-prende-trattenuti-v1`, `vendite/test-select-perimetro-consegnato-v1`, `vendite/test-specchio-lane-diagnostica-v1`, `vendite/test-vw-commesse-attivita-emittibilita-v1` |
| Ordine | `dbops/test-fn-pgtap-crea-ordine-v1`, `script/test-trgfn-default-emittente-fiscale-v1`, `vendite/test-fn-list-ordini-da-pushare-v1`, `vendite/test-ordini-guard-transizione-v1` |
| DDT, reso | nessuno |

**Ricadute sul backend, da scrivere come richiesta al team BE** (lato DB non si toccano):

* `apps/vendite/tests/db/test_ricerca_liste_db.py:126` inserisce un preventivo EMESSO;
* `backend/scripts/tests/smoke-pratica-doc-sorgente-cross-emittente.py:331` inserisce un preventivo
  copiando lo stato di uno esistente, qualunque sia;
* i 4 test di `apps/pagamenti/tests/db/` che creano fatture senza stato dipendono da P-2;
* i 5 service che scrivono lo stato iniziale per nome dipendono da P-2 (se il DB lo mette da sé,
  quelle cinque copie si ritirano).

Fuori dal perimetro, per memoria: i documenti interni di magazzino (stato testo con DEFAULT `DRAFT`
e un loro guard di transizione), le sistemazioni dei pagamenti (stato testo, e **hanno già** la
regola della nascita nel loro guard: «un atto non nasce già fatto»), le versioni di listino (il
vocabolario arriva con M-5).

| # | Domanda | Note |
| --- | --- | --- |
| P-1 | Come dichiara il vocabolario qual è il suo stato iniziale? (a) colonna `iniziale boolean` su ogni vocabolario, con indice unico parziale (uno solo per vocabolario); (b) `fase = 'APERTO'` più un vincolo d'unicità; (c) lo stato senza passaggi in ingresso nella matrice | ✅ **Deciso da Tid il 2026-10-24: (a)** — colonna `iniziale` con indice unico parziale. (b) darebbe un significato nuovo a una colonna che ne ha già uno; (c) si rompe se la matrice ammette un ritorno alla bozza (la fattura ha già EMESSA → DRAFT). Tocca 8 vocabolari (i CSV di `80_data`) |
| P-2 | Se l'INSERT non dice lo stato (NULL), la regola (a) lo rifiuta o (b) mette lo stato iniziale? | ✅ **Deciso da Tid il 2026-10-24: (b)** — il DB mette l'iniziale quando manca e rifiuta ogni altro stato. Lo stato iniziale si scrive in un posto solo e le 16 copie si ritirano nello stesso giro (regola del 2): letterali nelle funzioni DB, i 5 service, il DEFAULT `1` della commessa. La colonna della fattura diventa NOT NULL. Con (a) le copie restano, e la fattura senza stato va trattata a parte |
| P-3 | Il perimetro: le 8 testate di vendita più `acquisti.ordini` e `acquisti.ddt`? | ✅ **Deciso da Tid il 2026-10-24: sì, anche acquisti** — stessi vocabolari, nessuno scrittore da adeguare. In più (Tid): **acquisti parte con tutto ciò che vendite ha imparato**, senza rifarne gli errori (§5). Magazzino, sistemazioni e listino restano fuori finché non hanno un vocabolario in tabella |

### 4-quinquies. Primo giro: applicato, test verdi (2026-10-24)

**I changeSet** (`20261024-07` … `-25`, nell'ordine):

| # | Cosa |
| --- | --- |
| `-07` | colonna `iniziale` sugli 8 vocabolari, indice unico parziale `uq_<voc>_iniziale`, CHECK `chk_<voc>_iniziale_attivo`, backfill per codice (P-1) |
| `-08` | `vendite.commesse.stato_commessa_id` perde il DEFAULT `1`; `vendite.fatture.stato_doc_fiscale_id` diventa NOT NULL (P-2) |
| `-09` | `script.fn_stato_iniziale_id(regclass)`: l'unico lettore dello stato iniziale |
| `-10` | il BB `script.trgfn_doc_stato_iniziale`: stato assente → lo mette; iniziale → passa; altro → `E_DOC_STATO_INIZIALE_NON_VALIDO` (N-1, N-3) |
| `-11`, `-12` | montaggio `trg_<tabella>_a05_stato_iniziale_ins` sulle 8 testate di vendita e sulle 2 d'acquisto (N-2, P-3) |
| `-13` … `-21` | le 9 funzioni che scrivevano `'DRAFT'`/`'BOZZA'` non lo cercano più; `fn_push_preventivo_a_ordine` legge lo stato delle righe con `fn_stato_iniziale_id` |
| `-22` | `dbops.fn_pgtap_porta_a_stato` vale per tutte le 8 testate (fattura compresa, solo coi passaggi che il guard della fattura singola ammette) |
| `-23` … `-25` | i builder pgTAP di ordine, preventivo e fattura fanno nascere in bozza e portano avanti per la matrice (la fattura scrive prima gli snapshot di indirizzi e intestazione, come la pipeline) |

Dati: colonna `iniziale` in coda agli 8 CSV dei vocabolari, dichiarata nei 10 mirror che li caricano;
il codice `E_DOC_STATO_INIZIALE_NON_VALIDO` (TECNICO) in `messaggi_errore.csv` e `codici_errore.csv`.
La frase di N-3 diventa «Il documento %s non può nascere…»: il nome viene da
`config.sorgenti.etichetta` («Offerta», «Commessa»), e «Il Offerta» non si legge.
Doc: `docs/it/dbzero/script/manual/trgfn_doc_stato_iniziale.md`.

**Le copie ritirate nello stesso giro** (regola del 2): i letterali nelle 9 funzioni e il DEFAULT
`1` della commessa. Restano i 5 service del backend: richiesta qui sotto.

**pgTAP.** Nuovo `script/test-trgfn-doc-stato-iniziale-v1.sql` (18 test: il montaggio si ricava dal
catalogo, quindi una testata nuova senza il trigger fa rosso). Portati alla nascita in bozza i 52 file
del censimento più il presidio del builder dell'ordine (48 file toccati). Attese cambiate, dichiarate:

* `vendite/test-contratto-attiva-spento-se-sovrapposto-v1.sql` test 19: il contratto «nato ATTIVO»
  si aspettava 23P01 dall'EXCLUDE, ora `E_DOC_STATO_INIZIALE_NON_VALIDO`. Il 23P01 non si raggiunge
  più per nessuna strada lecita (prima lo ferma la nascita, poi il guard di transizione): l'EXCLUDE
  resta provato nella forma (test 21-23);
* `vendite/test-testata-dopo-emissione-rdb-v1.sql`: test 37 nuovo (un contratto non nasce ATTIVO),
  piano 37;
* `dbops/test-fn-pgtap-crea-ordine-v1.sql`: il test 5 chiede ANNULLATO invece di CONFERMATO, e il
  test 10 nuovo fissa che un CONFERMATO senza righe lo ferma il guard vero, piano 10.

**Come è provato** (scratch `zeroerp_ruoli`, SQL estratto dai changeSet in transazione annullata,
come owner):

* regressione su 152 file (i 52 del censimento, gli 81 che chiamano le funzioni riscritte, 28
  presidi trasversali, il test nuovo): **109 verdi, 43 rossi identici a prima** (stesso conteggio,
  stesso errore: debiti di fixture preesistenti, per lo più «il primo billing account del
  database», che sullo scratch non c'è), **nessuna regressione**;
* per i file fermi su quei debiti il percorso nuovo è stato provato su copie con il mondo costruito
  dai builder (nello scratchpad della sessione, non nel repo);
* `plpgsql_check` senza errori sulle 11 funzioni; nessun doppione di firma; i guardrail statici e i
  due SQL della CI (`codice_errore_strutturato`, `riferimenti_morti`) verdi;
* i 10 mirror ricaricati per intero (57 righe) sopra i trigger di oggi, nella forma del loader
  (UPDATE, poi INSERT se manca): passano;
* ✅ applicato da Tid il 2026-10-24 su dbdev e scratch, corsa pgTAP verde (come applicazione, RLS
  attiva). Due file che pescano dati veri, rossi solo su dbdev, corretti nella stessa giornata:
  `test-fondi-fattura-governo` (Q-1) e `test-fn-resolve-iva-riga` (il contratto clonato senza listino
  prende una riga AGGIUNTA, con l'articolo scelto da `catalogo.fn_articoli_ammessi`).

**Aperti, per Tid:**

* ✅ **Q-1. Una fattura ANNULLATA il modello non la sa costruire** — **deciso da Tid il 2026-10-24:
  B**, il modello resta com'è. DRAFT → ANNULLATA c'è solo coi passaggi del lotto (`solo_lotto`), e
  l'annullo del lotto cancella le fatture. `vendite/test-fondi-fattura-governo.sql` (D-1/D-9) faceva
  nascere una sorgente ANNULLATA: ora è una sorgente **EMESSA**, perché la regola provata è «genera e
  propone solo una fattura DEFINITIVA» ed EMESSA è il caso più stretto (uscita dalla bozza,
  completa, lo stato subito prima). Provato su una variante col mondo costruito, sullo scratch già
  applicato: i due test verdi, file 29/30 (il rosso è il test 2, preesistente).
* ✅ **Q-2. Builder di fixture ripetuti** (regola del 2, proposti dal porting, non scritti): commessa
  emittibile (6 file), fattura «fuori bozza ma senza snapshot» (4 file), contratto figlio di
  un'offerta e contratto ATTIVO sul billing account del test (4 file). **Deciso da Tid il
  2026-10-24: A** — tre builder in `dbops`, e i 14 file passano a usarli nello stesso giro: le copie
  scrivono a mano la strada d'uscita dalla bozza, la stessa che questo giro ha accentrato.
* ✅ **Q-3.** `vendite/test-snapshot-indirizzi-lotto-v1.sql` rimette `DEFERRED` i soli tre trigger di
  coerenza lotto/fatture (il file era escluso dai differiti per quel guard, e
  `fn_pgtap_porta_a_stato` esce con `IMMEDIATE`). **Deciso da Tid il 2026-10-24: B** — si cura il
  debito invece di aggirarlo: la fixture allinea lo stato delle fatture a quello del lotto prima di
  chiudere, il `SET CONSTRAINTS … DEFERRED` si toglie, il file gira tutto `IMMEDIATE` e il guard di
  coerenza viene esercitato (la correzione è quella già scritta in testa al file, debito di
  brief-db-pgtap-runner-rls-baseline §22).
* ✅ **Q-4.** I debiti «primo billing account» (una decina di file) si curano col mondo costruito.
  **Deciso da Tid il 2026-10-24: dentro questo giro**, non a parte: insieme ai builder di Q-2.
* Fuori da questo giro: `dbops/test-automazioni-guasto-ambiente-rilanciato-v1.sql` è rosso nel
  guardrail del preambolo già in HEAD (commit `dbb810c3d`).

**Richiesta al team BE** (si accetta che qualcosa resti rotto fino al loro giro, §5):

1. rigenerare `apps/core/services/error_policies_generated.py`
   (`manage.py genera_error_policies`): codice nuovo `E_DOC_STATO_INIZIALE_NON_VALIDO`, TECNICO;
2. i 5 service che scrivono lo stato iniziale per nome (`ordini_service`, `ddt_service`,
   `resi_service`, `offerte_service`, `preventivi_service`, con i loro repository) smettono di
   passarlo: il database lo mette da sé (P-2). Le cinque copie si ritirano;
3. `apps/vendite/tests/db/test_ricerca_liste_db.py:126` inserisce un preventivo EMESSO: va creato
   in bozza e portato avanti;
4. `backend/scripts/tests/smoke-pratica-doc-sorgente-cross-emittente.py:331` copia lo stato di un
   preventivo esistente: va creato in bozza;
5. i 4 test di `apps/pagamenti/tests/db/` che creano fatture senza stato continuano a funzionare
   (lo stato lo mette il database): nessuna modifica, da sapere.

**Fatto dal team BE** (2026-10-24, `dev/backend-tid`, da committare):

1. `error_policies_generated.py` rigenerato (`--check` pulito, il codice è nel CSV in git) e la
   frase di ripiego in `error_messages_fallback.py`, senza segnaposto;
2. i 5 service non cercano più lo stato iniziale e i loro repository non lo scrivono: tolti il
   parametro di `create_ordine` / `create_ddt` / `create_reso` / `create_preventivo`, la colonna
   dalla whitelist d'inserimento delle offerte (`TESTATA_CREATE_COLUMNS`),
   `PreventiviRepository.get_stato_bozza_id` e `ResiRepository.get_stato_id_by_codice`, che non
   avevano altri chiamanti;
3. `test_ricerca_liste_db`: il preventivo nasce in bozza e va a EMESSO con
   `dbops.fn_pgtap_porta_a_stato`; contratto e offerta della stessa fixture non scrivono più lo stato;
4. `smoke-pratica-doc-sorgente-cross-emittente.py`: oltre a non copiare lo stato, costruisce **anche**
   il documento di casa (prima: «il primo preventivo dell'emittente», in qualunque stato). Lo smoke
   pretende che i due documenti abbiano lo stesso stato, perché la regola dell'ancora ordina anche
   sulla terminalità: con l'estraneo in bozza e quello di casa ANNULLATO vinceva il vivo, e il test
   misurava la terminalità invece del perimetro. Ora pareggiano per costruzione;
5. emersi dalla corsa e non in richiesta: tre test DB di creazione (`test_{ordini,ddt,resi}_create_db`)
   che passavano lo stato al repository; lo smoke bash `smoke-test-guida-inversione-preventivi.sh`,
   che faceva nascere un preventivo EMESSO (ora in bozza + `fn_pgtap_porta_a_stato`); l'etichetta
   `config_panel.campi.iniziale` in it/en per la colonna nuova dei vocabolari (presidio
   `test_config_panel_registro_db`);
6. revisione critica del giro (2026-10-24), su questo stesso diff:
   * presidio simmetrico sui 5 service: ordini e preventivi non avevano, come DDT, offerte e resi,
     l'asserzione che lo stato **non** arrivi al repository. Col repository mockato un
     `stato_doc_*_id` rimesso dal service sarebbe passato muto; aggiunta in `test_ordini_service` e
     `test_preventivi_service`;
   * `ResiRepository.get_stato_id_by_codice` ritirato (ok di Tid): l'unico chiamante era la
     creazione del reso. Tolta con lui l'asserzione `assert_not_called()` di `test_resi_service`,
     che senza il metodo non provava più niente;
   * smoke cross-emittente: `crea_preventivo` legge da sé il `soggetto_ruolo` dell'emittente (prima
     due letture diverse, una per «casa» e una per «estraneo»); l'esito stampa la **coda** dell'uid
     (`uid_breve`) e non la testa: gli uid sono UUIDv7, i primi caratteri sono il timestamp, e i due
     documenti nati nello stesso giro stampavano lo stesso prefisso. I `check` confrontavano già
     l'uid intero: era la diagnostica a non distinguerli, non l'esito;
   * `config_panel.campi.iniziale` rimessa in ordine alfabetico in it/en.

   Provato: `manage-test.sh` vendite/core/config verde; con `ZEROERP_TEST_DB_E2E=1` i test DB di
   vendite e config verdi sul DB reale (senza la variabile sono skippati: un verde senza non prova
   niente); `genera_error_policies --check` allineato; lo smoke cross-emittente TUTTO VERDE. ⚠️ Non
   eseguito: `smoke-test-guida-inversione-preventivi.sh` (vuole il login HTTPS col secondo fattore);
   il suo pezzo nuovo, `fn_pgtap_porta_a_stato` dal ruolo app, è esercitato da `test_ricerca_liste_db`.

Restano fixture di test che scrivono lo stato iniziale esplicito (`DRAFT`/`BOZZA`) in un INSERT: il
trigger le fa passare, e non sono copie della regola in codice di prodotto.

### 4-sexies. Secondo giro: Q-2 … Q-4 (2026-10-24)

**Verifica del giro BE, prima di partire.** Il commit `993dd7150` (PR #1936) fa i punti 1-5 della
richiesta: nessun service passa più lo stato in creazione. I `get_stato_id_by_codice` rimasti servono
al cambio di stato (giro M-1), non alla nascita.

**La scelta (Tid, 2026-10-24: «estendi i builder esistenti»).** Due dei tre builder proposti in Q-2
esistevano già in parte (`fn_pgtap_crea_commessa` + `_commessa_attivita`; `fn_pgtap_crea_contratto` con
ATTIVO e BA): un builder nuovo accanto sarebbe stato una seconda copia. Si estendono i tre esistenti,
parametri in coda, DROP + CREATE:

| # | Builder | Cosa aggiunge |
| --- | --- | --- |
| `-26` | `dbops.fn_pgtap_crea_commessa` | stato da raggiungere (per la matrice), BA del test (verificato dal BB), `p_con_attivita` (di default solo fuori bozza: l'uscita la pretende); RETURNS + `attivita_id`, `stato_commessa_id`. La sorgente ROOT resta del test |
| `-27` | `dbops.fn_pgtap_crea_fattura` | `p_spoglia_indirizzi`, `p_spoglia_intestazione`: la fattura si spoglia nell'ultimo stato non congelato del percorso (`congela_fiscale`, letto dal vocabolario: oggi EMESSA), poi arriva allo stato chiesto. Il COMMENT, stantio dal `-25`, riscritto |
| `-28` | `dbops.fn_pgtap_crea_contratto` | `p_offerta_id`: il figlio nasce dalla push `vendite.fn_push_offerta_a_contratto` (in produzione nasce solo così; `fn_create_contratto` non accetta l'offerta), sul cliente dell'offerta. Annullato, dichiara i legami da `vendite.fn_documento_legami`, come il backend |

Presidi estesi: commessa 6 → 11 test, fattura 8 → 12, contratto 8 → 11. Doc: le tre pagine `manual` e
la tabella dei builder in `pgtap-come-si-scrive-un-test.md` (era ferma a «stato scelto alla nascita»).

**I 28 pgTAP portati** (porting in cinque gruppi):

| Gruppo | File | Prima | Dopo |
| --- | --- | --- | --- |
| Commessa emittibile (Q-2) | `af-emessa-non-lockata-reset-e-riporto-v1`, `pull-non-prende-trattenuti-v1`, `select-perimetro-consegnato-v1`, `specchio-lane-diagnostica-v1`, `vw-commesse-attivita-emittibilita-v1`, `ordini-guard-transizione-v1` (solo la testata), `diagnostica-gruppi-fatturabili-v1` (+Q-4) | 6 verdi, 1 rosso | 7 verdi |
| Fattura senza snapshot (Q-2, Q-3) | `fattura-guard-uscita-draft-v1`, `snapshot-intestazione-fattura-v1`, `snapshot-indirizzi-lotto-v1`, `fattura-satelliti-lock-congelamento-v1` | 1 verde, 3 rossi | 4 verdi |
| Contratto e dashboard (Q-2, Q-4) | `vw-dash-backlog-v1`, `vw-dash-fatturazione-v1` (il figlio dalla push), `vw-dash-aperto-v1`, `dbops/test-fn-apply-chiusura-scadenze-v1`, `vw-dash-competenza-gruppi-v1`, `vw-dash-competenza-gruppi-riferimento-sorgente-v1`, `emissione-mirata-gruppi-fatturabili-v1` | 2 verdi, 5 rossi | 7 verdi |
| Preventivi (Q-4) | `fn-crea-revisione-preventivo`, `fn-list-preventivi-da-pushare-v1`, `-v2`, `vw-dash-preventivi-revisione-attiva`, `vw-preventivi-superata-vs-abortito-v1` | 5 rossi | 5 verdi |
| Fondi fattura (Q-4) | `fondi-fattura`, `fondi-fattura-lotto`, `fondo-fattura-cancellazione`, `fondo-fattura-eseguito`, `fondi-fattura-governo` (anche il test 2, rosso da prima del giro) | 5 rossi | 5 verdi |

**Attese cambiate, dichiarate nei file.** Nessun valore atteso delle asserzioni sul caso. Cambiano le
asserzioni di fixture (il test 0 o il test 2), che contavano le righe delle temp table o pescavano il
catalogo: ora contano le righe costruite, nella forma voluta. In `vw-dash-preventivi-revisione-attiva`
e `vw-preventivi-superata-vs-abortito-v1` il test 2 pescava «il primo OPERATORE» e riscriveva la sua
whitelist: ora è l'operatore del mondo, e l'asserzione è più stretta.

**Come è provato** (scratch `zeroerp_ruoli`, come owner):

* prima dell'apply: SQL estratto dai tre changeSet in transazione annullata; nessun doppione di firma,
  EXECUTE all'app, `plpgsql_check` pulito, i due SQL della CI (`riferimenti_morti`,
  `codice_errore_strutturato`) e i guardrail statici verdi; i 33 chiamanti dei tre builder identici
  prima e dopo;
* dopo l'apply di Tid (22:31): 64 file (i 28 portati, i 4 presidi, i 33 chiamanti), **63 verdi**;
  l'unico rosso, `test-annullo-documento-con-legami-v1` (29/30), è identico a prima del giro;
* ⚠️ non provato come app: la corsa di Tid. `test-diagnostica-gruppi-fatturabili-v1` gira come app
  (senza marcatore owner).

**Aperti, per Tid:**

* **R-1 (Q-3): la «definitiva» dentro il lotto in bozza.** La decisione diceva «la fixture allinea lo
  stato delle fatture a quello del lotto prima di chiudere». Non si può: il caso del file (test 3, 4,
  8) È una fattura DEFINITIVA in un lotto DRAFT, e una DEFINITIVA non torna in bozza; coi vincoli
  IMMEDIATE l'incoerenza scatta già all'INSERT del ponte. Il guard di coerenza ammette fuori passo solo
  le fatture `critical`. Il porting l'ha fatta entrare nel lotto **già ferma**: una segnalazione `C`
  in `vendite.fatture_log` (il flag lo accende il trigger z90 vero, non la fixture); il giro la salta
  per lo stato, non per il flag, quindi i test misurano la stessa cosa. DEFERRED tolto, file tutto
  IMMEDIATE, guard esercitato (controprova: senza la segnalazione il file si ferma sul guard).
  ⚠️ Se «la definitiva non ferma le altre» deve valere anche per una fattura NON critical, è il guard
  di coerenza a non ammetterlo: è un tema di modello, non di fixture. Da confermare.
* **Candidati a builder** (fixture ripetute che nessun builder copre; non scritti):
  * R-2: contratto ATTIVO con periodo e listino del test (bozza dal builder, UPDATE di date/listino,
    poi la matrice), 5 file delle dashboard;
  * R-3: la sorgente ROOT della commessa, 3 file;
  * R-4: il lotto DRAFT di fixture con l'esito che lo trattiene, 5 file;
  * R-5: il blocco «mondo + registro + catalogo» dei fondi (in pratica `fn_pgtap_crea_fattura` senza
    la fattura), 4 file; e `fn_pgtap_crea_fattura` non prende `minimo`, `totale_a_pagare`,
    `termine_pagamento_id`: le quattro fatture dei fondi restano INSERT a mano;
  * R-6: revisioni di preventivo con numero e rev fissati; `fn_pgtap_crea_preventivo` non accetta né
    restituisce il numero;
  * R-7: un secondo BA sullo stesso ruolo, su un'istanza nuova (`snapshot-indirizzi-lotto` lo scrive
    con `anagrafiche.fn_crea_billing_account` in una finestra differita);
  * R-8: un cliente senza indirizzi d'ambito FATTURA (i builder scrivono sempre il FATT generico);
  * R-9: il blocco «mondo + operatore + whitelist riscritta» delle dashboard.
* **Difetti dei builder, non corretti:** con il BA del test, `fn_pgtap_crea_commessa` e
  `fn_pgtap_crea_contratto` costruiscono comunque un cliente che non usano (chiamano
  `fn_pgtap_crea_mondo_cliente` prima): innocuo, ma le viste globali vedono un cliente in più. Il
  COMMENT di `fn_pgtap_crea_preventivo` è fermo a prima del `-24` («stato scelto alla nascita»).
  `fn_pgtap_crea_preventivo` e `fn_pgtap_crea_fattura` scelgono valuta e tipo documento «il primo per
  id». L'attività di `fn_pgtap_crea_commessa_attivita` ha `valuta_id` NULL (le fixture a mano la
  valorizzavano).

**Residui fuori dal giro** (debito noto, non curato qui):

* `test-ordini-guard-transizione-v1`: la fixture dell'ordine pesca ancora emittente e soggetto «il
  primo per id»;
* le commesse di `vw-dash-aperto`, `-backlog`, `-fatturazione` nascono ancora da INSERT a mano;
* `CANONE_NON_GENERATO`: il commento e il test 10 di `vw-dash-backlog` lo dichiarano, ma nessuna vista
  né funzione lo produce (c'è solo nel seed di `config.motivi_fermo`). Il test resta vero per un altro
  motivo (il contratto è fuori dal backlog);
* rossi sullo scratch per la pesca del primo BA, NON portati in questo cantiere: `test-fatturazione-
  reset-lotto-draft`, `test-fatture-atti-v1`, `test-resi-rinunce-scenario-v1`,
  `test-vw-preventivi-smistamento-v1`, `test-genera-scadenze-lotto-v1`, `test-arrotondamento-ambito-
  idempotenza-v1`, `test-chiave-fattura-tre-specchi-v1`, `test-data-documento-v1`,
  `test-fn-push-preventivo-a-ordine-v1` (esito del primo giro, §4-quinquies);
* altri debiti di fixture visti nel primo giro: articolo-onere pescato
  (`fn-preventivo-ha-residuo-commessa-v1`), `fn-resolve-iva-riga`, `proiezione-stato-sorgente`,
  `test_fn_successione_contratti`. Gli articoli-onere non si costruiscono (`causale_onere_id` UNIQUE,
  le 5 causali hanno l'articolo nel seed): si leggono per causale.

**Richiesta al team BE** (⚠️ firme aggiornate dal §4-septies, che le cambia di nuovo):

1. due test Django sondano la firma VECCHIA dei builder con `richiedi_db_provvisto`, e con la firma
   nuova **saltano in silenzio** (verde per sottrazione). Le firme FINALI, dopo il §4-septies, sono
   `dbops.fn_pgtap_crea_commessa(text,character varying,bigint,boolean,boolean)` e
   `dbops.fn_pgtap_crea_fattura(text,character varying,bigint,boolean,boolean,boolean,numeric,bigint,boolean)`
   (rev §4-octies, `-42`; le righe qui sotto sono quelle del secondo giro, superate):
   * `apps/vendite/tests/db/test_prezzo_riga_commessa_db.py:133`:
     `"dbops.fn_pgtap_crea_commessa(text)"` → `"dbops.fn_pgtap_crea_commessa(text,character varying,bigint,boolean)"`;
   * `apps/core/tests/db/test_scritture_email_note_db.py:109`:
     `"dbops.fn_pgtap_crea_fattura(text,character varying,bigint)"` → `"dbops.fn_pgtap_crea_fattura(text,character varying,bigint,boolean,boolean)"`;
2. nessun'altra ricaduta: i chiamanti BE (2 test Django, 3 smoke) passano al più tre argomenti e
   restano validi.

### 4-septies. Terzo giro: i debiti emersi e le decisioni R-1 … R-9 (2026-10-24)

Tid, 2026-10-24: «i debiti emersi vanno risolti»; R-1 sì (regola sotto), R-2, R-3, R-4, R-5 sì, R-6 e
R-9 come consigliato, R-7 e R-8 non ora (regola del 2: una copia sola).

**I debiti emersi, chiusi:**

* `CANONE_NON_GENERATO` non era un difetto del database: dal `20260707-03` i contratti non hanno un
  motivo di fermo finché non esiste il push ricorrente, e il codice resta nel seed **apposta**. Era il
  test (`vw-dash-backlog`, test 10 e commento) a dichiarare il motivo sbagliato: corretto;
* il COMMENT di `fn_pgtap_crea_preventivo` e quello di `fn_pgtap_crea_ordine` (fermi a prima del
  `-23`/`-24`): `20261024-29`, solo testo; e le due pagine `manual`;
* `test-ordini-guard-transizione-v1` e i nove file rossi «fuori giro» del §4-sexies: mondo costruito,
  tutti verdi; più altri otto rossi da pesca trovati nella regressione (articolo-onere, BA, chiave di
  sorgente, IVA) e `test-guard-lotto-fatture-stato-coerente` (il test del guard di coerenza, rosso dal
  test 1 per il primo BA: non provava niente);
* nove file con un solo rosso, diagnosticati (non toccati): **tutti dipendono dal ruolo** (l'owner dello
  scratch salta la RLS; come app sono verdi per costruzione). Nei quattro che non lo dichiaravano
  l'avviso è nel titolo del test.

**R-1, la regola di Tid:** «se un documento è in errore o in uno stato bloccante, gli altri non possono
passare a uno stato definitivo: prima i documenti non conformi si tolgono dal lotto; non può esistere un
documento definitivo se un altro dello stesso lotto è in errore». Completa D-Q (2026-07-31: «il lotto
NON avanza»), non revoca niente. Provato il 2026-10-24 che il DB **non** la applicava: lotto e fattura
sana DEFINITIVA, fattura in errore DRAFT nello stesso lotto; lo stop stava solo nel runner BE.

**I changeSet** (tutti `dbops` salvo `-34`/`-35`):

| # | Cosa |
| --- | --- |
| `-29` | COMMENT di `fn_pgtap_crea_preventivo` / `_ordine` allineati alla nascita in bozza |
| `-30` | `fn_pgtap_porta_a_stato` conosce il lotto di fatturazione (vuoto; con fatture si muove col verbo `fn_sync_lotto_fatture_stato`) |
| `-31` | NUOVO `fn_pgtap_crea_lotto` (R-4): dalla madre `fn_create_fatturazione_lotto`, stato per la matrice, esito che trattiene un gruppo |
| `-32` | `fn_pgtap_crea_commessa` + `p_con_sorgente_root` (R-3) |
| `-33` | `fn_pgtap_crea_contratto` + periodo, data e listino del test (R-2) |
| `-34` | (R-1 b) `vendite.vw_lotti_fatture_incoerenti` diventa la **sede unica** dell'invariante lotto ↔ fatture e il guard la legge (prima ripetevano lo stesso predicato); l'eccezione critical vale per chi resta **indietro**, non per una fattura già congelata davanti a un lotto non congelato |
| `-35` | (R-1 a) `vendite.trgfn_fatturazione_lotti_guard_stato`: un lotto FERMO (`vw_lotti_segnalazioni_summary.fermo`, la sede del runner) non entra in uno stato congelato e non abortito: `E_PIPELINE_LOTTO_CRITICAL`, lo stesso codice del runner; l'annullo resta ammesso |
| `-36` | `fn_pgtap_crea_fattura` + `minimo`, `totale_a_pagare`, `termine_pagamento_id` alla nascita (R-5) |

Dati: nota di `E_PIPELINE_LOTTO_CRITICAL` (`codici_errore.csv`, chi la solleva) e causa di
`E_LOTTO_FATTURE_STATO_INCOERENTE` (`messaggi_errore.csv`, citava ancora `esclusa`). Censimento di chi
muove i lotti: `fn_riporta_lotto_a_draft` cancella le fatture prima; la sync e la chiusura del
giornaliero lasciano INDIETRO le critical; l'annullo va in uno stato abortito; nel giro vero il runner
legge lo stesso verdetto prima di `update_lotto_stato_doc`. Nessuno produce il caso vietato.

Presidi: nuovi `dbops/test-fn-pgtap-crea-lotto-v1` (9) e `vendite/test-lotto-fermo-non-diventa-definitivo-v1`
(8: **rosso senza** i due guard, verde con; prova anche l'annullo e il rilancio che sblocca); estesi
commessa (13), contratto (14), fattura (14). Doc: le `manual` dei builder, di `porta_a_stato`, dei due
guard e della vista, la tabella dei builder della guida pgTAP.

**Porting** (agenti in parallelo, ogni file riprovato a mano): sorgente ROOT e lotto nei builder (11
file), dashboard con contratto col periodo, mondo costruito e commesse dal builder (7), revisioni dei
preventivi per la strada del dominio (2), pesca residua (12), test di coerenza. Attese cambiate,
dichiarate nei file: il codice del lotto in `diagnostica-gruppi-fatturabili` (test 13: quello della
madre, non `PGTAP-DG-LOTTO`); numeri di preventivo e di contratto letti dal dominio invece che fissi;
in `test_fn_successione_contratti` i casi 3 e 6 erano verdi per sottrazione (`is(NULL, NULL)`).

**Come è provato:** regressione prima/dopo su 134 file (builder `-29`…`-33`) e su 163 file (`-34`…`-36`):
nessuna regressione; le sole differenze sono i presidi nuovi e i due file del trucco «definitiva
critical nel lotto» (sotto). ⚠️ Tid ha applicato `-26`…`-28` alle 22:31 e `-29`…`-33` alle 23:02 mentre
le prove giravano: da lì le misure sono «senza». `-34`…`-36` applicati da Tid alle 23:26 (dbdev e scratch).

**Aperti / in corso:**

* ✅ `test-snapshot-indirizzi-lotto-v1` e `test-genera-scadenze-lotto-v1` provavano «la definitiva nel
  lotto in bozza non si tocca» costruendo una definitiva critical agganciata al lotto: con R-1 quel mondo
  non esiste. Il ramo che la salta resta nelle funzioni come **difesa dichiarata, non provata** (Regola
  zero). Diventano `skip` motivati il 4 e l'8 di indirizzi-lotto e il 4 di genera-scadenze (l'8 prova un
  critico di un altro task, e resta); attese aggiornate, dichiarate: indirizzi-lotto 2, 3, 9 (nessuna
  saltata), genera-scadenze 1 (nessuna oltre soglia, e le due in bozza contate davvero). Verdi con e senza
  i changeSet;
* ✅ i cinque pgTAP dei fondi passano a `fn_pgtap_crea_fattura` con i tre valori di R-5: verdi col `-36`.
  ⚠️ **Senza il `-36` non girano** (chiamano il builder a otto argomenti): dopo l'apply. Restano a mano le
  tre fatture la cui utility è il caso del test (diversa dal BA, o vuota): candidato `p_utility_id`;
* ✅ il marcatore `pgtap-contesto` nei tre file della pesca residua che aprono il contesto col mondo;
* **candidati a builder**, non scritti (regola del 2, decide Tid): due fixture ripetute in 3 file
  ciascuna (coppia di articoli MERCE + SERVIZIO; scheda precontrattuale della fornitura); l'attività di
  commessa «di push» (chiave del preventivo, stato di emissione) in 2 file; più gruppi trattenuti dallo
  stesso lotto (1 file); `p_iva_id` in `fn_pgtap_crea_articolo` (1 file); `listino_versione_id` e
  variazione globale nel contratto (1 file);
* **difetto comune dei builder**, da decidere: con il BA del test, commessa, contratto, fattura, ordine e
  lotto costruiscono comunque un cliente che non usano (chiamano `fn_pgtap_crea_mondo_cliente` prima).
  La cura è un BB «l'azienda del contesto» per quando il BA arriva dal test: tocca cinque builder;
* il guardrail del preambolo riconosce il contesto solo da `fn_pgtap_set_contesto_operatore(`: quattro
  dashboard tengono una riga ridondante per lui.

### 4-octies. Quarto giro: il pezzo comune e i builder delle fixture ripetute (2026-10-24)

Tid, 2026-10-24: «sul da decidere procedere ai miglioramenti: pezzo comune / builder quando ripetuti».
Criterio, quello dei builder del progetto: **entra ciò che ha una trappola d'ordine o ricopia una regola
del dominio, non ciò che serve spesso**; e alla seconda copia (regola del 2), con le copie ritirate nello
stesso giro.

| # | Cosa |
| --- | --- |
| `-37` | NUOVO `dbops.fn_pgtap_azienda_di_chi_agisce`: l'azienda del contesto aperto, dalla regola di produzione; estratta dal «ramo B» del mondo |
| `-38` | NUOVO `dbops.fn_pgtap_cliente_del_builder`: senza BA il mondo; col BA del test l'azienda di chi agisce e il BA verificato, **senza un cliente in più** |
| `-39` | `fn_pgtap_crea_mondo_cliente` usa `-37` (la copia si ritira) |
| `-40` | commessa, contratto, fattura, ordine, lotto: il blocco ricopiato cinque volte diventa una chiamata a `-38` |
| `-41` | `fn_pgtap_crea_commessa_attivita` + sorgente (la chiave da `script.fn_segment_key`, il SOLO costruttore: dieci pgTAP la componevano a mano, come i sedici rotti il 20-10), quantità, stati di approvazione/emissione, periodo |
| `-42` | `fn_pgtap_crea_fattura` + `p_senza_utility` (due copie nei fondi) |

✅ **Applicato e verde** (Tid, 2026-10-24): `-37` … `-42` alle 23:50 su dbdev e scratch, corsa pgTAP come
app verde. Prima dell'apply: regressione sullo scratch (come owner) su 174 file, nessuna regressione; sei
rossi identici prima e dopo, tutti dipendenti dal ruolo (l'owner salta la RLS), verdi come app.

Presidi: nuovo `dbops/test-fn-pgtap-cliente-del-builder-v1` (7: nessun cliente in più anche passando dai
cinque builder; rosso senza, verde con); estesi attività (14) e fattura (15: anche il valore restituito
senza utility, che il builder prima riportava sbagliato). Regressione del pezzo comune su 164 file:
nessuna differenza oltre al presidio nuovo.

**Porting**, ogni file riprovato a mano (verde col `-37` … `-42`):

* l'attività di push in otto file (`annullo-commessa`, `emissione-mirata-gruppi-fatturabili`,
  `fn-list-preventivi-da-pushare-righe-ids`, `-v2`, `fn-preventivo-ha-residuo-commessa`, `vw-dash-backlog`,
  `vw-dash-fatturazione`, `vw-preventivi-smistamento`): le chiavi ora le compone `script.fn_segment_key`.
  Tre righe scritte a mano con una chiave **inventata** che nessuna push produce (una sorgente PREVENTIVO
  con chiave `PGTAP-BL-NE-*`; una riga d'ordine con sorgente PREVENTIVO; la riga della commessa di B che
  puntava al preventivo di A) diventano righe della commessa, o della sorgente giusta. Attesa cambiata,
  dichiarata: in `emissione-mirata` il tipo documento del perimetro si legge dalle righe scritte (11, 12,
  16), non più «il primo tipo con un registro». Restano a mano, perché sono il caso: le chiavi con i
  suffissi `#CMP:` e `#RET:` (il match a prefisso, il classificatore) e il canone del contratto con la
  chiave del **mese** (`:M:AAAA-MM`; il builder non lo passa, un file solo), ma la base della chiave ora la
  compone il dominio anche lì; `fn-list-preventivi-da-pushare-v1` non ha righe da portare (la chiave a
  mano è l'attesa del suo test 2, il formato);
* la fattura senza utility nei due file dei fondi;
* `test-drop-uq-commesse-attivita-src-uid-partial-v1`, rosso da prima per la pesca del primo BA e con un
  uuid sintetico come sorgente (che il guard delle sorgenti oggi respinge): mondo costruito, preventivo
  vero, righe dal builder. 4/4 col `-41`.

Da sapere sui builder (nessuno rompe un test): l'attività del builder ha `data_attivita` = inizio del
periodo e `valuta_id` NULL (la madre non la deriva); chi ne avesse bisogno lo dichiara nel test.

**Valutati e lasciati** (non hanno trappola: spostare la riga in un builder non centralizza niente):
la scheda precontrattuale (un INSERT di 2-5 colonne, i cui valori sono il caso del test); la coppia di
articoli MERCE + SERVIZIO (il builder dell'articolo accetta già la natura); il controllo «l'operatore del
mondo è OPERATORE» delle dashboard (un'asserzione, non una fixture). Sotto la regola del 2 (una copia):
più gruppi trattenuti dallo stesso lotto, l'IVA nel builder dell'articolo, la versione di listino e la
variazione globale nel contratto, la fattura con un'utility diversa da quella del cliente.

La bolla generata da un ordine e il reso scritto a mano, ripetuti in tutta la suite, sono un tema suo:
[brief-db-pgtap-bolla-e-reso-costruiti](../work-done/brief-db-pgtap-bolla-e-reso-costruiti.md) (chiuso il 2026-10-25; il reso è proseguito in [brief-db-pgtap-reso-costruito](../work-done/brief-db-pgtap-reso-costruito.md), chiuso anch'esso il 2026-10-25).

**Richiesta al team BE**, aggiornata: (1) le due sonde `richiedi_db_provvisto` sulle firme finali (sopra);
(2) dopo l'apply di `-35`, il DB può sollevare `E_PIPELINE_LOTTO_CRITICAL` anche dall'UPDATE dello stato
del lotto (`pipeline_repository.update_lotto_stato_doc`): il runner lo gestisce già come codice, ma
oggi lo produce solo lui; nessuna modifica attesa, da sapere.

**Fatto dal team BE** (2026-10-25, `dev/backend-tid`, da committare):

1. le sonde sulle firme finali, verificate su dbdev con `to_regprocedure` (non ricopiate dal brief):
   `test_prezzo_riga_commessa_db` → `fn_pgtap_crea_commessa(text,character varying,bigint,boolean,boolean)`,
   `test_scritture_email_note_db` → `fn_pgtap_crea_fattura(text,character varying,bigint,boolean,boolean,boolean,numeric,bigint,boolean)`;
2. ⚠️ **una terza sonda rotta, fuori dalla richiesta**: `catalogo/tests/db/test_scritture_dinamiche_db`
   sondava `fn_pgtap_crea_articolo` con 5 argomenti, la firma è a 10 da `69844e217` (un brief
   precedente). Saltava in silenzio da allora; portata alla firma vera. Trovata controllando **tutte**
   le 21 sonde di firma della suite contro il DB: le altre 18 risolvono;
3. i tre test, che saltavano, girano e sono verdi (13 casi);
4. `error_policies_generated.py` rigenerato: il `--check` divergeva per la `note` nuova di
   `E_PIPELINE_LOTTO_CRITICAL` (solo il commento, nessuna classe cambiata);
5. suite completa con `ZEROERP_TEST_DB_E2E=1`: 6899 test, OK; l'unico skip è il presidio «verso 2,
   solo misurato» di `test_ui_action_e_canale_campi`, dichiarato.

Per Tid, due decisioni — ✅ **accettate il 2026-10-25, fatte** (sotto, «Fatto per BE-1 e BE-2»):

* **BE-1. Le sonde di firma sono un presidio che si spegne da solo.** Una sonda con la firma esatta
  di un builder trasforma ogni cambio di firma in uno skip muto — è successo tre volte, e la terza
  nessuno l'aveva vista. Proposta: un test che raccoglie le sonde dichiarate nella suite e, sul DB
  provvisto (sonda di default verde), è **rosso** se una non risolve. Tocca il BB
  `richiedi_db_provvisto` (`apps/core/tests/db_e2e.py`), trasversale a tutte le app.
* **BE-2. Il codice del DB nel runner del lotto si perde.** Il punto (2) qui sopra non regge: un
  `E_PIPELINE_LOTTO_CRITICAL` sollevato dal guard (`trgfn_fatturazione_lotti_guard_stato`) arriva
  al runner come `DatabaseError`, non come `ServiceError`; `run_pipeline` lo prende nel ramo
  `except Exception` e lo appiattisce in `E_PIPELINE`, e il driver esce con `ERRORE` invece che
  con `BLOCCATO_CRITICITA`. Oggi il guard scatta dal runner solo se il lotto diventa fermo **fra**
  il controllo Python e l'UPDATE (stessa sede, `vw_lotti_segnalazioni_summary.fermo`; il rilancio
  dello stesso step non cambia stato e il guard non scatta; il runner è l'unico che scrive quello
  stato): è un'ultima difesa, ma quando difende dice la cosa sbagliata. Vale per **ogni** codice
  strutturato del DB dentro uno step (`E_LOTTO_PARAMETRO_NON_COERENTE` dello stesso guard compreso).
  Proposta: nel ramo generico, un `DatabaseError` con un codice del catalogo
  (`diagnostica_db(...).codice_strutturato`) diventa un `ServiceError` con quel codice, attraverso il
  BB esistente (`ErrorManager.raise_from_database_error`), e segue il ramo di dominio.

**Fatto per BE-1 e BE-2** (2026-10-25, `dev/backend-tid`, da committare):

* **BE-1, nel BB e non con un test che scansiona i file.** `richiedi_db_provvisto`
  (`apps/core/tests/db_e2e.py`) legge sempre lo schema dalla sonda di default (assente → skip,
  ambiente) e la sonda del chiamante solo dopo (assente su schema presente → `AssertionError`). È la
  regola che header del BB e catalogo dichiaravano già («schema presente + oggetto assente è un
  difetto»), e che il parametro `sonda` contraddiceva. Una scansione col regex avrebbe mancato le
  cinque chiamate scritte su più righe; il BB le copre tutte, e anche quelle future. Presidio dei tre
  rami: `apps/core/tests/test_db_e2e_sonda.py`; voce del catalogo BB aggiornata;
* **BE-2.** `run_pipeline`: il ramo generico riconosce un `DatabaseError` col codice **strutturato**
  del catalogo (non il testo) e lo traduce col BB `raise_from_database_error` (frase e soluzione
  del catalogo, nessun doppione nel diario); il fallimento segue il ramo di dominio, estratto in
  `_registra_fallimento_di_dominio` per non copiarlo. Test in `test_pipeline_runner`: il codice
  arriva intatto, il driver esce con `BLOCCATO_CRITICITA`, un errore DB senza codice resta
  `E_PIPELINE`. Provato che i due test nuovi vanno rossi sul runner di prima;
* suite completa verde con e senza `ZEROERP_TEST_DB_E2E=1` (6905 e 6426 test); il cancello mypy
  (`check_mypy_baseline.py`) pulito.

---

## 5. Come si procede dopo le decisioni

Due regole di Tid, 2026-10-24, che valgono per il piano e per ogni giro:

* **Si ottimizza per la velocità.** Non c'è produzione: si sceglie la strada più corta verso il
  modello, a colpi secchi, senza fasi di convivenza fra vecchio e nuovo. **Si accetta che qualcosa
  non funzioni** (backend, smoke, test Django) finché il cantiere BE del giro non è chiuso. Il lato
  DB non aspetta il BE: consegna il giro e scrive al BE cosa si è rotto e come si ripara. Restano
  verdi i pgTAP, che sono lato DB e si portano nello stesso giro.
* **Acquisti nasce sul modello, non lo rincorre.** Ogni volta che un documento di vendita viene
  portato al modello, il suo gemello di acquisti (ordine, DDT) ci arriva **nello stesso giro**:
  stesso verbo, stessa matrice, stesse azioni, stessi building block. Niente «fase due»: la
  guida del modello (§2) è scritta per entrambi, e gli errori censiti nel §3 non si ripetono in
  acquisti perché acquisti non ne ha una copia sua da sbagliare.

* Il §2, corretto con le decisioni, diventa la guida. Da lì una proposta che non è nella guida, o
  la contraddice, si dichiara come revoca.
* Si porta **un documento per giro, tutto intero** al modello (verbo, matrice, azioni, emissione,
  annullo), invece di un tema per giro su nove documenti. L'ordine dei documenti si decide col piano.
* Prima di ricopiare una regola nelle 11 capability o negli 11 guard, si valuta se quella parte può
  vivere in un building block comune che legge la matrice: è la causa strutturale del §1.

---

## 6. Punto 3: la guida del modello (2026-10-25)

**Verifica del giro BE, prima di partire.** Il commit `9fbff66d2` (PR #1938) contiene quello che il
§4-octies dichiara: le tre sonde sulle firme finali, `richiedi_db_provvisto` che fallisce
sull'oggetto mancante (BE-1, presidio `test_db_e2e_sonda.py`), il runner del lotto che tiene il
codice del DB (BE-2), `error_policies_generated.py` rigenerato, la voce del catalogo BB.

**Scritto:**

* la guida [modello-documento-di-vendita](../../guide/modello-documento-di-vendita.md): il §2 di
  questo brief con le decisioni M-1 … M-6, N-1 … N-3, P-1 … P-3 dentro, in sei regole (nascita,
  vocabolario e matrice, verbo, permesso sul passaggio, emissione, annullo), gli acquisti (§5) e
  «come si porta un documento» (§5). La tabella del §3.1 diventa il §10 della guida, «a che punto è
  ogni documento», **riverificata il 2026-10-25 sulla doc auto-generata** (verbi con e senza
  `fn_guard_azione`, guard che leggono o no la matrice): nessuna differenza dal censimento del
  2026-10-21, oltre alla nascita in bozza ora presente ovunque. In più la riga degli acquisti
  (vocabolario e nascita sì, nessun guard di transizione);
* le otto guide dei documenti (`gestione-preventivi`, `-ordini`, `-ddt`, `-contratti`,
  `-offerte-commerciali`, `-commesse`, `fatturazione`, `gestione-listini`): il rimando nell'header e,
  in testa alla sezione degli stati, una riga che manda alle regole comuni e al §10. Il loro corpo
  **non** è riscritto: descrive com'è oggi ogni documento, e si riallinea nel giro di quel documento;
* `fatturazione.md`, regole del modello lotti: R-1 (il lotto fermo non diventa definitivo) mancava
  dalla guida, c'era solo nella scheda del guard;
* `readme.md` (regole trasversali ai documenti) e `mkdocs.yml` (nav, accanto a numerazione e IVA).

⚠️ La guida descrive come regola ciò che Tid ha deciso, anche dove i documenti non ci sono ancora
arrivati: il §10 dice dove. È la condizione del §5 («da lì una proposta che non è nella guida si
dichiara come revoca»), e differisce dalla norma delle guide («lo stato attuale») in modo
dichiarato.

**Domande per il piano (punto 4)**, emerse scrivendo la guida; la guida non le decide:

| # | Domanda | Proposta |
| --- | --- | --- |
| S-1 | **La porta.** La guida dei permessi (§7.4) dice che il verbo protegge solo se non si aggira, e per i domini nuovi toglie all'app `INSERT`/`UPDATE` sulle tabelle. Una testata di documento però l'app la scrive anche per i campi ordinari (CRUD). Come si chiude la sola colonna di stato? (a) privilegio per colonna; (b) un guard sulla colonna di stato che passa solo se attraversato dal verbo (`script.fn_is_proprietario_tabella`, già previsto dal §7.4 per questo); (c) nessuna porta, il verbo è la strada ma non l'unica | **(b)**: (a) si scontra col loop dei grant di `ci_apply`, che rimette i privilegi di tabella; (c) lascia che un `UPDATE` del backend salti il permesso, cioè il buco che M-1 chiude. Un guard solo, montato su ogni testata come quello della nascita ✅ **Deciso da Tid il 2026-10-25: (b)** |
| S-2 | **Un verbo per documento, o uno solo?** Il verbo di stato legge matrice e azione dalla riga (M-3): il suo corpo è lo stesso per ogni documento. (a) un BB comune che riceve il documento (la sua sorgente) e lo stato, con i verbi specifici (annulla, conferma, emetti) che lo chiamano; (b) un verbo per documento, come oggi DDT, preventivo e commessa | **(a)**: è la regola del §5 («prima di ricopiare una regola nei guard o nelle capability, un BB comune che legge la matrice») e la causa del §1; i tre verbi di oggi diventano chiamate al BB nel giro del loro documento ✅ **Deciso da Tid il 2026-10-25: (a)** |

✅ Tid, 2026-10-25: guida approvata; fermo allentato (C, in PROJECT_CONTEXT); primo documento il DDT
col DDT d'acquisto; S-1 (b), S-2 (a). Il giro si scrive col via di Tid.

---

## 7. Giro 5: il DDT al modello — ricognizione e piano (2026-10-25)

Via di Tid il 2026-10-25 («ok procedi»). Ricognizione sul codice (doc auto-generata, `backend/`,
`db/pgtap/`), prima di scrivere i changeSet.

### 7.1 Com'è oggi

* **Verbo.** `vendite.fn_cambia_stato_ddt` (DEFINER) fa ogni passaggio e, sulle bolle che muovono
  merce, i prelievi e i movimenti. Il permesso è scritto nel corpo: `emetti_ddt` verso EMESSO e per
  EMESSO → ANNULLATO, `registra_magazzino` alla consegna di un trasferimento che muove merce; gli altri
  passaggi senza controllo («al permesso del backend»). `fn_annulla_ddt` ritira i legami e chiama il
  verbo. Il backend passa già **sempre** dal verbo (giro A1 del 2026-10-12).
* **Porta.** Esiste già, ma a metà: la Regola 3 di `trgfn_ddt_guard_transizione` (GUC
  `zeroerp.ddt_cambio_stato` + `script.fn_is_proprietario_tabella`, `E_DDT_STATO_SOLO_DA_VERBO`) chiude
  solo emissione, annullo dell'emesso e consegna del trasferimento, e solo se la bolla muove merce. La
  stessa forma, copiata, sta sul reso (`E_RESO_STATO_SOLO_DA_VERBO`) e sui documenti interni di
  magazzino (`E_MAG_DOCUMENTO_POSTED_SOLO_DA_OPERAZIONE`): tre copie.
* **Chi scrive lo stato della bolla senza il verbo:** `vendite.fn_conferma_reso` (CONSEGNATO → RESO) e
  `vendite.fn_annulla_reso` (RESO → CONSEGNATO), i due passaggi di processo (`manuale = false`) della
  matrice; `dbops.fn_pgtap_porta_a_stato`; nei pgTAP 19 file con un `UPDATE` diretto e 12 con
  `porta_a_stato` sulla bolla (conteggio del 2026-10-25, per dimensionare il porting).
* **Capability.** `script.fn_available_actions_ddt` legge la matrice, ma non guarda il permesso: un
  bottone «Emetti» compare anche a chi non ha `emetti_ddt` (§12.1 della linee guida SQL: permesso ⇒
  nascondi).
* **Emissione (M-2).** `/emetti/` chiama `ddt_service.emetti`, che è `cambia_stato(…, 'EMESSO')`: la
  rotta generica `cambia-stato/` accetta EMESSO allo stesso modo.
* **La mappa dei documenti** (testata → colonna di stato, vocabolario, matrice) esiste in un posto
  solo, dentro `dbops.fn_pgtap_porta_a_stato`. Il verbo comune ne ha bisogno: è la seconda occorrenza.
* **DDT d'acquisto.** `acquisti.ddt` usa `config.stati_doc_ddt` e ha solo il trigger della nascita:
  nessun guard di transizione, nessun verbo, nessuna capability, nessun backend, zero righe. ⚠️ La
  decisione D-3 di [analisi-simmetria-ordini-acquisto](analisi-simmetria-ordini-acquisto.md)
  (Tid, 2026-09-02) dice che gli stati condivisi descrivono un documento **emesso da noi**, e che
  vendite e acquisti si separano con un satellite per ambito (`config.stati_doc_ddt_ambiti`, `ambito`
  nella chiave delle transizioni). Il satellite non c'è ancora.
* ⚠️ **Un'altra sessione** lavora in questo momento su
  [brief-db-pgtap-reso-costruito](../work-done/brief-db-pgtap-reso-costruito.md) (giro 2): una trentina di pgTAP di
  bolla e reso modificati e non committati, `20261025-05`/`-06` nuovi. Sono gli stessi file che questo
  giro deve portare.

### 7.2 Il piano (da confermare con le domande del §7.3)

**I pezzi comuni** (schema `script`, montati sulla bolla e riusati dai documenti dei giri dopo):

| Pezzo | Che cosa fa |
| --- | --- |
| la mappa dei documenti | testata → colonna di stato, vocabolario, matrice; estratta da `fn_pgtap_porta_a_stato`, che la legge (la copia si ritira) |
| l'azione sulla riga (M-3) | colonna `azione_processo_codename` sulla matrice (FK a `config.azioni_processo.permission_codename`, la chiave stabile: §6b delle linee guida), valorizzata nel CSV: emissione e annullo dell'emesso = `emetti_ddt` |
| la prima riga del verbo | legge la riga del passaggio, applica il permesso (l'azione della riga; senza azione il permesso sul documento resta al backend, niente `fn_guard_livello`: l'operatore dei pgTAP è bloccato su più aree) e rifiuta i passaggi di processo chiesti a mano |
| la primitiva di scrittura | apre la porta per **quel** documento e scrive lo stato. `SECURITY INVOKER` e non riservata: la porta chiede anche il proprietario, quindi dall'app si ferma da sola |
| la porta (S-1) | un guard sulla colonna di stato: passa solo dalla primitiva (GUC + proprietario). Prende il posto della Regola 3 della bolla, che si ritira |
| il permesso nelle capability | il bottone di un passaggio con azione si nasconde a chi non ce l'ha, dalla stessa riga |

**La bolla:** `fn_cambia_stato_ddt` comincia dalla prima riga comune e scrive con la primitiva; restano
suoi i prelievi e i movimenti. `fn_conferma_reso`/`fn_annulla_reso` scrivono lo stato della bolla con
la primitiva. `fn_pgtap_porta_a_stato` passa dal verbo per i documenti con la porta. pgTAP portati nello
stesso giro.

**Richiesta al BE** (da completare col percorso intero): `cambia-stato/` rifiuta EMESSO (M-2, solo
`/emetti/`); il 403 dell'endpoint legge l'azione dalla riga del passaggio, con la funzione del DB; i
codici nuovi in `error_policies_generated.py`.

### 7.3 Domande per Tid

Una alla volta, nel giro di domande del 2026-10-25.

* ✅ **T-1. L'altra sessione** — Tid: **B**, si parte subito; l'altra sessione ha committato
  (`2e1a6aaac`, 2026-10-25), l'albero è libero.
* ✅ **T-2. Il DDT d'acquisto** — Tid: **non si fa** in questo giro («il ddt acquisto no, non
  farlo»). Il giro porta la sola bolla di vendita; il DDT d'acquisto aspetta il satellite per ambito
  (D-3 di analisi-simmetria-ordini-acquisto). ⚠️ È un'eccezione dichiarata alla regola del §5 «nello
  stesso giro»: i pezzi comuni nascono generici, così il DDT d'acquisto li monta senza copie.
* ✅ **T-3. Il reso** — Tid: **A**, entra nel giro: il pezzo comune della porta sostituisce la sua
  copia (`E_RESO_STATO_SOLO_DA_VERBO`), `conferma_reso` passa sulla riga del passaggio. I documenti
  interni di magazzino restano fuori (nessun vocabolario degli stati in tabella): la loro porta resta,
  dichiarata.
* ✅ **T-4. `registra_magazzino` alla consegna del trasferimento** — Tid: **A**, resta nel verbo della
  bolla come permesso dell'operazione di magazzino dentro il passaggio; la riga CONSEGNATO non porta
  azioni. Scritto nella guida del modello §6 come regola.

### 7.4 Scritto (2026-10-25)

| # | Cosa |
| --- | --- |
| `-07` | NUOVO `script.fn_doc_stato_modello(regclass)`: la mappa, estratta da `fn_pgtap_porta_a_stato` |
| `-08` | colonna `azione_processo_codename` (FK al codename) su `config.transizioni_stati_ddt` e `_reso`; valori nei CSV, mirror `20260709-10` e `20260713-41` con la colonna e `nullValue: "NULL"` |
| `-09` | NUOVO `script.fn_doc_passaggio`: la riga viva del passaggio (manuale, azione), lettore unico |
| `-10` | NUOVO `script.fn_guard_passaggio`: prima metà del verbo (processo → `E_DOC_PASSAGGIO_DI_PROCESSO`; azione → `fn_guard_azione`) |
| `-11` | NUOVO `script.fn_doc_scrivi_stato`: seconda metà, la scrittura attraverso la porta (GUC `zeroerp.doc_cambio_stato` = `oid:id`, rimessa com'era) |
| `-12`, `-13` | NUOVO `script.trgfn_doc_stato_solo_dal_verbo` (`E_DOC_STATO_SOLO_DAL_VERBO`), montato `_a05_` su `vendite.ddt` e `vendite.resi` |
| `-14`, `-15` | i guard di transizione di bolla e reso perdono la loro porta del registro (Regola 3 e Regola 2): la copia si ritira |
| `-16` | `fn_cambia_stato_ddt` sul verbo comune; resta suo `registra_magazzino` (T-4) |
| `-17`, `-18` | `fn_conferma_reso`, `fn_annulla_reso` sul verbo comune; il flip della bolla (RESO ↔ CONSEGNATO) dalla scrittura comune |
| `-19` | `fn_pgtap_porta_a_stato`: la mappa comune; sotto la porta, i passi col verbo (solo manuali) e l'azione concessa |
| `-20`, `-21` | capability di bolla e reso: il passaggio con l'azione si nasconde a chi non ce l'ha |

Dati: `E_DOC_STATO_SOLO_DAL_VERBO` e `E_DOC_PASSAGGIO_DI_PROCESSO` (TECNICO) in `messaggi_errore.csv` e
`codici_errore.csv`; `E_DDT_STATO_SOLO_DA_VERBO` e `E_RESO_STATO_SOLO_DA_VERBO` obsoleti dal 2026-10-25.
Doc: cinque pagine `manual` nuove (script), le schede del reso, la guida del modello (§5, §6, §10),
`gestione-ddt` (§4.4), la tabella dei builder della guida pgTAP. pgTAP nuovo:
`script/test-doc-verbo-comune-e-porta-v1` (20).

**Attese cambiate, dichiarate:**

* l'annullo di un reso in **bozza** non chiede più `conferma_reso` (M-4: non è un passaggio pesante); il
  backend lo chiedeva staticamente (`ApiResoAnnulla.post_permission`), vedi la richiesta;
* una conferma (o un annullo) di un reso che non ha la riga del passaggio (già confermato, già annullato)
  risponde col codice dello stato (`E_RESO_STATO_NON_CONFERMABILE` / `_NON_ANNULLABILE`) anche a chi non
  ha l'azione: prima `E_PERMESSO_NEGATO`;
* **ogni** cambio di stato diretto di bolla e reso è rifiutato, non più solo quelli del magazzino;
* le capability di bolla e reso non mostrano più «Emetti» / «Conferma» / «Annulla» (dell'emesso o del
  confermato) a chi non ha l'azione.
* pgTAP, attese della regola ritirata (dichiarate nei file): `magazzino/test-ddt-scarico-v1` 4 e 16 (la
  bolla senza merce non passa più dall'`UPDATE` diretto), `test-ddt-trasferimento-v1` 8,
  `test-reso-carico-v1` 11 → `E_DOC_STATO_SOLO_DAL_VERBO`; `vendite/test-ddt-causale-immutabile-v1` 4:
  provava che il guard della causale legge lo stato VECCHIO quando causale e stato cambiano nella stessa
  istruzione. ⚠️ Con la porta quell'istruzione non si può più scrivere da fuori (il verbo scrive solo lo
  stato): il test ora asserisce il rifiuto della porta. ✅ **Confermato da Tid il 2026-10-25**: il test
  discrimina ancora, perché il lock della causale (`trg_ddt_a05_lock_fuori_bozza_upd`) scatta prima
  della porta (`…a05_stato_solo_dal_verbo_upd`): un lock che leggesse lo stato nuovo rifiuterebbe con la
  sua frase. La dipendenza dall'ordine dei nomi è scritta nel test. Tre test, dopo l'apply e prima del porting, erano verdi **per la ragione sbagliata** (prendevano il P0001 della porta
  invece del guard che provavano: `test-fn-check-ddt-emittibile-v1` 9, `test-ddt-solo-trasporto-causale-v1`
  2 e 3) passano dal verbo e cadono sul guard vero.

### 7.5 Incidente dell'apply (2026-10-25, 01:53)

Tid ha applicato `-07` … `-21` su dbdev e scratch mentre la prova era in corso; il migrate si è fermato
nel mirror `20260709-10`: la colonna nuova aveva celle vuote e il mirror `nullValue: ""`, Liquibase ha
scritto `''` e la FK l'ha rifiutata. ⛔ Era una trappola già scritta (memoria del 2026-09-28, mirror
`20260709-11`), e la prova col seed simulato in Python non la vede. Corretto: `nullValue: "NULL"` nei
due mirror e il token `NULL` nelle celle. Stato dopo l'incidente: i changeSet `-07` … `-21` applicati, le
azioni sulle righe **ancora NULL** fino al prossimo migrate (il mirror è `runOnChange`).

### 7.6 Richiesta al team BE (elenco chiuso)

Percorso censito: `ddt_service.cambia_stato` / `emetti`, `ApiDdtCambiaStato`, la fabbrica `/emetti/`
(`emetti_post_permission`), `ApiResoConferma` / `ApiResoAnnulla`, `ddt_repository`, il catalogo dei
messaggi di ripiego.

1. **M-2, solo da «Emetti».** `ddt_service.cambia_stato` (e `ApiDdtCambiaStato`) rifiuta `EMESSO`: la
   bolla si emette solo da `/emetti/`, che produce numero e PDF insieme. Codice: un `*_VALIDATION`
   del dominio (400), la frase dice di usare «Emetti».
2. **M-3, il 403 dalla riga del passaggio.** Il permesso dell'endpoint di un cambio di stato non si
   dichiara più a mano: si legge da `script.fn_doc_passaggio(<testata>, <stato corrente id>, <stato
   chiesto id>)` (colonna `azione_processo_codename`; NULL = basta `model_permission`) e si controlla
   con la stessa regola del DB, prima di aprire la transazione. Vale per `ApiDdtCambiaStato` (oggi
   nessun `post_permission`: l'annullo dell'emesso arrivava al DB senza 403 prima), per
   `ApiResoConferma` e `ApiResoAnnulla` (oggi `post_permission = "conferma_reso"` fisso: con M-4
   l'annullo di una bozza **non** lo chiede più, e il 403 statico lo rifiuterebbe), e per l'`/emetti/`
   della bolla (`emetti_post_permission="emetti_ddt"`: coincide con la riga, ma è una seconda copia).
3. **I codici.** Rigenerare `error_policies_generated.py`: `E_DOC_STATO_SOLO_DAL_VERBO`,
   `E_DOC_PASSAGGIO_DI_PROCESSO` (TECNICO, frasi chiuse o col solo identificativo del documento);
   `E_DDT_STATO_SOLO_DA_VERBO` / `E_RESO_STATO_SOLO_DA_VERBO` obsoleti (le due voci di
   `error_messages_fallback.py` e il commento di `ddt_repository.cambia_stato` si allineano).
4. **Da sapere, nessuna modifica attesa:** `cambia_stato` verso `RESO` (passaggio di processo) ora
   risponde `E_DOC_PASSAGGIO_DI_PROCESSO`; le capability nascondono le azioni senza permesso (il
   frontend non cambia: riceve meno azioni).
5. **I test DB che scrivono lo stato della bolla con un `UPDATE` diretto** (censiti il 2026-10-25, ora
   rifiutati con `E_DOC_STATO_SOLO_DAL_VERBO`): `apps/vendite/tests/db/_ddt_consegnato.py` (righe 75-77,
   EMESSO → SPEDITO → CONSEGNATO) e `apps/vendite/tests/db/test_date_consegna_righe_db.py` (riga 120).
   Si portano a `dbops.fn_pgtap_porta_a_stato('vendite.ddt', <id>, '<stato>')`, che passa dal verbo e
   concede all'utente del contesto l'azione del passaggio; senza un utente di contesto il verbo non vede
   la bolla (`E_DDT_NOT_FOUND`).

### 7.7 Debito emerso e chiuso nello stesso giro

* **`-22`: la frase del rifiuto di matrice di bolla e reso.** `E_STATO_DDT_TRANSIZIONE_NON_VALIDA` e
  `E_STATO_RESO_TRANSIZIONE_NON_VALIDA` hanno due segnaposto (stato da, stato a), ma i due guard
  passavano anche l'id del documento: a video «da 14566 a EMESSO» per un EMESSO → CONSEGNATO. Difetto di
  prima del giro, visto nel porting; corretto qui perché i due corpi erano appena stati riscritti
  (`-14`/`-15`, già applicati: non si toccano). Provato in transazione: compila, `plpgsql_check` pulito.
* Lasciato: `E_DDT_EMISSIONE_SENZA_RIGHE` riceve id e numero per un segnaposto solo, e mostra l'id; in
  bozza il numero non c'è ancora, e l'id è l'informazione giusta.

### 7.8 Applicato e verde (2026-10-25)

Tid: `-07` … `-22` applicati su dbdev e scratch (il mirror `20260709-10` è ripartito dopo la correzione
del §7.5, le azioni sulle righe sono valorizzate), corsa pgTAP verde. Un solo rosso visto come app prima
della corsa finale, corretto: il test 2 del presidio nuovo confrontava il **testo** di un `regclass`, che
dipende dal `search_path` (come app `config` ci sta e lo schema sparisce); ora i test 2 e 9 confrontano i
`regclass`. La corsa come app ha confermato anche i due test della porta (19, 20) che da owner non si
potevano provare.

### 7.9 Fatto dal team BE (2026-10-25) e richiesta al team DB per il giro dopo

**Fatto** (`dev/backend-tid`, da committare), sulla richiesta del §7.6:

1. **M-2.** `ddt_service.cambia_stato` rifiuta `EMESSO` con `400 E_DDT_VALIDAZIONE` (campo
   `stato_codice`, «La bolla si emette solo da «Emetti»…»); `emetti` passa da un corpo comune con
   `stato_del_modello="emissione"`. Frontend e smoke usavano già `/emetti/`.
2. **M-3, il 403 dalla riga.** BB nuovo in `core` (ok Tid, 2026-10-25): la view dichiara
   `post_passaggio = PassaggioDocumento(testata, documento_kwarg, stato_chiesto)` e
   `ZeroERPPermission` legge l'azione con `script.fn_doc_passaggio` (stato corrente → stato chiesto)
   prima della transazione. Con l'azione decide lei (semantica di `post_permission`); senza riga o
   senza azione, livello sul documento. Montato su `ApiDdtCambiaStato`, `/emetti/` della bolla
   (`emetti_passaggio` della factory documenti, esclusivo con `emetti_post_permission`),
   `ApiResoConferma`, `ApiResoAnnulla`. Le copie ritirate: `post_permission = "conferma_reso"` (due) e
   `emetti_post_permission="emetti_ddt"`. Catalogo BB, `api.md`, `api_ddt`, `api_resi`,
   `api_documenti_per_sorgente` aggiornati.
3. **Codici.** `error_policies_generated.py` rigenerato (i due nuovi, i due ritirati), ripiego senza
   segnaposto per `E_DOC_STATO_SOLO_DAL_VERBO` / `E_DOC_PASSAGGIO_DI_PROCESSO`, nota di ritiro sulle due
   voci vecchie, commento di `ddt_repository.cambia_stato` allineato.
5. **Test DB.** `_ddt_consegnato.py`, `test_date_consegna_righe_db.py` e (non in elenco)
   `test_ddt_cambia_stato_db.py`, che passava a EMESSO dal cambio stato generico: tutti dal verbo.

Emerso e non in richiesta: la sonda di `test_origine_ordine_sorgente_db` cercava
`dbops.fn_pgtap_crea_ordine` a tre argomenti; la firma è a quattro (`p_data`) da `fae207c9e`
(brief-db-pgtap-bolla-e-reso-costruiti, che dichiarava «nessuna ricaduta sul backend»). La sonda
falliva sull'oggetto mancante, come vuole BE-1: allineata.

**Provato:** suite completa con `ZEROERP_TEST_DB_E2E=1`, 6923 test, verdi tranne 2 che **non sono di
questo giro**: `test_error_policies_divergenza_db` e `test_error_codes_db_policy_guardrail` vedono 5
codici `E_INDIRIZZO_*` presenti su dbdev ma non in git (brief-db-unicita-civico-indirizzi-dettaglio, in
corso). Si rigenera la policy dopo il suo push. mypy (cricchetto) e ruff puliti. Presidi nuovi:
`core/tests/api/test_permesso_passaggio.py`, `core/tests/test_passaggio_rotte.py` (il kwarg è nella
rotta, nessun `post_permission` accanto, la testata è sul modello), `vendite/tests/db/test_permesso_passaggio_db.py`.
⚠️ Non eseguiti gli smoke HTTP (login col secondo fattore).

**Richiesta al team DB, per il giro dopo** (Tid, 2026-10-25). Per rispondere 403 il backend deve
passare a `script.fn_doc_passaggio` due **id** di stato, e oggi li ricava da sé componendo SQL sulla
mappa (`DocumentoModelloRepository.azione_del_passaggio`):

* lo stato **chiesto** arriva come codice e si traduce in id leggendo `codice_interno` del vocabolario.
  La colonna c'è, UNIQUE, negli otto vocabolari, ma `script.fn_doc_stato_modello` non la dichiara: è
  un pezzo del contratto del vocabolario che vive solo in Python;
* lo stato **corrente** si legge da `<testata>.<colonna_stato>`, con gli identificatori presi dalla
  mappa.

Si chiede un lettore DB unico per la traduzione codice → id dello stato di una testata (per esempio
`script.fn_doc_stato_id(p_testata regclass, p_codice text) RETURNS bigint`, il gemello di
`fn_stato_iniziale_id`). Da valutare se esporre direttamente la domanda intera,
`script.fn_doc_azione_passaggio(p_testata regclass, p_documento_id bigint, p_stato_a_codice text)`:
il backend non comporrebbe più SQL, e quel lettore servirebbe ai giri dei documenti successivi così
com'è. In entrambi i casi il backend cambia **solo** il repository (una funzione), e i presidi restano.

✅ **Deciso da Tid il 2026-10-25: sì, la colonna** (emerso dalla revisione critica del giro BE). M-2 («si emette solo
da Emetti») vale per **tutti** i documenti che si stampano, ma nessun vocabolario dice **quale** stato
è l'emissione: `config.stati_doc_ddt` ha `iniziale`, `is_abortito`, `fase`, `pdf_mode`, non un segno
dell'emissione. Il backend lo scrive quindi come letterale `EMESSO` (`ddt_service.STATO_EMESSO`, una
sede sola), e ogni documento dei giri dopo ne avrebbe uno suo: è la copia per documento che il §1
descrive. Proposta: il vocabolario dichiara lo stato di emissione come dichiara l'iniziale (colonna
`emissione boolean` con indice unico parziale, oppure un segno sulla riga della matrice), e il backend
lo legge invece di scriverlo: il cambio stato generico rifiuta lo stato di emissione di qualunque
documento, senza un letterale per documento. Il PDF nasce nel backend, quindi il rifiuto resta lì: al
DB si chiede solo di **dire** quale stato è l'emissione.

**Richiesta al team DB (seconda, insieme a quella sopra):**

1. colonna `emissione boolean NOT NULL DEFAULT false` sui vocabolari degli stati dei documenti che si
   stampano, con indice unico parziale (al più uno per vocabolario) e il CHECK «solo su una riga
   attiva», nella stessa forma di `iniziale` (P-1, `20261024-07`); valori dai CSV di `80_data` e
   colonna dichiarata nei mirror (⚠️ `nullValue`, §7.5). Quali vocabolari: quelli dei documenti che
   passano da «Emetti» (oggi la factory `/emetti/`: preventivo, offerta, contratto, ordine, DDT); il
   team DB verifica il perimetro sulla guida §7 e lo dichiara;
2. un lettore unico, gemello di `script.fn_stato_iniziale_id`: per esempio
   `script.fn_stato_emissione_id(p_testata regclass)`, NULL se il documento non si emette;
3. se si sceglie la domanda intera del punto sopra (`fn_doc_azione_passaggio`), può valere la pena
   esporre anche «il passaggio chiesto è l'emissione?», così il backend fa una chiamata sola.

**Ricaduta sul backend, al giro dopo:** `ddt_service.STATO_EMESSO` si ritira; il cambio stato generico
rifiuta lo stato di emissione letto dal DB, e `/emetti/` lo prende dallo stesso lettore (la factory non
riceve più lo stato in `emetti_passaggio`, solo la testata). Il presidio diventa generico su tutti i
documenti della factory.

---

## 8. Giro 6: il preventivo al modello — ricognizione e piano (2026-10-25)

✅ **Deciso da Tid il 2026-10-25:** il documento del giro è il **preventivo** (nessun gemello d'acquisto).
Il lettore del §7.9 si fa in **due pezzi**, come il backend chiedeva: `script.fn_doc_stato_id(p_testata
regclass, p_codice text)` (codice → id dello stato di una testata, il BB) e la domanda intera
`script.fn_doc_azione_passaggio(p_testata, p_documento_id, p_stato_a_codice)`, che lo compone e dice anche
se il passaggio è l'emissione. Il backend sceglie il lettore che gli serve; nessuno dei due compone SQL
sulla mappa. Lo sviluppo parte col via di Tid.

### 8.1 Com'è oggi (doc auto-generata e `backend/`, 2026-10-25)

* **Verbo.** `vendite.fn_cambia_stato_preventivo(id, codice, user)` è **INVOKER**, valida la matrice nel
  corpo (copia del guard di transizione, «voluta» dal 2026-08-05), scrive lo stato con un `UPDATE`.
  Nessun controllo di permesso. Codice → id scritto nel corpo (`codice_interno = p AND attivo`).
* **Guard di transizione** `trgfn_preventivi_guard_transizione`: matrice, condizioni dell'emissione
  (`fn_check_preventivo_emettibile`), prezzi autorizzati all'accettazione. Letterali `'EMESSO'`,
  `'ACCETTATO'`: sono condizioni di un passaggio, restano (guida §7, «le condizioni stanno sul passaggio»).
* **Annullo.** `fn_annulla_preventivo` (DEFINER) ritira i legami e chiama il verbo: già al modello.
* **Scrittori dello stato senza il verbo:** `vendite.fn_preventivo_proietta_stato_smistamento`
  (ACCETTATO ↔ EVASO, i passaggi di processo 4→10 e 10→4, `manuale = false`), consumata da push a
  ordine, ritiro dei legami e trigger della commessa. Il passaggio di processo EMESSO → SCADUTO (2→7) è
  nella matrice ma **nessuno lo scrive** (né DB né backend): si dichiara, non si tocca.
* **Azione.** `cambia_stato_preventivi` («emetti/accetta/rifiuta/annulla»), su **ogni** passaggio e solo
  nel backend: `ApiPreventivoStato`, `ApiPreventivoStatoDaPratica`, `ApiPreventivoCollegaPratica` (che
  non è un cambio di stato), `/emetti/` della factory (`emetti_post_permission`). Nessun profilo la
  riceve dai seed. È la divergenza dalla guida §6 («una azione, sui passaggi pesanti»).
* **Emissione (M-2).** Già lato BE: `preventivi_service.cambia_stato` rifiuta `'EMESSO'` con un
  letterale suo, `emetti` passa dal repository.
* **Codice → id dello stato, copie censite:** `fn_cambia_stato_preventivo`, `fn_cambia_stato_ddt`,
  `dbops.fn_pgtap_porta_a_stato`, `DocumentoModelloRepository.azione_del_passaggio` (BE). Quattro: il BB
  `fn_doc_stato_id` le ritira tutte nello stesso giro (quelle DB qui, quella BE nella richiesta).
* **pgTAP:** 6 file scrivono lo stato del preventivo con un `UPDATE` diretto, 39 passano da
  `porta_a_stato` o dal verbo (conteggio del 2026-10-25, per dimensionare il porting).
* ⚠️ **Controesempio, lato BE:** `cambia_stato` dichiara «ACCETTATO → ACCETTATO (no-op stato)» per
  aggiornare la modalità di fatturazione, ma poi chiama il verbo con lo stesso stato: la matrice non ha
  la riga 4→4 e il verbo risponde `E_PREV_TRANSIZIONE_NON_AMMESSA`. Va nella richiesta al BE.

### 8.2 Il piano

| Pezzo | Che cosa |
| --- | --- |
| `fn_doc_stato_id` | NUOVO BB in `script`: l'id dello stato **attivo** con quel `codice_interno` nel vocabolario della testata (dalla mappa), NULL se non c'è (decide il chiamante); testata fuori mappa: `E_SCRIPT_CHIAMATA_NON_VALIDA` |
| `emissione` | colonna `boolean NOT NULL DEFAULT false` su `stati_doc_preventivi`, `_offerte`, `_contratti`, `_ordini`, `_ddt` (i documenti della factory `/emetti/`, guida §7), indice unico parziale e CHECK «solo su una riga attiva» come `iniziale`; valori dai CSV, mirror con la colonna (⚠️ `nullValue`, §7.5) |
| `fn_stato_emissione_id(p_testata)` | NUOVO lettore, gemello di `fn_stato_iniziale_id`: NULL se il documento non si emette |
| `fn_doc_azione_passaggio` | NUOVO: stato corrente del documento (dalla mappa) + `fn_doc_stato_id` + `fn_doc_passaggio`; restituisce `manuale`, `azione_processo_codename`, `emissione` (lo stato chiesto è quello di emissione). Nel perimetro di chi chiama (INVOKER) |
| matrice del preventivo | colonna `azione_processo_codename`, valori dal CSV: l'azione sui passaggi pesanti (U-1) |
| verbo | `fn_cambia_stato_preventivo` sul verbo comune: `fn_guard_passaggio` in testa, `fn_doc_scrivi_stato` per scrivere; la copia della matrice nel corpo si ritira (la fa il guard). Diventa DEFINER come la bolla: la porta vuole il proprietario |
| porta | `trgfn_doc_stato_solo_dal_verbo` montato `_a05_` su `vendite.preventivi` |
| processo | `fn_preventivo_proietta_stato_smistamento` scrive con `fn_doc_scrivi_stato` (sola seconda metà, come il flip della bolla dal reso) |
| capability | `fn_available_actions_preventivo`: il passaggio con l'azione si nasconde a chi non ce l'ha |
| copie | `fn_cambia_stato_ddt` e `fn_pgtap_porta_a_stato` usano `fn_doc_stato_id`; `porta_a_stato` passa dal verbo per il preventivo (lo dice già il catalogo, porta montata) |
| pgTAP | i 6 `UPDATE` diretti a `porta_a_stato`; test nuovo dei due lettori e della colonna; i presidi del verbo comune estesi al preventivo |

**Richiesta al BE** (si scrive col percorso intero, a giro DB provato): `post_passaggio` su
`ApiPreventivoStato`, `ApiPreventivoStatoDaPratica` e `/emetti/` (le copie di `cambia_stato_preventivi`
si ritirano; `ApiPreventivoCollegaPratica` resta da decidere col BE, non è un passaggio); il repository
del §7.9 sui lettori nuovi; `STATO_EMESSO` e il letterale del preventivo ritirati, il rifiuto
dell'emissione letto dal DB per tutti i documenti della factory; il controesempio ACCETTATO → ACCETTATO;
i codici rigenerati.

### 8.3 Domande per Tid

✅ **Decise da Tid il 2026-10-25: U-1 (a), U-2 sì, U-3 sì, come da proposta; via allo sviluppo.**

* **U-1. L'azione del preventivo.** (a) azione **nuova** `emetti_preventivo` («emette un preventivo o
  annulla un preventivo emesso»), sulle righe 1→2 (emissione), 2→9 e 4→9 (annullo dell'emesso e
  dell'accettato), e `cambia_stato_preventivi` obsoleta; (b) si tiene `cambia_stato_preventivi` sulle
  stesse tre righe, cambiandole il significato. **Proposta (a)**: il gemello di `emetti_ddt`, e un
  profilo che oggi ha «cambia stato» per accettare e rifiutare non si ritrova in silenzio il potere di
  emettere e annullare.
* **U-2. ACCETTATO → ANNULLATO chiede l'azione?** La guida §6 dice «l'annullo di un documento emesso»;
  l'accettato è emesso. **Proposta: sì** (è dentro U-1).
* **U-3. `fn_doc_stato_id` legge solo gli stati attivi?** **Proposta: sì**: risponde alla domanda «verso
  quale stato vado», e uno stato spento non è una destinazione; i verbi di oggi filtrano già così (il
  repository BE no: è la copia che si ritira).

### 8.4 Scritto (2026-10-25)

| # | Cosa | Stato |
| --- | --- | --- |
| `-37` | colonna `emissione` su `stati_doc_preventivi`, `_offerte`, `_contratti`, `_ordini`, `_ddt`, con indice unico parziale e CHECK «attivo»; valori nei CSV (EMESSO, EMESSA, ATTIVO, CONFERMATO, EMESSO), dichiarata nei sei mirror dei vocabolari | applicato |
| `-38` | colonna `azione_processo_codename` su `config.transizioni_stati_preventivi`; nel CSV `emetti_preventivo` sulle righe 1→2, 2→9, 4→9; i due mirror con la colonna e `nullValue: "NULL"` | applicato |
| CSV | `azioni_processo`: `emetti_preventivo` (id 40) nuova; `cambia_stato_preventivi` marcata **obsoleta** nella descrizione ma **attiva** (vedi §8.6) | applicato su dbdev |
| `-39` | NUOVO `script.fn_doc_stato_id(testata, codice)`: codice → id dello stato attivo (U-3) | applicato |
| `-40` | NUOVO `script.fn_stato_emissione_id(testata)`: lo stato di emissione, NULL se il documento non si emette | applicato |
| `-41` | NUOVO `script.fn_doc_azione_passaggio(testata, id, codice)`: la domanda intera del backend (stati, emissione, riga del passaggio) | applicato |
| `-42` | `fn_cambia_stato_preventivo` sul verbo comune: firma (id, stato), DEFINER col predicato del perimetro, `fn_guard_passaggio` + `fn_doc_scrivi_stato`; ritirate dal corpo le copie della matrice e dell'annullabilità | applicato |
| `-43` | `fn_annulla_preventivo` chiama il verbo con la firma nuova | applicato |
| `-44` | `fn_cambia_stato_ddt`: codice → id e stato di emissione dai lettori comuni (nessun cambio di comportamento) | applicato |
| `-45` | `fn_preventivo_proietta_stato_smistamento`: ACCETTATO ↔ EVASO da `fn_doc_scrivi_stato`, DEFINER (§8.6) | applicato |
| `-46` | la porta montata su `vendite.preventivi` | applicato |
| `-47` | capability del preventivo: il passaggio con l'azione si nasconde a chi non ce l'ha; i motivi dell'emissione sulla colonna `emissione` | applicato |
| `-48` | `fn_pgtap_porta_a_stato`: il preventivo dal suo verbo, lo stato voluto da `fn_doc_stato_id` | applicato |
| `-49` | guard di transizione del preventivo: la regola «almeno una riga attiva» all'emissione (prima solo nel verbo: guida §7, «le condizioni stanno sul passaggio») | **da applicare** |
| `-50` | il verbo non ripete più la regola delle righe | **da applicare** |
| `-51` | COMMENT di `fn_stato_emissione_id`: i consumatori dopo `-49` | **da applicare** |
| `-52` | NUOVO builder `dbops.fn_pgtap_crea_preventivo_con_righe`: una riga valida e lo stato chiesto (gemello di quello dell'ordine) | **da applicare** |

Doc: tre pagine `manual` nuove (script), la guida del modello (riferimenti, §4, §7, §10), `gestione-preventivi`
§3.1 (chi cambia lo stato, quale permesso, SCADUTO), la tabella dei builder della guida pgTAP. pgTAP nuovo:
`script/test-doc-lettori-stato-e-preventivo-al-modello-v1` (22; il 22 è rosso da owner, verde come app).
Presidio del giro 5 esteso: `script/test-doc-verbo-comune-e-porta-v1` test 9 e 10 (la porta anche sul preventivo).

**Incidente (2026-10-25, 11:37).** Tid ha applicato `-37` … `-48` su dbdev e scratch mentre la regressione
girava; dopo l'apply ho ritoccato `-40` (COMMENT) e `-42` (tolta la regola delle righe), e i checksum non
tornavano. I due file sono riportati al contenuto applicato (corpo e COMMENT uguali al vivo su dbdev); le
modifiche stanno in `-50` e `-51`. ⚠️ **Sullo scratch** i mirror dei CSV non sono ripartiti: mancano
`emetti_preventivo` e i valori di `emissione` (dbdev li ha). Da rifare lo scratch prima della corsa pgTAP lì.

### 8.5 Regressione e porting dei pgTAP

Regressione da owner su dbdev, 399 file che toccano preventivo, bolla, capability, matrici e verbo comune: con
`-37` … `-48` applicati, i rossi dovuti al giro sono 21, in tre famiglie; `-49` … `-51` non cambiano nessun
esito. Il controesempio vero è il primo: **14 pgTAP emettevano preventivi senza righe**, perché
`porta_a_stato` scriveva lo stato con un `UPDATE` e la regola stava solo nel verbo. Ora lo stato passa dal
verbo e la regola dal guard, su ogni strada. Si portano al builder `-52`, non ricopiando la riga in ogni test
(criterio dei builder, §4-octies). Le altre due famiglie: 6 test con l'`UPDATE` diretto (ora la porta; si
portano al verbo, così provano ancora il guard) e i test con la firma vecchia del verbo.

Rossi **non** del giro, lasciati: i test «rosso da owner» (scope, porta) e `vendite/test-vw-dash-aperto-v1`
(chiede EVASO a `porta_a_stato`, che è un passaggio di processo: rosso anche prima del giro).
**Portato il 2026-10-25:** il caso (b), «CHIUSO, non abortito, non transitato», era un preventivo EVASO con
una riga residua, cioè uno stato che il modello non ammette più: EVASO lo scrive solo la proiezione dello
smistamento quando nessuna riga è RESIDUA, quindi un preventivo EVASO è anche transitato. Il caso ora è un
**contratto CESSATO** (esito POSITIVO, `is_transitato` NULL, il giudizio è sospeso), su un cliente suo per non
sovrapporsi al contratto ATTIVO del test 8, cessato a mano dalla matrice con `valido_al` = oggi. Lo stesso file emetteva due preventivi senza righe
(quello NEGATIVO e quello dell'emittente B): ora passano da `fn_pgtap_crea_preventivo_con_righe` sulla
testata del test, come i 9 del porting. Da lanciare (Tid).

**Portati (2026-10-25, tre agenti in parallelo), 22 file:** i 9 che scrivevano la testata a mano e la
emettevano senza righe passano a `fn_pgtap_crea_preventivo_con_righe(…, p_preventivo_id => …)`; i 5 col
builder in uno stato oltre la bozza passano al builder con le righe; 6 test con l'`UPDATE` diretto passano dal
verbo (con `emetti_preventivo` concessa) e provano ancora il **guard**, non la porta; il test del verbo e
quello dell'annullo con legami alla firma a due argomenti. Due test erano verdi per la ragione sbagliata e ora
discriminano: `test-fn-cambia-stato-preventivo` 7 e 8 (`throws_ok NULL` passavano sulla funzione
inesistente) e `test-preventivi-guard-transizione-v1` 3 (prendeva il P0001 della porta).
**Regressione finale da owner su dbdev, 400 file, con `-49` … `-52` in testa:** i 20 file rossi hanno gli
stessi test rossi di prima del porting (rossi da owner o rossi preesistenti), più il 22 del test nuovo,
rosso da owner per costruzione. Nessuna regressione.

**Attese cambiate nel porting, da guardare (Tid):**
* `vendite/test-preventivi-guard-transizione-v1` 6: contava due funzioni che sollevano
  `E_PREV_TRANSIZIONE_NON_AMMESSA` (verbo e guard); dal `-42` il verbo non ricopia la matrice, e il test ora
  asserisce che lo solleva **solo** il guard (sede unica);
* `vendite/test-fn-list-preventivi-da-pushare-v1` 7: «riga inattiva esclusa» costruiva un preventivo ACCETTATO
  con la sola riga spenta, che il modello non ammette più; ora il preventivo ha anche una riga attiva e il test
  asserisce **a livello di riga** (la spenta assente, l'attiva presente): più stretto, forma diversa;
* `script/test-fn-available-actions-preventivo-v1` 2: un ACCETTATO «senza righe» con la sola azione `annulla`
  non si costruisce più (senza residuo il preventivo è EVASO); con la riga di merce compare anche
  `genera_ordine`, e l'attesa è ora `["annulla","genera_ordine"]`. Il test 8, che leggeva un motivo da quel
  preventivo, lo legge ora dal preventivo in bozza, per non perdere una sorgente in silenzio;
* `dbops/test-fn-pgtap-crea-preventivo-v1`: due test in più (5b: il parametro di stato provato su ANNULLATO
  dalla bozza; 6b: il builder senza righe si ferma sull'emissione).

### 8.6 Attese cambiate e debiti, dichiarati

* **La proiezione dello smistamento è DEFINER** (`-45`). Prima un preventivo che chi chiamava non vedeva non si
  proiettava; ora sì, perché lo stato è la conseguenza dei residui, non una scelta di chi chiama. Il perimetro di
  chi agisce lo controllano i consumatori (il trigger delle righe di commessa legge sotto la RLS). EXECUTE resta
  PUBLIC: la chiama quel trigger per chiunque scriva le righe di commessa, anche un ruolo batch.
* **Il verbo fuori perimetro risponde `E_PREV_NOT_FOUND`** (prima `E_PREV_STATO_CORRENTE_NON_TROVATO`, che
  resta della revisione).
* **Righe all'emissione**: ora la regola vale su ogni strada, non solo dal verbo.
* **`cambia_stato_preventivi` non si spegne in questo giro.** Su dbdev è concessa a 4 profili e a 1 override:
  mettere `attivo = false` dal CSV fermerebbe il migrate sul guard delle figlie (vedi la memoria del ritiro di
  `approva_rimessa`). Si spegne quando il backend non la chiede più, togliendo prima a mano le concessioni.
  ⚠️ Chi oggi ha `cambia_stato_preventivi` **non** ha `emetti_preventivo`: la capability non gli mostra più
  «Emetti» e l'annullo dell'emesso, e il verbo glieli rifiuta. Concedere `emetti_preventivo` ai profili è un
  dato, da decidere (Tid).
* **EMESSO → SCADUTO non lo scrive nessuno**: la guida dei preventivi parlava di un job notturno che non
  esiste (verificato il 2026-10-25, DB e backend). Debito di prodotto, fuori da questo giro.
* Letterali rimasti, fuori dal perimetro del giro: `'ANNULLATO'` in `fn_annulla_preventivo` e nel verbo della
  bolla (la guida §8 vuole `is_abortito`).

### 8.7 Richiesta al team BE (elenco chiuso)

Percorso censito: `preventivi_repository.cambia_stato`, `preventivi_service.cambia_stato` / `emetti` /
`cambia_stato_da_pratica`, `ApiPreventivoStato`, `ApiPreventivoStatoDaPratica`, `ApiPreventivoCollegaPratica`,
la factory `/emetti/` del preventivo, `DocumentoModelloRepository`, i `get_stato_id_by_codice` dei repository.

1. **La firma del verbo.** `preventivi_repository.cambia_stato` chiama
   `vendite.fn_cambia_stato_preventivo(id, stato)`: il terzo argomento (`'django_api'`) non c'è più.
   **Oggi il cambio di stato del preventivo è rotto** finché non si cambia questa riga.
2. **Il 403 dalla riga del passaggio** (BB `PassaggioDocumento`): su `ApiPreventivoStato`,
   `ApiPreventivoStatoDaPratica` e `/emetti/` del preventivo (`emetti_passaggio` al posto di
   `emetti_post_permission="cambia_stato_preventivi"`). Le copie di `cambia_stato_preventivi` si ritirano.
   `ApiPreventivoCollegaPratica` non è un cambio di stato: il suo permesso lo decide il team BE (livello sul
   documento, o un'azione sua), ma non `cambia_stato_preventivi`, che si spegne.
3. **I lettori nuovi.** `DocumentoModelloRepository.azione_del_passaggio` legge
   `script.fn_doc_azione_passaggio` (o `script.fn_doc_stato_id` + `script.fn_doc_passaggio`) e non compone più
   SQL sulla mappa. I `get_stato_id_by_codice` di ordini, offerte, DDT e contratti sono la stessa traduzione:
   `script.fn_doc_stato_id` è la sede.
4. **L'emissione dal vocabolario (M-2).** `ddt_service.STATO_EMESSO` e il letterale `'EMESSO'` di
   `preventivi_service.cambia_stato` si ritirano: il cambio di stato generico rifiuta lo stato con
   `emissione = true` (colonna `emissione` di `fn_doc_azione_passaggio`, o `script.fn_stato_emissione_id`), per
   ogni documento della factory; `/emetti/` lo prende dallo stesso lettore.
5. **Controesempio.** `cambia_stato` verso ACCETTATO da ACCETTATO (aggiornare la modalità di fatturazione)
   chiama il verbo con lo stesso stato: la matrice non ha la riga 4→4 e la risposta è
   `E_PREV_TRANSIZIONE_NON_AMMESSA`. Il ramo «no-op» deve aggiornare i due campi senza chiamare il verbo.
6. **Da sapere, nessuna modifica attesa:** il verbo fuori perimetro risponde `E_PREV_NOT_FOUND`; un passaggio
   di processo chiesto (ACCETTATO → EVASO, EMESSO → SCADUTO) risponde `E_DOC_PASSAGGIO_DI_PROCESSO`; la
   capability nasconde «Emetti» e l'annullo dell'emesso a chi non ha `emetti_preventivo`. Nessun codice nuovo:
   la policy non si rigenera per questo giro.
7. **Test Django** che scrivono lo stato del preventivo con un `UPDATE` o chiamano il verbo a tre argomenti: si
   portano al verbo (o a `dbops.fn_pgtap_porta_a_stato`). Censimento del 2026-10-25: nessuna chiamata diretta
   nei test, solo il repository (punto 1).

### 8.8 Applicato e verde (2026-10-25)

Tid: `-49` … `-52` applicati, corsa pgTAP verde. Il giro DB 6 è chiuso; restano a DB solo lo spegnimento di
`cambia_stato_preventivi` dopo il giro BE e il dato dei profili (§8.6).

### 8.9 Anticipati: le concessioni passano a `emetti_preventivo`, `cambia_stato_preventivi` si spegne (2026-10-25)

Tid: i due passi del §8.6 si fanno subito, prima del giro BE.

✅ 2026-10-25: script eseguito su dbdev (4 + 1 righe), migrate applicato da Tid: `cambia_stato_preventivi` spenta.

* **Le concessioni** (dato di dbdev, nessun CSV le semina): le righe di `config.profili_accesso_azioni` (4: profili
  1, 3, 9221 negati, 9222 concesso) e di `config.user_override_azioni` (1, utente 6, concesso) passano da
  `cambia_stato_preventivi` a `emetti_preventivo`, **con lo stesso `abilitata`**: chi poteva emettere può
  ancora, chi era negato resta negato, e l'azione vecchia resta senza figlie. Script nel brief, sotto; provato
  in transazione su dbdev il 2026-10-25 (4 + 1 righe, zero residue, lo spegnimento passa il guard).
* **`cambia_stato_preventivi` spenta** nel CSV di `config.azioni_processo` (`attivo = false`, descrizione
  «ritirata»). ⚠️ **Ordine: prima lo script, poi il migrate**: con una figlia ancora attaccata il mirror di
  febbraio (`20260228-18`) si ferma sul guard delle figlie. Su un database da zero non ci sono figlie.
* ⚠️ **Il backend**: finché `post_permission = "cambia_stato_preventivi"` resta nelle tre view e nella factory,
  quegli endpoint rispondono 403 a tutti (l'azione è spenta). Era già rotto dalla firma del verbo (§8.7 punto
  1): il punto 2 della richiesta lo ripara.

```sql
UPDATE config.profili_accesso_azioni x
   SET azione_id = (SELECT a.id FROM config.azioni_processo a WHERE a.permission_codename = 'emetti_preventivo')
 WHERE x.azione_id = (SELECT a.id FROM config.azioni_processo a WHERE a.permission_codename = 'cambia_stato_preventivi');
UPDATE config.user_override_azioni x
   SET azione_id = (SELECT a.id FROM config.azioni_processo a WHERE a.permission_codename = 'emetti_preventivo')
 WHERE x.azione_id = (SELECT a.id FROM config.azioni_processo a WHERE a.permission_codename = 'cambia_stato_preventivi');
```


### 8.10 Fatto dal team BE (2026-10-25) e richiesta al team DB

**Fatto** (`dev/backend-tid`, da committare), sulla richiesta del §8.7:

1. **La firma del verbo.** `PreventiviRepository.cambia_stato(id, stato)` chiama
   `vendite.fn_cambia_stato_preventivo` a due argomenti; tolto il `'django_api'` dai tre chiamanti.
2. **Il 403 dalla riga.** `post_passaggio = PassaggioDocumento(...)` su `ApiPreventivoStato`,
   `ApiPreventivoStatoDaPratica` e `/emetti/` del preventivo (`emetti_passaggio`), con
   `model_permission = ("vendite", "preventivo")` per le righe senza azione. Il BB prende due campi
   nuovi: `campo_stato` (il preventivo porta lo stato in `nuovo_stato`, non in `stato_codice`) e
   `risolvi_documento` (la rotta dalla pratica porta il `pratica_id`: il preventivo ROOT lo ricava
   la stessa lettura del service). `ApiPreventivoCollegaPratica` chiede il **livello sul preventivo**:
   non è un passaggio, è una modifica del documento (scelta del team BE, come chiedeva il punto 2).
   Le tre copie di `cambia_stato_preventivi` ritirate; con loro `emetti_post_permission` della factory
   documenti, che non aveva più consumatori (e il controllo di esclusività che gli stava accanto).
3. **I lettori nuovi.** `DocumentoModelloRepository.azione_del_passaggio` legge
   `script.fn_doc_azione_passaggio`: nessun SQL composto sulla mappa. Una testata fuori mappa ora è
   `E_SCRIPT_CHIAMATA_NON_VALIDA` dal DB (prima un `RuntimeError` del backend: sempre un 500). I
   quattro `get_stato_id_by_codice` (ordini, offerte, DDT, contratti) delegano a
   `DocumentoModelloRepository.stato_id` → `script.fn_doc_stato_id`: ora leggono solo gli stati
   **attivi** anche offerte e contratti (U-3; prima no). La testata di ogni documento sta nel suo
   repository (`TESTATA_<DOC>`), una sede sola per service, view e catena dei permessi.
4. **L'emissione dal vocabolario, sul cambio stato generico.** BB nuovo
   `core/services/documento_modello.rifiuta_stato_di_emissione` (regola del 2): rifiuta lo stato con
   `emissione = true` (`fn_doc_stato_id = fn_stato_emissione_id`), 400 del dominio col campo del corpo.
   Montato su bolla, preventivo, contratto **e ordine**. Ritirati i letterali `EMESSO` (bolla,
   preventivo) e `ATTIVO` (contratto). ⚠️ Per l'**ordine** è un cambio di comportamento: il cambio
   stato generico accettava CONFERMATO (opzione (i) del 2026-06-05, revocata da M-2); il frontend non lo
   usava (passa da «Emetti»). Resta com'è `POST /ordini/<id>/conferma/` (la conferma senza PDF): è il
   «censire chi emette senza /emetti/» di M-2, da decidere nel giro dell'ordine. L'offerta non ha un
   cambio stato generico.
5. **Controesempio.** ACCETTATO → ACCETTATO aggiorna la modalità di fatturazione e non chiama il
   verbo; la risposta ha `stato_precedente = stato_nuovo = ACCETTATO`.
7. **Test.** Nessuna chiamata diretta al verbo nei test (come censito). Emerso: le classi di test dei
   quattro service chiedevano al DB lo stato di emissione; mixin nuovo `ModelloDocumentoMockatoMixin`
   (mock sul repository del BB, default «non è l'emissione»). Due classi sovrascrivevano `setUp` senza
   `super()` (ordini, preventivi): il mock non si applicava, e `TestPreventiviService`
   (`unittest.TestCase`) avrebbe interrogato il DB di sviluppo. Test nuovi: il rifiuto sull'ordine,
   l'ACCETTATO che non chiama il verbo, i due campi del BB, le rotte del preventivo nel presidio
   `test_passaggio_rotte`, le dichiarazioni delle view; sul DB reale
   `test_permesso_passaggio_db` (preventivo, stato di emissione, `stato_id`, testata fuori mappa) e il
   nuovo `test_preventivo_cambia_stato_db` (verbo a due argomenti, accettazione, ACCETTATO →
   ACCETTATO, il 400 dell'emissione), con le sonde sulle firme finali.
8. **Revisione critica dello stesso giro.** `_parse_cambio_stato_payload` leggeva `nuovo_stato` con
   `str(payload.get(...))`: `null` diventava `"None"`, e senza lo strip il rifiuto dell'emissione
   guardava un codice diverso da quello del permesso (`PassaggioDocumento` ripulisce). Ora
   `PayloadValidator.require_string` (400 col campo), con due test. `TESTATA_DDT` si importa dal
   repository anche in `views_ddt` e `ddt_documenti_views` (non più via `ddt_service`); il test della
   testata fuori mappa legge il codice dal campo strutturato (`structured_db_error_code`), non dal testo.

Doc: catalogo BB backend (`PassaggioDocumento`, voce nuova `rifiuta_stato_di_emissione`, factory),
`api.md`, `api_preventivi`, `api_preventivi_collega_pratica`, `api_documenti_per_sorgente`, e una
nota nella guida del modello (riga del preventivo: «il backend chiede ancora `cambia_stato_preventivi`»
non era più vero). ⚠️ Non toccato, è del team DB: `docs/it/dbzero/config/manual/azioni_processo.md`
elenca ancora `cambia_stato_preventivi` come attiva e non ha `emetti_preventivo`.

**Provato:** suite completa con `ZEROERP_TEST_DB_E2E=1`, 6940 test: due rossi, entrambi ricadute del
giro DB 6 e non del codice di questo giro, corretti e rilanciati verdi: l'etichetta it/en della colonna
nuova `emissione` dei vocabolari (`config_panel.campi.emissione`, presidio
`test_config_panel_registro_db`, lo stesso caso di `iniziale` al primo giro) e la fixture di
`test_ricerca_liste_db`, che emetteva un preventivo senza righe (il controesempio del §8.5): ora passa da
`dbops.fn_pgtap_crea_preventivo_con_righe`. I due presidi della policy sono verdi (nessun codice nuovo).
mypy (cricchetto, 0 rilievi) e ruff puliti. ⚠️ Non eseguiti gli smoke HTTP (login col secondo fattore).

**Non fatto, e perché: il codice dello stato di emissione per «Emetti».** Il §8.7 punto 4 chiede che
`/emetti/` prenda lo stato dal lettore e che `ddt_service.STATO_EMESSO` si ritiri. Il verbo di bolla e
preventivo prende il **codice** dello stato; il DB dà l'**id** (`fn_stato_emissione_id`) e nessun lettore
traduce id → codice. Leggerlo dal vocabolario nel backend vorrebbe dire comporre di nuovo SQL sulla mappa
(quello che il punto 3 ha appena tolto). Restano quindi, dichiarati con questo rimando: `STATO_EMESSO` in
`ddt_service` e in `preventivi_service` (una sede per documento, usata da `emetti` e dalla factory), e
`emetti_passaggio=(testata, stato)`.

**Richiesta al team DB (per il giro dopo):** un lettore del **codice** dello stato, gemello di
`script.fn_doc_stato_id`, per esempio `script.fn_doc_stato_codice(p_testata regclass, p_stato_id bigint)
RETURNS text` (oppure direttamente il codice dello stato di emissione di una testata: lo sceglie il team
DB). Con quello il backend legge una volta `fn_doc_stato_codice(t, fn_stato_emissione_id(t))`: si
ritirano i due `STATO_EMESSO`, `emetti_passaggio` riceve la sola testata, e il presidio dell'emissione
diventa generico sui documenti della factory. Ricaduta BE: il repository del modello e le due view
documentali.

**Residui per i giri dei documenti** (non toccati, per memoria): `contratti_service.emetti` e
`ordini_service.conferma` cercano lo stato di emissione per codice scritto (`"ATTIVO"`,
`_STATO_CONFERMATO`) ma scrivono l'id: lì basterebbe già `fn_stato_emissione_id`; `offerte_service.emetti`
usa `StatoOfferta.EMESSA`. Si allineano col giro del loro documento. ➡️ Superato da V-2 (§8.11): si
chiudono nello stesso passaggio BE.

### 8.11 Chiusura della richiesta del §8.10: il codice dello stato di emissione (2026-10-25)

Analisi del team DB sul percorso intero (lettori DB, repository del modello, factory documentale,
service), poi le decisioni di Tid. Lo scopo: dare al backend in un giro solo tutto quello che serve a
chiudere 4-bis-octies, senza residui per i giri dei documenti.

**Il punto che la richiesta non diceva.** «Emetti» fissa lo stato chiesto quando la view si definisce
(`emetti_passaggio=(TESTATA, STATO_EMESSO)` nelle due view documentali → `PassaggioDocumento(stato_chiesto=…)`),
cioè all'import, dove il DB non si interroga. Sostituire la costante col lettore sposterebbe il
letterale, non lo ritirerebbe: il permesso di «Emetti» deve chiedere lo stato di emissione **a ogni
richiesta**. Da qui `emetti_passaggio` con la sola testata.

**Fatti letti dalla struttura (2026-10-25).** I cinque vocabolari con la colonna `emissione` la
dichiarano tutti nei CSV di `80_data` (ordine `CONFERMATO`, preventivo `EMESSO`, bolla `EMESSO`,
offerta `EMESSA`, contratto `ATTIVO`); il CHECK `chk_stati_doc_<doc>_emissione_attivo` garantisce che lo
stato di emissione sia attivo. Reso, commessa e fattura non si emettono: `fn_stato_emissione_id` dà NULL.
I verbi di bolla e preventivo prendono il `codice_interno` e lo traducono con `fn_doc_stato_id`.

**Decisioni di Tid (2026-10-25).**

| # | Domanda | Decisione |
| --- | --- | --- |
| V-1 | Un lettore generico id → codice, o uno apposta per il codice dell'emissione | ✅ **Generico**: `script.fn_doc_stato_codice(p_testata regclass, p_stato_id bigint) RETURNS text`, gemello inverso di `fn_doc_stato_id`. Uno stato ha due chiavi (id e `codice_interno`): la traduzione nei due sensi sta nella stessa coppia; un lettore dell'emissione sarebbe una terza lettura della stessa cosa. Il backend compone `fn_doc_stato_codice(t, fn_stato_emissione_id(t))` |
| V-2 | Contratto, ordine e offerta nello stesso passaggio BE, o al giro del loro documento | ✅ **Stesso passaggio**: poggiano su pezzi comuni già fatti (scelta C del fermo). Per l'ordine si ritira solo il letterale: chi conferma senza `/emetti/` (M-2) resta al giro dell'ordine |
| V-3 | Archiviare subito `brief-db-documento-nasce-nello-stato-iniziale` | ✅ **Sì**: N-1 … N-3 decise qui (§4-bis) e costruite nel primo giro (§4-quinquies). Archiviato in `work-done/` il 2026-10-25, D32 chiuso nel registro |

**Il contratto del lettore (V-1).**

* Il codice che rende è il `codice_interno`, la chiave stabile, quella che leggono i verbi.
* Testata fuori mappa (`script.fn_doc_stato_modello`): `E_SCRIPT_CHIAMATA_NON_VALIDA`, come i gemelli.
* Id NULL o che il vocabolario non ha: NULL, decide il chiamante. Per «Emetti» un NULL vuol dire
  documento che non si emette: la factory monta `emetti_passaggio` solo dove l'emissione esiste.
* Nessun filtro sugli attivi: un id è già una riga esistente, e uno stato spento come destinazione lo
  rifiuta il verbo con `fn_doc_stato_id` (U-3). Per l'emissione il caso non si pone (il CHECK).
* `STABLE`, `SECURITY INVOKER` esplicito; parametri `bigint` e non `%TYPE` (vocabolario polimorfo, come i gemelli).

**Elenco chiuso, giro DB (dopo il via di Tid).**

| # | Che cosa |
| --- | --- |
| K-1 | ChangeSet in `20_code/script`: `script.fn_doc_stato_codice` (numero al prossimo progressivo del giorno, riletto prima di salvare) |
| K-2 | COMMENT di `script.fn_stato_emissione_id` e `script.fn_doc_stato_id`: il gemello e i consumatori nuovi («Emetti» del backend) |
| K-3 | pgTAP: per le cinque testate con l'emissione, il codice reso è quello che il vocabolario dichiara (letto dalla colonna, non scritto nel test); testata senza emissione → NULL; id inesistente → NULL; testata fuori mappa → `E_SCRIPT_CHIAMATA_NON_VALIDA`; andata e ritorno con `fn_doc_stato_id` |
| K-4 | `docs/it/dbzero/script/manual/fn_doc_stato_codice.md`; la coppia di lettori nella guida del modello |
| K-5 | `docs/it/dbzero/config/manual/azioni_processo.md`: `cambia_stato_preventivi` non più attiva, `emetti_preventivo` presente (§8.9) |
| K-6 | Questo brief: l'esito del giro e il passaggio al BE |

**Elenco chiuso, passaggio BE (dopo l'apply del giro DB).**

| # | Che cosa |
| --- | --- |
| B-1 | `DocumentoModelloRepository`: il codice dello stato di emissione di una testata (una lettura, i due lettori composti); NULL → il documento non si emette |
| B-2 | Il permesso di «Emetti» chiede lo stato a ogni richiesta: `emetti_passaggio` riceve la sola testata, `PassaggioDocumento` risolve lo stato chiesto dal lettore |
| B-3 | Ritirati `STATO_EMESSO` in `ddt_service` e `preventivi_service`: «Emetti» passa al verbo il codice letto |
| B-4 | V-2: `contratti_service.emetti` e `ordini_service.conferma` su `fn_stato_emissione_id` (scrivono l'id); `offerte_service.emetti` sul codice letto al posto di `StatoOfferta.EMESSA`; ritirati `"ATTIVO"` e `_STATO_CONFERMATO` |
| B-5 | Il presidio dell'emissione generico sui documenti della factory; test sul DB reale del lettore composto (le cinque testate, una senza emissione) |
| B-6 | Guida del modello, §«L'emissione», riga «Quale stato è l'emissione»: «Emetti» ne legge il codice con `script.fn_doc_stato_codice` (si scrive quando è vero, cioè con B-3) |

**Scritto e provato (team DB, 2026-10-25, dopo il via di Tid).**

| # | Fatto |
| --- | --- |
| K-1 | `20_code/script/20261025-70-create-fn-doc-stato-codice`: `script.fn_doc_stato_codice(regclass, bigint) RETURNS text`, `STABLE`, `SECURITY INVOKER`, il contratto qui sopra. Il `-69` era gia' preso dal lotto della grammatica |
| K-2 | `20_code/script/20261025-71-update-fn-doc-stato-id-emissione-commento-gemello`: i due COMMENT (il gemello inverso; «Emetti» fra i consumatori). Corpi invariati |
| K-3 | `db/pgtap/script/test-doc-stato-codice-v1.sql` (plan 8): forma; emissione composta sulle cinque testate contro la colonna `emissione` dei vocabolari; NULL su reso, commessa, fattura; andata e ritorno con `fn_doc_stato_id` su ogni stato attivo delle otto testate (contando gli stati provati, niente verde per sottrazione); id assente e NULL; stato spento che rende il suo codice; fuori mappa |
| K-4 | `docs/it/dbzero/script/manual/fn_doc_stato_codice.md`; il lettore nell'area tecnica della guida del modello. La riga «Emetti» della guida e' B-6: oggi non e' ancora vera |
| K-5 | `docs/it/dbzero/config/manual/azioni_processo.md`: `cambia_stato_preventivi` ritirata, `emetti_preventivo` con la sua forma (l'azione sulla riga del passaggio, come `emetti_ddt`) |
| K-6 | Questo paragrafo e il blocco «Chi riparte» |

**Provato** su dbdev, come owner, in transazione annullata (`BEGIN` e `ROLLBACK` del file, `psql -v ON_ERROR_STOP=1`): l'SQL estratto dai due YAML davanti al pgTAP nuovo, 8 eseguiti su 8 pianificati, tutti `ok`; lo stesso SQL davanti a `dbops/test-riferimenti-morti-v1` (plpgsql_check su ogni funzione), 9/9 (`ok 8` e' lo `skip` dichiarato del file). La corsa come app e lo scratch restano a Tid, dopo l'apply.

✅ **Applicato e verde** (Tid, 2026-10-25): `-70` e `-71` EXECUTED su dbdev alle 15:27 (`databasechangelog`), corsa pgTAP verde.

### 8.12 Cosa resta al cantiere, lato DB (censimento del 2026-10-25)

Letto dalla guida del modello (§10, la tabella per documento), dai debiti dichiarati dei giri (§7.7, §8.6, §4-septies)
e dai corpi vivi (doc auto-generata). Elenco chiuso: ogni cosa che manca è una riga qui, o non manca.

**I documenti ancora da portare al modello** (un documento per giro, tutto intero: §5). Fra parentesi quello che
la guida §10 segna ❌.

| # | Documento | Che cosa manca | Note |
| --- | --- | --- | --- |
| D-1 | Ordine (+ ordine d'acquisto, §5) | verbo di stato, azione sul passaggio, annullo dal verbo (`fn_annulla_ordine` scrive da sé) | matrice in tabella e colonna `emissione` già ci sono; da decidere qui `POST /ordini/<id>/conferma/` (M-2: chi conferma senza «Emetti»); l'ordine d'acquisto oggi non ha guard di transizione |
| D-2 | Commessa | l'azione `cambia_stato_commessa` sulla riga del passaggio e controllata dal verbo (oggi solo dal backend) | il più piccolo: verbo, matrice e annullo ci sono; matrice in `vendite`, non in `config` |
| D-3 | Contratto | matrice in tabella (oggi scritta nel guard), verbo, azione, annullo dal verbo | il backend scrive lo stato con `UPDATE` |
| D-4 | Offerta | verbo, azione, annullo con l'avviso dei legami invece di `fn_check_offerta_annullabile`; il nome della matrice fuori serie (`stati_doc_offerte_transizioni`) | gli stati di partenza ripetuti in Python |
| D-5 | Fattura | verbo al posto delle funzioni della pipeline e dell'`UPDATE` dello stato del lotto; azioni della pipeline sulla riga | il più lungo: tocca la pipeline di fatturazione |
| D-6 | Versione di listino | vocabolario degli stati (oggi testo con `CHECK`), matrice in tabella (oggi nel guard e in Python), verbo | parte da zero |
| D-7 | DDT d'acquisto | tutto | ⏸️ T-2 di Tid: aspetta il satellite per ambito (D-3 di analisi-simmetria-ordini-acquisto) |

**I debiti DB dichiarati e ancora aperti.**

| # | Debito | Dove è scritto |
| --- | --- | --- |
| X-1 | Letterali `'ANNULLATO'` in `vendite.fn_annulla_preventivo` (chiama il verbo con il codice) e in `vendite.fn_cambia_stato_ddt` (riconosce l'annullo dell'emesso confrontando il codice): la guida §8 vuole lo stato abortito letto dal vocabolario (`is_abortito`) | §8.6 |
| X-2 | EMESSO → SCADUTO del preventivo non lo scrive nessuno: la guida dei preventivi parlava di un job notturno che non esiste | §8.6 (debito di prodotto) |
| X-3 | R-7, R-8: due casi dei builder delle fixture | §4-septies, «non ora» per decisione di Tid: restano chiusi così |

Fuori da questo brief: pagamenti e magazzino (§3.1, «stessa domanda»); il tema è di tutte le famiglie e non si
apre senza l'ok di Tid (AGENTS.md).

**Decisioni per Tid.**

| # | Domanda | Consiglio del team DB |
| --- | --- | --- |
| W-1 | Il documento del giro dopo, e l'ordine dei successivi — ✅ **Tid 2026-10-25: l'ordine, senza acquisti; poi contratto, offerta, commessa, fattura, listino** | **D-1, l'ordine** (col gemello d'acquisto): è il più vicino al modello dopo bolla e preventivo, ha già matrice ed emissione, e chiude la domanda aperta di M-2 su `/conferma/`. Poi D-2 (piccolo), D-3, D-4, D-5, D-6. D-7 resta fermo su T-2 |
| W-2 | X-1: un giro a sé subito, o dentro il giro del prossimo documento | **Dentro il giro dell'ordine**: il lettore dello stato abortito serve anche lì (`fn_annulla_ordine`), e nasce una volta sola per i tre (regola del 2) |
| W-3 | X-2: lo scrive un job del DB, o si toglie SCADUTO dal modello del preventivo | Decisione di prodotto: se resta, è un processo con la sua riga di matrice di processo (`manuale = false`, già così) e un job; lo si scrive in un brief suo, non in questo |

## 9. Giro 7: l'ordine al modello — ricognizione e piano (2026-10-25)

✅ **Deciso da Tid il 2026-10-25 (W-1):** il documento del giro è l'**ordine di vendita**. L'ordine d'acquisto
**non** entra: come per il DDT (T-2), gli acquisti arrivano al modello tutti insieme, quando parte quel
cantiere (eccezione dichiarata alla regola del §5, «nello stesso giro»; i pezzi comuni restano generici).
Ordine dei giri dopo: contratto, offerta, commessa, fattura, versione di listino.

### 9.1 Com'è oggi (doc auto-generata e `backend/`, 2026-10-25)

* **Vocabolario e matrice.** `config.stati_doc_ordini`: DRAFT (iniziale), CONFERMATO (emissione), ALLOCATO,
  SPEDITO, CONSEGNATO, PARZIALMENTE_EVASO, EVASO, FATTURATO, ANNULLATO (`is_abortito`). Matrice
  `config.transizioni_stati_ordini`, nove righe: tre **manuali** (DRAFT → CONFERMATO «conferma», DRAFT →
  ANNULLATO e CONFERMATO → ANNULLATO «annulla») e sei **di processo** (`manuale: false`, fra CONFERMATO,
  PARZIALMENTE_EVASO ed EVASO). La matrice **non ha** la colonna `azione_processo_codename`. ALLOCATO,
  SPEDITO, CONSEGNATO e FATTURATO non hanno righe: nessun passaggio li raggiunge (si dichiara, non si tocca).
* **Guard di transizione** `trgfn_ordini_guard_transizione`: matrice, righe attive su DRAFT → CONFERMATO,
  `fn_check_ordine_confermabile`, `fn_check_ordine_annullabile`, prezzi autorizzati. Letterali `'DRAFT'`,
  `'CONFERMATO'`, `'ANNULLATO'`: condizioni di un passaggio, restano (come sul preventivo, §8.1).
* **Verbo di stato: non c'è.** Lo scrivono:
  * il **backend** con un `UPDATE` (`OrdiniRepository.update_stato`), da `ordini_service.conferma` (usata da
    «Emetti» **e** da `POST /ordini/<id>/conferma/`) e dal cambio stato generico. Sul generico, dopo il §8.10, non
    resta nessun passaggio manuale da scrivere con l'`UPDATE`: la conferma è rifiutata (emissione), l'annullo
    passa già da `fn_annulla_ordine`;
  * `vendite.fn_annulla_ordine` (DEFINER, ritira i legami) con un `UPDATE` suo e il letterale `'ANNULLATO'`;
  * `vendite.fn_ordine_proietta_stato_evasione` (**INVOKER**), i sei passaggi di processo, con un `UPDATE`.
    La chiamano `fn_genera_ddt_da_ordine`, i cinque verbi del reso, `fn_ddt_riga_correggi_qta_evasa` e il trigger
    `trgfn_dlt_block_ordrig_ddtrig`.
* **Azione: nessuna.** Nessuna azione dell'ordine a catalogo (`config.azioni_processo`).
* **«Emetti» e `/conferma/`.** `/emetti/` della factory chiama `ordini_service.conferma` e genera il PDF; dentro
  la stessa transazione completa lo step `CONFERMA_ORDINE` della pratica. `POST /ordini/<id>/conferma/` fa la sola
  transizione, senza PDF: il frontend la espone (`ordiniApi.confermaOrdine`, azione `conferma` dello store) ma
  **nessun componente la chiama** (letto il 2026-10-25). È il «chi conferma senza Emetti» di M-2.
* **Numero alla nascita.** `trgfn_ordini_gen_numero` numera l'ordine all'INSERT, scelta dichiarata nel corpo
  («l'ordine nasce numerato… i buchi da bozza scartata restano»). La guida §7 dice «il numero lo assegna il
  database al passaggio allo stato emesso»: è una divergenza (Z-4).
* **Capability** `fn_available_actions_ordine`: matrice e motivi; nessun filtro sull'azione.
* **pgTAP:** 19 file scrivono lo stato dell'ordine con un `UPDATE` diretto; 10 lo portano in EVASO o
  PARZIALMENTE_EVASO, che sono passaggi di processo: con la porta si costruiscono evadendo davvero
  (`dbops.fn_pgtap_crea_ddt_da_ordine`, già a catalogo). Conteggio del 2026-10-25, per dimensionare il porting.

### 9.2 Il piano

| Pezzo | Che cosa |
| --- | --- |
| matrice | colonna `azione_processo_codename` su `config.transizioni_stati_ordini` (FK alla chiave stabile, come preventivo e bolla), valori dal CSV: l'azione su DRAFT → CONFERMATO e CONFERMATO → ANNULLATO (Z-1); mirror con la colonna (⚠️ `nullValue`) |
| azione | `emetti_ordine` a catalogo (Z-1) |
| verbo | NUOVO `vendite.fn_cambia_stato_ordine(p_ordine_id, p_stato)`, gemello di quello del preventivo: DEFINER col predicato del perimetro (`fn_scope_ef_whitelist_via_ordine`), `fn_doc_stato_id`, `fn_guard_passaggio`, `fn_doc_scrivi_stato` |
| porta | `trgfn_doc_stato_solo_dal_verbo` montato `_a05_` su `vendite.ordini` |
| annullo | `fn_annulla_ordine` chiama il verbo (lo stato d'annullo dal vocabolario se Z-3 = sì) |
| processo | `fn_ordine_proietta_stato_evasione` scrive con `fn_doc_scrivi_stato` (sola seconda metà) e diventa DEFINER, come la proiezione del preventivo (`-45`) |
| capability | `fn_available_actions_ordine`: il passaggio con l'azione si nasconde a chi non ce l'ha (stessa forma di bolla e preventivo) |
| fixture | `fn_pgtap_porta_a_stato` conosce il verbo dell'ordine; i 19 `UPDATE` diretti portati: al verbo dove provano il guard, a `crea_ddt_da_ordine` dove serve un EVASO o un PARZIALMENTE_EVASO |
| guida | §10, riga dell'ordine; la guida degli ordini rimanda al modello |

**Richiesta al BE** (si scrive col percorso intero, a giro DB provato): `OrdiniRepository.update_stato` si ritira
e `conferma` chiama il verbo (lo step della pratica resta nella stessa transazione); il 403 dalla riga del passaggio
(`PassaggioDocumento`) su «Emetti» e sull'annullo; il cambio stato generico senza `UPDATE`; `/conferma/` secondo Z-2;
`_STATO_CONFERMATO` già nel passaggio B-4 del §8.11.

### 9.3 Domande per Tid

✅ **Decise da Tid il 2026-10-25: Z-1, Z-2, Z-3, Z-4 come da proposta; W-3 in un brief separato
([brief-db-scadenza-preventivi](brief-db-scadenza-preventivi.md)); via allo sviluppo.**

* **Z-1. L'azione dell'ordine.** Proposta: azione **nuova** `emetti_ordine` («emette un ordine o annulla un ordine
  confermato») sulle righe DRAFT → CONFERMATO e CONFERMATO → ANNULLATO; DRAFT → ANNULLATO senza azione. È la guida §6
  («un'azione per documento, sui passaggi pesanti») e il gemello di `emetti_ddt` ed `emetti_preventivo`. ⚠️ Nessun
  profilo la riceve dai seed: dopo il giro chi non ce l'ha non vede «Emetti» né l'annullo del confermato. Concederla
  ai profili è un dato (su dbdev lo fa Tid, come per `emetti_preventivo`).
* **Z-2. `POST /ordini/<id>/conferma/`.** Proposta: **si ritira** (rotta, view, API e azione dello store del
  frontend, che nessun componente chiama). È l'ultimo «conferma senza Emetti» (M-2): l'ordine si conferma solo da
  «Emetti», con numero e PDF insieme. Alternativa: resta, e chiede la stessa azione di «Emetti».
* **Z-3 (era W-2). Lo stato d'annullo dal vocabolario.** Proposta: **sì, in questo giro**: lettore
  `script.fn_stato_abortito_id(p_testata)` (gemello di `fn_stato_iniziale_id` e `fn_stato_emissione_id`) e indice unico
  parziale su `is_abortito` nei vocabolari (oggi ognuno ne ha uno solo: fatto letto dai CSV, la regola è sul
  modello, «un documento ha un solo stato d'annullo»). Lo leggono `fn_annulla_ordine`, `fn_annulla_preventivo` e il
  verbo della bolla, che oggi scrivono `'ANNULLATO'` (X-1 chiuso). Alternativa: X-1 resta debito, l'ordine nasce col
  letterale come il preventivo.
* **Z-4. Il numero alla nascita.** L'ordine si numera all'INSERT, la guida §7 lo vuole all'emissione. Proposta:
  **fuori da questo giro**, dichiarato come divergenza nella riga dell'ordine della guida §10: spostarlo cambia la
  numerazione (e i buchi da bozza scartata), è un tema suo da decidere con la storia della scelta
  (`trgfn_ordini_gen_numero`, rev 2026-08-31). Alternativa: si porta in questo giro.

### 9.4 Scritto (2026-10-25)

| # | Cosa |
| --- | --- |
| `-72` | un solo stato d'annullo per vocabolario, ed è attivo: indice unico parziale `uq_<voc>_abortito` e CHECK `chk_<voc>_abortito_attivo` sugli otto vocabolari (Z-3) |
| `-73` | colonna `azione_processo_codename` su `config.transizioni_stati_ordini` (FK alla chiave stabile) |
| CSV | `azioni_processo`: `emetti_ordine` (id 41); matrice dell'ordine: `emetti_ordine` su DRAFT → CONFERMATO e CONFERMATO → ANNULLATO; mirror `20260605-11` con la colonna e `nullValue: "NULL"` |
| `-74` | NUOVO `script.fn_stato_abortito_id(testata)`: lo stato d'annullo dal vocabolario, gemello di `fn_stato_emissione_id` |
| `-75` | NUOVO `vendite.fn_cambia_stato_ordine(id, stato)`: il verbo dell'ordine sul verbo comune, DEFINER col predicato del perimetro; EXECUTE solo all'app |
| `-76` | `fn_annulla_ordine` chiama il verbo, con lo stato d'annullo dal vocabolario |
| `-77` | `fn_annulla_preventivo`: lo stato d'annullo dal vocabolario (X-1) |
| `-78` | `fn_cambia_stato_ddt`: l'annullo dell'emessa riconosciuto dallo stato d'annullo del vocabolario (X-1) |
| `-79` | `fn_ordine_proietta_stato_evasione` scrive con `fn_doc_scrivi_stato`, DEFINER (attesa cambiata dichiarata nel file: la proiezione vale per ogni ordine) |
| `-80` | la porta montata su `vendite.ordini` |
| `-81` | capability dell'ordine: il passaggio con l'azione si nasconde a chi non ce l'ha; motivi legati a `is_abortito` ed `emissione` |
| `-82` | `fn_pgtap_porta_a_stato`: l'ordine dal suo verbo |

Firme, `RETURNS TABLE` e `DECLARE` ancorati con `%TYPE`, anche nelle firme di GRANT e COMMENT (Tid, 2026-10-25);
`fn_cambia_stato_ddt` torna alle ancore di `20261001-20`. Prova in transazione: una sola funzione per nome dopo il
`CREATE OR REPLACE` (nessun sovraccarico nato dall'ancora).

Doc: pagine `manual` di `fn_stato_abortito_id` e `fn_cambia_stato_ordine`; la guida del modello (riferimenti, §8,
§10 riga dell'ordine con la divergenza del numero, Z-4); `gestione-ordini` §4.2 e §4.4; `azioni_processo.md`.
pgTAP nuovo: `vendite/test-ordine-al-modello-v1` (16; il 16 è rosso da owner, verde come app).

**Applicato da Tid** su dbdev alle 15:59, a metà della regressione (§9.5).

### 9.5 Regressione e porting dei pgTAP (2026-10-25)

La prima regressione prima/dopo (736 file che toccano documenti, stati, capability e presidi) non vale: l'apply di
Tid è caduto a metà corsa, e quattro corse in parallelo con la DDL dell'SQL estratto si sono bloccate a vicenda
(deadlock). Rifatta **in sequenza sul db migrato**, come owner: 70 file con almeno un rosso; letti uno per uno.

* **Del giro, 11 file**, tutti per la stessa causa: scrivevano lo stato dell'ordine con un `UPDATE` diretto (ora la
  porta), o cercavano «Conferma» con un utente senza `emetti_ordine`. Portati (tre agenti in parallelo, file
  diversi): al verbo dove provano il guard (con `emetti_ordine` concessa), a `porta_a_stato` o ai builder dove serve
  una fixture, all'**evasione vera** (`dbops.fn_pgtap_crea_ddt_da_ordine`) dove serviva un EVASO scritto a mano. Più
  il presidio `script/test-doc-verbo-comune-e-porta-v1`: la porta su quattro testate (anche l'ordine), e il
  «documento non ancora portato» del test 8 è ora la fattura, che arriva per ultima.
* **Non del giro, 59 file**: 57 con gli stessi rossi della corsa prima dell'apply (rossi da owner dichiarati e
  rossi preesistenti), 2 test di perimetro (`ddt-reason-catch-all` 18, `get-stato-push-segment` 12) rossi da owner
  per costruzione (l'owner salta la RLS), la cui corsa «prima» era morta nel deadlock.

**Dopo il porting**, rilanciati i 12 file (gli 11 e il test nuovo): tutti eseguiti contro il piano; rossi solo quelli
da owner dichiarati (`annullo-documento-con-legami` 30, `vw-situazione-merce-ordine` 11, `doc-verbo-comune-e-porta`
19 e 20, `ordine-al-modello` 16).

**Attese cambiate nel porting, da guardare (Tid):**
* `script/test-fn-check-prezzi-autorizzati-v1`: un test in più (30b, l'ordine è davvero EVASO dopo l'evasione), plan 45;
* `script/test-seed-stati-doc-ordini-evaso-v1` 5: da «la transizione CONFERMATO → EVASO è ammessa» (scritta a mano)
  a «l'evasione vera porta in EVASO»; il 7 ora dice che il rifiuto di EVASO → ANNULLATO viene dal guard;
* `vendite/test-ordini-guard-transizione-v1`: i `throws_ok` dei test 3, 5 e 7 controllavano solo `P0001` e passavano
  anche sulla porta; ora passano dal verbo e provano di nuovo il guard;
* `vendite/test-ritiro-alla-chiusura-documento-v1` 7 resta un `UPDATE`: riscrive lo stesso stato, e la porta lo lascia
  passare.

✅ **Applicato e verde** (Tid, 2026-10-25): migrazione su dbdev e corsa pgTAP verde.

⚠️ Nell'albero c'è anche `vendite/test-vw-dash-aperto-v1.sql` modificato alle 15:43, rev «§8.5»: non è di questo giro
(un'altra sessione), non l'ho toccato.

### 9.6 Richiesta al team BE (elenco chiuso)

Percorso intero letto il 2026-10-25 (`backend/apps/vendite`, `frontend/src/vendite/ordini`, test Django). Si fa in **un
passaggio**, insieme a B-1 … B-6 del §8.11 (lo stato di emissione letto dal DB): l'ordine ne usa il lettore.

| # | Che cosa | Dove |
| --- | --- | --- |
| C-1 | `OrdiniRepository.update_stato` si ritira (l'`UPDATE` ora lo ferma la porta: `E_DOC_STATO_SOLO_DAL_VERBO`); nuovo `cambia_stato(id, codice)` su `vendite.fn_cambia_stato_ordine`, gemello di `PreventiviRepository.cambia_stato` | `ordini_repository.py` |
| C-2 | `ordini_service.conferma` chiama il verbo con lo stato di emissione letto dal DB (B-1 del §8.11) e ritira `_STATO_CONFERMATO`; lo step `CONFERMA_ORDINE` della pratica resta nella stessa transazione. Il fail-fast `E_ORD_NESSUNA_RIGA` è la copia della Regola 2 del guard (`E_ORDINE_CONFERMA_SENZA_RIGHE`): si ritira (niente logica duplicata fra livelli) | `ordini_service.py` |
| C-3 | Il cambio stato generico: il ramo che non è l'annullo chiama il verbo invece di `update_stato`. Oggi la matrice non ha altri passaggi manuali (la conferma è rifiutata come emissione, l'annullo passa da `fn_annulla_ordine`): il ramo resta per i passaggi che la matrice potrà avere | `ordini_service.cambia_stato` |
| C-4 | Z-2: si ritira `POST /ordini/<id>/conferma/` (`ApiOrdineConferma`, la rotta, `ordiniApi.confermaOrdine`, l'azione `conferma` dello store e il suo mock nello spec, la doc API). L'ordine si conferma solo da «Emetti» | `views_ordini.py`, `urls_ordini.py`, `frontend/src/vendite/ordini/` |
| C-5 | Il 403 dalla riga del passaggio (`PassaggioDocumento`) su `ApiOrdineCambiaStato` (l'annullo del confermato chiede `emetti_ordine`) e su «Emetti» dell'ordine (`emetti_passaggio`, con la sola testata dopo B-2) | `views_ordini.py`, `ordini_documenti_views.py` |
| C-6 | Test: `test_ordini_service` (mock di `update_stato` → `cambia_stato`); l'helper DB `tests/db/_ddt_consegnato.py` scrive lo stato dell'ordine con un `UPDATE` (ora la porta): passa da `dbops.fn_pgtap_porta_a_stato` o da `dbops.fn_pgtap_crea_ordine_con_righe`; sonda `richiedi_db_provvisto` sulla firma del verbo nuovo; i codici della policy rigenerati se serve (nessun codice nuovo dal DB in questo giro) | `apps/vendite/tests/` |

**Da sapere.** Dopo il giro, chi non ha `emetti_ordine` non vede «Conferma» né l'annullo di un ordine confermato, e il
verbo glieli rifiuta. Concedere l'azione ai profili è un dato (su dbdev lo fa Tid, come per `emetti_preventivo`).
Fino al passaggio BE la conferma dal backend e il cambio stato generico rispondono `E_DOC_STATO_SOLO_DAL_VERBO`: è
la rottura accettata del §5, «il DB consegna e scrive al BE cosa si è rotto».

### 9.7 Fatto dal team BE (2026-10-25): B-1 … B-6 del §8.11 e C-1 … C-6 del §9.6

Un passaggio solo, `dev/backend-tid`, da committare.

**Lo stato di emissione letto dal DB (§8.11).**

| # | Fatto |
| --- | --- |
| B-1 | `DocumentoModelloRepository.stato_di_emissione(testata)` → `StatoDiEmissione(id, codice)` o None: una lettura, `fn_doc_stato_codice(t, fn_stato_emissione_id(t))`. BB service `documento_modello.stato_di_emissione(testata, *, function_name)`: None è `E_CONFIG_MANCANTE` (codice già a catalogo, `TECNICO`: è cablaggio, non dato) |
| B-2 | `PassaggioDocumento` prende il campo `emissione: bool` (esclusivo con `stato_chiesto`, `ValueError` alla definizione): lo stato chiesto lo legge a ogni richiesta, e solo quando servono documento e stato (la lettura resta pigra). `emetti_passaggio` della factory riceve la sola testata |
| B-3 | Ritirati `STATO_EMESSO` di `ddt_service` e `preventivi_service`: «Emetti» passa al verbo il codice letto |
| B-4 | `contratti_service.emetti` scrive l'id letto (via `"ATTIVO"`); `ordini_service.conferma` sul verbo col codice letto (via `_STATO_CONFERMATO`); `offerte_service.emetti` col codice letto al posto di `StatoOfferta.EMESSA` (la classe resta: le altre transizioni dell'offerta la usano come condizione) |
| B-5 | Presidio generico in `core/tests/test_passaggio_rotte.py`: ogni «Emetti» che legge il passaggio chiede lo stato al vocabolario, nessuno lo fissa; sul DB, ogni testata che lo dichiara ha lo stato di emissione. In `test_permesso_passaggio_db` il lettore composto sulle cinque testate, contro la colonna `emissione` dei vocabolari, e il reso → None |
| B-6 | Guida del modello §7, riga «Quale stato è l'emissione»: «Emetti» ne legge il codice con `fn_doc_stato_codice` |

**L'ordine al modello (§9.6).**

| # | Fatto |
| --- | --- |
| C-1 | `OrdiniRepository.update_stato` ritirato; nuovo `cambia_stato(id, codice)` su `vendite.fn_cambia_stato_ordine` |
| C-2 | `ordini_service.conferma` sul verbo con lo stato di emissione letto; lo step `CONFERMA_ORDINE` resta nella stessa transazione. Ritirato il fail-fast `E_ORD_NESSUNA_RIGA` della conferma (resta quello del push, che è un'altra regola); il rifiuto arriva dal guard, `E_ORDINE_CONFERMA_SENZA_RIGHE` |
| C-3 | Il ramo non-annullo del cambio stato generico chiama il verbo |
| C-4 | Ritirati `ApiOrdineConferma`, la rotta `/conferma/` (ora 404), `ordiniApi.confermaOrdine`, l'azione `conferma` dello store e il suo mock; doc `api_ordini` |
| C-5 | `post_passaggio` su `ApiOrdineCambiaStato` (l'annullo del confermato chiede `emetti_ordine`) e `emetti_passaggio=TESTATA_ORDINI` su «Emetti» dell'ordine |
| C-6 | `test_ordini_service` sul verbo; `_ddt_consegnato` conferma l'ordine con `fn_pgtap_porta_a_stato`; test nuovo `vendite/tests/db/test_ordine_cambia_stato_db` (sonde sulla firma del verbo e sul lettore: conferma dal verbo, senza `emetti_ordine` → `E_PERMESSO_NEGATO`, senza righe → il codice del guard, l'emissione dal generico → 400, annullo della bozza). Nessun codice nuovo: la policy non si rigenera |

**Emerso nello stesso giro.** I test unitari dell'offerta (`OfferteServiceTests`, `unittest.TestCase`) non avevano il
mixin del modello: `emetti` avrebbe chiesto lo stato al DB di sviluppo, verde per il motivo sbagliato. Ora hanno
`ModelloDocumentoMockatoMixin`, che prende `emissione_del_documento(codice)` (default: il documento non si emette).

**Doc:** catalogo BB backend (`PassaggioDocumento`, `stato_di_emissione`, factory), `api.md`, `api_ordini`,
`api_documenti_per_sorgente`, guida del modello (B-6 e la riga dell'ordine del §10).

**Provato:** suite completa con `ZEROERP_TEST_DB_E2E=1`, 6960 test, verde (1 skip, 1 expected failure, come
prima). mypy (cricchetto, 0 rilievi) e ruff puliti; vitest dello store ordini ed ESLint sui file toccati puliti.
⚠️ Non eseguiti gli smoke HTTP (login col secondo fattore).

**Residui:** ritirati nel §9.8 (il letterale dell'annullo) o sospesi su un difetto DB (il «solo da DRAFT» della
conferma). Da sapere: finché `emetti_ordine` non è concessa ai profili, nessuno conferma un ordine né annulla un
confermato (dato su dbdev, Tid).

### 9.8 I due residui del §9.7 (team BE, 2026-10-25, ok di Tid) e un difetto DB emerso

**1. Lo stato d'annullo dal vocabolario: fatto.** I service riconoscevano l'annullo confrontando lo stato chiesto
con i letterali `STATO_ANNULLATO` / `STATO_ANNULLATA` di `_annullo_con_legami`. Ora lo chiedono al DB: BB
`documento_modello.e_stato_di_annullo(testata, codice)` (`fn_doc_stato_id = fn_stato_abortito_id`), nel cambio
stato di ordine, bolla, preventivo, contratto e commessa (costante nuova `TESTATA_COMMESSE` nel suo repository).
La rotta dell'annullo del reso dichiarava lo stato fisso (`stato_chiesto=STATO_ANNULLATO`): ora
`PassaggioDocumento(stato_del_modello="annullo")`, letto a ogni richiesta. Per questo il campo `emissione` del §9.7
diventa `stato_del_modello: "emissione" | "annullo"`, e `StatoDiEmissione` diventa `StatoDocumento`. Le due
costanti sono ritirate. Test: sul DB, lo stato d'annullo delle otto testate contro la colonna `is_abortito`, e uno
stato non abortito che non lo è. Emerso: `CommesseServiceTests` (`unittest.TestCase`) non aveva il mixin del
modello e avrebbe chiesto al DB di sviluppo: ora ce l'ha; il mixin riconosce come annullo `ANNULLI_DI_PROVA`.

**2. Il «solo da DRAFT» della conferma dell'ordine: NON ritirato, e perché.** Il §9.7 lo chiamava copia della
matrice. Il test sul DB l'ha smentito: **il verbo comune accetta un passaggio allo stesso stato**, che nessuna
matrice ha. Provato il 2026-10-25 su dbdev, in transazione annullata:

| Documento | Richiesta | Esito |
| --- | --- | --- |
| Ordine | `fn_cambia_stato_ordine(id, 'CONFERMATO')` su un ordine CONFERMATO | passa: `CONFERMATO → CONFERMATO` |
| Preventivo | `fn_cambia_stato_preventivo(id, 'EMESSO')` su un preventivo EMESSO | passa: `EMESSO → EMESSO` |
| Bolla | `fn_cambia_stato_ddt(id, 'CONSEGNATO')` su una bolla CONSEGNATA | passa, nessun movimento |

La causa, dalla doc auto-generata: il guard di transizione esce subito quando lo stato non cambia (`IF NEW.<stato>
IS NOT DISTINCT FROM OLD.<stato> THEN RETURN NEW`, per esempio `trgfn_ordini_guard_transizione`), quindi la
matrice non viene consultata, e il verbo non rifiuta prima. Per l'ordine il controllo del service è oggi l'**unica**
cosa che ferma una seconda conferma: si lascia, dichiarato nel codice e nel test DB (`test_conferma_due_volte`, che
oggi si aspetta `E_ORD_STATO_TRANSIZIONE`).

⚠️ **Lo stesso buco è aperto su «Emetti» di preventivo e bolla**, che il controllo non l'hanno mai avuto: un secondo
`POST …/emetti/` su un documento già emesso passa dal verbo senza errore e genera un secondo PDF. Il bottone nel
frontend è nascosto dalle capability, ma un client può chiamare l'API. Non metto una copia del controllo nei due
service: sarebbe un tampone, e il difetto è nel modello.

**Richiesta al team DB (priorità alta, difetto del modello).** Il verbo comune rifiuta il passaggio X → X quando la
matrice non ha la riga X → X (in `script.fn_guard_passaggio` o nel verbo, lo sceglie il team DB), col codice di
transizione non ammessa del documento. Da decidere col team DB: cosa resta della scorciatoia «stato invariato» nei
guard (un `UPDATE` della riga che riscrive lo stesso stato, come `test-ritiro-alla-chiusura-documento-v1` 7, non deve
diventare un errore: la regola vale per il **verbo**, non per ogni `UPDATE`). Ricaduta BE dopo l'apply: si ritira
`_assert_stato` dalla conferma dell'ordine, `test_conferma_due_volte` si aspetta il codice della matrice, e un test
DB per preventivo e bolla prova che il secondo «Emetti» è rifiutato.

**Provato (§9.8):** suite completa con `ZEROERP_TEST_DB_E2E=1`, 6963 test. Prima corsa: un rosso fuori perimetro,
`core/tests/db/test_processi_accensione_db.test_un_non_spegnibile_rifiuta_col_suo_codice` (`E_CORE_VALIDATION` al
posto di `E_PROCESSO_NON_SPEGNIBILE`), verde da solo e nella seconda corsa completa, verde per intero: instabile,
non toccato, da guardare a parte. mypy (cricchetto, 0 rilievi) e ruff puliti.

### 9.9 Tre ritocchi dopo la rilettura (team BE, 2026-10-25, ok di Tid)

* **Il controllo «lo stato esiste?» nel cambio stato dell'ordine: ritirato.** Leggeva l'id dello stato chiesto solo
  per un 400 del dominio, e l'id non era più usato: il verbo prende il codice e risponde da sé
  `E_STATO_WORKFLOW_NON_TROVATO`. Con lui è ritirato `OrdiniRepository.get_stato_id_by_codice`, rimasto senza
  chiamanti. Test: unitario (il codice del verbo passa) e sul DB (`test_stato_inesistente`).
* **Lo stesso controllo nella bolla: NON ritirato.** Provato sul DB: il verbo della bolla tratta uno stato
  sconosciuto come chiamata malformata, `E_VENDITE_CHIAMATA_NON_VALIDA` (`TECNICO`, un 500 «segnala
  all'assistenza»), mentre i gemelli di ordine e preventivo rispondono `E_STATO_WORKFLOW_NON_TROVATO`. Togliere il
  controllo avrebbe trasformato un 400 in un 500. Resta, dichiarato nel codice.
  **Richiesta al team DB:** `vendite.fn_cambia_stato_ddt` risponde a uno stato che il vocabolario non ha con
  `E_STATO_WORKFLOW_NON_TROVATO`, come i gemelli (il ramo `v_stato_a_id IS NULL`; il guard dei parametri NULL o
  vuoti può restare tecnico). Si unisce alla richiesta del §9.8. Ricaduta BE dopo l'apply: si ritirano il controllo
  di `ddt_service._passa_a` e `DdtRepository.get_stato_id_by_codice`.
* **Test di `PassaggioDocumento`:** l'helper della view finta usava il parametro `ddt_id` per tutte le testate; ora
  ha un nome neutro, `documento_id`. Nessun cambio di comportamento.
* **Non toccato, già deciso:** `_STATI_DA_EMESSA` di `offerte_service` (gli stati di partenza di accettazione,
  rifiuto e revisione) è una copia Python della matrice, da ritirare per M-5 nel giro dell'offerta (D-4).

**Provato (§9.9):** test unitari di vendite, core e documenti verdi; test sul DB di `vendite` e il presidio delle
rotte verdi; mypy e ruff puliti. Suite completa (6964): 8 rossi, tutti fuori da questo giro e con la stessa causa,
il giro DB di `brief-db-parametri-senza-override` applicato su dbdev durante la sessione (`1b2e26556`, su
`dev/db-tid`): i codici nuovi `E_PARAMETER_OVERRIDE_NON_AMMESSO` / `_PRESENTI` senza policy (i due presidi della
policy) e il guard nuovo sugli override che rifiuta le fixture di `test_parameter_overrides_db` (5) e
`test_accessi_db` (1). Tocca al passaggio BE di quel brief.

## 10. Ereditati da brief-db-grammatica-unica-documenti (2026-10-25)

Il brief della grammatica unica si è chiuso il 2026-10-25 (lotto 4, il presidio) ed è in
[work-done](../work-done/brief-db-grammatica-unica-documenti.md). Due punti non erano grammatica e passano qui
(scelta di Tid, 2026-10-25):

* **D-G1 — il blocco «origine» della stampa della fattura, che non si vede mai** (dal suo §12.9, in fondo). I
  modelli della fattura (le versioni pubblicate 2334 e 3097 su dbdev, al 2026-10-19) hanno il blocco
  `fattura.origine.tipo`, ma `VenditeRepository.get_fattura_testata` non porta né `origine_tipo` né
  `origine_codice`: sulla carta il blocco resta sempre vuoto. Non è la correzione dell'ordine (L2b-1, etichetta in
  `config.sorgenti`): una fattura può nascere da più documenti. **Da decidere (Tid), nel giro della fattura**:
  togliere il blocco dal modello, o dire che cosa una fattura chiama «origine»;
* **D-G2 — la prova a video del lotto 2b** (dal suo §12.7, riga 6-septies-d), a Tid quando vuole: «Genera ordine»
  da un'offerta accettata; la finestra dell'annullo con legami di un ordine nato da offerta («Offerta …, torna
  trasformabile», col link) e di una commessa con righe da reso e da consumi; il pannello di smistamento di un
  preventivo misto (tag Ordine/Commessa, «Smista tutto» / «Smista selezionate», il routing verso ordine e
  commessa).
