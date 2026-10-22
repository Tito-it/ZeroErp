# Migliorie generali da test valutazione

> Due valutazioni dello **strato DB**, a sette mesi di distanza.
>
> * **febbraio 2026** — voto sintetico 8.9/10, «design production-ready». Rimane
>   qui sotto (§1) come **fatto datato**, insieme a ciò che di quel giudizio non
>   reggeva già allora.
> * **2026-09-08** — questa. Perimetro: solo DB. Sorgenti: la **struttura** del
>   database `zeroerp` di sviluppo (catalogo PostgreSQL: policy, GRANT,
>   `proconfig`, `pg_trigger`, `pg_constraint`), il repo al commit `89d36ad1b`
>   su `dev/db-tid`, e i file di CI. Nessun conteggio di righe di lavoro è usato
>   come argomento.
>
> ✅ **Come è tenuto.** §3 contiene **solo il lavoro che resta**, §6 ne è la
> check-list, e le voci chiuse stanno in fondo, in **§7 «Attività svolte»**, con
> la data e il rimando al brief. Quando una voce ha ancora una parte aperta il
> numero compare **due volte**: in alto ciò che resta, in fondo ciò che è fatto
> (`D6`, `D7`, `D11`, `D12`). Il dettaglio di come si è arrivati a chiudere sta
> nei brief e nella storia git di questo file (sfoltito il 12-09, riordinato il
> 20-09, il 22-09 e il 26-09).
>
> ✅ **Riordinato il 2026-09-26.** Usciti da §3 perché fatti o superati: in D6 la
> tabella delle tre `SECURITY DEFINER` «senza `search_path`» e l'avvertimento su
> `dblink` (i pin del 12-09 includono `public`; il vincolo resta scritto in
> D6-bis); in D7 il triage del 20-09, la rev `20260920-01`, la corsa del 21-09
> con il suo rimedio, il debito dei `COMMIT`/autocommit e i residui `PGTR…`
> sullo scratch — chiusi dal giro 2 e riassunti in §7 D7. Il difetto di
> `storico.parameters` trovato nel lotto 1 è chiuso il 25-09. In D8 `magazzino`
> non è più «modellato e non scritto»: ha i lotti 1 e 2.
>
> ✅ **Numeri rimisurati il 2026-10-13** (repo al commit `2bda3ee3b`) — i registri
> che stanno nel repo si rimisurano, non si citano: suite pgTAP a **830** file
> nella corsa di Tid su dev del 2026-10-14, con **7** rossi noti e tutti in
> baseline, nessuno nuovo (714 al 26-09);
> `SOGLIA_THROWS_SENZA_DISCRIMINANTE` a **115** (117 al 26-09, 123 al 20-09, 131
> quando questa valutazione è stata scritta); `baseline-rossi.tsv` di sviluppo a
> **7** file (12 al 26-09, 16 al 12-09); `baseline-rossi-ci.tsv` ancora a **361**,
> fermo dal 22-09; `baseline-smoke.tsv` a **7** su 52 script (il perimetro
> comprende i bash dal 12-10). ⚠️ Dopo il 26-09 il repo non registra nessuna
> misura nuova della CI. ✅ **La CI ha misurato il 26-09: 227 rossi su 714**, contro
> **361** noti in `baseline-rossi-ci.tsv` (la baseline sullo scratch
> `zeroerp_ci` del 24-09 dava 229 su 687): il registro scende a 227 solo con
> `pgtap-baseline-ci-rientrati.sh` lanciato sul log di **questa** corsa, il
> giorno stesso. `rls_perimetro_debito` ha **6** righe nel suo seed CSV (13-10;
> 7 al 20-09). Il numero che sta solo nel catalogo del database
> (`vw_codici_errore_da_dichiarare` 545) è del 20-09: la data è accanto.
>
> ⭐ **Aggiunto il 2026-10-04 — §2-bis, la valutazione qualitativa del
> design**: modello dati, logica nelle funzioni, trigger/RLS, governo. Fino a
> quel giorno il documento giudicava solo la catena che rende vero il
> database, non il database. Le voci di §2-bis non sono ancora entrate in §3:
> diventano difetti aperti solo con l'ok di Tid, una per una.
>
> ✅ **Verificata dal team DB lo stesso giorno, sul catalogo di dbdev** (§2-bis.8):
> concorda nella sostanza; Q-2 e Q-6 sono **più larghe** di come scritte, Q-4 è
> **più grave** (la corsa c'è), Q-3 scende a 🟠. Con l'ok di Tid sono entrate in
> §3 come **D17** (Q-1…Q-4, brief `brief-db-esclusioni-implicite.md`) e in D8
> (Q-5); Q-6 è diventata una regola delle linee guida. ✅ **D17 chiusa lo stesso
> giorno tranne Q-2**, rimandata da Tid (§7 D17, §3 D17).
>
> ✅ **2026-10-05**: brief di D17 archiviato in `work-done/`. Le due voci «da
> verificare» del suo censimento `UPDATE OF` sono state verificate: una è
> innocua, l'altra è un difetto vero della catena delle istanze su un PDP ed è
> entrata in §3 come **D18**.
---

## 0. Come si legge, e perché il metodo conta più del voto

⛔ **Un voto medio su undici aree è lo strumento sbagliato**, ed è il primo
difetto della valutazione di febbraio. La media tratta «naming conventions» e
«la catena che impedisce a una regressione di entrare» come due addendi dello
stesso peso. Non lo sono: la prima è cosmesi, la seconda decide se tutto il
resto è vero. Un 9,0 di media che contiene un anello rotto **non descrive un
sistema al 90%**: descrive un sistema di cui non si sa quanto sia vero.

Questa valutazione perciò:

* separa ciò che è **stato costruito** (§2) da ciò che **non tiene** (§3);
* ordina i difetti per **conseguenza**, non per area;
* dichiara esplicitamente ciò che febbraio chiamava difetto **e non lo era** (§4);
* dà una scorecard **pesata**, non una media (§5).

⚠️ Tutte le misure qui dentro sono **letture di struttura** — quali policy
esistono, quali GRANT, quale `search_path`, cosa contiene un file di CI o un
registro nel repo — e sono **fatti datati**: 2026-09-08 dove non è scritto
altrimenti.

### Perimetro

Solo **strato DB**: schema, funzioni, trigger, viste, policy, GRANT, seed,
changelog Liquibase, pgTAP e i cancelli di CI che li riguardano. Backend e
frontend compaiono **solo** dove sono il destinatario di un contratto scritto nel
database (la classe di un codice errore, il GUC di identità, la lettura di una
vista). Non sono valutati.

---

## 1. La valutazione di febbraio, riletta

### 1.1 Cosa aveva visto giusto

**L'unico allarme vero era «test coverage 7.0/10, priorità alta»**, e sette mesi
dopo era ancora l'allarme — non perché i test non fossero cresciuti (94 → **600
file**, ~6.183 asserzioni), ma perché il problema non era il numero: era che
**nessuno li faceva contare**. Vedi §7 D1 (chiuso il 2026-09-09).

Erano corrette anche: la lode ai trigger generici (oggi il riuso è
strutturalmente più forte di allora), l'error handling centralizzato, la FK index
policy, la disciplina Liquibase.

### 1.2 Cosa non reggeva, già allora

| Diceva febbraio                                                          | Perché non reggeva                                                                                                                                                                                                                                                                                                                               |
| ------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| «`contabilita`: **0 test, gap critico, dominio business-critical**»      | ⛔ **Sbagliato allora e sbagliato oggi.** Lo schema `contabilita` è **vuoto**: zero tabelle, zero funzioni, zero viste. La misura «0 test» è stata letta come difetto senza chiedere al modello *cosa* avrebbe dovuto coprire. È il caso da manuale della Regola zero: un conteggio ha disegnato una priorità alta su un perimetro che non esiste |
| «`acquisti`: 0 test, **critico — specchia vendite**»                     | Mezzo giusto. Che *specchi* vendite è un'affermazione sul modello, e vale. Che il rimedio sia «aggiungere test» no: mancano prima **le funzioni** — `acquisti` ha 42 FK e 2 funzioni. Non si collauda un dominio che non è stato scritto                                                                                                         |
| «`clienti` ha 18 trigger → valutare consolidamento (**priorità bassa**)» | Osservazione a livello di **sintomo**. Il numero non è una scelta di stile: è la conseguenza meccanica di un pattern che genera **un trigger per figlia**. Oggi `catalogo.articoli` ne ha **46**. La domanda giusta non era «consolidare?» ma «la forma del pattern regge al crescere delle figlie?» — vedi §3 D9                                |
| «Voto 8.9/10 — design **production-ready**»                              | Nessuna area era pesata per conseguenza, e due delle domande che decidono la frase «production-ready» non erano nella griglia: *chi vede quali righe* (la RLS non esisteva ancora) e *cosa impedisce a una regressione di entrare*                                                                                                               |
| «509 pagine manuali, gap su 3 schemi»                                    | Corretto e **chiuso**: oggi 1.410 pagine manuali su 1.500 auto-generate. `magazzino` 32, `acquisti` 11, viste coperte                                                                                                                                                                                                                            |

### 1.3 Le proposte di automazione di febbraio, sette mesi dopo

| #   | Proposta                           | Stato al 2026-09-08                                                                                                                                                                                                                                                                                                    |
| --- | ---------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | Scaffolding changelog YAML         | ⛔ non fatto                                                                                                                                                                                                                                                                                                            |
| 2   | Scaffolding pgTAP                  | ⚠️ parziale — `db/pgtap/_TEMPLATE.sql.txt` + `docs/it/guide/pgtap-come-si-scrive-un-test.md`                                                                                                                                                                                                                            |
| 3   | Generatore `loadUpdateData` da CSV | ⛔ non fatto (esiste `scripts/gen_seed_lista.py`, che è un'altra cosa)                                                                                                                                                                                                                                                  |
| 4   | Linter `%TYPE`                     | ⛔ non fatto                                                                                                                                                                                                                                                                                                            |
| 5   | `fn_setup_standard_table`          | ⭐ **superata da qualcosa di meglio.** Il framework automazioni (`dbops.fn_run_automations_*` + `automation_scope`/`automation_rules_tbl`) applica audit, `tx_id`, storico, lock colonne, cleanup e delete-block **per pattern** nella passata `ci_apply`. Non serve chiamarla per tabella: non serve chiamarla affatto |
| 6   | Validatore pre-deploy              | ⭐ **realizzato in forma migliore**: sette cancelli statici in `ci-validate.yaml` (`runOnChange`, preambolo pgTAP, letterali SQL, preCondition su `80_data`, DDL su trigger di automazione, GRANT ai ruoli batch, licenze) più `scripts/ci-local.sh`, che replica la CI in locale                                       |
| 7   | Diff signature funzioni            | ⛔ non fatto                                                                                                                                                                                                                                                                                                            |
| 8   | Report trigger per tabella         | ⚠️ interrogabile (`dbops.vw_trigger_functions`), non confezionato                                                                                                                                                                                                                                                       |
| 9   | Template Liquibase per pattern     | ⛔ non fatto — e in buona parte reso inutile dal #5                                                                                                                                                                                                                                                                     |

⭐ Le due proposte che sono state realizzate sono anche le due che hanno cambiato
forma strada facendo. Le sette non fatte sono tutte **acceleratori di scrittura**:
sette mesi senza che siano mancati dice che non erano il collo di bottiglia.

---

## 2. Cosa è nato in questi sette mesi

Sono le aree che febbraio **non poteva** avere in griglia. Non è un elenco di
novità: ognuna porta un giudizio.

### 2.1 ⭐ Il perimetro dei dati (RLS + multi-veste) — l'area nuova più importante

Non esisteva. Oggi: 32 tabelle con RLS attiva, 46 policy, quattro vesti
(`OPERATORE` 33 policy, `CLIENTE_PORTALE` 8, `SHOP_CUSTOMER` 3,
`FORNITORE_PORTALE` 2) e tredici funzioni `script.fn_scope_*` che risolvono
l'ambito. Dal **2026-08-07** i pgTAP girano come l'**applicazione**
(`zeroerp_app`), non più come owner: è il cambiamento singolo di maggior valore
dell'anno, perché prima nessuna policy veniva esercitata da nessun test.

⭐ **Ed è fail-closed per costruzione**, che è la scelta giusta: ogni policy è
permissiva e condizionata a `current_setting('app.ruolo_applicativo')`. Una
sessione senza GUC, o con una veste che nessuna policy nomina, non vede **niente**
— non vede troppo. Il costo è che l'accesso amministrativo deve arrivare da un
meccanismo suo, e non da una policy dimenticata.

⚠️ **Ed era anche l'area con il difetto peggiore** (D2, D3): costruita bene dove
era finita, ed era finita su **una famiglia di documenti su sei**, con lo storico
interamente fuori. ✅ Chiusi entrambi l'11-09-2026 (§7): il dominio documento è
protetto fino ai satelliti e ogni versione di storico porta lo scope congelato.
Resta **D8** — le due policy inerti di `acquisti`, che aspettano il modello, a
registro con la ragione.

### 2.2 ⭐ I presidi e i registri del debito — un artefatto raro

`docs/it/guide/presidi-e-registri-del-debito.md` non è documentazione: è una
teoria di come un controllo mente. Il §4-bis («una regola che mente», con il caso
delle sedici chiamate rotte zittite da un'etichetta rassicurante) e il §6 punto 5
(«fai fallire il controllo quando non può misurare») sono il genere di cosa che
in un progetto normale non si scrive mai.

⛔ **E il difetto principale di questo documento (D1, chiuso il 2026-09-09) era
la violazione del §6 punto 5 di quella stessa guida.** Il progetto aveva scritto
la regola e non l'aveva applicata al proprio cancello più costoso.

Oggi in `dbops` ci sono **30 viste di presidio**. Sono il livello meta del
progetto e vanno considerate un asset, non uno strumento.

### 2.3 Il codice errore come contratto a tre lati

897 codici a catalogo, 847 messaggi, dieci classi. Il contratto è esplicito:
`codice` → backend (status HTTP e `ui_action`), `context->>'campo'` → frontend,
`VARIADIC valori` → l'operatore. Con il presidio del «terzo lato»
(`dbops.vw_codici_errore_da_dichiarare`) e il «rubinetto» che impedisce a un
codice di allargare il proprio significato.

⚠️ **Il registro non cala: cresce.** 545 codici su 897 risultano non dichiarati
lato applicativo — erano 508 su 852 l'08-09. Vedi §3 D11.

⛔ **Sei codici vivi non hanno nessun messaggio.** Tutti `AVVISO`, tutti nominati
da esattamente una funzione: `W_FONDO_ESEGUITO_NON_RESETTABILE`,
`W_FONDO_FIGLIA_CONGELATA`, `W_FONDO_MINIMO_NON_RIPRISTINABILE`,
`W_FONDO_RIGA_CONTABILE_NON_AGGIORNABILE`, `W_FONDO_TRATTENUTO_DA_SISTEMAZIONE`,
`W_SCADENZE_TOTALE_NEGATIVO`. Il `note` a catalogo spiega la condizione allo
sviluppatore; **all'operatore non arriva nessuna frase**. Il verso opposto è
pulito: zero messaggi orfani.

⚠️ **E il «multi-lingua» è una capacità, non un fatto**: 846 messaggi in `it`,
**uno** in `en`. La colonna `lingua` c'è e il modello regge; il catalogo è
monolingue. Febbraio lo elencava fra i punti di forza a 9,5/10 — è il modo tipico
in cui una valutazione diventa ottimista: si dà per fatto ciò che è **possibile**.

### 2.4 I processi automatici hanno un'identità e un emittente

`dbops.processi` + `processi_identita` + `processi_bersagli`, con
`vw_processi_dominio_senza_identita` / `_senza_emittente` / `_senza_difesa` che
misurano l'invariante e oggi sono a **zero**. Un processo notturno non è più «il
DB che scrive»: è un utente con una veste e un perimetro. È la cosa che rende
onesta la RLS — senza, un batch la aggirerebbe e nessuno lo saprebbe.

⚠️ Resta un solo bypass, e **dichiarato**: `zeroerp_batch_fatturazione`
(`vw_processi_che_bypassano`, ritiro previsto alla fase 6-bis).

### 2.5 Domini nuovi

`pratiche` (23 tabelle, 72 funzioni — motore di workflow versionato), `documenti`
(10 tabelle — motore documentale parametrico), `ui` (12 tabelle — liste
configurabili come **dato**, non come DDL), `shop`/portale. Più la coda lavori
generica e il fan-out isolato.

⭐ `ui` merita una nota a sé: aver spostato la configurazione di una lista da
codice a dato — riga in `ui.lista_definizione` + N in `ui.lista_colonna` — è la
decisione che ha tolto di mezzo una classe intera di richieste.

### 2.6 Piattaforma

PostgreSQL 18, Liquibase 5, `daterange`/`tstzrange` nativi su 18 tabelle (con
`EXCLUDE` a presidiare le sovrapposizioni: 12 vincoli), `uuidv7()` come default.

---

## 2-bis. Il design del database — valutazione qualitativa (2026-10-04)

> Fin qui il documento giudica la **catena che rende vero** il database: CI,
> perimetro, presidi, registri. Questa sezione giudica **il database stesso**:
> il modello dei dati, la logica scritta nelle funzioni, l'architettura
> trasversale e il modo in cui il tutto è governato.
>
> **Fonti**: la doc auto-generata (`docs/it/dbzero/`), le pagine `manual/`, le
> linee guida e i master Liquibase, letti il 2026-10-04 in quattro passate
> indipendenti (modello · logica · trigger/RLS · governo). Nessun DB vivo,
> nessuno YAML come fonte del DDL. ✔ = **ricontrollato sulla doc** prima di
> scriverlo; gli altri rilievi vengono dalla lettura e non sono stati
> ricontrollati uno per uno.
>
> ⛔ **Cosa non si giudica**: l'ordine di costruzione. Un anno sul solo DB prima
> di BE e FE è una scelta (§4), ed è quella che ha reso economici i refactor
> pesanti del modello. Qui si giudica **la forma** di ciò che è stato
> costruito, non i tempi.

### 2-bis.1 Il giudizio, in breve

⭐ **Il metodo è eccellente; il modello è buono e disomogeneo.** Le parti nate
da un incidente e poi chiuse da un cancello sono di qualità rara: numerazione
fiscale, contratto dell'eccezione, automazioni dichiarative, pgTAP come
applicazione. Le parti nate **per famiglia, una dopo l'altra**, sono simmetriche
nei **nomi** e non nella **forma**: testate dei documenti, macchine a stati,
identità dell'emittente. È la firma tipica di un modello cresciuto a cantieri.
Nessun singolo pezzo è sbagliato, ma ogni dominio ha scelto la forma che serviva
al suo cantiere.

🔴 **Il punto più debole è un altro, ed è nascosto**: le esclusioni dalla
sicurezza. La RLS e i blocchi reggono su **invarianti impliciti**: chi possiede
cosa, una GUC che nessuno imposta, un utente che non è mai NULL. Sono giusti
oggi, ma nessun cancello li tiene, e su un ERP sono i difetti che non danno
errore.

### 2-bis.2 Cosa è costruito bene

* ⭐ **Il party model.** `soggetti` è l'entità unica, i ruoli stanno in
  `soggetti_ruoli` (`UNIQUE(soggetto_id, tipo_ruolo_id)`), fornitore ed
  emittente sono 1:1 sul ruolo, `billing_account` sta sopra il ruolo e le FK
  puntano al ruolo, non al soggetto. La stessa persona è cliente, fornitore ed
  emittente senza duplicare l'anagrafica.
* ⭐ **Chiavi stabili per design.** `uuid DEFAULT uuidv7()` sui master;
  `id bigint` interno più `uid uuid` sui documenti; `codice_interno` bloccato in
  scrittura come chiave fra ambienti (linee guida §6b/6c).
* ⭐ **Tempo e immutabilità dove servono.** Range nativi con `EXCLUDE` o
  `WITHOUT OVERLAPS` (contratti, listini, distinta base); listini
  BOZZA → ATTIVA → CHIUSA con righe immutabili; template pubblicati protetti;
  il registro di magazzino si corregge **solo per storno**, in unità base.
* ⭐ **Snapshot omogenei sui documenti.** Tutte le tabelle `*_indirizzi` hanno la
  stessa forma (`snapshot jsonb`, origine, `UNIQUE(doc, tipo)`), e la fattura
  congela cliente, emittente e termine di pagamento.
* ⭐ **La numerazione fiscale.** `fn_get_next_progressivo`: advisory lock per
  registro e serie, poi `FOR UPDATE` sul contatore. Il controllo della data sta
  **sotto** il lock e legge il contatore, non `fatture` (che ha la RLS e
  potrebbe nascondere righe). Le quattro copie di DDT, ordini, resi e commessa
  sono confluite in `fn_assegna_numero_documento`.
* ⭐ **Il contratto dell'eccezione.** Un solo punto solleva
  (`fn_log_and_raise_error`): codice, campo ed entità in campi strutturati, log
  fuori transazione, ripieghi che non perdono mai il codice. Il backend sceglie
  lo status senza leggere il testo.
* ⭐ **Operazioni a lotti atomiche e rieseguibili per costruzione.**
  `fn_applica_fondi_lotto` è un solo statement; `fn_ricalcola_totali_fattura`
  legge il saldo al netto del proprio contributo; `fn_scrivi_movimento` è
  l'unica porta di scrittura del magazzino, con il TOCTOU analizzato per
  iscritto; `FOR UPDATE SKIP LOCKED` dove si contende.
* ⭐ **Le automazioni dichiarative.** Audit, `tx_id`, storico, blocco colonne e
  `ATTIVO` si applicano **per regola** (schema/nome), con dry-run e controllo di
  convergenza: una tabella nuova li eredita senza che qualcuno la elenchi.
* ⭐ **Il perimetro RLS derivato dalle FK.** `vw_rls_perimetro_scoperto` vede la
  figlia nuova da sola; lo storico congela lo scope al momento della scrittura;
  le partizioni delle note sono usate per avere **FK vere** per tipo di
  bersaglio, non per volume.
* ⭐ **Il circuito incidente → divieto → cancello → template.** I divieti di
  `linee-guida-sql.md` §11 spiegano il meccanismo, nominano l'incidente e
  hanno un `guardrail_*.py` in CI; il pgTAP ha un template che spiega ogni
  riga del preambolo, presidiato, e fixture che **costruiscono il mondo**
  invece di cercarlo.

### 2-bis.3 Rischi di modello — 🔴, da chiudere

| #     | Rilievo                                                                                                                                                                                                                                                     | Conseguenza                                                                                                                                                                                                       |
| ----- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Q-1 ✔ | **Utente NULL = vede tutto, dentro la funzione chiamata dalle policy.** `script.fn_check_user_emittente_scope` risponde `true` con `p_auth_user_id IS NULL` («job batch»), e `fn_scope_ef_whitelist` la chiama. Le policy sono chiuse **solo** perché combinano `app.ruolo_applicativo = 'OPERATORE'` | Una sessione con il ruolo impostato e `app.current_user_id` vuoto (un difetto del middleware, una connessione riusata) vede **tutte** le aziende. Il «NULL = tutto» va dove c'è il ruolo `BYPASSRLS`, non in una funzione di policy |
| Q-2 ✔ | **I blocchi si spengono con una GUC che chiunque imposta.** `zeroerp.allow_lock_columns_override` (blocco colonne, cioè anche `codice_interno`), la GUC di `trgfn_delete_block_by_guc`, `zeroerp.maintenance_reset_lotto_draft` (spegne da sola `trgfn_fatturazione_lotti_guard_stato`) | Le GUC personalizzate le imposta anche `zeroerp_app`: l'immutabilità è disciplina del backend, non un vincolo. Il progetto ha già il giudizio giusto — «una GUC è un cartello, non un cancello» (`trgfn_guard_emittente_scope`) — e il rimedio: legare il bypass al ruolo (`fn_is_proprietario_tabella`, come fa già `zeroerp.ddt_cambio_stato`) |
| Q-3   | **L'esclusione dalla RLS regge su un invariante di proprietà implicito.** Le `SECURITY DEFINER` vedono oltre la RLS solo perché il loro owner possiede le tabelle e la RLS è senza `FORCE`; `fn_get_fattura_intestazione` lo scrive («con un `FORCE` va rivista»), mentre le linee guida §10.5 **raccomandano** `FORCE` | Chi seguisse la regola scritta romperebbe in silenzio i risolutori di scope. Serve un presidio che fallisca su `FORCE` acceso o su una `DEFINER` nuova non censita                                                       |
| Q-4 ✔ | **Ritorno a DRAFT: voluto; resta una sola domanda di concorrenza.** Che `fn_riporta_lotto_a_draft` cancelli le fatture **pre-fiscali** del lotto è il disegno (RD-1, Tid 2026-10-04), e il controllo prima del lock è una scelta dichiarata («una chiamata invalida non deve serializzare»). Lo stesso disegno però **rifiuta** il lotto se una fattura è già numerata (`E_LOTTO_FATTURE_NUMERATE`) | 🟡 Non un difetto di disegno. La domanda aperta è solo se una numerazione **concorrente** possa entrare fra il controllo e `fn_cleanup_fatture_by_ids`: il lock nomina la funzione e non il lotto, e su `fatture` non c'è un guard `BEFORE DELETE` sul numero. Se lo stato del lotto (pipeline in esecuzione) esclude già i due percorsi insieme, il punto si chiude con un pgTAP che lo provi; altrimenti basta il guard sul numero come difesa in profondità |
| Q-5 ✔ | **`acquisti` non ha il perimetro dell'emittente.** `acquisti.ordini` e `acquisti.ddt` non hanno `emittente_fiscale_id` né `registro_id`; l'unicità `(anno, serie, numero)` è **globale**, mentre `acquisti/manual/ddt.md` la vuole **per fornitore**, e senza `NULLS NOT DISTINCT` non vincola le righe con `serie` NULL | È esattamente il caso del §4: non un ritardo, ma una decisione di `vendite` (multi-emittente, RLS per emittente) non riportata su `acquisti`. Si chiude **nel modello**, prima di scrivere il comportamento |
| Q-6 ✔ | **Lo stesso emittente ha due identità.** `preventivi`, `ordini`, `ddt`, `resi`, `contratti` e `offerte` portano `emittente_fiscale_id`; `fatture` e `registri_fatturazione` portano `emittente_soggetto_ruolo_id`. `trgfn_ordini_gen_numero` lo scrive: «due convenzioni per lo stesso emittente» | Ogni passaggio da un documento all'altro traduce. La coerenza registro ↔ emittente sta in trigger, non in una FK composta                                                                                           |

### 2-bis.4 Debolezze — ⚠️, la forma diverge fra famiglie

* **Testate dei documenti simmetriche solo nei nomi** ✔. Totali
  `totale_imponibile/totale_documento` (preventivi) contro
  `imponibile_tot/iva_tot/totale_doc` (ordini) contro `imposta_tot` (fatture);
  `numero` è `varchar` ovunque e `bigint` in fattura; validità `validita_dal`
  sui preventivi contro la regola §7b `valido_dal/valido_al`; unicità del
  numero con `COALESCE(serie,'')` in fattura e `NULLS NOT DISTINCT` altrove;
  `quantita` contro `qta`. La controparte è ancorata in quattro modi
  (`billing_account_id NOT NULL`, BA più `istanza_utility_id`,
  `soggetto_ruolo_id`, `destinatario_soggetto_ruolo_id`).
  ⇒ Una vista o una funzione unica «sul documento» non si può scrivere.
* **Quattro forme di macchina a stati.** Tabelle `config.transizioni_stati_*`;
  tabelle con colonne diverse (`stati_doc_fiscale_transizioni`,
  `stati_doc_offerte_transizioni`, e altre in `vendite`/`pagamenti`); un `CASE`
  in una funzione `IMMUTABLE` (documento interno di magazzino); transizioni
  cablate negli `IF` (stato del lotto, sistemazioni). Il lotto ha tre assi di
  stato, uno da tabella, uno cablato, uno testo libero. E dove la transizione è
  un dato, gli **effetti** restano cablati (`fn_cambia_stato_ddt` ramifica su
  coppie di stati): aggiungere una riga di transizione non aggancia il
  movimento di magazzino.
* **Il contratto d'errore rispettato a metà.** `E_GENERICO` (vietato da §5b) in
  `fn_set_fatturazione_lotto_stato`; due convenzioni per i parametri
  (`E_PARAMETRO_INVALIDO` e `E_VENDITE_CHIAMATA_NON_VALIDA`); `p_area` ora
  schema, ora dominio, ora `'database'`; nomi di parametro e di tabella dentro
  la frase per l'operatore.
* **Volatilità dichiarata falsa.** Funzioni `STABLE` (e una `STABLE PARALLEL
  SAFE`) che sollevano tramite `fn_log_and_raise_error`, cioè **scrivono** via
  dblink.
* **Sicurezza delle madri divisa.** Le linee guida chiedono madri `SECURITY
  INVOKER`; i verbi di magazzino e DDT sono `DEFINER`, ricopiano il filtro della
  policy nella `WHERE` e controllano il permesso a DB, mentre altri passaggi lo
  lasciano al backend («presidio permessi sul BE»). Due fonti di verità per i
  permessi.
* **Capability disomogenee.** Il principio è giusto e applicato bene dove c'è
  (la stessa `fn_check_*` alimenta pulsante e madre). Ma `reason`/`reasons`
  hanno due forme, `can_change_state` conta tutte le azioni nel DDT e solo le
  abilitate altrove, e il blocco degli step della pipeline sta in Python
  (`LottoPipelineRunner`).
* **Tipi senza criterio.** PK dei cataloghi `integer`, `bigint` o `smallint`;
  scala dei prezzi `numeric(15,6)`, `(18,6)`, senza limite, `(22,10)` lungo la
  catena listino → preventivo → ordine → DDT, senza una regola nelle linee
  guida (rischio di troncamento silenzioso); `split_payment` è `character
  'S'/'N'` su `soggetti` e `boolean` su `fornitori` ✔; `fornitori.regime_fiscale`
  è un `varchar` senza FK, mentre sugli emittenti c'è la FK ✔;
  `billing_account.valuta_id` senza FK ✔.
* **Tre modelli di riferimento polimorfo** (`sorgente_tipo_id + sorgente_uid`,
  il modello testuale, `documento_origine_tipo + _id`), nessuno una FK vera.
  L'integrità è centralizzata in guard generici, che è il meglio possibile, ma
  la tracciabilità fra documenti dipende tutta dai trigger.
* **Il costo per riga sugli aggiornamenti massivi.** `tx_id`, storico (che in
  modo `PADRE` risale la catena), blocco colonne con `EXECUTE` dinamico e
  `ATTIVO` (un controllo dinamico per ogni figlia, con la politica indici FK in
  opt-in) si sommano. L'unico alleggerimento sono le GUC di Q-2.
* **Storico debole nel tempo.** `valid_from/valid_to` a granularità di giorno,
  l'INSERT non tracciato, il flag `storicizza` che esclude per riga: con più
  modifiche nello stesso giorno, «com'era alla data X» è ambiguo. Il `tx_id`,
  che dovrebbe ricucire le operazioni su più tabelle, ripiega su `uuid_nil` in
  silenzio se manca il canale dblink.
* **Tabelle nuove scoperte fino a `ci_apply`.** Audit, `tx_id` e storico li
  crea la seconda passata (in sviluppo, pgAgent la sera): fra il migrate e il
  giro, una tabella nuova scrive senza storia.

### 2-bis.5 Governo ed evoluzione

* ⚠️ **`linee-guida-sql.md` contiene due regolamenti.** La parte §1-§10 è un
  elenco di convenzioni senza presidio, con paragrafi **numerati due volte**
  (§8-§10 compaiono due volte, con un blocco YAML ripetuto); la parte §11-§12 è
  fatta di divieti nati da incidenti e presidiati. Manca una gerarchia, e la
  mappa «divieto → presidio» più utile sta in `.codex/AGENTS.md`, cioè nel file
  che un nuovo sviluppatore non legge. Le linee guida mescolano anche regola e
  diario («al 2026-08-20», «erano tredici fino al…»): invecchiano ogni
  settimana.
* ⚠️ **Le convenzioni di nome dei trigger sono in conflitto**, e il nome è ciò
  che decide l'ordine di esecuzione. §2 dice `trg_<tabella>_<evento>`,
  `linee-guida-trigger.md` dice le fasi `a05/a10/z90`; i trigger generati
  usano altre forme (`trg_{table}_ins_upd_gen_tx_id`,
  `trg_upd_{table}_audit_data_user`) e lo storico ne ha due. Una
  normalizzazione che scattasse dopo lo storico renderebbe lo snapshot diverso
  dalla riga salvata.
* 🔴 **La regola su `UPDATE OF` è descritta male.** `linee-guida-trigger.md`
  dice che il trigger «non scatta se non cambiano quelle colonne»: in
  PostgreSQL scatta se la colonna è nel `SET`, a prescindere dal valore, e
  **non** scatta se la colonna la cambia un altro trigger `BEFORE`. Un guard
  `a10` costruito su quella frase si aggira con una normalizzazione.
* 🔴 **Il residuo v1 non è isolato** ✔. `changelog-master-v2.yaml` include
  `changelog-master.yaml`, che fa `includeAll` di `baseline/` e `migrations/`:
  la prima generazione rigira in ogni migrate da zero, con centinaia di file
  `runOnChange: true` che `guardrail_run_on_change.py` **non guarda** (presidia
  solo `migrations_v2`), e con file come `… - Copia.yaml` e nomi con lo spazio
  finale. Il bug di checksum del §11.1 può ripartire da lì. Rimedio: estendere
  il cancello, o consolidare il v1 in una baseline unica.
* 🔴 **La «fonte di verità» dei corpi è generata dal DB di sviluppo** ✔. In CI
  `gen_db_docs.py` gira in modo `ci` (senza sorgenti SQL); la doc completa si
  genera in locale e si committa. Il DB di sviluppo è quello che §11.1 e
  §11.9 descrivono come divergente per costruzione, e nessun controllo confronta
  la doc con un DB ricostruito da zero.
* ⚠️ **`logicalFilePath` dichiarato obbligatorio e non presidiato**, con file
  che ne sono privi e uno che punta ancora a un percorso v1; `nullValue` dei CSV
  fra token `NULL` e cella vuota; `85_pgagent` mai eseguito in CI
  (`MARK_RAN`), cioè il rischio dichiarato del primo deploy.
* ⚠️ **La storia vive nei corpi.** COMMENT e blocchi `--` raccontano revisioni,
  brief e lezioni, spesso più lunghi del codice. Sono preziosi, ma pesano su
  lettura e diff e invecchiano con il codice che descrivono.
* ⚠️ **Il bus factor.** Oggi un secondo sviluppatore DB seguirebbe i cancelli,
  ma non saprebbe ragionare sulle eccezioni: il perché delle regole sta nei
  brief e nella memoria dell'autore, e alcuni divieti richiedono di conoscere
  il funzionamento interno di Liquibase.

### 2-bis.6 Cosa fare, in ordine di conseguenza

1. **Q-1, Q-2, Q-3**: togliere «NULL = tutto» dalle funzioni di policy; legare
   ogni GUC di bypass al ruolo (`fn_is_proprietario_tabella`); un presidio
   sull'invariante owner/RLS (`FORCE` acceso, `DEFINER` non censita).
2. **Q-4**: provare con un pgTAP che numerazione e ritorno a DRAFT non
   possono sovrapporsi; se possono, il guard «fattura con numero non si
   cancella».
3. **Q-5, Q-6**: decidere **nel modello di `acquisti`**, prima del suo
   comportamento: emittente, registro, unicità per fornitore. E scegliere una
   sola identità dell'emittente sui documenti.
4. **Governo**: estendere `guardrail_run_on_change.py` al v1; generare la doc
   completa dal DB che la CI ricostruisce e confrontarla con quella committata;
   correggere `UPDATE OF` e la convenzione dei nomi; portare in testa a
   `linee-guida-sql.md` la tabella «divieto → presidio» e togliere i paragrafi
   doppi.
5. **Forma comune delle famiglie** (testate, macchine a stati, capability,
   scala monetaria): non un refactor generale, ma una **regola scritta** che il
   prossimo cantiere (`acquisti`) applica dal primo changeSet.

### 2-bis.7 Doc da allineare — non contano come difetti del modello

* `script/manual/trgfn_storico_generic.md`: l'esempio dice `AFTER`, le altre
  pagine `BEFORE`; dice che gli errori «non bloccano la DML», ma
  `E_SNAPSHOT_CLOSE_ERROR` blocca; snapshot `NEW` contro «stato precedente».
* Nome del trigger di storico: `trg_z90_{table}_…` contro `trg_<tab>_z90_…`.
* `fn_scope_ef_whitelist.md`: il manuale dice «whitelist vuota = true» e
  «inlineable, valutata una volta»; `fn_check_user_emittente_scope.md` e §10.9
  dicono fail-closed e «chiamata per riga».
* `fn_run_automations_attivo.md` parla di `automation_fk_exclusions` come
  inerte; `automation_rules_tbl.md` la dice droppata.
* Tre famiglie di GUC d'identità (`app.user_id`/`app.group_ids` in
  `fn_set_gucs_conn`, `app.current_user_id` nelle policy, `app.jwt_user`
  nell'audit), a livelli diversi (sessione/transazione).
* `linee-guida-sql.md`: §10.3 usa `app.current_identita_id` (le policy vere usano
  `app.current_user_id`) ✔; §3 dice «UUID PK per i master» mentre i documenti
  sono `bigint` + `uid`; il vecchio §9 dice «`runAlways` o `runAlways: false`»;
  §12.4 dice che `fn_available_actions_lotto`/`_commessa` non hanno il motivo,
  ma il corpo emette `reasons`.
* `linee-guida-trigger.md`: `_z90_` definito due volte, in due modi.
* `fn_assegna_numero_documento`: il COMMENT dice `SECURITY DEFINER`, la
  definizione no.
* `anagrafiche/tabelle/soggetti.md`: un trigger usa `soggetti_ruoli.attivo`,
  che la pagina di `soggetti_ruoli` non elenca.
* Il generatore della doc: mostra gli `EXCLUDE` come `CREATE INDEX … gist` e
  non fra i vincoli; non mostra precisione e scala di `numeric`/`varchar`;
  `tools/gen_db_docs.md` indica `tools/gen_db_docs.py`, ma lo script è in
  `scripts/`.

### 2-bis.8 La verifica del team DB, e le decisioni di Tid (2026-10-04)

> Fonte: il catalogo del database `zeroerp` di sviluppo (struttura, non
> righe) e il codice del repo, letti il 2026-10-04. Le decisioni sono di Tid,
> lo stesso giorno.

| #     | Esito della verifica                                                                                                                                                                                                                                                                                                                                                                                                                                                   | Decisione e destinazione                                                                                                                                                                         |
| ----- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Q-1   | ✔ Confermato, ed è un **residuo**: il guard di scrittura aveva tolto «utente NULL = batch» il 2026-09-04 (passa senza utente solo chi bypassa la RLS, `row_security_active`), la lettura no. La famiglia è di **tre** funzioni: la canonica, `fn_scope_ef_whitelist_via_efba` (con un commento rimasto a prima del P-2a) e `fn_get_emittenti_scope_sr_effettivo`, che dava «tutto» alle due ricerche. Il BE imposta le GUC «tutto o niente»: serve un difetto applicativo, ma è il «backend che sbaglia» da cui il modello promette di proteggere | ✅ Utente NULL → nessun accesso, sulle tre. Chiuso il 2026-10-04 (§7 D17)                                                                                                                         |
| Q-2   | ✔ Confermato e **più largo**: le GUC di bypass slegate dal ruolo sono **nove**, non tre (oltre alle tre citate: `allow_contabile_riga_delete_override`, `allow_user_emittente_delete_override`, `maintenance_allow_attivita_bypass`, `maintenance_allow_delete_logs`, `maintenance_indirizzi_dettaglio`, `maintenance_toponomastica`). Solo `ddt_cambio_stato` e `reso_cambio_stato` usano `fn_is_proprietario_tabella`. Il backend non ne accende nessuna | ⏳ **Rimandata** da Tid (proposta in **D17**: legare ogni bypass al proprietario; il ritorno a DRAFT passa da una madre DEFINER, approvata)                                                  |
| Q-3   | ⚠️ Vero a metà. Su dbdev l'invariante **regge**: le 172 tabelle con RLS sono del migratore, nessuna ha `FORCE`. §10.5 chiede `FORCE` solo se la tabella fosse di `zeroerp_app`, quindi «chi seguisse la regola romperebbe» è esagerato. Il vuoto vero: **nessun presidio** guarda proprietario e `FORCE`, e l'invariante non è scritto                                                                                                                        | 🟠 ✅ Presidio di postura + invariante scritto in §10.5. Chiuso il 2026-10-04 (§7 D17)                                                                                                      |
| Q-4   | 🔴 **Più grave di come scritta: la corsa c'è.** La check gira prima del lock, il lock nomina (funzione, lotto) e la numerazione non lo prende, il cleanup cancella per `id`. In più `numero` non era protetto: in EMESSA un UPDATE poteva toglierlo e la DELETE passare. Il pgTAP proposto non basta (servono due sessioni)                                                                                                                                       | ✅ Guard di tabella «una fattura numerata non si cancella e non cambia numero». Chiuso il 2026-10-04 (§7 D17)                                                                                     |
| Q-5   | ✔ Confermato: niente emittente, niente registro, unicità globale senza `NULLS NOT DISTINCT`, e nessuna tabella di `acquisti` ha la RLS                                                                                                                                                                                                                                                                                                                            | Accorpata a **D8**: si chiude nel modello di `acquisti`, prima del comportamento                                                                                                                  |
| Q-6   | ✔ Confermato e **più largo**: 22 tabelle con `emittente_fiscale_id`, 13 con `emittente_soggetto_ruolo_id`. Le chiavi sono 1:1: costo di traduzione, non dati sbagliati                                                                                                                                                                                                                                                                                         | ✅ **`emittente_soggetto_ruolo_id`** per ogni tabella nuova (linee-guida-sql §2); le esistenti convergono quando un cantiere ne tocca il modello                                                    |
| v1    | ✔ Confermato: 374 file `runOnChange: true` sotto `baseline/` e `migrations/`, fuori dal raggio del §11.1                                                                                                                                                                                                                                                                                                                                                         | ✅ «Il v1 non si tocca»: `guardrail_v1_congelato.py` + manifesto, in CI; linee-guida-sql §11.11. Chiuso il 2026-10-04                                                                             |
| UPDATE OF | ✔ Confermato, e **mordeva**: i cinque trigger di propagazione delle quantità ai componenti del kit erano `UPDATE OF quantita`, ma `quantita` la ricalcola un trigger BEFORE da `qta_operativa`. Il backend sui preventivi aggiorna solo `qta_operativa`: i componenti restavano con la quantità vecchia. Gli altri casi del censimento sono innocui (scritture solo da NULL, normalizzazioni idempotenti). I due «da verificare», visti il 2026-10-05: il registro di DDT e resi è innocuo (lo sceglie un lettore che filtra gli attivi); la catena delle istanze dei clienti **morde** | ✅ Doc corretta (linee-guida-trigger); trigger ricreati con `WHEN (OLD.quantita IS DISTINCT FROM NEW.quantita)` (`20261004-85/-86`). Chiuso il 2026-10-04. La catena delle istanze → **D18** |
| Doc da dev | Vero, già noto («dev ≠ CI»)                                                                                                                                                                                                                                                                                                                                                                                                                                   | Resta in §2-bis.5, nessuna decisione                                                                                                                                                               |

---

## 3. I difetti **aperti**, in ordine di conseguenza

> ✅ **Le voci chiuse non stanno qui**: sono in **§7 «Attività svolte»**, con la
> data e il rimando al brief — chiuse **per intero** D1, D2, D3, D4, D5, D10,
> D13, D14, D15, D19, D20, D21, D22, D23, D25, D26, D26-2, D28, D29, D30, D33, D35; **in parte** D6 (i pin), D7 (il perimetro e il giro 2), D11 (i
> registri calati), D12 (la quantità), D17 (tutto tranne Q-2).
>
> ⭐ **D15 è nata dalla chiusura di D14** (2026-09-22) e **D16** da un test
> diventato rosso da solo (2026-09-23).
>
> ⭐ **D17 è nata dalla valutazione qualitativa del 2026-10-04** (§2-bis.8), e
> **D18** dal censimento `UPDATE OF` di D17 (2026-10-05). **D19** dal debito
> che `brief-db-righe-esclusione-solo-non-si-vende` (§10.8) ha lasciato
> all'archiviazione (2026-10-08), chiusa lo stesso giorno; **D20** da ciò che
> la sua chiusura ha trovato. **D21** dal lato BE/FE di
> `brief-db-istanza-nasce-col-ba` (2026-10-09). **D23** dal giro R-6 di
> `brief-db-codici-non-trovato-email-e-permessi` (2026-10-10). **D24** dal giro BE
> di D22 (2026-10-10), che è chiusa. **D25** dai residui di `brief-db-istanza-nasce-col-ba`
> alla sua chiusura (2026-10-10), chiusa lo stesso giorno. **D26** (la testata dopo l'emissione) e
> **D27** (gli indirizzi del documento seguono il cliente) da `brief-db-esecutivi-ba-coppia`
> (2026-10-09/10). **D28** (le righe evase di un DDT da ordine) dal collaudo di Tid (2026-10-10). **D29** (l'annullo di un documento con legami) dal giro di D28 (2026-10-11), chiusa lo stesso giorno. **D30** (tornare indietro: annullare a valle riapre a monte) dal collaudo di D29 (2026-10-11), chiusa il 2026-10-13. **D31** (canone, orario e consumo del contratto in commessa) dalla segnalazione BE sul push dei contratti (2026-10-13). **D32** (un documento nasce nel suo stato iniziale) dal giro del `20261013-53` (2026-10-13). **D33** (un cliente manuale per soggetto e utility) dallo smoke clienti del giro notturno (2026-10-13), chiusa il 2026-10-15. **D34** (la creazione non scrive tutta la sezione dei dati societari) dalla chiusura di `brief-db-dati-fiscali-e-societari-del-soggetto` (2026-10-14). **D35** (`zeroerp_log` nasce con gli altri ruoli di sistema) dalla chiusura di `brief-db-ruoli-di-sistema` (2026-10-15), chiusa lo stesso giorno.
>
> ⚠️ **Rinumerazione del 2026-10-10:** D23 e D25 erano stati dati due volte, a voci diverse. Il
> numero è rimasto alla voce che l'aveva preso per prima (D23 alla ricerca universale, D25 ai
> residui dell'istanza col BA); le due arrivate dopo sono diventate D26 (testata dopo l'emissione,
> era D23) e D27 (indirizzi del documento, era D25). Brief e PROJECT_CONTEXT allineati lo stesso giorno.
> Lo stesso giorno D26 è stato dato una seconda volta (le funzioni che ripianificano): per decisione di
> Tid quella voce è diventata **D26-2**, e D26 è rimasto alla testata dopo l'emissione, che l'aveva prima.
>
> Qui sotto, **solo il lavoro che resta**: D17, D18, D6, D7, D8, D9, D11, D12, D16, D24, D31, D32, D34.

### 🟠 D17 — Resta Q-2: le GUC di bypass che chiunque può accendere

✅ **Il resto di D17 è chiuso il 2026-10-04** (§7): Q-4, Q-1, Q-3, `UPDATE OF`, v1.
Resta la parte che Tid ha **rimandato** lo stesso giorno: dieci blocchi del DB si
spengono con una GUC che anche l'applicazione può accendere (il lock di colonna,
cioè anche `codice_interno`; il divieto di DELETE su clienti ed emittenti; otto
guard del lotto e delle fatture…). Il backend non ne accende nessuna, ma un blocco
che l'applicazione può spegnere da sola protegge solo finché l'applicazione non
sbaglia. Proposta nel brief
[brief-db-esclusioni-implicite.md](../work-done/brief-db-esclusioni-implicite.md) §4: un
building block che lega il bypass al **proprietario delle tabelle** (la forma di
`zeroerp.ddt_cambio_stato`), i verbi del lotto DEFINER (approvato), circa 45 pgTAP
da riscrivere perché usano quelle GUC come scorciatoia di fixture.

✅ **R-1 del brief chiusa dal BE il 2026-10-04**: i due codici nuovi di Q-4 in
`error_policies_generated.py`, con i ripieghi (`63deeb194`).

### 🔴 D18 — La catena delle istanze su un PDP si rompe quando un anello esce o entra

Trovata il 2026-10-05 verificando il censimento `UPDATE OF` di D17. Su un PDP i
clienti si succedono, e ogni istanza punta a quella del cliente precedente
(`istanze_utilities.parent_istanza_id`, da cui il subentro clona il catasto). Il
calcolo ha tre difetti, tutti sul modello:

* **annullare un cliente non lo toglie dalla catena**: il trigger è `UPDATE OF
  pdp_id, data_attivazione`, l'annullamento cambia lo stato, e `data_attivazione`
  la azzera un altro trigger `BEFORE`. I due rami scritti per l'annullamento non
  si raggiungono mai da un UPDATE;
* **si ricalcola un anello, non la catena**: annullare, inserire in mezzo,
  spostare una data, cambiare PDP o cancellare lascia sbagliato il **successore**;
* **il calcolo legge sotto RLS**: il subentro attraversa le aziende, e il
  predecessore di un'altra azienda per chi lavora non esiste.

Proposta nel brief
[brief-db-catena-istanze-pdp.md](brief-db-catena-istanze-pdp.md): un ricalcolo
DEFINER della catena intera del PDP, da un trigger `AFTER` senza `OF`. Cinque
decisioni aperte per Tid.

### 🟠 D6 — Resta solo D6-bis: i pin e il registro degli owner sono chiusi (§7)

✅ I pin del `search_path` sulle tre DEFINER di `postgres` dal 12-09, e il
registro degli owner con la sync **riservati al migratore** dal 26-09: §7 D6.
Qui resta D6-bis.

#### D6-bis — una forma di `search_path` per le 38 `SECURITY DEFINER`

Le `SECURITY DEFINER` proprie sono **38**, e il `search_path` ha sei forme
(2026-09-08, con i tre pin del 12-09):

| Forma                                                  | Quante |
| ------------------------------------------------------ | ------ |
| `pg_catalog, public`                                   | 16     |
| `pg_catalog, pg_temp`                                  | 8      |
| `public, pg_temp`                                      | 5      |
| `pg_catalog, pratiche, script, config, dbops, pg_temp` | 4      |
| `pg_catalog, public, pg_temp` *(i pin del 12-09)*      | 3      |
| `pg_catalog, anagrafiche, config, script`              | 2      |

In **18 su 38** `pg_temp` non è elencato — e quando non è elencato PostgreSQL lo
cerca **per primo** per le relazioni. In altre 5 `public` viene **prima** di
`pg_catalog`, che è l'ordine opposto a quello prudente.

⛔ **Una forma canonica uguale per tutte non esiste** (lezione del 12-09, §7 D6).
`pg_catalog, pg_temp` **accieca** chi chiama un'estensione non qualificata —
`dblink`, `unaccent`, `postgis`, `plpgsql_check` stanno tutte in `public` — e
dentro un `EXCEPTION WHEN OTHERS` la cecità non fa un rosso: degrada in
silenzio. Quindi si decide **per funzione**, guardando i suoi chiamati: o si
qualifica la chiamata, o `public` resta nell'elenco. ⭐ La forma giusta quando
`public` serve davvero è quella di `dbops.fn_check_funzioni_riferimenti_morti`:
pinna `pg_catalog, public, pg_temp` **e** qualifica la chiamata (changeSet
`20260912-37`). ⚠️ Vale anche per `fn_get_or_create_session_tx_id`: se un giorno
il suo pin si stringesse, **prima** `public.dblink(...)` nel corpo, poi il pin.

---

### 🟠 D7 — La copertura dei test non è bassa: è concentrata

600 file, ~6.183 asserzioni (2026-09-08; 714 file al 26-09, e `magazzino` da 1
a 17 coi suoi lotti — D8). Il numero non dice niente; la distribuzione sì.

|              | mai nominato in un pgTAP | totale    |
| ------------ | ------------------------ | --------- |
| **Funzioni** | **315**                  | 829 (38%) |
| **Tabelle**  | **83**                   | 372 (22%) |

*(«mai nominato» è la soglia più generosa possibile: essere nominato non
significa essere collaudato. È un limite inferiore.)*

Per schema, i file di test: `vendite` 253, `script` 69, `anagrafiche` 66,
`pratiche` 43, `config` 33, `dbops` 32, `rls` 22, `pagamenti` 17, `catalogo` 15,
`ui` 13, `documenti` 11, `maintenance` 5, **`magazzino` 1**, **`shop` 1**,
**`acquisti` 0**, **`storico` 0**.

⚠️ E la copertura dichiarata è più alta di quella reale per due motivi già
scritti nella guida sui presidi: **110 file** contengono uno `skip()`
condizionato (2026-09-08: su un DB ricostruito da zero si saltano, e un test
saltato conta verde), e il debito `throws_ok` senza discriminante è a **117**
(2026-09-26; 131 quando questa valutazione è stata scritta) — un
`throws_ok(sql, NULL, NULL)` accetta *qualunque* errore, compreso quello
sbagliato. Due volte, sanandone uno, è venuto fuori un test **verde per l'errore
sbagliato** (§7 D11, §7 D7).

### 🔴 Il numero che conta davvero: la suite fuori dalla macchina di sviluppo

Su un database **ricostruito da zero** — quello che serve il giorno in cui si
prepara un'installazione nuova — la prima misura della CI (2026-09-09) ha dato
**407 rossi su 601**. La misura più recente della CI, **227 rossi su 714**
(2026-09-26; lo scratch `zeroerp_ci` dava 229 su 687 il 24-09), dice che
fuori dalla macchina di sviluppo la suite era **verde su due terzi dei file**.
⚠️ È ancora l'ultima misura CI registrata: al 14-10 la suite è a **830** file (corsa di Tid su dev), e il
corsa di Tid sullo scratch `zeroerp_ci` del 14-10 dà **164** rossi su 830, tutti
noti nel suo registro (`baseline-rossi-scratch.tsv`: 133 `ERRORE_FIXTURE`, 30
`ASSERZIONE`, 1 `SORGENTE_POLIMORFA`). Sullo scratch, ricostruito da zero, la suite è
quindi verde su circa **l'80%** dei file. ⛔ *Lo scratch non è
la CI*: il numero che vale resta quello del registro della CI. Il calo è
lavoro vero, non igiene: la fixture che **costruisce** il mondo invece di
cercarlo (§7 D7).

⚠️ **Il registro però non lo sa ancora.** `db/pgtap/baseline-rossi-ci.tsv` è
**fermo a 361 righe** dal 22-09, mentre la CI del 26-09 ne vede rossi 227: le righe rientrate le toglie
`scripts/pgtap-baseline-ci-rientrati.sh` leggendo il **log della corsa CI**, e
il log scade — va lanciato **il giorno stesso** della push su `Tito-dev` che
tocca `db/`. Finché non succede, il cancello tollera come «noti» circa 134 file
che sono già verdi: una regressione su uno di loro **non ferma il merge**.

⚠️ E il difetto vero non è la percentuale: è che quei file **passano sul DB di
sviluppo**. Cioè la suite verifica in larga parte *lo stato di una macchina*,
non che le migrazioni sappiano ricostruirla — e la seconda è la proprietà che
serve al secondo cliente. Un rosso `ERRORE_FIXTURE` non esegue **nessuna**
asserzione: sono aree che *sembrano* coperte.

#### Che cosa resta

La ricetta è stabilita e i builder ci sono (§7 D7: la riga di contesto che
costruisce se il DB è vuoto, il BB di composizione
`dbops.fn_pgtap_crea_mondo_cliente()`, i builder di fattura, filiale, gestore,
operatore umano, PDP e listino, e dal 2026-10-07 quelli di **ordine, preventivo,
commessa e attività di commessa**). Resta applicarla, e ciò che il giro 2 ha
lasciato
([brief-db-fixture-che-costruiscono-giro-2.md](../work-done/brief-db-fixture-che-costruiscono-giro-2.md)
§5, §7, §9, §11):

* ⏳ **certificare in CI** i rientrati dei lotti 1 e 2 — corsa e
  `pgtap-baseline-ci-rientrati.sh` lo stesso giorno (361 → 227, misura CI del
  26-09);
* ⏳ **i 18 rossi del lotto 2**, da guardare uno per uno (elenco nel brief, §11
  «Stato di chiusura»; ⚠️ per nome sono 19, scarto di uno da riconciliare), più
  i 3 del lotto 1 da riconciliare (16 + 21 + 3 = 40 su 43);
* ⏳ **lotto 3** — `pratiche` (37 a registro, quasi tutti verdi nella simulazione
  del 20-09) — e **lotto 4** — `vendite` (211), a famiglie: dash, resi,
  fatture, DDT, preventivi;
* ⏳ **le copie a mano dei documenti di vendita** (2026-10-07): un ordine scritto
  a mano in 54 pgTAP, un preventivo in 40, una commessa in 36, un'attività di
  commessa in 32. I builder ci sono (`dbops.fn_pgtap_crea_ordine`, `_preventivo`,
  `_commessa`, `_commessa_attivita`): si migrano con il lotto 4, per famiglia
  ([brief-db-fixture-rls-documenti-costruiti.md](../work-done/brief-db-fixture-rls-documenti-costruiti.md)
  §6);
* ⏳ i file che fissano `SET LOCAL app.current_user_id = '1'` (**7** al 13-10,
  28 al 22-09: l'utente 1 non esiste in CI) — una ricetta a sé, l'utente di sessione è
  quello del mondo costruito;
* ⏳ la **baseline di sviluppo** (`baseline-rossi.tsv`): **7** file al 13-10
  (12 al 26-09), di cui **6** muoiono nella fixture;
* ⏳ i file con `pgtap-runner: owner` (**130** al 13-10, 109 al 22-09): quanti di quei motivi siano
  ancora veri dopo la rev `20260912-38` non è misurato;
* 🔵 **decisione (Tid)**: i file legati a dati di **questa** macchina (gestore,
  CF, PIVA, PDP GAS) — si riscrivono o si dichiarano test di macchina;
* 🔵 **decisione (Tid)**: il ramo «ultimo SUPER_ADMIN» sull'identità è
  raggiungibile o è codice morto? Oggi a rifiutare è sempre il guard generico
  delle figlie, che scatta prima (brief giro 2, §7 punto 7).

#### 🔵 Due cancelli da disegnare (Tid)

1. **Il verso del registro** (brief giro 2, §6): un pgTAP che pesca in
   `anagrafiche.*` o `vendite.*` con `LIMIT 1` senza passare da un builder è
   rosso, con una soglia che può solo calare, come quella dei `throws_ok`.
   Deciso il 22-09: **dopo** il primo lotto, che è chiuso.
2. **La finestra differita dopo la riga di contesto.** La regola è scritta
   (template §3, guida pgTAP, `COMMENT` di `fn_pgtap_set_contesto_operatore`):
   *dopo la riga di contesto non si conta sulla finestra differita di default;
   chi la vuole la riapre con `SET CONSTRAINTS ALL DEFERRED`*. Un cancello in
   `guardrail_pgtap_preambolo.py` la renderebbe leggibile da uno script, ma il
   censimento del 21-09 dà 9 candidati e 7 falsi positivi, e il criterio
   «`IMMEDIATE` dopo una scrittura» è cieco sui file che **non hanno** un
   `IMMEDIATE` (i `pgtap-differiti: escluso`: nove caduti il 23-09).

⛔ Per tutti e due vale la lezione del 21-09: un criterio testuale conta le
scritture che **vede**, e una scrittura che passa per una funzione
(`fn_crea_*`, `fn_pgtap_crea_*`) è invisibile. Il cancello o guarda anche
quelle, o **dichiara di non vederle** — nel messaggio, non in un commento.

> ⭐ **Incrocio con D11, e decide l'ordine dei due lavori** (2026-09-20). Dei
> `throws_ok` senza discriminante, **102** stavano in file a registro qui, e
> **94** di quei 102 in file `ERRORE_FIXTURE` — che su un database ricostruito
> non eseguono nessuna asserzione. Discriminarli lì è severità che si vede solo
> su dbdev: prima la fixture, poi il discriminante.

---

### 🟠 D8 — `acquisti` e `magazzino`: modellati, non scritti

✅ **Deciso l'11-09-2026 (Tid): sono il PROSSIMO CANTIERE**, non congelati —
scritto in `.codex/PROJECT_CONTEXT.md`, con la conseguenza che questa voce
cercava: *ogni decisione presa su `vendite` è presa anche per `acquisti`*, e
un'asimmetria fra i due si chiude subito, non in una «fase due». ⚠️ `storico`
**non** è coperto dalla decisione come dominio (sul lato RLS l'ha chiuso D3).

✅ **Al 2026-09-26 i due schemi non sono più allo stesso punto.** `magazzino` ha
il comportamento dei lotti 1 e 2 — il terreno vuoto
(`work-done/brief-db-magazzino-lotto-1-terreno-vuoto.md`, chiuso il 17-09), il
motore (`work-done/brief-db-magazzino-lotto-2-motore.md`, lato DB chiuso il
18-09) e i verbi con permesso
(`work-done/brief-db-magazzino-verbi-con-permesso.md`, 25-09) — e **17** file
pgTAP; resta aperto come cantiere (collaudo a video). ⛔ `acquisti` è ancora
dove lo descrive la tabella: **zero** test, comportamento da scrivere. La
tabella qui sotto è la fotografia dell'8-09 e per `acquisti` resta vera.

| Schema                | Tabelle | FK  | CHECK | Funzioni | Viste | Test  |
| --------------------- | ------- | --- | ----- | -------- | ----- | ----- |
| `magazzino`           | 26      | 57  | 71    | **2**    | 4     | **1** |
| `acquisti`            | 9       | 42  | 25    | **2**    | 0     | **0** |
| `vendite` (confronto) | 88      | 359 | 194   | 292      | 60    | 253   |

⭐ Il modello c'è, ed è curato: 71 CHECK su `magazzino` non sono di un abbozzo.
Manca lo **strato di comportamento**. In un progetto DB-first questo è un tipo
preciso di debito: le regole che *non* sono esprimibili come vincolo non hanno
ancora un posto dove stare, e quando arriveranno la pressione sarà di scriverle
nel backend — cioè fuori dal modello architetturale dichiarato.

⚠️ Che il comportamento arrivi dopo il modello è l'ordine scelto (§4), non il
difetto. Il difetto possibile è un altro, e sta sul modello: `acquisti`
specchia il ciclo vendite, quindi ogni decisione presa di là (numerazione, serie,
perimetro emittente, righe senza prezzo, lineage) **è una decisione presa anche
di qua, che qui non è ancora scritta**. Più cresce `vendite`, più cresce il debito
di `acquisti` senza che nessuno lo tocchi.

🔴 **Il primo caso, verificato il 2026-10-04 (Q-5 di §2-bis):** `acquisti.ordini`
e `acquisti.ddt` non hanno né emittente né registro; l'unicità
`(anno, serie, numero)` è **globale**, mentre il DDT di un fornitore porta il
numero **del fornitore** (unicità per fornitore, come vuole
`acquisti/manual/ddt.md`), e senza `NULLS NOT DISTINCT` non vincola le righe con
`serie` NULL; nessuna tabella dello schema ha la RLS. È la decisione di `vendite`
(multi-emittente, RLS per emittente) non riportata su `acquisti`: si chiude nel
modello, prima del comportamento. L'emittente si nomina
`emittente_soggetto_ruolo_id` (Q-6, linee-guida-sql §2).

---

### 🟡 D9 — Il guard generico non scala per figlia, e il progetto sa già come si fa

`catalogo.articoli` ha **46 trigger**. La rilettura è importante: non sono 46
scelte diverse, sono **due pattern istanziati una volta per figlia** —
`trgfn_prevent_deactivate_if_children` ×29 (BEFORE ROW) e
`trgfn_child_requires_active_parent` ×8 (AFTER ROW), più i 3 di
audit/`tx_id`/storico, 2 `lock_columns` e 4 guard specifici di dominio.

⇒ **Ogni `UPDATE` su una riga di `catalogo.articoli` esegue 29 query `EXISTS`
sequenziali**, una per tabella figlia. In tutto il DB: 2.035 trigger, di cui
**758** sono queste due funzioni.

⭐ **Il progetto ha già la forma alternativa e l'ha già usata**: la primitiva
unica che ricava le figlie da `pg_constraint` invece di essere montata una per
figlia (è il pattern del cleanup). Non è un'invenzione da valutare: è
un'**incoerenza interna** fra due parti dello stesso framework.

⚠️ Effetto collaterale del numero: i nomi arrivano al limite di 63 caratteri e
vengono troncati con un hash (`…_articoli_descrizioni_aggiuntive_block_d_315e77`).
Un nome troncato non dice più cosa fa il trigger — e **l'ordine di scatto è
governato dal nome**.

Che porta al secondo pezzo: la **fase** (`_a10_` / `_z90_`) è presente su
**1.335 trigger su 2.035** — il **66%**. Per un terzo dei trigger l'ordine
relativo è quindi accidentale, deciso dall'alfabeto di una descrizione. Su un
sistema dove due guard `BEFORE ROW` parlano in ordine alfabetico, non è cosmesi.

**Aderenza naming, per completezza** (2026-09-08): prefisso `trg_` 2.030/2.035
(99,8%); suffisso evento 1.745/2.035 (85,8%); `fk_` 822/857 (95,9%); `chk_`
563/599 (94,0%); `uq_` 336/339 (99,1%); `pk_` 316/374 (84,5%); `ix_` 558/612
(91,2%). Il 94% dichiarato a febbraio regge — **tranne la fase**, che era la voce
con più conseguenze e non era misurata.

---

### 🟡 D11 — I registri di debito non calano

Un registro di debito è una buona invenzione **a condizione che scenda**. Stato
al 2026-09-08, salvo dove è scritta un'altra data:

| Registro                                   | Oggi                                                                                       |
| ------------------------------------------ | ------------------------------------------------------------------------------------------ |
| `dbops.vw_codici_errore_da_dichiarare`     | **545** su 897 codici (2026-09-20)                                                         |
| `db/pgtap/baseline-rossi-ci.tsv`           | **361** file al 13-10 (292 `ERRORE_FIXTURE`, 69 `ASSERZIONE`), fermo dal 2026-09-22 — nato il 09-09 con 407; la CI del 26-09 misura **227 rossi su 714**: il registro scende con `pgtap-baseline-ci-rientrati.sh` (D7) |
| `SOGLIA_THROWS_SENZA_DISCRIMINANTE`        | **115** (2026-10-13; 117 al 26-09, 129 all'08-09)                                          |
| `dbops.vw_fk_con_indice_missing_policy`    | **57**                                                                                     |
| `db/pgtap/baseline-rossi.tsv`              | **7** file al 2026-10-13 (6 `ERRORE_FIXTURE`, 1 `ASSERZIONE`) — erano 19, 16 al 12-09, 12 al 24-09 |
| `dbops.rls_perimetro_debito`               | **6** righe nel seed al 2026-10-13 (7 al 20-09, era 10 → D2)                               |
| `backend/scripts/tests/baseline-smoke.tsv` | **7** su 52 script (2026-10-13: dal 12-10 il perimetro comprende anche i 36 bash; 2 su 16 al 12-09) |
| Header di licenza mancanti                 | 2.042 file (misura 2026-08-26)                                                             |
| `dbops.vw_indici_ridondanti_prefisso`      | 1                                                                                          |
| Codici vivi senza messaggio                | 6 (tutti `W_`, §2.3)                                                                       |
| `dbops.vw_processi_che_bypassano`          | 1 (dichiarato, con data di ritiro)                                                         |

⭐ L'ultima riga è l'unica fatta bene: **una** voce, con il motivo e il momento in
cui sparisce. Le prime quattro sono liste lunghe, e la guida sui presidi dice
esattamente perché è un problema: *«il registro nasce piccolo. Se parte con
trenta righe, nessuno lo leggerà»*. `rls_perimetro_debito` è nato nella forma
giusta — ogni riga con la sua ragione — ed è calato di due terzi nel cantiere
che l'ha aperto.

⚠️ **E uno di questi registri cresce: i codici.** 508 → **545** su 897 (08-09 →
20-09) mentre `rls_perimetro_debito` scendeva. Il motivo è strutturale e sta
nella forma: gli altri hanno una **causa** e un **rimedio** (riscrivere la
fixture, discriminare l'asserzione, armare la RLS), il registro dei codici
misura il *terzo lato* — le dichiarazioni dell'applicativo — che si allarga a
ogni dominio nuovo. Non è un presidio che mente: è un presidio **senza un
verso**, ed è esattamente ciò che D11 chiede di dargli.

⚠️ Le due baseline pgTAP meritano una riga a parte: i file `ERRORE_FIXTURE`
(292 in CI e 6 in sviluppo al 13-10) non eseguono **nessuna**
asserzione. La loro copertura vale zero, non «parziale» — e sono aree che
*sembrano* coperte.

---

### 🟡 D12 — Documentazione: il problema non è più la quantità

1.410 pagine manuali contro 1.500 auto-generate: copertura sostanzialmente piena,
il gap di febbraio è chiuso. Restano due cose:

* `storico`: 111 pagine, media 15 righe, **98 sotto le 12 righe**. Sono specchi
  auto-generati, e va bene — ma gonfiano il conteggio di copertura del 7%;
* `magazzino` (35 righe/pagina) e `acquisti` (36) hanno pagine **presenti e
  sottili**. Coerente con D8: si documenta poco ciò che fa poco.

---

### 🟡 D16 — Test con una data scritta a mano: diventano rossi da soli

> Emerso il 2026-09-23: `vendite/test-nc-rata-unica-v1.sql`, test 6, rosso senza
> che fosse cambiato il codice.

Il test creava la nota di credito con `DATE '2026-09-10'` e poi le assegnava il
numero. La numerazione applica la **finestra di emissione** del registro: un
documento non può essere datato più indietro di N giorni. Quando il test è stato
scritto (17-18 settembre) il 10-09 era dentro la finestra. Il 23-09 la prima data
ammessa era l'11-09, e il test è morto con «la data del documento è troppo
vecchia perché sia ancora emettibile».

⛔ **Non è un caso isolato, è una classe.** Ogni volta che il database applica una
regola che dipende da **oggi** (finestra di emissione, scadenze, congelamenti,
competenze chiuse), un test che scrive a mano una data è una bomba a tempo:
verde il giorno in cui nasce, rosso qualche settimana dopo, senza che nessuno
abbia toccato niente. E il rosso arriva sempre nel momento peggiore, mentre si
sta lavorando ad altro, e sembra una regressione.

**La regola:** in un test, una data che passa da una regola temporale si scrive
**relativa a oggi** (`current_date`, `current_date - 5`, il primo del mese
corrente…), mai come letterale. Le date assolute vanno bene solo quando la regola
non guarda il calendario (per esempio una competenza passata a una funzione pura).

**Sanato:** il test 6 (fixture a `current_date`, e l'atteso del test 3 calcolato
dalla stessa data), con un commento sul perché.

**Che cosa resta:**

* ⏳ **Censimento.** Oggi nei pgTAP ci sono decine di date scritte a mano. Quasi
  tutte sono competenze, attività, ordini o preventivi, e non passano dalla
  finestra di emissione (se ci passassero, sarebbero già rosse). Il censimento
  vero va fatto per **regola temporale** — quali regole del DB leggono
  `current_date` — e poi per test che le attraversano, non per ricerca testuale
  delle date.
* 💡 **Presidio possibile**: un guardrail statico come
  `scripts/guardrail_pgtap_preambolo.py`, che segnali un letterale `DATE '…'`
  nella colonna `data` di un documento fiscale che il test poi numera. Da
  valutare dopo il censimento: senza sapere quali regole sono temporali, il
  presidio sarebbe una ricerca testuale, cioè il criterio sbagliato.

### 🟡 D24 — Il presidio C2 non vede i building block trigger che ricevono il codice negli argomenti

Trovato il 2026-10-10 chiudendo il lato BE di D22 (§9.2 di
[brief-db-guard-emittente-ba-unico](../work-done/brief-db-guard-emittente-ba-unico.md)). Il presidio
C2 (`backend/apps/core/tests/test_ui_action_e_canale_campi.py`, «una promessa
`highlight_form_fields` ha un sito che manda il campo») legge i siti PL/pgSQL da
`dbops.vw_punti_canale_campo`, che trova il codice nel **corpo** della funzione. Un building block
trigger lo riceve invece da `TG_ARGV` (`pg_trigger.tgargs`), e il `'campo'` lo mette nel contesto
per conto suo: per la vista quel sito non esiste.

* **Il caso che l'ha mostrato:** `E_DOC_EMITTENTE_BA_INCOERENTE` (BB
  `script.trgfn_doc_guard_emittente_ba`, sei tabelle) promette il campo, e il campo arriva — provato
  con una chiamata vera il 2026-10-10 su ordine, preventivo e contratto, `fields =
  ('emittente_fiscale_id',)` — ma il verso 1 era rosso con «nessun sito». Lato BE è una riga in
  `_ESENZIONI[("E_DOC_EMITTENTE_BA_INCOERENTE", 1)]`, motivata come esenzione della **misura**, non
  della regola.
* **Perché è un difetto della forma, non di un codice:** la stessa cecità vale per ogni BB che
  prende il codice dagli argomenti. Un override `highlight_form_fields` su uno qualunque di quei
  codici sarebbe rosso allo stesso modo, e un codice di quella forma che **non** manda il campo
  passerebbe inosservato dal verso 2. Fatto datato (dbdev, 2026-10-10): otto funzioni ricevono un
  codice `E_*` da `tgargs` (`trgfn_lock_columns`, `trgfn_doc_testata_lock_fuori_bozza`,
  `trgfn_doc_righe_lock_fuori_bozza`, `trgfn_doc_guard_emittente_ba`,
  `trgfn_doc_guard_chiusura_sorgente`, `trgfn_doc_ritira_commessa_attivita`,
  `trgfn_fattura_satellite_guard_congelamento`, `trgfn_guard_fatturazione_immediata_immutabile`);
  dei 24 codici così passati la vista ne vede due, `E_CODICE_NON_MODIFICABILE` ed
  `E_COLONNA_NON_MODIFICABILE`, probabilmente perché nominati anche altrove.
* **Richiesta al team DB:** insegnare alla vista la forma «BB trigger col codice negli argomenti» —
  per ogni trigger che esegue una funzione con un codice `E_*` fra i `tgargs`, un sito per quel
  codice, col canale campo della funzione (anche quando il `'campo'` dipende da una condizione,
  come la classe del codice in `trgfn_doc_guard_emittente_ba`).
* **Come si chiude:** quando la vista vede il sito, la riga di `_ESENZIONI` va rossa da sola (verso
  di ritiro del presidio) e il BE la toglie.

### 🟠 D31 — Le righe di contratto CANONE, ORARIO e CONSUMO non hanno la loro generazione

Trovato il 2026-10-13 dalla segnalazione BE del push batch CONTRATTO (un contratto senza scadenza
cadeva sul NOT NULL di `competenza_al`). Il lister dei contratti mandava ogni riga una volta sola, con
la competenza di tutto il contratto: un canone diventava un addebito unico. D-2 (a) di Tid: dal
`20261013-24` il push manda solo le UNA_TANTUM; la generazione per periodo del canone e le quantità di
orario e consumo dalle loro fonti si progettano nel brief
[brief-db-contratto-righe-periodiche-in-commessa.md](brief-db-contratto-righe-periodiche-in-commessa.md).
📝 Aperto, non iniziato: decisioni G-1…G-4 di Tid.

### 🟠 D32 — Un documento può nascere già fuori dalla bozza

Trovato il 2026-10-13 nel giro del `20261013-53` (i trigger della bolla che leggono l'emittente
girano dopo il normalize). Le regole dell'uscita dalla bozza stanno tutte sul passaggio di stato
(`BEFORE UPDATE`), su ogni famiglia: un `INSERT` con lo stato già avanti le salta. Provato sulla
bolla: nasce EMESSA e numerata con zero righe, e dopo le righe non si aggiungono più. Brief
[brief-db-documento-nasce-nello-stato-iniziale.md](brief-db-documento-nasce-nello-stato-iniziale.md).
📝 Aperto, non iniziato: decisioni N-1…N-3 di Tid.

---

## 4. Cosa NON è un difetto

* ⛔ **`contabilita` vuoto.** Fuori perimetro per decisione: se servirà, sarà un
  aggancio a una contabilità esterna, con la forma dettata dal sistema di
  destinazione. Zero test su zero oggetti non è un gap.
* ⛔ **Un dominio modellato che aspetta il suo turno** (`acquisti`, e
  `magazzino` prima dei suoi lotti). Il progetto è nato DB-first per scelta
  (Tid, chiarita il 2026-10-04): un anno sul solo DB per fissare nomi,
  trigger e regole, e poi BE e FE. Proprio l'assenza di consumatori ha reso
  economici i refactor pesanti — rinomine di colonne, la ripartenza in
  `migrations_v2` — che con BE e FE già scritti molti non si sarebbero fatti.
  L'ordine di costruzione non si vota (§5); il difetto, se c'è, è una decisione
  di `vendite` non riportata su `acquisti` (D8).
* ⛔ **Il numero di trigger per tabella, di per sé.** È la conseguenza del numero
  di figlie. Il difetto è la *forma* del pattern (D9), non il conteggio.
* ⚠️ **Il mix `VARCHAR + CHECK` vs tabella-lookup.** Febbraio chiedeva una guida:
  il criterio è oggi scritto in `linee-guida-sql.md` §«esiste già una chiave
  stabile per-design?» e in memoria (JSONB vs tabella-vocabolario). Voce chiusa.
* ⚠️ **`relforcerowsecurity = false` ovunque.** È corretto: l'owner deve poter
  fare manutenzione. Il pgTAP che deve esercitare le policy accende `FORCE` da
  sé. Non confondere questo con D4, che è tutt'altro.
* ⚠️ **Il `makefile` locale usa `--contexts="!test AND !provision"`** e quindi
  carica anche `dati_macchina`, mentre la CI usa
  `--contexts="!provision and !dati_macchina"`. È **voluto**: sul DB di sviluppo i
  dati di macchina servono.

---

## 5. Scorecard — pesata, non mediata (2026-09-08, aggiornata al 2026-09-26; numeri al 2026-10-13)

Il peso è **la conseguenza di un difetto in quell'area**, non la sua estensione.

| Area                                   | Peso    | Voto       | Perché                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| -------------------------------------- | ------- | ---------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Catena di verifica (CI)**            | 🔴 alto  | **7,5/10** | Dal 2026-09-09 la suite pgTAP è un cancello vero: baseline misurata dalla CI, niente `continue-on-error`, bootstrap che fallisce invece di passare. Resta il registro fermo a 361 mentre la CI misura 227 rossi (26-09): finché non si tolgono i rientrati, file già verdi sono tollerati come rossi (D7)                                                                                                                                                                                                                              |
| **Perimetro dei dati (RLS)**           | 🔴 alto  | **8/10**   | D2 e D3 chiusi l'11-09-2026: dominio documento protetto fino ai satelliti, versioni di storico con scope congelato, e due presidi a criterio (`vw_rls_perimetro_scoperto`, `vw_storico_scope_da_dichiarare`) che vedono le tabelle nuove. Restano le due policy inerti di `acquisti` (D4 → D8), a registro con la ragione; `shop.ricevute` armata il 12-09. D13 (il `RETURNING` del BA per gli operatori non di default) chiuso il 13-09 |
| **Copertura test**                     | 🔴 alto  | **4/10**   | 830 file (corsa su dev del 14-10; 714 al 26-09), ma su un DB ricostruito da zero la suite è rossa su **227 file su 714** (corsa CI del 26-09, l'ultima registrata; il registro è ancora a 361 finché non si tolgono i rientrati). Il 38% delle funzioni non è mai nominato (D7)                                                                                                                                                                                                                                                                                          |
| **Postura di sicurezza degli oggetti** | 🟠 medio | **7,5/10** | I tre invarianti di D5 presidiati per criterio (`search_path` dal 12-09, pin applicati). Non di più per i due rubinetti di D6-bis (il registro `sec_functions_owner` e la sync sono riservati al migratore dal 26-09)                                                                                                                                                                                                     |
| **Simmetria del dominio**              | 🟠 medio | **non votata** (04-10) | Che lo strato di comportamento di `acquisti` e `magazzino` arrivi a lotti, dopo il modello, è l'**ordine di costruzione** scelto, non un difetto (§4). Il voto 4/10 dato fino al 04-10 misurava il calendario. Resta vero, ed è in D8, il punto **sul modello**: le decisioni prese su `vendite` valgono anche per `acquisti` |
| **Osservabilità dei presidi**          | 🟠 medio | **7/10**   | D10 chiuso l'11-09-2026: le 30 viste hanno un destinatario che ha già riferito, e la classificazione è **dato** (`dbops.presidi`). Non 8+ per il debutto col rumore (processi ritirati in `vw_job_run_da_guardare`)                                                                                                                                                                                                                      |
| **Gestione del debito**                | 🟠 medio | **6/10**   | Registri ben progettati; le liste lunghe restano lunghe, e ne è nata una nuova da 362 (D11)                                                                                                                                                                                                                                                                                                                                              |
| **Pattern trigger e automazioni**      | 🟡 basso | **7,5/10** | Riuso raro (758 trigger da due funzioni), framework `ci_apply` eccellente; la forma per-figlia non scala e la fase è al 66% (D9)                                                                                                                                                                                                                                                                                                         |
| **Error handling / codici errore**     | 🟡 basso | **8,5/10** | Contratto a tre lati esplicito e presidiato; il registro **sale**                                                                                                                                                                                                                                                                                                                                                                        |
| **Disciplina Liquibase**               | 🟡 basso | **9/10**   | 3.354 changeSet, cinque cancelli dedicati, tutti nati da un incidente reale                                                                                                                                                                                                                                                                                                                                                              |
| **Documentazione**                     | 🟡 basso | **8,5/10** | Copertura piena; sottile dove il dominio è sottile                                                                                                                                                                                                                                                                                                                                                                                       |
| **Naming**                             | 🟡 basso | **8/10**   | 94-99% sui vincoli; 66% sulla fase dei trigger, che è la voce con conseguenze                                                                                                                                                                                                                                                                                                                                                            |

### Il giudizio, in una frase

⭐ **Il metodo di ingegneria di questo progetto è sopra la media del settore** —
la guida sui presidi, il contratto a tre lati dei codici errore, il framework
delle automazioni per pattern e il passaggio dei pgTAP al ruolo applicativo sono
cose che in un ERP non si vedono quasi mai.

✅ **E la catena che deve rendere vero tutto questo, dal 2026-09-09, tiene**:
la suite pgTAP ferma un merge su un rosso nuovo (D1). ⚠️ Con una cosa scomoda,
adesso misurata: fuori dalla macchina di sviluppo la suite era rossa per due
terzi (09-09), ed è ancora rossa per un terzo (227 file su 714, CI del 26-09). Non è
una regressione — è sempre stato così — e la differenza fra «i test
passano» e «le migrazioni sanno ricostruire un sistema che passa i test» è
tutta lì dentro (D7).

⚠️ **«Production-ready»**: all'8 settembre non era la parola giusta, e non per
la qualità del design — per D1, D2 e D3: righe di cinque famiglie di documento
su sei e tutto lo storico leggibili da chiunque. Chiusi tutti e tre fra il 9 e
l'11 settembre, la frase torna difendibile sul perimetro dei dati — e il 13
settembre è caduto anche D13, che su un'installazione a due emittenti avrebbe
impedito al secondo di aprire clienti. Quello che resta sono le due policy
inerti di `acquisti` (D4 → D8, a registro con la ragione), il pezzo nuovo di
D6 e il registro dei rossi in CI.

---

## 6. Checklist, in ordine di ritorno

> `[ ]` = **da fare** — sono le voci di §3. `[x]` = **fatta** — resta qui perché
> una check-list completa serve a chi la scorre, e il **dettaglio** di ognuna è
> in §7 «Attività svolte» (con la data e il brief).

### 🔴 Prima di tutto il resto

* [x] **D1** — ✅ chiuso il 2026-09-09: classificatore bilingue, baseline della
      CI committata, `continue-on-error` tolto, bootstrap che fallisce. (D1-bis,
      la frase di `.codex/AGENTS.md` su `baseline-rossi-ci.tsv`, è diventata
      vera da sé nel momento in cui il file è stato committato.)

### 🔴 Il perimetro

* [x] **D2** — ✅ chiuso l'11-09-2026, brief
      `work-done/brief-db-perimetro-emittente-righe-documento.md`. Presidio
      transitivo in servizio, 10 righe di debito con la ragione.
* [x] **D3** — ✅ chiuso l'11-09-2026, brief
      `work-done/brief-db-rls-storico-scope-congelato.md` — compreso
      `dbops.audit_log` (cancello sugli scrittori + append-only).
* [x] **D4** — ✅ `shop.ricevute` armata il 2026-09-12 (`20260912-42/43`,
      registro 10 → 8). Per `acquisti.ddt`/`ordini` prima il modello — colonna
      emittente e veste operatore — cioè **D8**: restano a registro con la
      ragione, non sono D4.
* [x] **D5** — ✅ tre invarianti su tre presidiati per criterio
      (`security_invoker` dal 09-07, `relrowsecurity` dall'11-09, `search_path`
      dal 12-09 in `test-security-definer-search-path-v1.sql`).
* [x] **D6** — ✅ pin applicati il 12-09 (`-39/-40/-41`, forma `pg_catalog,
      public, pg_temp`); ✅ il 26-09 registro `sec_functions_owner` in sola
      lettura per l'app e `fn_sync_functions_owner` riservata al migratore da
      una guardia nel corpo (`20260926-11`/`-12`, applicati, pgTAP verdi) —
      brief `work-done/brief-db-registro-owner-e-sync-riservati-al-migratore.md`.
      `EXECUTE` a PUBLIC sulla sync: valutato, resta — la sync si difende da
      sola, con `session_user`.
* [ ] **D6-bis** — scegliere **una** forma canonica di `search_path` per le
      `SECURITY DEFINER` (`pg_catalog, <schemi necessari>, pg_temp`, con
      `pg_temp` sempre ultimo ed esplicito) e allineare le 18 che oggi non
      elencano `pg_temp` e le 5 che mettono `public` prima di `pg_catalog`.
      ⛔ **Non applicabile a vista**: `pg_catalog, pg_temp` è la scelta sbagliata
      per chi tocca un'estensione (`dblink`, `unaccent`, `postgis`,
      `plpgsql_check` stanno tutte in `public`). Si decide **per funzione**,
      guardando i suoi chiamati — o si qualifica la chiamata, o `public` resta
      nell'elenco.

### 🟠 La sostanza

* [x] **D8** — ✅ deciso l'11-09-2026 (Tid): prossimo cantiere, scritto in
      `.codex/PROJECT_CONTEXT.md`. ✅ `magazzino` ha il comportamento dei lotti
      1 e 2 (17-09, 18-09, verbi con permesso il 25-09). ⛔ `acquisti` è ancora
      a zero. ⚠️ `storico` resta senza decisione come dominio; sul lato RLS
      l'ha chiuso D3.
* [x] **D10** — ✅ chiuso l'11-09-2026: digest su catalogo `dbops.presidi`, due
      timer. Residuo: i processi ritirati in `vw_job_run_da_guardare` (decisione
      del team DB).
* [~] **D7** — far calare il registro della CI e portare a zero la baseline
      di sviluppo nella *fixture*. ✅ Fatto (§7 D7): il perimetro (12-09), il
      triage delle cause e la riga di contesto che costruisce (20/21-09), il BB
      di composizione e i lotti 1 e 2 (22-24/09) — **227 rossi su 714** in
      CI il 26-09, contro 407 su 601 il 09-09. ⏳ Resta (§3 D7): la corsa CI
      che certifica i rientrati (registro **fermo a 361**), i 18 rossi del
      lotto 2, i lotti 3 (`pratiche`) e 4 (`vendite`), i file con l'utente
      `'1'` (7 al 13-10), i 6 `ERRORE_FIXTURE` della baseline di sviluppo (7 file al 13-10), due decisioni
      per Tid e due cancelli da disegnare.
* [x] **D13** — ✅ chiuso il 2026-09-13: changeSet `20260913-01/02/03`
      applicati, baseline di sviluppo senza regressioni, brief
      `brief-db-ba-riserva-emittente-operatore-d13.md`. ✅ Le tre copie
      Python della regola vecchia sono delegate al check dal 13-09 (team BE,
      brief §6.2). Restano due decisioni di modello in coda (§3.4).
* [~] **D11** — dare a ciascun registro lungo un **verso** (chi lo abbassa, di
      quanto, entro quando), o dichiararlo congelato con il motivo.
      ✅ La soglia `throws_ok` è scesa **129 → 117** fra il 20 e il 24-09, e a
      **115** al 13-10 —
      due volte con un test verde per l'errore sbagliato (§7 D11, §7 D7).
      ⛔ Restano i due registri grossi, e sono quelli che non hanno un verso:
      i rossi della CI (361 a registro, 227 misurati il 26-09) e i codici da
      dichiarare, che sono **saliti** (508 → 545 al 20-09).
* [ ] **D11-bis** — scrivere il messaggio dei sei `W_` che non ce l'hanno
      (append al CSV dei messaggi, mai un loader nuovo), oppure dichiarare che
      quei codici non raggiungono mai un operatore — e scriverlo nel `note`.
* [x] **D14** — ✅ chiusa il 2026-09-22, brief archiviato in
      `work-done/brief-db-partita-merce-per-documento.md`: otto giri fra il 17 e
      il 22-09, **sette applicati** e l'ottavo provato e **ritirato** lo stesso
      giorno. La partita di merce si legge **per documento**, l'eleggibilità ha
      **una** implementazione e il classificatore, `af` e i billing account si
      leggono **per chiave** (§7). Residui dichiarati, ciascuno con la sua sede:
      due decisioni **non prese** (la catena del `sospetto`, raccomandato
      lasciar stare; **D8(b)**, che nessuna misura reclama), i tre `LIKE` di
      `fn_accredita_riga_reso` — un changeSet suo —, i preventivi come quarto
      adottante del BB «righe solo in bozza» (dopo il censimento
      dell'approvazione prezzo) e tre voci BE (due commenti che nominano oggetti
      ritirati, la decisione sui pre-check `_STATI_RIGHE_MODIFICABILI`).
      ⛔ La statistica assente **non** è un residuo di questo cantiere: è **D15**.
* [x] **D15** — dare al database **un** posto che tiene aggiornate le
      statistiche (`dbops`/`maintenance`): in `vendite` 82 tabelle su 87 non
      hanno mai avuto un `ANALYZE`, quindi ogni piano nasce da stime di default
      e si ribalta da solo. ⛔ È un **prerequisito** di qualunque cantiere che
      misuri un piano, non una miglioria — e finché non c'è, un guadagno
      dichiarato in millisecondi non è difendibile.
      ✅ Chiusa il 2026-10-15: `work-done/brief-db-statistiche-tabelle-job-notturno.md`.
* [ ] **D17** — Q-2, rimandata da Tid: legare le GUC di bypass al proprietario
      delle tabelle (proposta in `work-done/brief-db-esclusioni-implicite.md`
      §4). Il resto di D17 è chiuso (§7), R-1 del BE compresa.
* [ ] **D18** — la catena delle istanze su un PDP: ricalcolo DEFINER della
      catena intera da un trigger `AFTER` senza `OF`; brief
      `work-in-progress/brief-db-catena-istanze-pdp.md`, da analizzare con Tid.

### 🟡 Struttura

* [ ] **D9** — valutare la primitiva unica «figlie da `pg_constraint`» al posto
      dei guard per-figlia, partendo da `catalogo.articoli` (29 `EXISTS` per
      update).
* [ ] **D9-bis** — portare la fase (`_a10_`/`_z90_`) sul 34% di trigger che non
      ce l'ha, o dichiarare che per quelli l'ordine è indifferente.
* [ ] **D12** — nessuna azione: la documentazione seguirà il dominio.
* [ ] **D16** — censire le regole del DB che leggono `current_date` e i pgTAP
      che le attraversano con una data scritta a mano; poi decidere se serve un
      guardrail statico.
* [x] **D19** — allineare righe e componenti di preventivo, ordine e DDT a
      contratto e offerta: chiusa il 2026-10-08 (§7).
* [x] **D20** — i tre debiti rimasti da D19: brief `brief-db-righe-e-componenti-debiti-residui`,
      chiuso e archiviato il 2026-10-09.
* [x] **D26** — la testata dopo l'emissione, colonna per colonna: brief
      `work-done/brief-db-testata-dopo-emissione` — chiuso e archiviato il 2026-10-11 (fasi 1-2 e giro R-DB a DB,
      BE/FE, collaudo a video di Tid).
* [x] **D22** — il guard emittente <-> BA scritto sette volte: brief
      `work-done/brief-db-guard-emittente-ba-unico` — chiuso e archiviato il 2026-10-10 (DB `20261010-17…-19`, BE §9).
* [ ] **D24** — la vista del presidio C2 (`dbops.vw_punti_canale_campo`) non vede i BB trigger col
      codice negli argomenti: al team DB (§3). Al rimedio, il BE toglie l'esenzione di
      `E_DOC_EMITTENTE_BA_INCOERENTE`.
* [x] **D23** — il tetto delle 10.000 righe della ricerca universale (totale e pagine falsi oltre
      il tetto): brief `work-done/brief-db-ricerca-universale-tetto-10000` — chiuso e archiviato il 2026-10-10 (DB `20261010-16`, BE/FE §7.4).
* [x] **D21** — ordine, DDT e reso col cliente come preventivo, offerta e contratto: brief
      `work-done/brief-db-esecutivi-ba-coppia` — chiuso e archiviato il 2026-10-10 (DB `20261009-62…-92` e
      `20261010-02…-07`, BE/FE §12).
* [x] **D25** — i residui di «l'istanza nasce col billing account»: brief
      `work-done/brief-db-istanza-nasce-col-ba-residui` — chiuso e archiviato il 2026-10-10 (DB `20261010-50…-59`, FE/BE §4).
* [x] **D27** — gli indirizzi del documento seguono il cliente: brief
      `work-done/brief-db-indirizzi-documento-seguono-il-cliente` — chiuso e archiviato il 2026-10-19 (DB, BE/FE, collaudo di Tid).
* [x] **D26-2** — le funzioni che ripianificano a ogni chiamata: brief
      `work-done/brief-db-plancache-funzioni-con-query-incorporate` — chiuso e archiviato il 2026-10-18
      (DB `20261010-44`, `20261011-42`, `20261012-03`, `20261018-15 … -33`, `-48 … -52`; verbo dell'accredito
      ~115 → 50,6 ms; residuo in D36).
* [x] **D28** — le righe evase di un DDT da ordine: brief `work-done/brief-db-ddt-righe-evase-dall-ordine` —
      chiuso e archiviato il 2026-10-11 (DB `20261011-05 … -20`, `-34`, `-35`; BE/FE §10; collaudo di Tid superato).
* [x] **D29** — annullare un documento con legami: brief `work-done/brief-db-annullo-documento-con-legami` —
      chiuso e archiviato il 2026-10-11 (DB `20261011-68 … -91` e il caso 1 del giro D28; BE/FE §9; collaudo di Tid).
* [x] **D30** — tornare indietro, annullare la commessa: brief `work-done/brief-db-annullo-a-valle-riapre-a-monte` —
      chiuso e archiviato il 2026-10-13 (DB `20261012-08 … -24`, `-27 … -29`, `-43 … -47`, `20261013-69 … -72`;
      BE/FE §9, §10.8, §11.6; collaudo di Tid).
* [ ] **D31** — canone, orario e consumo del contratto in commessa: brief
      `brief-db-contratto-righe-periodiche-in-commessa` (aperto il 2026-10-13, non iniziato; decisioni G-1…G-4).
* [ ] **D32** — un documento nasce nel suo stato iniziale: brief
      `brief-db-documento-nasce-nello-stato-iniziale` (aperto il 2026-10-13, non iniziato; decisioni N-1…N-3).
* [x] **D33** — un cliente manuale per soggetto e utility: brief
      `work-done/brief-db-cliente-manuale-uno-per-soggetto-e-utility` — chiuso e archiviato il 2026-10-15
      (DB `20261014-08 … -20`; BE §6-bis; smoke clienti verde).
* [x] **D34** — dati societari in creazione: brief
      `work-done/brief-db-dati-societari-in-creazione` — chiuso e archiviato il 2026-10-22
      (DB `20261020-01…03`; BE/FE §6.1; collaudo di Tid riuscito).
* [x] **D35** — `zeroerp_log` nella fase `ruoli`: brief
      `work-done/brief-db-zeroerp-log-nella-fase-ruoli` — aperto e chiuso il 2026-10-15.
* [x] **D36** — il perimetro una volta per istruzione, le famiglie che restano: brief
      `work-done/brief-db-perimetro-una-volta-famiglie-residue` — aperto il 2026-10-18, chiuso il 2026-10-21.
---

## 7. Attività svolte — cosa è stato chiuso, e con che cosa

> Questa sezione è il **rovescio di §3**: qui sta ciò che era un difetto e non lo
> è più. Un numero che compare in **tutti e due** i posti (D6, D7, D11,
> D12, D17) non è una ripetizione: in §3 c'è **il lavoro che resta**, qui **quello
> fatto**. ⭐ **D14 non è più in §3**: è chiusa, e ciò che la sua chiusura ha
> scoperto è una voce nuova: **D15**, le statistiche che non esistono.
>
> Le date sono quelle dichiarate nei brief, e i brief restano la sede del
> dettaglio: qui si dice **che cosa è cambiato nel sistema**, non come ci si è
> arrivati.

### ✅ D26-2 — Le funzioni che ripianificano a ogni chiamata — chiuso il 2026-10-18

Il brief `work-done/brief-db-plancache-funzioni-con-query-incorporate.md`, aperto il 2026-10-10. Censite
le funzioni con query incorporate (D-1); il lister dei DDT senza filtri (D-2, `20261012-03`: la CTE
`src` si ricalcolava per ogni riga); i resi col piano generico (D-3a, `20261011-42`); pannello
«Passaggi» e liste nel brief figlio della lineage seminata (D-4…D-6). Poi il verbo dell'accredito
(D-3b), riga 15922, da ~115-120 ms a **50,6 ms** di mediana (dbdev come app, fatti datati):
D-3b-1 (`20261018-15`) i tre filtri `LIKE`/`split_part` su `segment_key` che sotto RLS non arrivavano
all'indice, ora da `segment_base`; D-3b-2 (`20261018-16…-33`, `-48…-51`) il perimetro dell'operatore
calcolato una volta per istruzione in tutte le policy ef_whitelist — `fn_scope_ef_perimetro` col
perimetro di `fn_get_emittenti_scope_pk_ids` in una sottoquery, l'emittente della riga da
`fn_resolve_emittente_fiscale_id` (DEFINER, decisione di Tid), gli adattatori riscritti sul
risolutore, presidio `script/test-scope-ef-perimetro-una-volta-per-istruzione-v1` sul testo e sul
piano; D-3b-3 (`20261018-52`) il `tx_id` generato sulla connessione di log persistente invece di
aprirne una a ogni transazione (12-13 → 1,3-2,2 ms). Debito residuo: **D36** (le famiglie che
restano per riga).

### ✅ D1 — Il cancello pgTAP in CI — chiuso il 2026-09-09

Il passo «Suite pgTAP» girava con `continue-on-error: true` e leggeva una
baseline mai committata: **600 file e ~6.183 asserzioni** buttati via a ogni
corsa. Ora il classificatore è bilingue (`ERRORE|ERROR`, il server della CI parla
inglese), `--update` **si rifiuta di scrivere** se non passa nemmeno un file,
`baseline-rossi-ci.tsv` è committato e **misurato dalla CI** (407 rossi su 601
alla prima corsa), `continue-on-error` è tolto e il ramo di bootstrap
**fallisce** invece di passare. ⭐ *Un cancello che passa perché non ha misurato
niente è peggio di un cancello assente.*

### ✅ D2 — Il perimetro emittente, fino a righe e satelliti — chiuso l'11-09-2026

Era protetta **una** famiglia di documento su sei, e le righe delle altre
cinque erano leggibili da qualunque operatore. Ora sono **nove** (più le sette
partizioni di `vendite.note`), il registro del debito è sceso da **33 a 10
righe** e `db/pgtap/rls/` è passato da 30 a 39 file. ⭐ In servizio resta un
**presidio a criterio transitivo** (`dbops.vw_rls_perimetro_scoperto` +
`rls_perimetro_debito` + `test-rls-perimetro-scoperto.sql`): una tabella nuova
con una FK verso una protetta esce `NON_DICHIARATO` e fa rosso il test 2.
Brief `work-done/brief-db-perimetro-emittente-righe-documento.md`.

### ✅ D3 — Lo `storico` porta il proprio perimetro — chiuso l'11-09-2026

120 tabelle senza RLS e 52 leggibili dall'app: chiudere D2 senza D3 avrebbe solo
spostato il punto da cui si legge. Ora lo scope **si cattura alla scrittura e si
congela** (`origine_schema` + `scope_emittente_fiscale_id`, mappa
`storico_scope_policy` con ripiego sull'archivio del padre), le **37 shadow**
delle madri protette hanno policy generata, backfill di **65.751 versioni** senza
residue, `REVOKE DELETE` all'app su tutto lo schema, e
`vw_storico_scope_da_dichiarare` vede quelle che non lo portano. Le tabelle nuove
nascono **armate** dal generatore: il lavoro è stato **uno**, non 120. Nello
stesso giro `dbops.audit_log` prende un **cancello** alla scrittura più il
`REVOKE UPDATE/DELETE` dichiarato nel loop dei grant — *un registro di audit
modificabile da chi è auditato non è un registro*.
Brief `brief-db-rls-storico-scope-congelato.md`.

### ✅ D4 — Le policy inerti — chiusa il 2026-09-12 (il resto è D8)

`acquisti.ddt`, `acquisti.ordini`, `shop.ricevute`: la policy c'era, la RLS era
spenta — il difetto che si auto-nasconde, perché `EXISTS (SELECT 1 FROM
pg_policies …)` legge verde. ✅ L'invariante generale è presidiato dal **criterio
`POLICY_INERTE`** (caso costruito nel test 7), e `shop.ricevute` è stata
**armata** il 2026-09-12 (`20260912-42/43`, registro 10 → **8**). Le due di
`acquisti` sono **D8**: *manca il modello, non l'accensione*.
Brief `brief-db-fixture-che-costruiscono-d7-d6-d4.md` §5.

### ✅ D5 — I tre invarianti di forma hanno un presidio — chiusa il 2026-09-12

Tre proprietà che, se violate, **non producono nessun errore visibile**, ora
hanno un presidio a **criterio** (non un elenco di nomi):

| Invariante                                                | Presidio                                                                                                    |
| --------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------- |
| Una vista che tocca dati in RLS ha `security_invoker`     | criterio transitivo dal 2026-09-07, ha sostituito quattro elenchi a mano. Zero violazioni                   |
| Una tabella con policy ha la RLS **accesa**               | criterio `POLICY_INERTE` dall'11-09 (le 2 violazioni rimaste sono D8)                                       |
| Una funzione `SECURITY DEFINER` ha un `search_path` fisso | `db/pgtap/dbops/test-security-definer-search-path-v1.sql` dal 12-09, con due soglie che possono solo calare |

⭐ **La lezione che resta, ed è la ragione per cui D5 esiste**: il criterio con
cui nasce un presidio è un **indicatore in ritardo** — le prime due righe hanno
morso prima di essere presidiate, la terza è stata presidiata prima di mordere
solo perché le è passato accanto un cantiere. Non è una voce da fare: è il
motivo per cui i presidi si scrivono **quando un cantiere ci passa**.

### ✅ D6 — I pin del `search_path` — chiusi il 2026-09-12

Tre `SECURITY DEFINER` di `postgres` senza `search_path`, una sul percorso di
**305 trigger** (`fn_get_or_create_session_tx_id`), una che cambia il
proprietario di funzioni. Pin applicati (`20260912-39/40/41`) nella timeline
normale, senza superuser: due col **prestito di proprietà** via
`fn_sync_functions_owner`, la terza con una **copia di servizio** della sync —
la sync non può prestarsi a sé stessa. La forma è `pg_catalog, public, pg_temp`
e **non** `pg_catalog, pg_temp`: la catena tocca `dblink`, che vive in `public`.
⚠️ La lezione del giro: la forma «prudente» avrebbe **accecato** `dblink` dentro
un `WHEN OTHERS`, spegnendo il tracciamento delle transazioni **senza un rosso da
nessuna parte** — *una forma canonica uguale per tutte non esiste: si decide per
funzione, guardando ciò che chiama.*

✅ **E il registro degli owner — chiuso il 2026-09-26.** Chi scriveva
`dbops.sec_functions_owner` ed eseguiva la sync sceglieva il proprietario delle
DEFINER di `postgres`, e `zeroerp_app` aveva entrambe le porte. Ora il registro
è in sola lettura per l'app (tre sedi, `90_end/20260926-12`) e la sync rifiuta
con `42501` chi non possiede lo schema `dbops` (`20_code/dbops/20260926-11`). La
difesa sta **nel corpo** e non nell'ACL, che per una funzione di `postgres` il
loop dei grant riscrive e il cambio di proprietario rimappa; il chiamante si
legge da `session_user` (dentro una DEFINER `current_user` è il proprietario —
limite dichiarato: un `SET ROLE` non lo cambia). Presidi:
`test-sec-functions-owner-riservato-v1` (come app) e
`test-sec-functions-owner-migratore-passa-v1` (come owner). Dettaglio nel
[brief](../work-done/brief-db-registro-owner-e-sync-riservati-al-migratore.md).
Resta D6-bis (§3).

### ✅ D7 — Il triage è partito dal perimetro — 2026-09-12, in CI dal 14-09

Dei rossi sul database ricostruito da zero, i primi **21** erano i test di
`script/fn_scope_*` (12) e di `rls/` (9) — cioè quelli che decidono *chi vede
cosa* — tutti con la stessa causa: la fixture **cercava** i soggetti nei dati
esistenti, e su un database ricostruito `anagrafiche` è a zero. Riscritti con
fixture che **costruiscono** il mondo: **20 verdi** su dbdev e su `zeroerp_ci`,
e il ventunesimo era un'altra classe (in CI il ruolo batch non veniva
provisionato) e ha avuto il suo passo in `ci-validate.yaml`. Sono **usciti dal
registro**, e da allora i rientrati li toglie
`scripts/pgtap-baseline-ci-rientrati.sh` **leggendo il log della corsa**, non una
mano. Il debito che resta è in §3 D7. Brief
`brief-db-fixture-che-costruiscono-d7-d6-d4.md` (in `work-done/` dal 19-09).

### ✅ D7 — I test RLS dei documenti costruiscono il loro documento — 2026-10-07

I sette `rls/` che **cercavano** il documento da provare (commessa, DDT, ordine,
preventivo, fattura) e andavano in soft-skip su un database ricostruito ora lo
**costruiscono**, con due aziende (A lo possiede, B è l'estranea) e senza soft-skip.
Quattro builder nuovi in `dbops` (ordine, preventivo, commessa, attività; gli ultimi due
compongono le madri del dominio). Emersi e corretti due verdi dovuti ai dati, fra cui
l'invarianza del lineage misurata sul grafo intero. Brief
`brief-db-fixture-rls-documenti-costruiti.md` (in `work-done/`).

### ✅ D7 — Il giro 2: la fixture che costruisce il mondo — 20-09 → 24-09

* **Il triage delle cause (20-09).** I 362 file a registro, rieseguiti come
  `zeroerp_app` sullo scratch leggendo la **prima** riga `ERROR` di ciascuno:
  una malattia sola in tre forme — la fixture *cerca* l'azienda, il billing
  account, un soggetto, invece di costruirli. E la radice era una riga di
  preambolo: su un DB vuoto `fn_pgtap_set_contesto_operatore()` apriva un
  contesto vuoto.
* **La riga di contesto costruisce se il DB è vuoto** (`20260920-01`, nel BB e
  non nei 352 file): 66 file da rosso a verde. Nello stesso giro un difetto del
  **database da zero** reso visibile: `config.tipi_ruoli.entita_tabella` /
  `entita_colonna_codice` le scriveva solo un `UPDATE` in `00_schema`, che da
  zero tocca zero righe — su un'installazione nuova la ricerca soggetti per
  codice era rotta. Rimedio nel CSV e nel mirror.
* **La corsa CI del 21-09** (293 rossi su 674) ha trovato una regressione, e la
  causa era la rev stessa: quando costruisce, la riga di contesto chiude la
  finestra dei differiti come ogni builder. Il rimedio «uscire IMMEDIATE in
  tutti i rami» è stato provato e **ritirato** (chiudere i vincoli nei panni di
  un altro attore vuol dire sotto un'altra RLS); è stato scritto invece il
  **contratto** (`20260921-18`, solo `COMMENT`) e la regola per i file: dopo la
  riga di contesto, chi vuole la finestra differita la riapre.
* **I file che committavano** (col contesto in autocommit o chiusi con
  `COMMIT`): chiusi nel lotto 2, nella suite non committa più nessuno. Il
  residuo `PGTR0001` che lasciavano teneva verdi altri sei file; tolto quello,
  nove file che contavano sulla finestra di default sono caduti e sono stati
  sanati. Lo scratch ricostruito ha **zero** emittenti residui.
* **Il BB di composizione** `dbops.fn_pgtap_crea_mondo_cliente()` (`20260922-17`,
  con il suo presidio): la regola d'ordine fra mondo, legame del BA e contesto
  sta in un oggetto, invece di essere riscritta a mano in 205 file.
* **Lotto 1** (`config`, `pagamenti`, `documenti`, `catalogo`, `ui`, `dbops`, 43
  file), chiuso il 23-09: 21 file riscritti, 235 asserzioni verdi da zero, i
  builder `fn_pgtap_crea_fattura` e `fn_pgtap_crea_filiale_bancaria`
  (`20260923-04/-05`) — un BB, non nove copie. Committato in `9304f209c`
  (PR #1649).
* **Lotto 2** (`anagrafiche`, `script`, 70 file): da 12 a **51 verdi** (+1 da
  owner), con i builder `fn_pgtap_crea_gestore`, `_operatore_umano`, `_pdp`,
  `_listino` (`20260923-06/-08/-09/-50`).
* **Difetti del prodotto** trovati costruendo invece di pescare: il profilo
  SUPER_ADMIN per id cablato in `fn_crea_risorsa_umana_v2` (`-10`);
  `fn_get_indirizzo` / `_by_soggetto` che confrontavano il codice col
  `codice_interno` (`-49`); il presidio C1 che contava le fixture come
  scrittori (`-51`); i CSV di `tipi_utenze`/`classi_utenze` che nessuno
  caricava (`-52/-53`); e `storico.parameters` con `parameter_id` dove il
  trigger passa `parameters_id` — le madri erano cinque, quattro rotte anche su
  dbdev — chiuso il 25-09 da
  [brief-db-storico-colonna-fk-dei-trigger.md](../work-done/brief-db-storico-colonna-fk-dei-trigger.md).
* **Verdi finti smascherati**: tre skip soft che scrivevano il valore atteso,
  sei test che asserivano per la ragione sbagliata, uno verde per l'errore
  sbagliato (il super admin).

Risultato: **229 rossi su 687** sul database da zero (24-09), contro i 362 del
20-09 — e la CI del 26-09 ha confermato: **227 su 714**; `baseline-rossi.tsv` di sviluppo da 16 a **12**. Brief
[brief-db-fixture-che-costruiscono-giro-2.md](../work-done/brief-db-fixture-che-costruiscono-giro-2.md),
chiuso il 23-09. Il debito che resta è in §3 D7.

### ✅ D10 — I presidi hanno un destinatario — chiuso l'11-09-2026

Trenta viste di presidio che nessuno guardava — e sei lavori falliti da tre
notti in una vista che si chiama `vw_coda_lavori_**da_guardare**`. Ora la
classificazione è **dato** (`dbops.presidi`), il **digest** lo costruisce il
backend, due timer sono in servizio (giornaliero 07:00, settimanale lunedì
07:30), e dal 19-09 il contatore è anche a video, nel **pallino in topbar**,
sullo stesso metro. Il primo giro ha già riferito, e ha insegnato il resto: un
allarme su un processo obsoleto dal 07-09 — *un presidio che comincia col rumore
insegna a non guardarlo*, ed è proprio la proprietà che il cantiere comprava.
Brief `brief-db-un-destinatario-per-i-presidi.md`.

### ✅ D11 — I registri che sono calati (e quello che cresce)

Non tutti i registri di §3 stanno fermi: `dbops.rls_perimetro_debito` è sceso da
**33 a 7 righe** (ogni riga con la sua ragione tecnica, calato nei cantieri D2,
D4 e in quelli passati dopo), `db/pgtap/baseline-rossi.tsv` da **19 a 12** file
sul database di sviluppo (16 al 12-09, 12 col giro 2 di D7 il 24-09), e
`db/pgtap/baseline-rossi-ci.tsv` da **403 a 361** (22-09; la misura da zero
della CI del 26-09 è a 227: le righe rientrate sono da togliere). ⭐ È la forma che la guida prescrive e che
qui ha funzionato: registro piccolo, ogni voce con il motivo, e un cantiere che
lo abbassa mentre passa. ⚠️ E ce n'è uno che invece **cresce** — `vw_codici_errore_da_dichiarare`,
508 → 545 su 897: è il registro **senza un verso** (§3 D11).

#### La soglia `throws_ok`: 129 → 123, e il test che era verde per l'errore sbagliato

Il 2026-09-20 sei asserzioni di
`db/pgtap/catalogo/test-articoli-vincoli-note-uom-overlap.sql` hanno ricevuto il
loro discriminante — `23505` per i tre casi di unicità (il codice duplicato e i
due `uq_artuomop_*`), `23514` per il CHECK su
`note_target_tipo`, `23503` per la FK su `note_id`, `23P01` per l'`exclusion`
sull'overlap — e la soglia del cancello è scesa a **123**.

⚠️ **Non è stata una passata di cosmetica: una di quelle sei era verde per
l'errore sbagliato.** Il test 11 dichiarava «codice articolo duplicato:
bloccato» e in realtà moriva su **`23502`** — un `NULL` su `uom_id`, che è NOT
NULL — perché l'INSERT ometteva quella colonna *e* il codice «duplicato» era
`'ART…'` mentre l'articolo creato sopra è `'ARC…'`: non duplicava niente. Il
vincolo che il test credeva di collaudare non era mai stato raggiunto, e il test
passava lo stesso.

⭐ **La sonda, ed è tutta qui** — il metodo vale più delle sei righe:

1. su una **copia usa-e-getta** del file, sostituire il secondo argomento con uno
   SQLSTATE impossibile (`'ZZZZZ'`), senza toccare il repository;
2. far girare il file: pgTAP non accetta più qualunque errore, e nel messaggio di
   fallimento stampa `caught: <stato>: <frase>` — cioè il dato che si cercava,
   per **tutte** le asserzioni, in una corsa sola;
3. leggerlo: l'asserzione che dichiarava lo stato giusto resta verde dopo il
   ripristino, quella sbagliata si spiega da sé;
4. **prima** correggere la causa, **poi** scrivere il discriminante — l'ordine
   conta: con `'23505'` e l'INSERT ancora incompleto il test sarebbe diventato
   rosso, e qualcuno avrebbe «aggiustato» il discriminante invece del test.

Costo: una copia temporanea e una corsa, zero modifiche al prodotto.
⭐ Resa: sei occorrenze in meno su 123, **un falso-verde trovato**, e una lista
di lavoro che si ripete su ogni file — i 123 sono elencabili in un comando, e
**21** di loro stanno in file che in CI girano davvero, **102** in file che lì
muoiono nella fixture (§3 D7).

Poi la soglia è scesa ancora, a **117** il 24-09: il lotto 1 del giro 2 (§7 D7)
e il test 1 di `vendite/test-preventivi-approvazione-prezzo.sql`, un
`throws_ok(…, NULL, NULL)` che passava con qualunque errore, anche uno della
fixture (`brief-db-preventivi-congelamento-pricing`).

### ✅ D12 — La quantità di documentazione — chiusa (era il gap di febbraio)

1.410 pagine **manuali** contro 1.500 autogenerate: il gap di febbraio («509
pagine, tre schemi scoperti») non c'è più — `magazzino` 32 pagine, `acquisti` 11,
viste coperte. Restano i due residui di **forma** (§3 D12): le pagine-specchio
dello `storico` che gonfiano il conteggio, e le pagine presenti ma sottili dei due
domini non ancora scritti (D8).

### ✅ D13 — Il `RETURNING` del billing account sotto RLS — chiuso il 2026-09-13

Con due emittenti in esercizio, l'operatore del secondo **non apriva clienti**:
il `RETURNING` chiedeva di vedere la riga *prima* che il trigger `AFTER` scrivesse
il legame, e il resolver ricadeva sul default — un'altra azienda. Ora *un BA non
ancora collegato appartiene a chi lo sta creando*: riserva a **tre livelli**
(`20260913-01/02/03`), la seconda copia della regola
(`fn_get_emittente_fiscale_pk`) che **delega**, e un pgTAP che costruisce
l'operatore del secondo emittente e prova l'`INSERT … RETURNING` **come
`zeroerp_app`**. Lato BE le tre copie inline delegano a
`fn_check_ba_visible_for_emittenti`, con un presidio a registro zero sulla forma.
⚠️ Prezzo dichiarato: un BA che *resta* senza legame è, in sessione, di chiunque
lo guardi — dato anomalo che il modello ammette.
Brief `brief-db-ba-riserva-emittente-operatore-d13.md`.

### ✅ D14 — La partita di merce si legge per documento — chiusa il 2026-09-22

Era: `script.fn_available_actions_ddt(id)` — la funzione che alimenta il drawer di
**un** DDT a ogni apertura — ricalcolava le partite di **tutti** i DDT, e sotto
RLS ogni riga scandita pagava la propria policy (~3.500 valutazioni per una
lettura). ⭐ Il difetto era **strutturale, non del planner**: la partita di una
riga dipende dalle spedizioni precedenti della stessa riga d'ordine, quindi
filtrare la CTE per documento avrebbe dato un numero **sbagliato**. La cura non
era un indice: era dare alla partita un **seme**, dopo aver mostrato sul modello
che la dipendenza è *bounded* (le due finestre sono partizionate per
`ordine_riga_id` e `ddt_riga_origine`: la chiusura di un documento è a due salti).

Otto giri fra il 17 e il 22 settembre, **sette applicati** e l'ottavo provato e
**ritirato lo stesso giorno**. Brief
`work-done/brief-db-partita-merce-per-documento.md`; changeSet `20260917-01`,
`20260921-20 → -34`, `20260921-50 → -55`, `20260922-01 → -16`; committato in
`c60f39eaa`, `559dbf351`, `acaaab569`, `e05e3b1e5`, `b40d9de24`, `660bbac59` e
`8d7f14829` (PR #1634, #1635, #1639, #1640, #1646).

**Che cosa è cambiato nel sistema** — le forme, non i millisecondi:

* `vendite.fn_partite_merce` (`BEGIN ATOMIC`) **semina** la partita con il
  documento o con l'ordine e ne calcola la chiusura; le viste diventano sue
  **proiezioni per nome** (un `SELECT *` perdeva `numeric(18,6)` e faceva uscire
  la vista dal presidio `security_invoker`);
* la stessa forma per `fn_situazione_merce_ordine`, `fn_resi_da_accreditare` e i
  due verbi degli accrediti: un seme, non un filtro su una popolazione intera;
* l'**eleggibilità ha una sola implementazione**: `fn_ddt_push_diagnosi` è la
  fonte, il lister ne deriva (`WHERE motivo IS NULL`) e la capability la legge
  **una** volta — prima erano due letture e due regole che potevano dissentire;
* ciò che è un insieme si legge **per chiave**: `vw_af_merce_per_riga` in una CTE
  `af AS MATERIALIZED` invece di quattro volte, il classificatore di segmento in
  forma a **range leakproof** (`~>=~`/`~<~`) con l'indice `varchar_pattern_ops`,
  i billing account seminati;
* `vw_contatore_merce` **ritirata** (censimento dal catalogo: nessun lettore), e
  nasce un BB generico — `trgfn_doc_righe_lock_fuori_bozza`, «le righe di un
  documento si toccano solo in bozza» — su `ddt_righe`, `ordini_righe` (solo
  DELETE) e `contratti_righe`, con le **due copie a DB ritirate** nello stesso
  giro.

| Lettura, come `zeroerp_app` | 17-09 | 22-09 sera |
| --------------------------- | ----- | ---------- |
| capability di un DDT (il drawer) | 290 ms | **39 ms** |
| partita di un DDT                | 120 ms | **27 ms**  |
| lista push senza documento (cockpit) | 214 ms | 73–94 ms |
| diagnosi di tutti i documenti    | 348 ms | 63–104 ms |

⚠️ **Le forcelle non sono un refuso**: sono lo stesso corpo misurato a un'ora di
distanza, ed è il motivo per cui è nata **D15**.

⭐ **Tre lezioni che valgono oltre il cantiere:**

1. *Ciò che è un insieme si legge una volta, e si semina con le chiavi in gioco.*
   ⛔ Col corollario che il giro 7 ha pagato: «una volta sola» **non basta** —
   leggere l'insieme intero è una volta sola, e fa pagare tutta la storia a chi
   chiede **un** documento. Le due forme si somigliano e non sono la stessa cosa.
2. ⛔ **Il banco di prova prova le righe, non il piano.** Il corpo eseguito come
   `SELECT` non predice il piano **dentro** la funzione: qui ha nascosto un
   difetto vero, ne ha **inventato** uno (la «terza occorrenza» che non esisteva)
   e ha promesso un guadagno che era una perdita. ⇒ L'equivalenza si prova sul
   banco, e il confronto **per seme** ha trovato un errore che il confronto
   globale dichiarava equivalente; il **piano** si misura dopo l'apply, sulla
   funzione, come applicazione.
3. ⚠️ **Un presidio verde a vuoto non è un presidio**: il ramo `DDT_SENZA_BA` non
   era esercitato da nessuna riga viva: caso costruito, e rosso per mutazione.

⛔ **Ciò che resta non è lavoro sospeso**, e sta in §6: due decisioni **non prese**
(la catena del `sospetto` — un avviso per una persona che nessuna macchina legge,
17,6 ms su 46, raccomandato lasciar stare; e **D8(b)**, che nessuna misura
reclama), i tre `LIKE` di `fn_accredita_riga_reso`, i preventivi come quarto
adottante del BB delle righe in bozza, e tre voci BE.

### ✅ D17 — Le esclusioni implicite, tranne Q-2 — chiusa il 2026-10-04

Nata e chiusa nello stesso giorno dalla valutazione qualitativa (§2-bis). Erano
invarianti veri ma non scritti, che quando smettono di valere non danno errore:

* **Q-4** — una fattura numerata **non si cancella e non cambia numero**: guard di
  tabella `_a05_` (`vendite.trgfn_fatture_guard_numero_fiscale`), due codici
  `CONFLITTO_STATO`. Chiude la corsa fra la check del ritorno a DRAFT (prima del
  lock) e la DELETE del cleanup, e il retro per cui un UPDATE poteva togliere il
  numero prima della DELETE;
* **Q-1** — **utente NULL = nessun accesso** nelle tre funzioni di scope che
  dicevano il contrario (la canonica, l'adapter del billing account, lo scope delle
  ricerche). Una sessione con la veste OPERATORE e senza utente vedeva tutte le
  aziende; ora la policy vera, provata come applicazione, non vede niente;
* **Q-3** — l'invariante «tabelle del migratore, applicazione senza proprietà,
  `FORCE` spento» è **scritto** (linee-guida-sql §10.5, che prima consigliava il
  contrario) e **presidiato** a criterio (`dbops/test-postura-proprietario-rls-v1`);
* **`UPDATE OF`** — la regola in linee-guida-trigger era rovesciata, e **mordeva**:
  la propagazione delle quantità ai componenti dei kit non scattava quando la
  quantità la ricalcola un trigger BEFORE. Cinque trigger rifatti con `WHEN`;
* **v1** — la prima generazione dei changelog **non si tocca**: cancello CI con
  manifesto (linee-guida-sql §11.11);
* **Q-6** — regola: l'emittente si nomina `emittente_soggetto_ruolo_id`
  (linee-guida-sql §2). **Q-5** è passata in D8.

Brief `work-done/brief-db-esclusioni-implicite.md` (archiviato il 2026-10-05);
changeSet `20261004-80 → -86`, applicati su dev il 2026-10-04, pgTAP verdi,
committato in `4617fabe6`. Il 2026-10-05 sono state verificate le due voci «da
verificare» del censimento `UPDATE OF`: il registro di DDT e resi è innocuo, la
catena delle istanze è un difetto vero ed è diventata **D18**. Ricaduta BE (R-1, i
due codici in `error_policies_generated.py` + ripieghi) chiusa il 2026-10-04
(`63deeb194`). Resta Q-2 (§3).

---

### ✅ D21 — Ordine, DDT e reso parlano del cliente come preventivo, offerta e contratto — chiusa il 2026-10-10

Trovato il 2026-10-09 chiudendo il lato BE/FE di `brief-db-istanza-nasce-col-ba` (§7.5). Ordine, DDT
e reso avevano il BA nullable, copie di utility e ruolo che nessun vincolo legava al BA, e anelli della
catena che potevano avere clienti diversi. Che cosa è cambiato nel sistema:
* l'ordine ha sempre il BA; il DDT lo vuole all'emissione quando la causale manda merce a un cliente
  (`config.causali_trasporto.richiede_cliente`); il reso ha il BA del suo DDT;
* utility e ruolo di testata legati al BA da una FK a tre colonne, e scritti dal BB
  `script.fn_cliente_dal_billing_account` se mancano; la catena ordine → DDT → reso ha un solo BA, e
  una sorgente dichiarata ma non visibile è un errore;
* il ruolo del BA, il soggetto dell'istanza e il cliente non cambiano intestatario (lock dichiarati);
* BA, destinatario ed emittente si scelgono solo in bozza (BB `vendite.trgfn_doc_testata_lock_fuori_bozza`,
  emittente bloccato fuori bozza su sei documenti);
* lato BE il cliente del DDT si sceglie e si cambia in bozza, le copie Python ritirate.

Dettaglio nel brief
[brief-db-esecutivi-ba-coppia.md](../work-done/brief-db-esecutivi-ba-coppia.md) (archiviato il
2026-10-10). Ciò che la chiusura ha trovato è **D27**; il debito fuori perimetro è D22 (chiusa) e D26.

### ✅ D22 — L'emittente del documento e' quello del cliente: una regola, una sede — chiusa il 2026-10-10

Trovato il 2026-10-09 (§5.5 di `brief-db-esecutivi-ba-coppia`): il guard «l'emittente del documento
e' quello che il billing account risolve» era scritto sette volte, con sei codici per lo stesso
significato, frasi che mostravano nomi di colonna all'utente e il log senza la transazione. Che cosa
è cambiato nel sistema:
* un building block, `script.trgfn_doc_guard_emittente_ba`, montato sulle sette tabelle con lo stesso
  nome e la stessa fascia dei trigger di prima; le sette funzioni sono ritirate (`20261010-17…-19`);
* un codice per i sei documenti, `E_DOC_EMITTENTE_BA_INCOERENTE` (DATO_ERRATO, col campo), con una
  frase che nomina le due aziende e il billing account; la commessa tiene il suo codice TECNICO, con
  i segnaposto nello stesso ordine;
* lato BE una voce di `ui_action` al posto di sei, le policy rigenerate, i ripieghi.

Dettaglio nel brief
[brief-db-guard-emittente-ba-unico.md](../work-done/brief-db-guard-emittente-ba-unico.md) (archiviato
il 2026-10-10). Ciò che la chiusura ha trovato è **D24**.

### ✅ D23 — Ricerca universale: oltre 10.000 risultati il totale e le pagine non dicevano il vero — chiusa il 2026-10-10

Trovato il 2026-10-10 scrivendo R-6 di `brief-db-codici-non-trovato-email-e-permessi` (§14.5): la
lista della ricerca universale teneva al massimo 10.000 corrispondenze con un `LIMIT` senza
`ORDER BY`, poi contava, ordinava e paginava su quelle. Oltre il tetto il totale era falso, la prima
pagina non era la prima vera e le pagine potevano ripetere o saltare soggetti. Che cosa è cambiato
nel sistema:
* `script.fn_search_soggetti_universale` conta, ordina e pagina **prima** degli aggregati, sull'intero
  insieme: il totale è vero (strada B, `20261010-16`);
* l'ordinamento per utility è ritirato, dal DB (`E_PARAMETRO_INVALIDO`), dalla whitelist BE e dal FE.

Dettaglio nel brief
[brief-db-ricerca-universale-tetto-10000.md](../work-done/brief-db-ricerca-universale-tetto-10000.md)
(archiviato il 2026-10-10; BE/FE §7.4).

### ✅ D25 — I residui di «l'istanza nasce col billing account» — chiusa il 2026-10-10

Ereditati il 2026-10-10 dalla chiusura di `work-done/brief-db-istanza-nasce-col-ba`. Che cosa è
cambiato nel sistema:
* via il resolver `script.fn_get_billing_account_by_istanza`: il cliente lo dice il documento o la
  pratica, non l'istanza;
* via il motivo `PREVENTIVO_SENZA_BILLING_ACCOUNT` delle capability del preventivo e i suoi due filtri
  gemelli (residuo commessa, lista del push): BA e utility del preventivo sono `NOT NULL`. Lato FE
  tolta la chiave dai locales;
* liste del push di ordini e contratti senza il filtro inutile sul BA; lo stato di partenza assente
  dal catalogo solleva `E_CODICE` invece di far cadere il filtro (D-2);
* ritirato `uq_gestori_singleton`, che ripeteva la chiave primaria;
* lo spostamento dell'azienda predefinita non dipende più da chi lo fa: i guard chiedono l'azienda dei
  BA per l'installazione (BB `script.fn_get_ba_emittente_sr_id_installazione`), con il suo pgTAP.

Dettaglio nel brief
[brief-db-istanza-nasce-col-ba-residui.md](../work-done/brief-db-istanza-nasce-col-ba-residui.md)
(archiviato il 2026-10-10; DB `20261010-50…-59`, pgTAP verdi anche su `zeroerp_ci`).

### ✅ D20 — Righe e componenti: tre debiti rimasti dalla chiusura di D19 — chiusa il 2026-10-09

Trovati il 2026-10-08 chiudendo D19 (`brief-db-righe-e-componenti-le-altre-famiglie`, §5). Tre
punti:
* righe d'ordine e di preventivo si cambiano ancora fuori bozza a DB (ora una riga kit no, una
  semplice sì);
* `user_update` nullable su circa 140 tabelle, e nessun presidio che fermi una tabella nuova;
* un componente spento in attesa di approvazione passa nella revisione, legato alla pratica
  della rev N (preventivo e offerta).

Dettaglio e stato nel brief
[brief-db-righe-e-componenti-debiti-residui.md](../work-done/brief-db-righe-e-componenti-debiti-residui.md)
(archiviato il 2026-10-09).
Decisi da Tid il 2026-10-08; DB scritto lo stesso giorno (`20261008-80` … `-94`), applicato su dev, pgTAP
verdi anche su `zeroerp_ci` (2026-10-09); tre test non più costruibili sono skip motivati (§4.5).
✅ **Chiuso lato DB**; ✅ lato BE chiuso il 2026-10-09 (§5 del brief): il verbo della data confermata
passa a `brief-db-ordine-data-consegna-confermata-capability`, il ciclo della pratica resta debito
dichiarato in PROJECT_CONTEXT.

### ✅ D19 — Righe e componenti di preventivo, ordine e DDT come contratto e offerta — chiusa il 2026-10-08

Brief `work-done/brief-db-righe-e-componenti-le-altre-famiglie.md`, changeSet `20261008-30` … `-35`,
applicati da Tid il 2026-10-08 (pgTAP verdi, nessuna regressione). Che cosa è cambiato nel sistema:
* la revisione del preventivo porta **tutti** i componenti, anche gli opzionali spenti (D-1 di Tid),
  e li lega alla riga nuova per identità, come quella dell'offerta;
* i componenti di preventivo, ordine e DDT si toccano solo in bozza (building block a livello RIGA);
  i due lettori DEFINER conoscono le sei famiglie;
* `user_update NOT NULL` su righe e componenti dei documenti di vendita;
* i CHECK della quantità dei componenti si chiamano `_nz`, come dice la regola.
Ciò che la chiusura ha trovato è **D20**.

### ✅ D26 — La testata dopo l'emissione: la regola sta nel DB — chiusa il 2026-10-11

Trovato il 2026-10-09 (§8 e §10.3 di `brief-db-esecutivi-ba-coppia`): quali colonne di testata si
cambiano dopo l'emissione lo diceva per intero solo il backend («testata modificabile solo in DRAFT»
su ordine, DDT, reso, preventivo, offerta; una tabella per stato sul contratto), e il database ne
bloccava solo dei pezzi. Che cosa è cambiato nel sistema:
* la regola «fuori bozza, che cosa si cambia» sta nel DB **per famiglie di colonne** (identità
  bloccata; ciò che arriva dopo e le note modificabili; stampato e condizioni decise per documento),
  nei BB `vendite.trgfn_doc_testata_lock_fuori_bozza` e `vendite.trgfn_doc_righe_lock_fuori_bozza`;
* un lettore del montaggio (`script.fn_doc_lock_montaggi`, `script.fn_doc_colonna_modificabile`) e,
  come fase 1, la capability della data di consegna confermata (assorbito
  `brief-db-ordine-data-consegna-confermata-capability`);
* lato BE via i «solo in DRAFT»; `E_CONTRATTO_NON_MODIFICABILE` ritirato.

Dettaglio nel brief
[brief-db-testata-dopo-emissione.md](../work-done/brief-db-testata-dopo-emissione.md) (archiviato il
2026-10-11; DB, BE/FE, collaudo a video di Tid).

### ✅ D27 — Gli indirizzi del documento seguono il cliente — chiuso il 2026-10-19

Sul DDT, sul preventivo e sull'offerta il cliente si cambiava in bozza, ma gli indirizzi presi dall'anagrafica
del cliente di prima restavano, e il gate d'emissione guardava che ci fossero, non di chi fossero. Ora la regola
«l'indirizzo e' del cliente del documento» sta nel DB: slot di default come dato, guard d'origine, cambio di
cliente a trigger (indirizzi, e scheda di fornitura su offerta e contratto), emittente e utility ferme anche in
bozza. Nel FE il cambio di cliente in modifica si salva subito, con conferma, cosi' gli indirizzi nuovi si vedono e
si correggono senza salvare prima. Brief
[brief-db-indirizzi-documento-seguono-il-cliente.md](../work-done/brief-db-indirizzi-documento-seguono-il-cliente.md)
(archiviato il 2026-10-19; DB, BE/FE, collaudo di Tid).

### ✅ D28 — Le righe evase di un DDT da ordine — chiuso il 2026-10-11

Sulla bozza di un DDT da ordine la riga evasa cambiava quantita' e articolo senza che il legame con
l'ordine lo vedesse (ordine evaso per 10, bolla a 6). Ora la riga evasa — da un ordine o da un reso da
ri-consegnare — e' **ferma** (`trgfn_ddt_righe_guard_riga_evasa`), la quantita' si corregge solo dal verbo
`vendite.fn_ddt_riga_correggi_qta_evasa` (riga, legami e stato dell'ordine insieme), la riga evasa si
cancella in bozza ritirando i suoi legami, i legami non si scrivono a mano ne' nascono su una bolla emessa,
e l'annullo di una bolla con legami li ritira **con conferma** (`vendite.fn_annulla_ddt`, D-8). La proiezione
dello stato dell'ordine ha una sede sola (`vendite.fn_ordine_proietta_stato_evasione`, sei copie ritirate).
BE/FE: endpoint `qta-evasa/` e `legami/`, finestra di conferma dell'annullo. Brief
`work-done/brief-db-ddt-righe-evase-dall-ordine.md`; il principio dell'annullo per gli altri documenti
continua in D29.

### ✅ D29 — Annullare un documento con legami — chiuso il 2026-10-11

Un documento nato da un altro, annullato, lasciava l'origine consumata per sempre (l'ordine evaso per
merce mai partita, il preventivo occupato da un ordine morto, l'offerta non piu' trasformabile) o la
ritirava in silenzio (le righe di commessa). Ora bolla, ordine, preventivo e contratto si annullano dal
loro verbo (`vendite.fn_annulla_<documento>`): con legami il DB avvisa (`E_DOC_ANNULLO_CON_LEGAMI`), la
finestra di conferma comune mostra che cosa si riapre (lettore unico `vendite.fn_documento_legami`) e
l'operatore dichiara quanti legami ha visto; poi i consumi si ritirano (BB
`vendite.fn_documento_ritira_legami`) e i documenti a monte si riaprono. L'unicita' offerta → contratto /
ordine vale sui soli documenti vivi. Brief `work-done/brief-db-annullo-documento-con-legami.md`; il verso
dalla commessa continua in D30.

### ✅ D30 — Tornare indietro: annullare la commessa riapre il documento a monte — chiuso il 2026-10-13

Annullare una commessa non mostrava niente e non restituiva niente: il preventivo restava EVASO, la sua
riga NON_EMESSA dentro una commessa ANNULLATA, e il documento non si rimandava in commessa. Ora la commessa
si annulla dal verbo (`vendite.fn_annulla_commessa`) con la finestra comune di D29: i documenti che l'hanno
alimentata si riaprono (preventivo di nuovo ACCETTATO, ordine di nuovo da mandare senza cambiare stato,
reso da accreditare, consumi da mandare), gli oneri si annullano. Una riga ANNULLATA non occupa piu' il
documento (`script.fn_get_stato_push_segment`); «Evaso» dell'ordine lo dicono solo le bolle; il verso in
avanti verso la commessa sta tutto nel DB; il link documento → commessa resta come storia, con una sola
commessa aperta per documento, e il lineage dice quando il legame e' ritirato (`is_legame_ritirato`).
Brief `work-done/brief-db-annullo-a-valle-riapre-a-monte.md`; il residuo (la commessa vuota del push
batch) e' in PROJECT_CONTEXT § «Aperto — Media priorità».

### ✅ D36 — Il perimetro una volta per istruzione: le famiglie che restano — chiuso il 2026-10-21

Ereditato il 2026-10-18 dalla chiusura di D26-2: dopo la cura delle policy ef_whitelist dell'operatore
restavano per riga le famiglie del cliente portale, cliente, shop, fornitore, email e note, più tre
policy dell'operatore. Chiuso in cinque giri (`20261021-24…-43`), tutti applicati e verdi: nessuna policy
calcola più per riga ciò che dipende solo da chi guarda. Per l'operatore la forma già pronta (smistatori
delle note col perimetro, il BA di una coppia da `fn_get_ba_id_da_coppia`); per le vesti di controparte
tre building block nuovi (`fn_get_identita_sr_perimetro`, `fn_resolve_controparte_sr_id` coi suoi modi,
`fn_scope_sr_perimetro`); per le email la regola dell'ambito resa pura, con chi guarda in quattro
sottoquery. Ritirate tredici funzioni per riga. Il presidio
`script/test-scope-ef-perimetro-una-volta-per-istruzione-v1` non ammette più eccezioni; regola in
linee-guida-sql §10.3. Brief `work-done/brief-db-perimetro-una-volta-famiglie-residue.md`.

### ✅ D34 — La creazione scrive tutta la sezione dei dati societari — chiuso il 2026-10-22

Trovato il 2026-10-14 chiudendo `work-done/brief-db-dati-fiscali-e-societari-del-soggetto.md`: in
creazione la sezione non arrivava intera al verbo `fn_scrivi_dati_societari`. Una società perdeva la data
di costituzione, una ditta individuale **tutta** la sezione, senza errore. Ora le due porte
(`fn_crea_soggetto_pg`, `fn_crea_soggetto_pf`) ricevono gli stessi dieci campi e lasciano decidere al BB
`anagrafiche.fn_scrivi_dati_societari_alla_nascita` se scriverli; una sezione passata a un privato si
rifiuta invece di sparire (`20261020-01…03`, E-1 (a) di Tid). BE: il binding della sezione in un punto
solo del repository, lo stesso contratto della PATCH anche in creazione; FE: la data di costituzione
anche in creazione. Collaudo di Tid riuscito il 2026-10-22. Brief
`work-done/brief-db-dati-societari-in-creazione.md`.

### ✅ D35 — `zeroerp_log` nasce con gli altri ruoli di sistema — chiuso il 2026-10-15

Il ruolo del canale dei registri lo creavano a mano i workflow e la guida d'installazione, e doveva
esistere prima del migrate perche' il `20260905-38` gli desse il giornale dei job. Ora lo crea la fase
`ruoli` di `provision_zeroerp.sql`, con gli altri ruoli di sistema; lo script del canale non lo crea piu'.
Con lui le due code della chiusura dei ruoli di sistema: i vecchi privilegi di default di `titodb` e una
corsa di `ci-local.sh`. Brief `work-done/brief-db-zeroerp-log-nella-fase-ruoli.md`.

### ✅ D15 — Le statistiche delle tabelle: un job notturno — chiuso il 2026-10-15

Il database non aveva un posto che tenesse aggiornate le statistiche del planner: l'autovacuum non
arriva alle tabelle piccole né alle madri partizionate, e nessun job lanciava `ANALYZE` (fatto datato
14-10 su dbdev: mai analizzate 69 tabelle su 89 in `vendite`, tutte quelle di `magazzino` e `acquisti`).
Ora c'è il job `analyze_statistiche`, ogni notte alle 02:30: `maintenance.fn_analyze_statistiche` fa
`ANALYZE` e poi un'**autoverifica**, perché `ANALYZE` salta senza errore le tabelle che il ruolo non può
analizzare; se una tabella resta senza statistiche il job fallisce con `E_STATISTICHE_MANCANTI` e la
nomina nel giornale. In CI gira nella convergenza di `ci_apply`, quindi i pgTAP partono da statistiche
reali. Insieme, il panorama dei processi distingue il job nuovo in attesa dal job in ritardo
(`IN_ATTESA`, `JOB_IN_RITARDO`). Provato su dbdev il 15-10, anche con pgAgent come `zeroerp_job`. Brief
`work-done/brief-db-statistiche-tabelle-job-notturno.md`; guida `guide/statistiche-del-planner.md`.


### ✅ D33 — Un cliente manuale per soggetto, utility e azienda — chiuso il 2026-10-15

La creazione manuale del cliente creava ogni volta un'istanza fittizia nuova, e con lo stesso soggetto e
la stessa utility nasceva un secondo cliente. Ora, fra le istanze fittizie, due clienti con lo stesso
soggetto, utility e azienda emittente non si sovrappongono nel periodo: il controllo scatta al COMMIT
(`E_CLIENTE_STESSA_CHIAVE`, col codice del BA esistente), anche quando cambia l'azienda del BA o
un'istanza diventa fittizia, e legge un predicato solo (`anagrafiche.fn_clienti_stessa_chiave`). Con lei
gli stati del cliente hanno un grafo (`config.transizioni_stati_cliente`): un chiuso non si riapre, si
torna con istanza, BA e cliente nuovi; ogni stato pretende la sua data; la data di chiusura di un chiuso
è ferma. «Attivo» si legge dal periodo anche per il PDP, la disdetta e il BE (`ha_ba_attivo`). Brief
`work-done/brief-db-cliente-manuale-uno-per-soggetto-e-utility.md`; i residui (§7 del brief) passano allo
sviluppo delle utility (Tid, 2026-10-15).

*Valutazione 2026-09-08 — perimetro DB. Le misure sono letture di struttura sul
database di sviluppo `zeroerp` (PostgreSQL 18.6) e sul repo al commit `89d36ad1b`,
branch `dev/db-tid`. La valutazione di febbraio 2026 resta in §1 come fatto
datato. Sfoltito il 2026-09-12: le voci chiuse sono ridotte a data e rimando; la
versione integrale è nella storia git del file. **Riordinato il 2026-09-20**: §3
contiene solo i difetti aperti, e le attività svolte stanno in §7 — con lo stesso
numero in entrambe le sezioni quando una voce ha due facce. **Riordinato il
2026-09-22**: D14 è chiusa e passata per intero in §7, e al suo posto in §3 è
entrata D15 — le statistiche assenti, che la sua chiusura ha scoperto.
**Riordinato il 2026-09-26**: D6 e D7 ridotti in §3 al lavoro che resta, il
giro 2 di D7 riassunto in §7, `magazzino` uscito dalla fotografia di D8, numeri
del repo rimisurati. **Aggiornato il 2026-10-05**: brief di D17 archiviato,
nata D18 (la catena delle istanze), il blocco D17 di §7 riportato dopo la coda
di D14, dove si era infilato.*
