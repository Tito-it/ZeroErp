# Brief — Il modello del documento di vendita, scritto una volta

## ⏭️ Chi riparte — aggiornato al 2026-10-25

**Riparte: il team BE**, con la richiesta del §7.6 (giro 5, il DDT e il reso al modello). Lato DB il giro è chiuso: `20261025-07` … `-22` applicati da Tid su dbdev e scratch dopo la correzione del mirror (§7.5), corsa pgTAP verde (Tid, 2026-10-25). Poi il team DB col documento del giro dopo (§5: l'ordine dei documenti si decide col piano).

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
| 5 | ✅ **Tid** | Fermo dei temi trasversali **allentato** (2026-10-25, scelta C): ammesso il tema che poggia su un pezzo comune già fatto, fermo quello da ricopiare documento per documento; scritto in PROJECT_CONTEXT | — | 3-bis |

Decisioni aperte di Tid: nessuna (T-1 … T-4 decise il 2026-10-25). Da decidere: il documento del giro dopo. Lavoro da committare: la
guida, i rimandi nelle otto guide, `readme.md`, `mkdocs.yml`, PROJECT_CONTEXT (fermo) e questo documento (`dev/db-tid`). Il
giro BE è committato (`9fbff66d2`); i giri 2-4 lato DB pure (`498cc8275`).

> **Chi scrive:** team DB (`dev/db-tid`), 2026-10-21. **A chi:** Tid; poi team DB e BE.
> **Origine:** D2 e D3 di [brief-be-verifica-documentazione-api](../work-done/brief-be-verifica-documentazione-api.md)
> (azioni di processo mancanti fra gemelli; permesso del cambio stato del DDT). Analizzandole sono
> uscite due proposte che, senza saperlo, contraddicevano una decisione viva e ne revocavano
> un'altra (§3.2). Tid: «non mi sto più fidando… una volta in un modo, poi in un altro, poi si torna
> al precedente». Da qui la ricostruzione della storia (§1) e questo brief.
> **Brief vicini verificati:**
> [brief-db-documento-nasce-nello-stato-iniziale](brief-db-documento-nasce-nello-stato-iniziale.md)
> (stato iniziale e verbo: candidato a confluire qui, M-6);
> [brief-db-grammatica-unica-documenti](brief-db-grammatica-unica-documenti.md) (solo i nomi dei
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
| M-6 | [brief-db-documento-nasce-nello-stato-iniziale](brief-db-documento-nasce-nello-stato-iniziale.md) confluisce qui? | aperto, non iniziato, stesso tema (stato e verbo) | ✅ **Deciso da Tid il 2026-10-24: A** — confluisce (§4-bis). Nascere già avanti e' un passaggio «dal nulla» che nessuna matrice ammette. Va **all'inizio** del cantiere: chiude un buco gia' provato (la bolla emessa, numerata e vuota) |

### 4-bis. Confluito: un documento nasce nel suo stato iniziale (ex D32, M-6)

Da [brief-db-documento-nasce-nello-stato-iniziale](brief-db-documento-nasce-nello-stato-iniziale.md)
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
[brief-db-pgtap-bolla-e-reso-costruiti](../work-done/brief-db-pgtap-bolla-e-reso-costruiti.md) (chiuso il 2026-10-25; il reso prosegue in [brief-db-pgtap-reso-costruito](brief-db-pgtap-reso-costruito.md)).

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
  [brief-db-pgtap-reso-costruito](brief-db-pgtap-reso-costruito.md) (giro 2): una trentina di pgTAP di
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
