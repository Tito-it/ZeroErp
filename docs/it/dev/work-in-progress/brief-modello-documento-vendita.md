# Brief — Il modello del documento di vendita, scritto una volta

## ⏭️ Chi riparte — aggiornato al 2026-10-24

**Riparte: Tid**, con le tre domande nate dal censimento (§4-ter, P-1 … P-3); poi il team DB col
primo giro (N-2). Decise il 2026-10-24: M-1 … M-6 (§4) e N-1 … N-3 (§4-bis). Censimento fatto il
2026-10-24; nessun codice scritto.

| # | Chi | Che cosa | Dove | Aspetta |
| --- | --- | --- | --- | --- |
| 1 | ✅ team DB | Bozza: il modello com'è oggi, le divergenze, le decisioni già prese | §2, §3 | — |
| 2 | ✅ **Tid** | M-1 … M-6, decise il 2026-10-24 | §4 | 1 |
| 2-bis | ✅ **Tid** | N-1 … N-3 (un documento nasce nel suo stato iniziale), decise il 2026-10-24 | §4-bis | 2 |
| 2-ter | ✅ team DB | Censimento di chi crea documenti gia' avanti (DB, backend, test Django, pgTAP), 2026-10-24 | §4-ter | 2-bis |
| 2-quater | **Tid** | P-1 … P-3: come si marca lo stato iniziale, che cosa fa la regola su uno stato NULL, il perimetro | §4-ter | 2-ter |
| 2-quinquies | team DB | Primo giro: la funzione unica dello stato iniziale (N-1 … N-3) e i 52 pgTAP portati alla nascita in bozza | §4-ter | 2-quater e il via di Tid |
| 3 | team DB | Il §2, corretto con le decisioni, diventa la guida `docs/it/guide/modello-documento-di-vendita.md`; le guide `gestione-*.md` rimandano lì | §2 | 2 |
| 4 | team DB + BE | Il piano: ogni documento portato al modello **tutto in una volta**, un documento per giro | §5 | 3 |
| 5 | Tid | Fine del fermo dei temi trasversali (PROJECT_CONTEXT) | — | 3 |

Decisioni aperte di Tid: P-1 … P-3 (§4-ter). Lavoro da committare: questo documento, la regola «un tema, un brief»
in `.codex/AGENTS.md` e il fermo in `.codex/PROJECT_CONTEXT.md`.

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
| P-1 | Come dichiara il vocabolario qual è il suo stato iniziale? (a) colonna `iniziale boolean` su ogni vocabolario, con indice unico parziale (uno solo per vocabolario); (b) `fase = 'APERTO'` più un vincolo d'unicità; (c) lo stato senza passaggi in ingresso nella matrice | Consiglio **(a)**: dice esattamente la regola, e il vincolo la presidia. (b) dà un significato nuovo a una colonna che ne ha già uno; (c) si rompe se la matrice ammette un ritorno alla bozza (la fattura ha già EMESSA → DRAFT). Tocca 8 vocabolari (i CSV di `80_data`) |
| P-2 | Se l'INSERT non dice lo stato (NULL), la regola (a) lo rifiuta o (b) mette lo stato iniziale? | Consiglio **(b)**: il DB mette l'iniziale quando manca e rifiuta ogni altro stato. Lo stato iniziale si scrive in un posto solo e le 16 copie si ritirano nello stesso giro (regola del 2): letterali nelle funzioni DB, i 5 service, il DEFAULT `1` della commessa. La colonna della fattura diventa NOT NULL. Con (a) le copie restano, e la fattura senza stato va trattata a parte |
| P-3 | Il perimetro: le 8 testate di vendita più `acquisti.ordini` e `acquisti.ddt`? | Consiglio **sì, anche acquisti**: stessi vocabolari, nessuno scrittore da adeguare, e «ogni decisione su vendite vale per acquisti» (PROJECT_CONTEXT). Magazzino, sistemazioni e listino restano fuori finché non hanno un vocabolario in tabella |

---

## 5. Come si procede dopo le decisioni

* Il §2, corretto con le decisioni, diventa la guida. Da lì una proposta che non è nella guida, o
  la contraddice, si dichiara come revoca.
* Si porta **un documento per giro, tutto intero** al modello (verbo, matrice, azioni, emissione,
  annullo), invece di un tema per giro su nove documenti. L'ordine dei documenti si decide col piano.
* Prima di ricopiare una regola nelle 11 capability o negli 11 guard, si valuta se quella parte può
  vivere in un building block comune che legge la matrice: è la causa strutturale del §1.
