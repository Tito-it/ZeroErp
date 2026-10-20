# Brief DB — Una sola grammatica per i tipi di documento

## ⏭️ Chi riparte — aggiornato al 2026-10-20

**Riparte: la sessione BE** (§12.10.4: `CONTEXT_VERSION = 3` dell'ordine con `origine.etichetta`, i commenti e la
doc del §12.8). `20261020-22` … `-25` sono applicati su dbdev (2026-10-19 sera), pgTAP come app verdi senza
regressioni (2026-10-20). Subito dopo il riavvio del backend
in forma 3, Tid lancia lo SQL una tantum di L2b-2 (§12.10.3), poi la prova a video del 2b (§12.7).
Il 2b è chiuso su DB e BE/FE, revisione compresa (§12.7). Il 2a è chiuso su DB, BE e FE (§11.6). I lotti 0 e 1
sono chiusi su DB, BE e FE.

| # | Chi | Che cosa | Dove | Aspetta |
| --- | --- | --- | --- | --- |
| 1 | ✅ **Tid** | Direzione: una grammatica sola per tutti i tipi di documento (la strada 3 dell'A-8-ter) | §2 | — |
| 2 | ✅ **Tid** | G-1 (vince `config.sorgenti`), G-2 (righe, varianti, tutti gli schemi, `EMAIL_BOZZA`), G-3 (il vincolo si adegua al nome), G-4 (lotti 0 → 4), 2026-10-18 | §5 | — |
| 3 | ✅ team DB | Censimento: otto vocabolari, matrice, chi parla e chi traduce (DB e backend), vincoli | §7 | — |
| 4 | ✅ **Tid** | G-5 famiglie di numerazione, G-6 aree al plurale, G-7 catalogo delle note, G-8 prefissi di chiave (2026-10-18) | §7.9 | — |
| 4-bis | ✅ **Tid** | Il via allo sviluppo (2026-10-18 sera; numeri da `20261019-14`) | — | — |
| 5 | ✅ team DB | Lotto 0 scritto e provato in transazione: `20261019-14`, `-15`, due CSV, pgTAP | §8 | — |
| 5-bis | ✅ **Tid** | K-1 = (b1), la chiave resta doppia; nomi `DISTINTA_INCASSO` ed `EMAIL` confermati (2026-10-19) | §8.3 | — |
| 5-ter | ✅ **Tid** | Apply del lotto 0, pgTAP 9/9 come app dopo la correzione del test 6 (2026-10-19) | §8.5 | 5 |
| 5-quater | ✅ sessione FE | Le 25 chiavi `config.tipi_entita.*` in `it.json`/`en.json`, `check_i18n_keys` verde (2026-10-19) | §8.4 | 5 |
| 6 | ✅ team DB | Lotto 1 scritto e provato in transazione: `20261019-18` … `-32`, pgTAP (2026-10-19) | §9 | — |
| 6-bis | ✅ sessione BE | Il giro BE del lotto 1: `DocumentoEccezioni` e i due service sui codici delle sorgenti, chiamata reale su dbdev (2026-10-19) | §9.4, §9.6 | 6 |
| 6-ter | ✅ **Tid** | Apply del lotto 1 su dbdev e corsa dei pgTAP come app: nessuna regressione (2026-10-19) | §9.5 | 6 |
| 6-quater | ✅ team DB | Piano del lotto 2: perimetro misurato, proposta di cinque sotto-giri (2026-10-19) | §10 | — |
| 6-quinquies | ✅ **Tid** | L2-1: sì ai cinque sotto-giri, via al 2a (2026-10-19) | §10.3 | 6-quater |
| 6-sexies-a | ✅ team DB | Lotto 2a scritto e provato in transazione: `20261019-40` … `-79` | §11 | — |
| 6-sexies-b | ✅ sessione BE/FE | Il giro BE/FE del 2a (mixin indirizzi, annullo con legami, due risposte API), chiamata reale su dbdev (2026-10-19) | §11.4, §11.6 | 6-sexies-a |
| 6-sexies-c | ✅ **Tid** | Apply del 2a su dbdev e corsa dei pgTAP come app: verdi, dopo l'adeguamento di un test (2026-10-19) | §11.5 | 6-sexies-a |
| 6-septies-a | ✅ team DB | Lotto 2b scritto e provato in transazione: `20261019-87` … `-99`, tre CSV, 16 pgTAP (uno nuovo) | §12 | — |
| 6-septies-b | ✅ sessione BE/FE | Il giro BE/FE del 2b: origine dell'ordine da offerta, origine dei legami, destinazione dello smistamento (tre risposte API), e2e sul DB vero (2026-10-19) | §12.4, §12.7 | 6-septies-a |
| 6-septies-d | **Tid** | Prova a video del 2b (§12.7); ✅ L2b-1 decisa: (a), etichetta in una colonna a DB (2026-10-19) | §12.7, §12.9 | 6-septies-b |
| 6-septies-c | ✅ **Tid** | Apply del 2b su dbdev e corsa dei pgTAP come app: verdi (2026-10-19) | §12.6 | 6-septies-a |
| 6-septies-e+f | ✅ team DB | §12.8 e §12.9 insieme (via di Tid, 2026-10-19 sera): `config.sorgenti.etichetta` (colonna, CSV, `NOT NULL` in `90_end`), `fn_partite_merce` con `ORDINE_VENDITA`, lo standard dell'ordine v2 (forma 3); `20261020-22` … `-25`, provati in transazione (2026-10-20) | §12.10 | — |
| 6-septies-h | ✅ **Tid** | Apply di `20261020-22` … `-25` su dbdev (2026-10-19 sera) e corsa dei pgTAP come app: verdi, nessuna regressione (2026-10-20); L2b-2 = (c) (2026-10-20) | §12.10.3, §12.10.5 | 6-septies-e+f |
| 6-septies-g | sessione BE | `get_ordine` con `documento_origine_etichetta`, builder dell'ordine in **forma 3** con `origine.etichetta`, test, `api_ordini.md`; i commenti e la doc del §12.8 | §12.10.4 | 6-septies-h |
| 6-septies-i | **Tid** | Subito dopo il riavvio del backend in forma 3: lo SQL una tantum di L2b-2 su dbdev | §12.10.3 | 6-septies-g |
| 6-sexies | team DB + sessione BE/FE | Sotto-giri 2c … 2e (DB e backend nello stesso giro; col 2e il SQL a mano delle chiavi, G-8), e lotto 3 (anticipabile); censimento su `pg_get_functiondef`, non su `prosrc` (§12.3) | §10, §5 G-4 | 6-septies-b |
| 7 | chi chiude | Lotto 4: presidio, ritiro del ponte di `fn_articolo_riga_contesto` (se non già nel 2), riga di PROJECT_CONTEXT, archiviazione | §5 G-4 | 6-sexies |

**Decisioni aperte di Tid:** il blocco «origine» della stampa della fattura, che non si vede mai (§12.9, in fondo). Il giro DB dei
§12.8 e §12.9 (§12.10) è **da committare** su `dev/db-tid`. Il §12.8 è partito il 2026-10-19 sera, insieme al
§12.9 (Tid). L2-1 decisa il 2026-10-19
(§10.3); il 2b applica G-3 così com'è (§12.2); L2b-1 decisa il 2026-10-19: (a), colonna a DB (§12.9). Il giro BE/FE
del 2b con la sua revisione (§12.7) e questo brief sono committati su `dev/backend-tid` (2026-10-19). Nello
stesso commit c'è anche un lavoro **fuori da questo brief**: `core/utils/ripristinaLookup.js`,
`vendite/_shared/cliente/` e i cinque drawer di vendita (preventivo, offerta, ordine, DDT, contratto) — il
cliente riaperto mostrava il solo codice (collaudo di Tid, regola del 2), coi due BB nel catalogo BB frontend. ⚠️ Mancano ancora i rimandi del §6.1 in
[brief-db-indirizzi-documento-seguono-il-cliente](brief-db-indirizzi-documento-seguono-il-cliente.md) (R-BE-1) e in
[brief-db-documento-nasce-nello-stato-iniziale](brief-db-documento-nasce-nello-stato-iniziale.md): oggi rimanda qui solo
quello degli articoli ammessi.

> **Chi scrive:** sessione BE (`dev/backend-tid`), 2026-10-18. **A chi:** il team DB, poi Tid.
> **Origine:** l'A-8-ter di
> [brief-db-articoli-ammessi-per-documento §9.8.3](brief-db-articoli-ammessi-per-documento.md).
> Spostare tre funzioni del listino sul vocabolario delle entità moltiplicava i punti di
> traduzione invece di toglierli: il problema non è di tre funzioni, è della grammatica.

## 1. Il caso

Lo stesso concetto, «di che tipo di documento si parla», ha **più nomi** nel database e nel backend,
e chi passa da un vocabolario all'altro traduce. Quello che si vede già dal contratto (seed in
`80_data` e doc auto-generata, 2026-10-18 — struttura, non popolazione):

| Vocabolario | Dove | Esempi | Note |
| --- | --- | --- | --- |
| **entità** | `config.tipi_entita` (`80_data/sql/config/tipi_entita.csv`) | `PREVENTIVO`, `ORDINE_VENDITA`, `DDT_VENDITA`, `OFFERTA_COMMERCIALE`, `CONTRATTO`, `COMMESSA`, `FATTURA`, `LISTINO_VERSIONE`, `ARTICOLO`, `PROMO_ARTICOLO`… | lo parla il picker degli articoli ammessi e la check per tipo di riga. ⚠️ Non ha un reso |
| **sorgenti** | `config.sorgenti` (`sorgenti.csv`) | gli stessi codici delle entità per le testate (`OFFERTA_COMMERCIALE`, `DDT_VENDITA`, `RESO_VENDITA`…), più le righe (`*_RIGA`) e altri (`ATTIVITA`, `EVENTO_ASSET`, `DDT_VENDITA_PRELIEVO`…) | le note dei due cataloghi dicono già «codice identico» dove si intersecano |
| **testate** | `script.fn_get_stato_testata_documento`, `fn_get_testata_id_di_riga`, `fn_get_cliente_testata_documento`, `fn_doc_indirizzi_sede` e altri (27 pagine della doc auto-generata) | `DDT`, `ORDINE`, `CONTRATTO`, `OFFERTA`, `PREVENTIVO`, `RESO`, `COMMESSA`, `EMAIL_BOZZA` | lock fuori bozza, annullo con legami, indirizzi, lineage |
| **documenti con eccezioni** | `vendite.fn_documento_listino_operativo`, `fn_documento_righe_eccezione`, `fn_documento_righe_preview`, `script.fn_check_riga_erogazione`… (la famiglia del §9.8.3) | `OFFERTA`, `CONTRATTO` | un sottoinsieme della grammatica delle testate |
| **partizioni delle note** | `target_tipo` delle note (`varchar(16)`), `backend/apps/vendite/db/note_repositories.py` | `OFFERTA` | il commento del backend dice che `OFFERTA_COMMERCIALE` non ci sta per lunghezza: un vincolo di **colonna** che decide un nome |

Il **ponte** dichiarato oggi è uno: `script.fn_articolo_riga_contesto` traduce dalle entità alle
testate. Gli altri punti di traduzione non sono censiti.

## 2. La decisione presa

**Tid, 2026-10-18:** la soluzione è **una grammatica sola** per i tipi di documento, usata da tutto
il database e dal backend, senza ponti. Non è un debito da tenere: è la direzione. Si apre qui, fuori
dal brief degli articoli ammessi, perché tocca decine di oggetti che con gli articoli non c'entrano e
perché altri brief aperti lavorano sugli stessi oggetti (§6).

## 3. Che cosa si chiede

### 3.1 Al team DB: il censimento (§4), prima di ogni changeSet

G-1 … G-4 sono decisi (§5, 2026-10-18) sulla struttura dei cataloghi; il censimento dà l'elenco
degli oggetti per lotto. Nessun changeSet prima del via di Tid.

### 3.2 La ricaduta sul backend (per il piano, non ora)

Le traduzioni del backend vanno ritirate **nello stesso giro** del lotto DB che le rende inutili
(regola del 2). Quelle già note:

* `backend/apps/vendite/db/_documento_eccezioni_repo.py`: `DocumentoEccezioni = Literal["CONTRATTO", "OFFERTA"]`;
* `offerte_service.py`, `contratti_service.py`, che passano quei codici;
* `_annullo_con_legami.py`, che traduce `OFFERTA` nel codice delle sorgenti;
* `backend/apps/config/sorgenti.py` (le costanti `SORGENTE_*`) e `note_repositories.py` (le partizioni).

Il censimento le completa: cercare nel backend ogni letterale di tipo documento usato come chiave.

## 4. Il censimento (team DB)

Da leggere sul **contratto** (seed, doc auto-generata, firme e corpi delle funzioni, CHECK, enum),
mai sulle righe di oggi.

1. **I vocabolari.** Tutti quelli che nominano un tipo di documento (testata o riga): catalogo,
   enum, CHECK, colonne `varchar` con valori ammessi, letterali nei corpi delle funzioni. Per
   ciascuno: dove vive, chi è la fonte, quali codici ha.
2. **La matrice dei codici.** Per ogni tipo di documento, il suo nome in ciascun vocabolario
   (una riga per tipo, una colonna per vocabolario), con i **buchi**: per esempio il reso, che
   `config.tipi_entita` non ha, ed `EMAIL_BOZZA`, che vive solo nella grammatica delle testate.
3. **Chi parla cosa.** Per ogni funzione, trigger, vista e montaggio che riceve o confronta un tipo
   di documento: quale vocabolario usa, e se lo riceve da fuori o lo scrive come letterale.
4. **Chi traduce.** Ogni punto in cui un codice di un vocabolario diventa un codice di un altro (il
   ponte di `fn_articolo_riga_contesto` e gli altri), DB e backend.
5. **I vincoli che decidono un nome.** Colonne troppo corte (`target_tipo varchar(16)`), indici,
   chiavi di partizione, chiavi dei locales: ciò che oggi impedisce di usare il codice lungo.
6. **I confini.** Che cosa è «un tipo di documento» e che cosa no: le entità che non sono documenti
   (`TASK_RUN`, `FLUSSO`, `LOTTO`), le righe (`*_RIGA`), le varianti di un documento
   (`DDT_VENDITA_PRELIEVO`, `RESO_VENDITA_RIENTRO`). La grammatica unica le comprende o le lascia
   fuori?
7. **Gli incroci con i cantieri aperti** (§6): quali oggetti del censimento stanno toccando altri
   brief. La ricognizione dei brief è già nel §6; qui si scende all'oggetto (funzione, trigger,
   service) e si leggono i documenti del §6.2.

Consegna: una sezione di questo brief con le tabelle, e una **proposta** per G-1 … G-4.

## 5. Le decisioni per Tid (dopo il censimento)

* **G-1 — quale vocabolario vince.** ✅ **Deciso da Tid il 2026-10-18: vince `config.sorgenti`**
  (strada A), prima del censimento e sulla struttura dei due cataloghi.
  * **Che cosa vuol dire.** Il tipo di documento si nomina col `codice_interno` di
    `config.sorgenti`, ovunque, DB e backend: `DDT_VENDITA`, `ORDINE_VENDITA`,
    `OFFERTA_COMMERCIALE`, `RESO_VENDITA`, `PREVENTIVO`, `CONTRATTO`, `COMMESSA`. I nomi corti della
    grammatica delle testate (`DDT`, `ORDINE`, `OFFERTA`, `RESO`) si ritirano; quel che manca
    (acquisti, `EMAIL_BOZZA`, secondo G-2) entra in `config.sorgenti`.
  * **`config.tipi_entita` resta**, col suo compito: il catalogo delle cose che si possono
    indicare (bersaglio d'errore, giornale, picker), documenti e non (`LOTTO`, `TASK_RUN`, `FLUSSO`,
    `ARTICOLO`…). Per i documenti porta lo stesso codice delle sorgenti, **legato da un vincolo** e
    non per convenzione: la forma del legame la propone il piano.
  * **Perché.** Le sorgenti sono già il catalogo dei documenti: hanno il codice immutabile, la
    tabella puntata (`target_table`), il reso e le righe, e le usano lineage e motore documentale.
    Il nome lungo regge l'ingresso degli acquisti (`DDT_ACQUISTO` accanto a `DDT_VENDITA`) senza
    rinominare niente. Le alternative scartate: allargare `config.tipi_entita` (rifarebbe lì ciò che
    le sorgenti hanno, e mescola documenti e non documenti) o un catalogo nuovo (un terzo
    vocabolario finché la migrazione non è finita).
  * **Da sciogliere nel piano:** i due cataloghi già divergono su `key_selector` (preventivo e
    offerta `uid` nelle sorgenti, `id` nelle entità). ~~Con un codice solo la chiave deve essere
    una.~~ ⚠️ Corretto il 2026-10-19 (K-1, §8.3): le due colonne rispondono a due domande diverse
    (collegare, aprire) e restano così. G-1 unifica il nome del tipo, non la chiave.
  * **Ricaduta su G-3:** `OFFERTA_COMMERCIALE` (19 caratteri) non sta in `target_tipo varchar(16)`.
  * Il censimento resta da fare: la matrice del §4 punto 2 si scrive verso i codici delle sorgenti,
    e dà il costo della migrazione, non la scelta.
* **G-2 — il perimetro.** ✅ **Deciso da Tid il 2026-10-18.**
  * **Righe e varianti: dentro.** Il nome di una riga si costruisce da quello della testata
    (`DDT_VENDITA` → `DDT_VENDITA_RIGA`), le varianti restano voci proprie (`DDT_VENDITA_PRELIEVO`,
    `RESO_VENDITA_RIENTRO`); le distingue `config.sorgenti.categoria` (`DOCUMENTO` | `RIGA`).
  * **Tutti gli schemi: dentro `acquisti` e `magazzino`.** Ogni tipo di documento che il database
    nomina in qualche punto (partizioni e `CHECK` delle note, sorgente di un movimento, lock, stato)
    ha la sua riga in `config.sorgenti`. Il motivo è sul modello: le note di `acquisti` e di
    `magazzino` nominano già quei documenti, fuori catalogo; lasciarli fuori terrebbe in vita un
    vocabolario a parte. Dare loro un nome non apre il cantiere degli acquisti.
  * **Il criterio:** è un tipo di documento ciò che ha una testata con uno stato e regole che da
    quello stato dipendono. Per questo **`EMAIL_BOZZA` è dentro**.
  * **Fuori:** ciò che non è un documento (`LOTTO`, `TASK_RUN`, `FLUSSO`, `ARTICOLO`,
    `LISTINO_VERSIONE`, `DEFINIZIONE_WORKFLOW`, `PROMO_ARTICOLO`): resta solo in
    `config.tipi_entita`, col suo compito di bersaglio.
  * Il censimento (§4 punto 2) elenca le voci da aggiungere a `config.sorgenti`, coi codici
    costruiti sulla stessa regola (`<DOCUMENTO>_<CICLO>`, per esempio `ORDINE_ACQUISTO`, `DDT_ACQUISTO`).
* **G-3 — i vincoli che decidono un nome.** ✅ **Deciso da Tid il 2026-10-18: si allarga il
  vincolo, il codice non si accorcia.**
  * **La regola:** *il vincolo si adegua al nome, mai il nome al vincolo.* Ogni colonna che porta un
    tipo di documento ha la lunghezza di `config.sorgenti.codice_interno` (`varchar(50)`, `UNIQUE`)
    e, dove si può, una **FK verso `config.sorgenti`** al posto del `CHECK` con l'elenco scritto a
    mano: un tipo nuovo è una riga del CSV, non un `CHECK` da riscrivere. Per le colonne che
    nominano qualcosa che si può indicare (le note) la FK va a `config.tipi_entita`: G-7.
  * **Le note** (`vendite.note`, `acquisti.note` `varchar(16)`; `magazzino.note` `varchar(32)`):
    `target_tipo` è la chiave di partizione, e il suo tipo non si cambia con un `ALTER`. Le tre
    tabelle si **ricostruiscono** (nuova, copia, scambio) in un lotto proprio. I valori di oggi
    (`DDT`, `ORDINE`, `OFFERTA`, `ATTIVITAFT`; nella storia dei changeSet anche `ddt` e `ordine`
    minuscoli, da verificare sulla doc auto-generata) passano ai codici delle sorgenti.
  * **Dove una FK non si può** (per esempio le chiavi delle traduzioni nel frontend): un presidio
    che confronti le chiavi col catalogo. Quali siano lo dice il censimento (§4 punto 5).
  * Scartate: accorciare i codici (contraddice G-1 e l'immutabilità di `codice_interno`) e lasciare
    alle note i loro nomi (sarebbe un ponte).
* **G-4 — l'ordine dei lotti.** ✅ **Deciso da Tid il 2026-10-18.** Ogni lotto è chiuso in sé:
  DB e backend cambiano nello stesso giro, e alla fine del lotto non resta una traduzione (regola
  del 2).

  | Lotto | Che cosa | Perché lì |
  | --- | --- | --- |
  | **0. Catalogo** | voci mancanti in `config.sorgenti` (acquisti, testate di magazzino, `EMAIL_BOZZA`, G-2); `key_selector` unico; `config.tipi_entita` legato alle sorgenti da un vincolo (G-1) | additivo, non rompe niente; i lotti dopo ne hanno bisogno per le FK |
  | **1. Eccezioni** | la famiglia del §9.8.3 (`fn_documento_listino_operativo` e le sorelle) da `OFFERTA` a `OFFERTA_COMMERCIALE`; nel backend si ritira `DocumentoEccezioni` coi letterali | il più piccolo e il più noto: prova il metodo prima del lotto grande |
  | **2. Testate** | stato, lock, annullo con legami, indirizzi, lineage: le funzioni coi codici corti e i loro chiamanti, DB e backend. Muore il ponte di `fn_articolo_riga_contesto` | il più grande, a metodo provato |
  | **3. Note** | le tre tabelle ricostruite con `target_tipo` lungo e FK verso le sorgenti (G-3); `note_repositories.py` | dipende solo dal lotto 0: **anticipabile** |
  | **4. Chiusura** | il presidio contro la ricaduta (per esempio un pgTAP: ogni colonna di tipo documento ha la FK verso le sorgenti), la riga di PROJECT_CONTEXT, l'archiviazione | senza presidio il prossimo letterale scritto a mano rientra |

  **Rispetto ai cantieri aperti (§6.1):**
  * **indirizzi**: il giro BE (R-BE-1) si chiude **così com'è**, coi selettori corti; li migra il
    lotto 2 insieme agli altri consumatori;
  * **stato iniziale**: parte **dopo il lotto 0**, così nasce sui codici delle sorgenti;
  * **articoli ammessi**: il ponte resta fino al lotto 2.

  Prima del lotto 0 resta il **censimento** (§4): con le decisioni prese, il suo compito è
  l'elenco degli oggetti di ciascun lotto. ⛔ I changeSet partono col via di Tid.

## 6. Cantieri che toccano gli stessi oggetti

Questo brief è la **sede unica** del vocabolario dei tipi di documento: gli altri brief vi
rimandano con una riga, non ne ricopiano il contenuto. Ricognizione del 2026-10-18, sui brief in
`work-in-progress/` (grep sui nomi degli oggetti del §1).

⛔ **Fino a G-1, nessun vocabolario nuovo.** Il codice che si scrive nel frattempo usa la
grammatica che c'è e si **iscrive al §4 punto 3** (chi parla cosa), così il perimetro della
migrazione resta chiuso invece di crescere a ogni giro.

### 6.1 Cantieri che scrivono oggi codice sul vocabolario (consumatori nuovi)

| Brief | Oggetti in comune | Che cosa si fa |
| --- | --- | --- |
| [brief-db-indirizzi-documento-seguono-il-cliente](brief-db-indirizzi-documento-seguono-il-cliente.md) | `vendite.fn_doc_indirizzo_default` coi selettori `DDT`, `ORDINE`, `PREVENTIVO`, `OFFERTA`, `CONTRATTO` (R-BE-1, il BE li passa da quattro service e dai verbi con cascata); `script.fn_doc_lock_regola` e il lock delle testate del §8.7 (`20261018-65`); `fn_get_cliente_testata_documento`, `fn_doc_indirizzi_sede` | rimando in R-BE-1; i selettori entrano nel censimento come consumatori della grammatica delle testate |
| [brief-db-documento-nasce-nello-stato-iniziale](brief-db-documento-nasce-nello-stato-iniziale.md) | i guard di transizione delle testate (`trg_<doc>_a10_guard_transizione_upd`), gli stati iniziali per famiglia | non iniziato: se introduce un registro per tipo di documento, nasce sulla grammatica decisa in G-1 |
| [brief-db-articoli-ammessi-per-documento](brief-db-articoli-ammessi-per-documento.md) | il ponte di `script.fn_articolo_riga_contesto`, la famiglia del §9.8.3 | il ponte resta fino al lotto che lo rende inutile: lo ritira chi chiude questo brief |

### 6.2 Documenti che pesano sulle decisioni G-1 … G-3 (da leggere nel censimento)

| Documento | Che cosa porta | Decisione |
| --- | --- | --- |
| [analisi-simmetria-ordini-acquisto](analisi-simmetria-ordini-acquisto.md) §4.6 | `config.sorgenti` ha solo sorgenti di `vendite`; `config.tipi_entita` non ha l'ordine d'acquisto: lineage, motore documentale e bersaglio d'errore non vedono gli acquisti | **G-2**: la grammatica comprende `acquisti`? |
| [brief-design-proiezione-stato-dominio](brief-design-proiezione-stato-dominio.md) | `config.sorgenti` trattato già da registro dei tipi (`target_table`, `key_selector`, la proposta `resolver_key`) | **G-1** |
| [valutazione-modello-di-dominio-db](valutazione-modello-di-dominio-db.md) | V-5: `codice` mutabile e `codice_interno` immutabile; le note di `vendite`, `acquisti`, `magazzino` partizionate per `target_tipo`, con `CHECK` e routing di partizione | **G-1** (quale colonna porta il codice), **G-3** (allargare `target_tipo` tocca le partizioni) |
| [analisi-db-magazzino-carico-e-scarico](analisi-db-magazzino-carico-e-scarico.md), [analisi-db-magazzino-aggancio-documento-e-produzione](analisi-db-magazzino-aggancio-documento-e-produzione.md) | le sorgenti di riga (`*_RIGA`) e la sorgente polimorfa (`sorgente_tipo_id` → `config.sorgenti`) di rettifiche, trasferimenti, inventari, eventi asset | **G-2** (righe e varianti) |

### 6.3 Solo da avvisare

* [brief-db-offerta-emissione-ed-erogazione](brief-db-offerta-emissione-ed-erogazione.md):
  `fn_documento_listino_operativo`, `fn_check_riga_erogazione`. Lato DB chiuso: la migrazione di
  quegli oggetti la fa un lotto di questo brief.

## 7. Il censimento (team DB, 2026-10-18)

Letto sul **contratto**: doc auto-generata (corpi di funzioni e viste), seed in `80_data`, e il
catalogo di PostgreSQL di dbdev per ciò che la doc non riporta (espressioni dei `CHECK`, confini
delle partizioni, argomenti dei trigger: `pg_constraint`, `pg_inherits`, `pg_trigger.tgargs`).
Nessun conteggio di righe: è la struttura, non la popolazione.

### 7.1 I vocabolari (§4 punto 1)

Il brief ne contava quattro più le note. Sono **otto**:

| # | Vocabolario | Dove vive | Forma dei codici | Fonte |
| --- | --- | --- | --- | --- |
| V1 | **sorgenti** | `config.sorgenti.codice_interno` (`varchar(50)`, `UNIQUE`) | lunga: `DDT_VENDITA`, `ORDINE_VENDITA`, `OFFERTA_COMMERCIALE`, `RESO_VENDITA`, `*_RIGA`, varianti | catalogo (✅ vince, G-1) |
| V2 | **entità** | `config.tipi_entita.codice` (PK) | lunga, uguale a V1 dove si incrociano; niente reso | catalogo |
| V3 | **testate** | il parametro `p_documento` di una famiglia di funzioni, e gli argomenti dei trigger montati per tabella | corta: `DDT`, `ORDINE`, `OFFERTA`, `RESO`, `EMAIL_BOZZA`, più `PREVENTIVO`, `CONTRATTO`, `COMMESSA`, `FATTURA` | ⛔ nessuna: elenchi scritti in ogni corpo (`NOT IN (…)`, `IF … ELSIF`) |
| V4 | **famiglie di numerazione** | `vendite.famiglie_documento.codice_interno` (`varchar(16)`); FK da `vendite.registri_fatturazione.famiglia_documento` | corta: `FATTURA`, `DDT`, `ORDINE`, `COMMESSA`, `RESO`, `DISTINTA` | catalogo (con `schema_tabella`, `nome_tabella`: «dove vive» il documento, come `config.sorgenti.target_table`) |
| V5 | **aree documentali** (plurale) | `config.sorgenti.area` (`varchar(30)`) e `config.tipi_indirizzi_allowed.ambito` (`text`, `CHECK`), argomento di `trgfn_tipi_indirizzi_only_allowed` | plurale: `PREVENTIVI`, `ORDINI`, `CONTRATTI`, `DDT`, `OFFERTE`, `COMMESSE`, `FATTURE`, `ACQUISTI_DDT` | due: una colonna di V1 e un `CHECK` |
| V6 | **bersagli delle note** | `target_tipo` delle note partizionate, `CHECK` + confini di partizione; argomento di `trgfn_note_validate_generic`; `fn_scope_note_*` | misto: `DDT`, `ORDINE`, `OFFERTA`, `ATTIVITAFT`, `PREVENTIVO`, `CONTRATTO`, `FATTURA` (vendite); `DDT`, `ORDINE` (+ `FATTURA`, `CONTRATTO` nel `CHECK`, senza partizione) (acquisti); `INVENTARIO`, `RETTIFICA`, `TRASFERIMENTO`, `*_RIGA`, `ASSET`, `EVENTO_ASSET`, `MOVIMENTO` (magazzino); `ARTICOLI`, `ARTICOLI_COMPONENTI` (catalogo) | ⛔ un `CHECK` per schema |
| V7 | **origine e destinazione** | `vendite.ordini.documento_origine_tipo` (`CHECK`: `PREVENTIVO`, `OFFERTA`); `config.nature_vendita.destinazione_tipo` (`CHECK`: `ORDINE`, `COMMESSA`, `CONTRATTO`); l'`origine` restituita da `vendite.fn_documento_legami` (`ORDINE`, `RESO`, `OFFERTA`) | corta | ⛔ `CHECK` |
| V8 | **prefissi di chiave** | `vendite.commesse_attivita.segment_key` (`ORD:…`, `DDT:…`), letto con `split_part(…) = ANY ('ORD','DDT')` da `vendite.fn_af_merce_per_riga`; la `corsia` `'DDT'` in `vendite.fn_partite_merce` | abbreviata | ⛔ nessuna |

⚠️ **Il caso che dimostra il problema, sul modello:** in `acquisti.note` i codici `DDT` e `ORDINE`
indicano la bolla e l'ordine **d'acquisto**; in `vendite.note` gli stessi codici indicano quelli di
**vendita**. Lo stesso nome per due documenti diversi: regge solo perché le due tabelle sono
separate. È il motivo di G-1, in un caso concreto.

### 7.2 La matrice dei codici (§4 punto 2)

`—` = il vocabolario non nomina quel documento. ❌ = dovrebbe e non c'è.

| Documento | V1 sorgenti | V2 entità | V3 testate | V4 famiglie | V5 aree | V6 note | V7 / V8 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Preventivo | `PREVENTIVO` | `PREVENTIVO` | `PREVENTIVO` | — | `PREVENTIVI` | `PREVENTIVO` | origine `PREVENTIVO` |
| Ordine di vendita | `ORDINE_VENDITA` | `ORDINE_VENDITA` | `ORDINE` | `ORDINE` | `ORDINI` | `ORDINE` | destinazione e legami `ORDINE`; chiave `ORD` |
| DDT di vendita | `DDT_VENDITA` | `DDT_VENDITA` | `DDT` | `DDT` | `DDT` | `DDT` | chiave e corsia `DDT` |
| Offerta | `OFFERTA_COMMERCIALE` | `OFFERTA_COMMERCIALE` | `OFFERTA` | — | `OFFERTE` | `OFFERTA` | origine e legami `OFFERTA` |
| Contratto | `CONTRATTO` | `CONTRATTO` | `CONTRATTO` | — | `CONTRATTI` | `CONTRATTO` | destinazione `CONTRATTO` |
| Commessa | `COMMESSA` | `COMMESSA` | `COMMESSA` | `COMMESSA` | `COMMESSE` | — | destinazione `COMMESSA` |
| Fattura | `FATTURA` | `FATTURA` | `FATTURA` (indirizzi, cliente) | `FATTURA` | `FATTURE` | `FATTURA` | — |
| Reso di vendita | `RESO_VENDITA` | ❌ | `RESO` | `RESO` | — | — | legami `RESO` |
| Attività fatturabile | `ATTIVITA` (riga) | — | — | — | — | `ATTIVITAFT` | — |
| Attività consumi | `ATTIVITA_CONSUMI` | — | — | — | — | — | — |
| Email in bozza | ❌ | — | `EMAIL_BOZZA` | — | — | — | — |
| Distinta d'incasso | ❌ | — | — | `DISTINTA` | — | — | — |
| Ordine d'acquisto | ❌ | ❌ | — | — | — | `ORDINE` (acquisti) | — |
| DDT d'acquisto | ❌ | ❌ | — | — | `ACQUISTI_DDT` | `DDT` (acquisti) | — |
| Fattura, contratto d'acquisto | ❌ | ❌ | — | — | — | nel `CHECK` di `acquisti.note`, senza partizione | — |
| Inventario, rettifica, trasferimento | ❌ (solo le `*_RIGA`) | ❌ | — | — | — | `INVENTARIO`, `RETTIFICA`, `TRASFERIMENTO` | — |
| Righe | `*_RIGA` | — | ruolo `RIGA` negli argomenti del lock | — | — | `*_RIGA` (magazzino) | — |

Non documenti con note (G-2: fuori dalla grammatica, dentro le note): `ARTICOLI`,
`ARTICOLI_COMPONENTI`, `ASSET`, `MOVIMENTO`. V2 ha `ARTICOLO`, al singolare.

### 7.3 Chi parla cosa (§4 punto 3)

**V3, codici ricevuti da fuori** (`p_documento` con elenco nel corpo):
`script.fn_get_stato_testata_documento`, `fn_get_testata_id_di_riga`,
`fn_get_cliente_testata_documento`, `fn_doc_indirizzi_sede`, `fn_doc_date_consegna_anteriori`,
`fn_check_listino_cambiabile`, `fn_check_listino_congelabile`, `fn_check_riga_erogazione`,
`fn_check_indirizzi_documento_cliente`, `fn_indirizzi_obbligatori_mancanti`;
`vendite.fn_documento_listino_operativo`, `fn_documento_righe_eccezione`,
`fn_documento_righe_preview`, `fn_documento_legami`, `fn_documento_ritira_legami`,
`fn_doc_fornitura_sede`, `fn_doc_porta_ritiro_ammette`, `fn_doc_indirizzo_default`.

**V3, codici negli argomenti dei trigger** (montaggio per tabella): `trgfn_doc_testata_lock_fuori_bozza`,
`trgfn_doc_righe_lock_fuori_bozza`, `trgfn_doc_guard_annullo_con_legami`, `trgfn_doc_guard_emittente_ba`,
`trgfn_doc_guard_listino_con_righe`, `trgfn_doc_guard_listino_documento`,
`trgfn_doc_indirizzi_guard_cliente`, `trgfn_doc_indirizzi_seguono_cliente`,
`trgfn_doc_fornitura_guard_coppia`, `trgfn_doc_fornitura_segue_cliente`,
`trgfn_doc_righe_guard_data_consegna`, `trgfn_doc_testata_guard_data_consegna_righe`,
`trgfn_righe_guard_erogazione_perimetro`.

**V3, codici scritti come letterale** nelle chiamate: i verbi di annullo (`fn_annulla_ddt`,
`fn_annulla_ordine`), i guard di bolla, ordine, reso e offerta, `fn_available_actions_offerta`,
`fn_offerta_righe_espanse`, `fn_offerta_righe_preview`, `trgfn_doc_guard_delete_solo_bozza`,
`trgfn_dlt_block_ordrig_ddtrig`, `trgfn_email_allegato_guard_solo_bozza`, `dbops.fn_pgtap_crea_ddt`.

**V1 (o V2), codici lunghi:** `catalogo.fn_articoli_ammessi`, `fn_articolo_righe_vive_non_ammesse`,
`script.fn_articolo_riga_contesto`, `fn_check_articolo_riga_su_contesto`, i lineage
(`fn_documento_lineage_nodi`, `_archi`), i push (`fn_push_offerta_a_contratto`,
`fn_push_preventivo_a_ordine`, `fn_list_*_da_pushare`), le viste `vw_stato_sorgente_*` e
`vw_*_lista`, i trigger montati con `DDT_VENDITA`/`ORDINE_VENDITA`/`OFFERTA_COMMERCIALE`
(`trgfn_righe_guard_articolo_ammesso`, `trgfn_doc_guard_chiusura_sorgente`,
`trgfn_guard_fatturazione_immediata_immutabile`). ⭐ Chi usa `sorgente_tipo_id` (FK) parla già V1
senza letterali: è la forma d'arrivo.

**V4:** i numeratori (`trgfn_ddt_gen_numero_emesso`, `trgfn_ordini_gen_numero`,
`trgfn_resi_gen_numero`, `fn_get_next_progressivo`, `fn_assegna_numero_documento`,
`fn_get_registro_documento`, `fn_lookup_registro_documento`, `fn_get_or_create_commessa`), il
provisioning dei registri, i guard delle famiglie, `anagrafiche.fn_ba_ha_storia_emittente`.

**V6:** `script.fn_scope_note_cliente`, `fn_scope_note_ef_whitelist`, `fn_scope_note_shop`,
`trgfn_note_validate_generic`. **V7:** `vw_ordini_lista`, `vw_dash_fatturazione_offerte`,
`fn_documento_lineage_archi`, `fn_offerta_documenti_vivi`, `fn_check_preventivo_annullabile`, le
viste di smistamento del preventivo, `catalogo.trgfn_articoli_guard_onere_natura`.

### 7.4 Chi traduce (§4 punto 4), lato DB

| Punto | Da → a |
| --- | --- |
| `script.fn_articolo_riga_contesto` | V1 → V3 (`OFFERTA_COMMERCIALE` → `OFFERTA`): il ponte dichiarato |
| `vendite.fn_documento_ritira_legami` | V3 → V1 (`CASE 'DDT' THEN 'DDT_VENDITA'`) |
| `script.fn_doc_indirizzi_sede` | V3 → V5 (`ORDINE` → `ORDINI`, `OFFERTA` → `OFFERTE`), dentro la tabella di `VALUES` |
| `config.sorgenti.area` | V1 → V5, come **dato** |
| `script.fn_check_articolo_riga_su_contesto` | V1 (`ORDINE_VENDITA`) confrontato con V7 (`destinazione_tipo = 'ORDINE'`) |
| `vendite.fn_documento_lineage_archi`, `vw_ordini_lista` | V7 (`OFFERTA`) letto accanto a V1 (`OFFERTA_COMMERCIALE`) |
| `vendite.trgfn_resi_guard_cliente_ddt`, `fn_check_ddt_riga_correggi_qta_evasa`, `fn_genera_ddt_riconsegna`, `fn_documento_legami`, `script.fn_available_actions_offerta` | due grammatiche nello stesso corpo (V1 e V3) |

Il backend: §7.8.

### 7.5 I vincoli che decidono un nome (§4 punto 5)

| Vincolo | Ostacolo |
| --- | --- |
| `vendite.note`, `acquisti.note`: `target_tipo varchar(16)`, chiave di partizione, nella PK (`target_tipo, id`) e negli indici | il tipo non si cambia con `ALTER`: ricostruzione (G-3) |
| `magazzino.note`, `catalogo.note`: `varchar(32)`, idem | idem, se cambiano i valori |
| `vendite.famiglie_documento.codice_interno varchar(16)`, FK da `registri_fatturazione.famiglia_documento varchar(16)` | i nomi lunghi ci stanno (`ORDINE_VENDITA` è 14), ma la regola G-3 vuole 50 |
| `vendite.ordini.documento_origine_tipo varchar(20)`, `config.nature_vendita.destinazione_tipo varchar(20)` | ci stanno; il `CHECK` va sostituito |
| Argomenti dei trigger (`tgargs`) | si cambiano solo smontando e rimontando il trigger: un changeSet per ogni montaggio |
| `vendite.commesse_attivita.segment_key` (`ORD:…`) | è una chiave di idempotenza scritta nelle righe: cambiare il prefisso cambia l'identità delle righe esistenti |
| Chiavi delle traduzioni nel frontend | fuori dal perimetro DB: le censisce la sessione FE |

### 7.6 I confini (§4 punto 6)

Li ha già decisi G-2. Il censimento aggiunge tre casi che G-2 non nominava: la **distinta
d'incasso** (`pagamenti.vendite_contabili`, in V4) e le **testate di magazzino** (inventario,
rettifica, trasferimento: in V6 ma non in V1) sono documenti numerati o con stato, quindi
**dentro**; asset e movimento non sono documenti, quindi **fuori** (ma con note: G-7).

### 7.7 Gli incroci con i cantieri aperti (§4 punto 7)

* **Indirizzi:** `fn_doc_indirizzo_default`, `fn_doc_indirizzi_sede`,
  `trgfn_doc_indirizzi_guard_cliente`, `trgfn_doc_indirizzi_seguono_cliente`,
  `trgfn_doc_testata_lock_fuori_bozza` (il `20261018-65` risulta montato: gli argomenti hanno già
  il `-`). Tutto V3 e V5: lotto 2.
* **Stato iniziale:** i guard di transizione di ogni famiglia; nessun vocabolario nuovo finché non
  parte (§6.1).
* **Articoli ammessi:** già su V1, salvo il ponte.
* **Offerta:** `fn_doc_fornitura_*`, `trgfn_righe_guard_erogazione_perimetro`,
  `fn_documento_listino_operativo`: V3, lotti 1 e 2.

### 7.8 Il backend

Ricerca dei letterali in `backend/` (Python; test esclusi, ripetono gli stessi codici). Esclusi gli
omonimi che non nominano un tipo di documento (la colonna `ordine` di posizione, i codici `E_*`, le
etichette leggibili, `TIPO_MOVIMENTO_RETTIFICA`). L'app `acquisti` è vuota.

**Già su V1, senza traduzione (la forma d'arrivo):** le costanti `SORGENTE_*` di
`apps/config/sorgenti.py` e chi le usa (PDF, lineage, push verso la commessa, pratiche,
`fn_list_*_da_pushare`), il picker degli articoli ammessi (il codice arriva dal client e passa così
com'è), il giornale (`entity_type` di V2).

**Parlano V3 (corto):**

| Dove | Codici | Per |
| --- | --- | --- |
| `vendite/services/_annullo_con_legami.py:48-52` | `DDT`, `ORDINE`, `PREVENTIVO`, `CONTRATTO`, `COMMESSA` | `vendite.fn_documento_legami`, dai cinque service |
| `vendite/db/_documento_eccezioni_repo.py:39` (`DocumentoEccezioni`), `offerte_service`, `contratti_service` | `OFFERTA`, `CONTRATTO` | la famiglia delle eccezioni (lotto 1) |
| `vendite/db/*_repository.py` col mixin indirizzi (`_indirizzi_documento`) | `PREVENTIVO`, `ORDINE`, `OFFERTA`, `CONTRATTO`, `DDT` | `vendite.fn_doc_indirizzo_default` |
| `vendite/services/ordini_service.py:738, 758` | `OFFERTA` | scrive `ordini.documento_origine_tipo` (V7) e lo **espone nella risposta API** |
| `vendite/services/_iva_contesto_documento.py:61-74` | `PREVENTIVO`, `ORDINE`, `DDT` | registro dei loader, **esposto come `choices`** di un endpoint (`views_iva.py:53`) |
| `vendite/services/vendite_service.py:2577` | `ORDINE`, `DDT` | il `contesto` della situazione merce, **nella risposta API** |

**Parlano V5 (plurale):** `_indirizzi_ambito` dei cinque repository (`PREVENTIVI`, `ORDINI`,
`OFFERTE`, `CONTRATTI`, `DDT`); le aree della dashboard in `vendite_repository.py:227-256`,
allineate a `area` delle viste `vw_dash_*`.

**Parlano V6:** `core/db/partitioned_note_repository.py:80-83` (`TARGET_TIPI_AMMESSI`, copia del
`CHECK` di `vendite.note`, `ATTIVITAFT` compreso) e `vendite/db/note_repositories.py`.

**Vocabolari che vivono solo nel backend** (nessun catalogo DB):

* `preventivo`, `contratto`, `offerta` **minuscoli** (`_approvazioni_prezzo_constants.py:46-55`):
  la chiave `META_KEY_SORGENTE` nel `meta` jsonb della pratica, cioè un vocabolario **scritto nei
  dati**. Stesso nome delle costanti di `sorgenti.py`, valori diversi;
* `TIPI_DOCUMENTO_AMMESSI` dell'IVA e il `contesto` della situazione merce (sopra);
* `ErrorScope = Literal["LOTTO", "FATTURA"]` (`pipeline_error_logger.py:20`): valori di V2,
  instradamento solo Python. Non è un tipo di documento come chiave nuova: resta, legato a V2.

**Chi traduce, lato backend:**

| Punto | Da → a |
| --- | --- |
| `_annullo_con_legami.py:63-70` | V3 → V1 (`DDT` → `DDT_VENDITA`, `ORDINE` → `ORDINE_VENDITA`) |
| `_annullo_con_legami.py:77-86` | l'`origine` di V7 → V1 (`OFFERTA` → `OFFERTA_COMMERCIALE`, `RESO` → `RESO_VENDITA`) |
| i cinque repository col mixin indirizzi | V5 ↔ V3, una coppia per classe |
| `magazzino/db/famiglie.py:84, 103` | segmento d'URL (`inventari`, `rettifiche`) → `INVENTARIO_RIGA`, `RETTIFICA_RIGA`. Il segmento è una rotta, non un codice: resta |
| `ordini_service.py:111-112` | `_TIPO_VIVO_ORDINE = 'ORDINE_VENDITA'`: copia locale di V1, non presa da `sorgenti.py` |
| `post_smistamento_handler.py:73-74`, `preventivi_service.py:2101` | `SORGENTE_PREVENTIVO` usato come valore di `documento_origine_tipo` (V7): due vocabolari che coincidono per caso, cosa che `sorgenti.py:15-20` vieta |

⚠️ **Ricaduta sul frontend.** Tre risposte API portano codici V3 (`documento_origine.tipo`, le
`choices` dell'IVA, il `contesto` della situazione merce), e le chiavi delle traduzioni possono
dipenderne. Il censimento del FE (chiavi i18n, confronti nei componenti) lo fa la sessione FE nel
lotto che cambia quelle risposte.

### 7.9 Le decisioni nuove che il censimento apre

G-1 … G-4 restano valide. Il censimento trova quattro vocabolari che non avevano una decisione:

* **G-5 — le famiglie di numerazione (V4).** ✅ **Deciso da Tid il 2026-10-18, come da
  proposta.** È un catalogo di tipi di documento con codici propri e con «dove vive» il documento
  (`schema_tabella`, `nome_tabella`), che ripete `config.sorgenti.target_table`.
  * `vendite.famiglie_documento` **resta** per ciò che è solo della numerazione: colonna del
    numero, prefisso stampato (`ORD`, `DDT`: non cambia), lunghezza, serie;
  * la sua identità diventa una **FK verso `config.sorgenti`**: il codice della famiglia è quello
    della sorgente (`DDT` → `DDT_VENDITA`, `ORDINE` → `ORDINE_VENDITA`, `RESO` → `RESO_VENDITA`), e
    `registri_fatturazione.famiglia_documento` segue;
  * `schema_tabella` e `nome_tabella` **si ritirano** a favore di `target_table` (regola del 2);
    `vendite.fn_crea_famiglia_documento` riceve una sorgente esistente invece della tabella;
  * la distinta d'incasso (`DISTINTA`) entra in `config.sorgenti` (G-2). Lotto 0 per il catalogo,
    lotto 2 per i numeratori.
* **G-6 — le aree documentali al plurale (V5).** ✅ **Deciso da Tid il 2026-10-18, come da
  proposta: il plurale si ritira.**
  * **Indirizzi:** `config.tipi_indirizzi_allowed.ambito` diventa il codice della sorgente, con FK
    al posto del `CHECK` (`ORDINI` → `ORDINE_VENDITA`, `ACQUISTI_DDT` → `DDT_ACQUISTO`); gli
    argomenti di `trgfn_tipi_indirizzi_only_allowed` seguono, e nel backend il mixin indirizzi
    passa un codice solo invece della coppia `_indirizzi_ambito` / `_indirizzi_documento`;
  * **Dashboard:** `config.sorgenti.area` si ritira; le viste `vw_dash_*` e le costanti
    `DASH_*_AREE` del backend raggruppano per `codice_interno`, e l'etichetta la danno le
    traduzioni;
  * ⭐ **il significato si tiene:** oggi `area IS NULL` vuol dire «la sorgente non è un documento
    sfogliabile in dashboard». È una regola nascosta in un vuoto: diventa una colonna esplicita di
    `config.sorgenti` (per esempio `in_dashboard boolean NOT NULL`), il nome lo fissa il piano;
  * lotto 2; il frontend della dashboard (chiavi di traduzione, filtri) lo verifica la sessione FE
    nello stesso lotto.
* **G-7 — il catalogo delle note (V6).** ✅ **Deciso da Tid il 2026-10-18: le note puntano a
  `config.tipi_entita`** (strada a). Le note stanno anche su cose che non sono documenti
  (articoli, componenti, asset, movimenti), quindi una FK verso `config.sorgenti` non le copre
  tutte; i due meccanismi (FK per i documenti, `CHECK` per il resto) sono scartati.
  * **Precisazione di G-3:** *una colonna che nomina un **documento** punta alle sorgenti; una
    colonna che nomina **qualcosa che si può indicare** (note, bersaglio d'errore, giornale)
    punta alle entità.* Per G-1 le entità dei documenti hanno il codice della sorgente, legato:
    il codice resta uno.
  * **I codici delle note si allineano:** `DDT` → `DDT_VENDITA` (vendite) e `DDT_ACQUISTO`
    (acquisti), `ORDINE` → `ORDINE_VENDITA` e `ORDINE_ACQUISTO`, `OFFERTA` →
    `OFFERTA_COMMERCIALE`, `ATTIVITAFT` → `ATTIVITA`, `ARTICOLI` → `ARTICOLO`,
    `ARTICOLI_COMPONENTI` → `ARTICOLO_COMPONENTE`. Il caso dello stesso nome per due documenti
    (§7.1) sparisce.
  * **In `config.tipi_entita` entrano** le voci che mancano: `ARTICOLO_COMPONENTE`, `ASSET`,
    `EVENTO_ASSET`, `MOVIMENTO`, `ATTIVITA`, le testate di magazzino e le righe con nota
    (`INVENTARIO_RIGA`…), i documenti d'acquisto, il reso.
  * Segue anche `catalogo.articoli.note_target_tipo` / `articoli_componenti.note_target_tipo`
    (oggi `CHECK` fisso). Nel backend si ritira `TARGET_TIPI_AMMESSI` di
    `partitioned_note_repository.py`: decide la FK.
  * ⚠️ **La FK toglie l'elenco, non la partizione.** Ogni tipo ha la sua partizione con la FK
    verso la tabella del documento (`target_id`): un tipo nuovo di nota resta un changeSet per
    la partizione, più una riga di `tipi_entita.csv` al posto del `CHECK` e della copia Python.
  * Lotto 3 (le tabelle si ricostruiscono comunque per G-3); le voci del catalogo nel lotto 0.
* **G-8 — i prefissi di chiave (V8).** ✅ **Deciso da Tid il 2026-10-18, come da proposta.**
  `vendite.commesse_attivita.segment_key` è la chiave d'idempotenza del push
  (`<PREFISSO>:<uid>:R:<riga>[:M:<mese>][#CMP:<componente>]`), coi prefissi `PREV`, `ORD`, `DDT`,
  `CONTR`, `CONS`: un sesto vocabolario corto.
  * **Chi decide non legge il prefisso:** «è merce?» (`vendite.fn_af_merce_per_riga`, oggi
    `split_part(…) = ANY ('ORD','DDT')`) si chiede a `sorgente_tipo_id`, la FK che la riga porta già;
  * **la chiave la costruisce un solo building block** in `script` (sorgente, uid, riga, mese):
    le copie scritte a mano (`'ORD:' || uid || ':R:' || id` nei push, nel reso
    `fn_accredita_riga_reso` / `fn_annulla_accredito_riga_reso`, nei builder pgTAP) si ritirano
    nello stesso giro, e chi ritrova una chiave usa la stessa funzione (regola del 2);
  * **il prefisso diventa il `codice_interno` della sorgente** (`ORDINE_VENDITA:<uid>:R:<id>`;
    `varchar(128)` basta). `MAN` (attività a mano) resta: non è un tipo di documento;
  * **le chiavi esistenti** si convertono **a mano con un SQL una tantum** sui database di sviluppo
    (Tid, 2026-10-18: non c'è produzione), non con un changeSet: in CI il database nasce vuoto e
    non ha chiavi da convertire. Va fatto **insieme all'apply del lotto 2**: una chiave vecchia
    davanti al builder nuovo non viene riconosciuta e il push successivo duplica la riga.
    ⚠️ L'`UPDATE` passa dai guard `BEFORE UPDATE` di `commesse_attivita` (quantità immutabile,
    prezzo di rettifica): il SQL lo prepara il team DB col lotto e lo prova in transazione.
  * Lotto 2.

V7 (origine e destinazione) non apre una decisione: rientra in G-3 (`CHECK` → FK verso le sorgenti).
Nemmeno i vocabolari solo del backend (§7.8): G-1 vale anche lì, e i minuscoli del `meta` della
pratica passano ai codici delle sorgenti nel lotto che tocca le approvazioni di prezzo.

## 8. Lotto 0 — il catalogo (team DB, 2026-10-19)

Via di Tid il 2026-10-18 sera, numeri da `20261019-14`. Scritto e provato in transazione; **non
applicato**.

### 8.1 Che cosa contiene

| Pezzo | Dove | Che cosa |
| --- | --- | --- |
| `20261019-14` | `00_schema/config` | `config.sorgenti.scope` ammette `CATALOGO`: il tipo è a catalogo per il suo nome, e nessun meccanismo (push, pipeline, movimenti) lo legge per scope. Nessuno dei valori di prima descriveva i tipi nuovi |
| `20261019-15` | `00_schema/config` | `config.tipi_entita.is_sorgente` + colonna generata `sorgente_codice_interno` con FK verso `config.sorgenti(codice_interno)`: un'entità che è anche una sorgente porta lo stesso codice **per vincolo** (G-1). COMMENT di tabella riscritto (diceva «non ci si aggancia») |
| `sorgenti.csv` | `80_data` | sette sorgenti nuove, id 23-29, scope `CATALOGO`: `ORDINE_ACQUISTO`, `DDT_ACQUISTO`, `INVENTARIO`, `RETTIFICA`, `TRASFERIMENTO`, `DISTINTA_INCASSO`, `EMAIL` |
| `tipi_entita.csv` + mirror `20260822-55` | `80_data` | colonna `is_sorgente` in coda (e nell'elenco del mirror, `ANY`); 25 voci nuove: ogni sorgente che non era un'entità (22) più le tre di G-7 che non sono sorgenti (`ARTICOLO_COMPONENTE`, `ASSET`, `MOVIMENTO`). Tutte con chiave `id`, non giornalabili |
| pgTAP | `db/pgtap/config/test-grammatica-catalogo-sorgenti-entita-v1.sql` | 9 test: ogni sorgente ha la sua entità (il verso che la FK non sa dire), la FK, il rifiuto di un'entità che si dichiara sorgente senza esserlo, le sette sorgenti nuove |

Il resync della sequenza di `config.sorgenti` non serve un changeSet: lo fa già `90_end/20260616-02`
(`runAlways`, tutte le sequenze di `config`). Il `20261019-16`, tenuto per K-1, non serve (§8.3).

### 8.2 Le scelte del piano

* **Il verso del legame: entità → sorgenti.** Nel migrate il mirror delle sorgenti (`20251002-21`)
  gira prima di quello delle entità (`20260822-55`): un tipo nuovo è una riga in tutti e due i CSV, e
  in questo verso la riga puntata c'è già. Nel verso opposto ogni tipo nuovo fermerebbe il migrate.
  Il verso che la FK non copre (ogni sorgente ha la sua entità) lo asserisce il pgTAP, test 1.
* **Ogni sorgente è un'entità**, righe e varianti comprese: ha una tabella e una chiave, quindi si può
  indicare (bersaglio, note). Così il presidio è una regola sola, senza eccezioni per categoria.
* **Le righe d'acquisto non entrano**: oggi nessun punto del database le nomina (le note di
  `acquisti` sono per testata). Entrano col primo che le nomina, per esempio il carico da DDT
  d'acquisto. Fattura e contratto d'acquisto, nominati solo dal `CHECK` di `acquisti.note`, non hanno
  tabella: fuori; il `CHECK` lo ricostruisce il lotto 3.
* **`label_selector`**: `numero` per i due documenti d'acquisto, `codice` per la distinta; `NULL` per le
  testate di magazzino (non hanno un numero leggibile) e per l'email.
* ⚠️ **L'automazione `attivo` non lega l'accensione.** Provato sullo scratch:
  `dbops.fn_run_automations_attivo('AUTO', ARRAY['config'], false)` non monta niente sulla FK nuova, e
  una sorgente con la sua entità si spegne senza errore. La FK lega il **nome**, non l'accensione. Se si
  vuole che un tipo nominato da note e bersagli non si spenga, è una regola da scrivere (lotto 4).

### 8.3 Le decisioni del lotto 0 (Tid, 2026-10-19)

* **K-1 — la chiave di preventivo e offerta: ✅ (b1), resta com'è.** `config.sorgenti.key_selector`
  dice `uid`, `config.tipi_entita.key_selector` dice `id`, e le due colonne restano così, col loro nome.
  * **Perché.** Le due colonne rispondono a due domande diverse: la prima dice con che chiave un
    documento si **collega** (collegamento polimorfo, guard, resolver, `vw_stato_sorgente_*`), la seconda
    con che chiave lo si **apre** a video (le rotte `<int:preventivo_id>`). Lo dicevano già la nota della
    riga `PREVENTIVO` in `tipi_entita.csv` e il manuale di `config.sorgenti` («convenzione voluta e
    portante: non va ripulita»). G-1 unifica il **nome del tipo**, non la chiave: la frase del §5 «con un
    codice solo la chiave deve essere una» era sbagliata, ed è corretta lì.
  * ⚠️ **Il vicolo cieco, da non ripercorrere.** La prima stesura di questo paragrafo raccomandava
    (a), «una chiave sola, `id`», contando solo i due collegamenti testuali (`pratiche_sorgenti`,
    `commesse_sorgenti`). L'`uid` vive anche fuori dal meccanismo polimorfo: `commesse_attivita` porta
    sempre l'`uid` del documento, le chiavi di idempotenza del push lo contengono, `vendite.ddt` e
    `vendite.resi` hanno `sorgente_uid uuid` tipizzato, e la proiezione dello stato delle pratiche si
    aggancia al preventivo per `uid` (`trgfn_documento_reconcile_proiezione('2', 'uid')`). La guida
    [sorgente polimorfa](../../guide/sorgente-polimorfa.md) §4 e §6 lo dice in chiaro («non
    canonicalizzare a un'unica chiave»), e il brief `work-done/brief-db-guard-sorgente-polimorfa` §2a
    aveva già scartato l'alternativa. Tid l'ha fermata: è una scelta discussa più volte, ed è (b).
  * Scartata anche (b2), rinominare la colonna delle entità: sposta lavoro su backend e frontend per una
    questione di nome già coperta dalla documentazione. Il `20261019-16` non serve.
* **I nomi: ✅ `DISTINTA_INCASSO` ed `EMAIL`**, come scritti nel lotto 0.
  * `DISTINTA_INCASSO` e non `DISTINTA`: la regola `<DOCUMENTO>_<CICLO>` di G-2. La distinta dei
    fornitori, quando esisterà, sarà `DISTINTA_PAGAMENTO`;
  * `EMAIL` e non `EMAIL_BOZZA`: la riga di `config.email_outbox` è l'email in ogni stato, e la bozza è
    uno stato.

### 8.4 Ricaduta sul frontend (stesso giro)

`scripts/check_i18n_keys.py` legge la colonna `etichetta_key` di `tipi_entita.csv`: senza le chiavi nei
locales la CI è rossa. Le 25 chiavi da seminare in `it.json` ed `en.json`, sotto `config.tipi_entita`:
`attivita`, `attivita_consumi`, `reso_vendita`, `preventivo_riga`, `contratto_riga`,
`ordine_vendita_riga`, `ddt_vendita_riga`, `fattura_riga`, `reso_vendita_riga`,
`ddt_vendita_prelievo`, `reso_vendita_rientro`, `ordine_acquisto`, `ddt_acquisto`, `inventario`,
`inventario_riga`, `rettifica`, `rettifica_riga`, `trasferimento`, `trasferimento_riga`,
`evento_asset`, `distinta_incasso`, `email`, `articolo_componente`, `asset`, `movimento`.
Il backend non cambia: il lookup dei tipi entità legge il catalogo così com'è.

### 8.5 La prova (2026-10-19, scratch `zeroerp_ruoli`, come owner, in transazione annullata)

* SQL estratto da `-14` e `-15`, poi l'upsert di **tutte** le righe dei due CSV come lo fa il loader
  (nessuna riga rifiutata: nessun mirror è una mina), poi il pgTAP: **9/9**.
* Controprova: senza le righe delle entità il test 1 e il test 8 sono rossi.
* Presidi vicini, prima e dopo, identici: `config/test-costanti-catalogo-citate-dal-codice-v1` 6/6,
  `script/test-giornale-registri-catalogo-v1` 13/13, `dbops/test-automazione-attivo-eccezioni-v1` 8/8,
  `dbops/test-vw-bersagli-non-dichiarati` 4/4. `script/test-vw-giornale-entita` è rosso **già prima**,
  con lo stesso errore di fixture (`p_tipo_doc_fiscale_id obbligatorio`): non viene da qui.
* Cancelli statici verdi: `run_on_change`, `precondition_seed`, `sql_letterali`,
  `ddl_su_trigger_automazione`, `timestamp_senza_fuso`, `v1_congelato`. `check_i18n_keys` rosso per le
  25 chiavi del §8.4.
* Non provato prima dell'apply: il pgTAP **come app** (lo lancia Tid).
* **Dopo l'apply su dbdev (2026-10-19), corsa di Tid come app: test 6 rosso**, per un difetto del
  test e non del lotto. `target_table::text` stampa il `regclass` **senza schema** quando lo schema è
  nel `search_path` di chi legge: come app `email_outbox`, come owner sullo scratch
  `config.email_outbox`. Il test legge ora schema e tabella da `pg_class`/`pg_namespace`, convertiti in
  `text` con `COLLATE "default"`: due `name` composti lasciano indeciso il confronto di `results_eq`.
  Rilanciato come app: **9/9**.

## 9. Lotto 1 — la famiglia delle eccezioni (team DB, 2026-10-19)

Via di Tid il 2026-10-19 («procedi col progressivo successivo»). Numeri `20261019-18` … `-32`. Scritto,
provato in transazione e ✅ **applicato su dbdev il 2026-10-19** (nessuna regressione). ⚠️ Andava applicato **insieme** al giro BE del §9.4: dopo l'apply il
codice `OFFERTA` è rifiutato dalle funzioni della famiglia.

### 9.1 Che cosa contiene

La famiglia dei documenti con eccezioni (§9.8.3 del brief degli articoli ammessi) passa da `OFFERTA` al
codice della sorgente, `OFFERTA_COMMERCIALE`. `CONTRATTO` è già il codice della sorgente.

| ChangeSet | Oggetto | Che cosa |
| --- | --- | --- |
| `-18` | `vendite.fn_documento_listino_operativo` | ramo `OFFERTA_COMMERCIALE`; `p_documento` ancorato (DROP + CREATE) |
| `-19` | `vendite.fn_documento_righe_eccezione` | idem |
| `-20` | `script.fn_check_esclusione_articolo_documento` | firma ancorata (il corpo passa il codice al `-18`) |
| `-21` | `script.fn_check_riga_erogazione` | valori ammessi `OFFERTA_COMMERCIALE`, `CONTRATTO`; firma ancorata |
| `-22` | `script.fn_check_listino_congelabile` | idem, e il ramo dell'offerta; i codici `E_OFFERTA_*` restano |
| `-23` | `vendite.fn_documento_righe_preview` | il ramo dei componenti dell'offerta; firma ancorata |
| `-24` | `vendite.fn_documento_riga_erogazioni` | firma ancorata (passa il codice al `-21`) |
| `-25` | `vendite.fn_offerta_righe_espanse` | chiama il listino operativo con `OFFERTA_COMMERCIALE` |
| `-26` | `vendite.fn_offerta_righe_preview` | chiama la preview comune con `OFFERTA_COMMERCIALE` |
| `-27` | `script.fn_available_actions_offerta` | chiama la check del listino con `OFFERTA_COMMERCIALE` |
| `-28` | `vendite.trgfn_offerte_commerciali_guard_transizione` | idem |
| `-29` | `script.trgfn_righe_guard_erogazione_perimetro` | il commento che elenca i documenti |
| `-30` | i due montaggi del guard dell'erogazione su `vendite.offerte_commerciali_eccezioni` | rimontati con `OFFERTA_COMMERCIALE`, stessa forma (`WHEN` compreso) |
| `-31` | `script.fn_articolo_riga_contesto` (il ponte A-8) | il listino operativo riceve il codice com'è; la chiave `doc_listino` esce dal contesto |
| `-32` | `script.fn_check_articolo_riga_su_contesto` | le due check del listino ricevono il documento del contesto; `v_doc_listino` esce |

pgTAP: nuovo `vendite/test-grammatica-eccezioni-codice-sorgente-v1` (12 test); adeguati
`vendite/test-righe-esclusione-solo-non-si-vende-v1` (test 25, il codice) e
`vendite/offerte_commerciali/test-offerta-emissione-congela-listino-v1` (test 2, la firma).

### 9.2 Le scelte

* **`p_documento` ancorato a `config.sorgenti.codice_interno%TYPE`** (raccomandazione di Tid: `%TYPE` in
  firma, `DECLARE` e `RETURNS TABLE`). Era un `text` nudo «senza colonna-vocabolario»; col lotto 0 la
  colonna c'è. Il tipo passa da `text` a `character varying`, quindi la firma cambia: **DROP + CREATE**
  per le sette funzioni che ricevono `p_documento` (un `CREATE OR REPLACE` avrebbe lasciato due overload).
  Tutte `plpgsql`, nessun dipendente registrato in `pg_depend`; nessun `COST`/`ROWS`/`SET` da ripetere
  (default). Il backend passa il codice come parametro semplice: un `text` si converte da solo.
* **Il ponte A-8 si restringe, non sparisce.** Traduceva per tre lettori (listino operativo, etichetta
  della testata, le due check via `doc_listino`). Dopo il lotto 1 traduce solo verso
  `script.fn_get_stato_testata_documento`, che parla la grammatica delle testate: lo ritira il lotto 2.
  La chiave `doc_listino` del contesto era diventata una copia di `documento` ed esce (regola del 2).
* **Due funzioni parlano per un giro due grammatiche**, dichiarato nei loro changeSet:
  `fn_available_actions_offerta` e `trgfn_offerte_commerciali_guard_transizione` passano ancora `'OFFERTA'`
  a `script.fn_check_indirizzi_documento_cliente` (grammatica delle testate, lotto 2).
* **I COMMENT** delle funzioni sono storie: non si riscrivono, prendono in coda una nota di revisione
  che dice il codice di oggi.

### 9.3 Fuori dal lotto 1 (e perché)

* `script.trgfn_righe_default_erogazione_da_articolo` (nel censimento del §9.8.3): non nomina il documento.
* I montaggi del contratto (`'CONTRATTO'`): già il codice della sorgente.
* Tutto ciò che parla la grammatica delle testate (`fn_get_stato_testata_documento`,
  `fn_check_indirizzi_documento_cliente`, lock, indirizzi, `_indirizzi_documento = "OFFERTA"` nel
  repository): lotto 2. Le note (`target_tipo = 'OFFERTA'`): lotto 3.

### 9.4 Richiesta al backend (stesso apply)

| Dove | Oggi | Dopo |
| --- | --- | --- |
| `vendite/db/_documento_eccezioni_repo.py:39` | `DocumentoEccezioni = Literal["CONTRATTO", "OFFERTA"]` | i codici delle sorgenti: `SORGENTE_CONTRATTO`, `SORGENTE_OFFERTA_COMMERCIALE` di `apps/config/sorgenti.py` (anche nel commento di testa, riga 15) |
| `vendite/services/offerte_service.py:1259` | `list_erogazioni_riga("OFFERTA", …)` | `SORGENTE_OFFERTA_COMMERCIALE` |
| `vendite/services/offerte_service.py:1678` | `listino_versione_operativa("OFFERTA", …)` | `SORGENTE_OFFERTA_COMMERCIALE` |
| `vendite/services/contratti_service.py` | `"CONTRATTO"` | invariato nel valore; `SORGENTE_CONTRATTO` se si vuole la costante |
| `vendite/tests/api/test_riga_erogazioni_api.py` | `"OFFERTA"` | da adeguare |

Restano come sono (lotti 2 e 3): `offerte_repository._indirizzi_documento = "OFFERTA"`, `note_views`
(`target_tipo="OFFERTA"`), `_annullo_con_legami.py`. Le API non cambiano forma: nessuna risposta porta il
selettore.

### 9.5 La prova (2026-10-19, scratch `zeroerp_ruoli`, come owner, in transazione annullata)

* **Censimento dal catalogo vivo** (`pg_proc.prosrc` di dbdev), non solo dalla doc: i chiamanti delle sette
  funzioni sono quelli del §9.1, più `vendite.trgfn_contratti_freeze_listino_versione`,
  `script.fn_available_actions_contratto` e `vendite.fn_contratto_righe_preview` (passano `CONTRATTO`:
  invariati) e `script.trgfn_righe_default_erogazione_da_articolo` (solo un commento).
  `script.trgfn_righe_guard_aggiunta_fuori_listino`, nominato in un COMMENT, non esiste più.
* SQL estratto dei 15 changeSet: applicato senza errori; una sola firma per ciascuna delle sette, primo
  argomento `character varying`; `plpgsql_check` a zero errori sulle dodici funzioni toccate.
* **48 pgTAP** (ogni file che nomina un oggetto del lotto, più `script/test-catalogo-messaggi-errore-completo`
  e `dbops/test-riferimenti-morti-v1`), prima e dopo: **identici**. Il nuovo
  `vendite/test-grammatica-eccezioni-codice-sorgente-v1`: **12/12**.
* Rossi **già prima**, con gli stessi test (da owner sullo scratch, non dal lotto):
  `script/test-capability-annulla-aspetto-e-stato-leggibile-v1` (2, 4, 8),
  `vendite/test-annullo-documento-con-legami-v1` (27), `vendite/test-fn-contratto-righe-preview-nuovi-campi-v1`
  (2, fixture), `vendite/test-offerta-righe-espanse` (6, 7, 8).
* Cancelli statici verdi (`run_on_change`, `precondition_seed`, `sql_letterali`,
  `ddl_su_trigger_automazione`, `timestamp_senza_fuso`, `v1_congelato`, `check_i18n_keys`).
* Non provato prima dell'apply: i pgTAP **come app** (li lancia Tid) e il giro BE del §9.4.
* **Dopo l'apply su dbdev (2026-10-19), corsa di Tid come app: nessuna regressione.** Resta il giro BE
  del §9.4: fino alla sua consegna, sul dev, le chiamate del backend con `OFFERTA` sono rifiutate.

### 9.6 Il giro BE (sessione BE, 2026-10-19)

* `DocumentoEccezioni = Literal["CONTRATTO", "OFFERTA_COMMERCIALE"]`; `offerte_service` e
  `contratti_service` passano `SORGENTE_OFFERTA_COMMERCIALE` e `SORGENTE_CONTRATTO` di `apps.config.sorgenti`;
  il test delle erogazioni dell'offerta segue.
* ⭐ Le costanti di `apps/config/sorgenti.py` sono ora **`Final`**: mypy le legge come letterali e le
  confronta col `Literal` della firma. Controprova: `SORGENTE_PREVENTIVO` e `'OFFERTA'` passati al
  repository sono errori di tipo; prima erano `str` e passavano.
* ⚠️ `_approvazioni_prezzo_constants` aveva un `SORGENTE_CONTRATTO = "contratto"` (il `meta` della
  pratica, §7.8): stesso nome, altro valore, e in un modulo che importava i due vinceva l'ultimo import in
  silenzio. Ora `META_SORGENTE_*` (sotto); i valori minuscoli si ritirano col lotto delle approvazioni di
  prezzo (§7.9, in coda).
* Prova: mypy a cricchetto pulito; 4291 test Django e 686 test FE verdi, build FE; chiamata **reale** su dbdev di
  `listino_versione_operativa` e `list_erogazioni_riga`: `OFFERTA_COMMERCIALE` e `CONTRATTO` passano,
  `OFFERTA` è rifiutato («Tipo documento OFFERTA sconosciuto»). Worker gunicorn del dev ricaricati.
* Le API non cambiano forma: il frontend non ha lavoro.
* **Revisione dello stesso giro.** I `SORGENTE_*` minuscoli del meta della pratica si chiamano ora
  `META_SORGENTE_*` (solo il nome Python: i valori scritti nei dati restano, li migra il lotto delle
  approvazioni), e `test_sorgenti_seed` ha un 4° test contro lo stesso nome con un altro valore. Lato FE:
  tre dialog di emissione e tre liste scrivevano a mano il codice sorgente invece di usare
  `SORGENTE_CODES`, e la chiave `SORGENTE_CODES.DDT` diventa `DDT_VENDITA` (la chiave è il codice);
  presidio `documenti/constants.spec.js`.

## 10. Lotto 2 — il piano (team DB, 2026-10-19)

### 10.1 Il perimetro misurato (catalogo vivo di dbdev, 2026-10-19; struttura, non popolazione)

* **42 funzioni** scrivono un codice corto (`DDT`, `ORDINE`, `OFFERTA`, `RESO`, `EMAIL_BOZZA`) come
  letterale fuori dai commenti: i lettori della grammatica delle testate (§7.3), i verbi di annullo e del
  reso, i generatori di bolla, i guard di bolla, ordine e reso, i numeratori, i lettori delle note, un
  builder pgTAP.
* **18 funzioni trigger** portano codici corti negli argomenti, per **76 montaggi**. Il lock delle righe
  fuori bozza da solo ne ha 22, quello delle testate 6, i due degli indirizzi 10, l'annullo con legami 5.
  Ogni montaggio si cambia solo smontando e rimontando.
* Dentro questo perimetro stanno pezzi che le decisioni hanno messo in **sedi diverse**: le note
  (`trgfn_note_validate_generic`, `fn_scope_note_*`) sono del **lotto 3**; i numeratori sono di **G-5**;
  `trgfn_tipi_indirizzi_only_allowed` e `config.sorgenti.area` di **G-6**; `documento_origine_tipo` e
  `destinazione_tipo` di **V7** (G-3); `segment_key` di **G-8**.
* Lato backend: il mixin degli indirizzi dei cinque repository, `_annullo_con_legami.py` (le due
  traduzioni), `_iva_contesto_documento.py` (le `choices` di un endpoint), il `contesto` della situazione
  merce, `ordini_service` (`documento_origine.tipo` nella risposta): tre risposte API toccano il frontend.

Messo tutto in un giro sarebbero un centinaio di changeSet e tre risposte API in un solo apply, coordinato
con BE e FE. G-4 chiede che ogni lotto sia chiuso in sé: un lotto così grande non lo è nei fatti.

### 10.2 La proposta: cinque sotto-giri, ciascuno chiuso (L2-1, per Tid)

| Sotto-giro | Che cosa | ChangeSet (stima) | Backend / frontend |
| --- | --- | --- | --- |
| **2a. Testate** | la grammatica delle testate passa ai codici delle sorgenti (`DDT_VENDITA`, `ORDINE_VENDITA`, `OFFERTA_COMMERCIALE`, `RESO_VENDITA`, `EMAIL`; gli altri sono già uguali): i lettori (`fn_get_stato_testata_documento` e i fratelli), i verbi e i guard coi letterali, i montaggi dei trigger. **Muore il ponte** di `fn_articolo_riga_contesto` | ~55 (circa 35 funzioni, una per changeSet, più un changeSet di rimontaggio per funzione trigger) | il mixin indirizzi passa un codice solo per il documento; `_annullo_con_legami.py` perde le due traduzioni |
| **2b. Origine e destinazione** (V7) | `vendite.ordini.documento_origine_tipo` e `config.nature_vendita.destinazione_tipo`: dal `CHECK` alla FK verso `config.sorgenti`; i dati di oggi convertiti; l'`origine` di `fn_documento_legami` | ~6 + CSV | `ordini_service` scrive `OFFERTA_COMMERCIALE`; **risposta API** `documento_origine.tipo` (FE) |
| **2c. Famiglie** (G-5) | `vendite.famiglie_documento` con identità FK verso le sorgenti, `schema_tabella`/`nome_tabella` ritirati, numeratori e `fn_crea_famiglia_documento` | ~10 + CSV | da censire nel giro (le famiglie si gestiscono dal CRUD) |
| **2d. Aree** (G-6) | `config.tipi_indirizzi_allowed.ambito` → codice della sorgente con FK; `config.sorgenti.area` ritirata e `in_dashboard` esplicita; viste `vw_dash_*` | ~10 + CSV | mixin indirizzi (l'ambito), costanti `DASH_*_AREE`; **dashboard** (FE) |
| **2e. Chiavi del push** (G-8) | il builder unico di `segment_key`, «è merce?» da `sorgente_tipo_id`, le copie a mano ritirate | ~8 | SQL una tantum sulle chiavi dei database di sviluppo, **insieme all'apply** |

Ordine proposto: **2a** per primo (il nucleo, e il ponte che muore); poi 2b, 2c, 2d, 2e in qualunque
ordine: dipendono solo dal lotto 0. Il lotto 3 (note) resta anticipabile, anche fra un sotto-giro e
l'altro. Ogni sotto-giro chiude con la sua consegna BE/FE, come il lotto 1.

Le **risposte API** che portano un codice di tipo documento (`choices` dell'IVA, `contesto` della
situazione merce) cambiano nel sotto-giro che cambia il loro produttore: 2a per la situazione merce e
per l'IVA, che usano i codici delle testate.

### 10.3 La decisione (Tid, 2026-10-19)

✅ **L2-1: sì ai cinque sotto-giri, si parte dal 2a** («ok parti come da tuo piano»), con `%TYPE` in firma,
`DECLARE` e `RETURNS TABLE`, e la numerazione che oltre `-99` passa al `20261020-01`.

## 11. Lotto 2a — le testate (team DB, 2026-10-19)

Numeri `20261019-40` … `-79`. Scritto, provato in transazione e ✅ **applicato su dbdev il 2026-10-19** (pgTAP
verdi come app). ⚠️ Andava applicato **insieme**
al giro BE del §11.4: dopo l'apply i lettori delle testate rifiutano `DDT`, `ORDINE`, `OFFERTA`, `RESO`,
`EMAIL_BOZZA`.

### 11.1 Che cosa contiene

La grammatica delle testate (V3) passa ai codici delle sorgenti: `DDT` → `DDT_VENDITA`, `ORDINE` →
`ORDINE_VENDITA`, `OFFERTA` → `OFFERTA_COMMERCIALE`, `RESO` → `RESO_VENDITA`, `EMAIL_BOZZA` → `EMAIL`.

| ChangeSet | Che cosa |
| --- | --- |
| `-40` … `-52` | **i lettori**, `DROP` + `CREATE` con `p_documento` ancorato a `config.sorgenti.codice_interno%TYPE`: `script.fn_get_stato_testata_documento`, `fn_get_testata_id_di_riga`, `fn_get_cliente_testata_documento`, `fn_doc_indirizzi_sede`, `fn_doc_date_consegna_anteriori`, `fn_check_listino_cambiabile`, `fn_check_indirizzi_documento_cliente`; `vendite.fn_doc_indirizzo_default`, `fn_doc_fornitura_sede`, `fn_doc_fornitura_da_anagrafica`, `fn_doc_porta_ritiro_ammette`, `fn_documento_legami`, `fn_documento_ritira_legami` |
| `-53` | **muore il ponte A-8**: `script.fn_articolo_riga_contesto` chiede l'etichetta col codice com'è |
| `-54` … `-67` | **i chiamanti coi letterali** (`CREATE OR REPLACE`): capability dell'offerta, check della bolla e dell'ordine, accredito del reso, i verbi di annullo di bolla e ordine, i guard di transizione dell'offerta, dell'allegato email, dei legami di bolla, della riga evasa, delle cancellazioni |
| `-68` … `-71` | funzioni trigger col commento o i valori ammessi da aggiornare, **più i loro montaggi**: annullo con legami (2), lock delle righe fuori bozza (15), i due guard del listino (2 + 1) |
| `-72` … `-79` | **solo i montaggi**: lock della testata (4), indirizzi (3 + 2), emittente (1), fornitura (1 + 1), date di consegna (1 + 1) |

Montaggi rimontati: **34**, rigenerati da `pg_get_triggerdef` di dbdev col solo primo argomento cambiato.
Quelli con `CONTRATTO`, `PREVENTIVO`, `COMMESSA`, `FATTURA` non cambiano e non si toccano.

### 11.2 Le scelte

* **Proprietà ripetute dal catalogo vivo**: volatilità, `SECURITY DEFINER`, `SET search_path`. Un
  `CREATE OR REPLACE` senza `SET` avrebbe tolto il `search_path` alle `DEFINER`.
* **Postura**: `fn_documento_legami` e `fn_documento_ritira_legami` restano senza `EXECUTE` a PUBLIC (il
  `DROP` + `CREATE` lo ridarebbe): `REVOKE` nello stesso changeSet, come nei `20261011-77`/`-84`.
* **La GUC del ritiro** (`zeroerp.doc_ritira_legami = '<DOCUMENTO>:<id>'`): scrittore
  (`fn_documento_ritira_legami`) e lettore (`fn_doc_porta_ritiro_ammette`) cambiano insieme; dentro il
  ritiro sparisce la traduzione `DDT` → `DDT_VENDITA` verso `config.sorgenti`.
* **`meta.accredito_da`** della riga di commessa scrive `RESO_VENDITA`: nessun lettore (cercato in DB,
  backend, frontend, pgTAP); le righe già scritte portano `RESO`.
* **Il ponte A-8 non c'è più.** L'etichetta di ripiego, quando la testata non si vede, è il codice in
  chiaro («Offerta Commerciale #id»).

### 11.3 Restano ad altri giri (e perché) — i codici corti che il 2a lascia

| Dove | Codice | Giro |
| --- | --- | --- |
| `vendite.fn_documento_legami` (colonna `origine`), `fn_documento_ritira_legami` (`l.origine IN (…)`), `vendite.ordini.documento_origine_tipo`, `fn_offerta_documenti_vivi`, `vw_ordini_lista`, `vw_dash_fatturazione_offerte` | `ORDINE`, `RESO`, `OFFERTA` | **2b** (V7) |
| `config.nature_vendita.destinazione_tipo` e i suoi lettori (`trgfn_articoli_guard_onere_natura`, `fn_check_articolo_riga_su_contesto`, le viste di smistamento del preventivo) | `ORDINE` | **2b** |
| numeratori (`p_famiglia_documento => 'DDT'`, `'ORDINE'`, `'RESO'`) | | **2c** (G-5) |
| ambito degli indirizzi (`fn_indirizzi_obbligatori_mancanti('DDT', …)`, `a.ambito = 'DDT'`, la quinta colonna di `fn_doc_indirizzi_sede`, `trgfn_tipi_indirizzi_only_allowed`), `area` delle viste `vw_dash_*` | | **2d** (G-6) |
| note (`trgfn_note_validate_generic`, `fn_scope_note_*`) | | **lotto 3** |
| il testo dei messaggi per l'operatore (`'DDT'` come parola nei guard di bolla e reso) | | resta: non è un codice |

### 11.4 Richiesta al backend (stesso apply)

| Dove | Oggi | Dopo |
| --- | --- | --- |
| `_indirizzi_documento` dei cinque repository (`ordini`, `offerte`, `ddt`; `preventivi` e `contratti` già uguali) | `"ORDINE"`, `"OFFERTA"`, `"DDT"` | `SORGENTE_ORDINE_VENDITA`, `SORGENTE_OFFERTA_COMMERCIALE`, `SORGENTE_DDT_VENDITA` (`apps/config/sorgenti.py`). `_indirizzi_ambito` resta fino al 2d |
| `_annullo_con_legami.py`: `DOCUMENTO_DDT`, `DOCUMENTO_ORDINE` passati a `vendite.fn_documento_legami` | `"DDT"`, `"ORDINE"` | i codici delle sorgenti; **la traduzione V3 → V1** (righe 63-70) **si ritira**. La traduzione dell'`origine` (righe 77-86) resta fino al 2b |
| `_iva_contesto_documento.py`: loader e `TIPI_DOCUMENTO_AMMESSI` (le `choices` di `views_iva.py`) | `"ORDINE"`, `"DDT"` | `ORDINE_VENDITA`, `DDT_VENDITA`. ⚠️ **cambia una risposta API** (FE) |
| `vendite_service.py:2577`, il `contesto` della situazione merce | `"ORDINE"`, `"DDT"` | `ORDINE_VENDITA`, `DDT_VENDITA`. ⚠️ **cambia una risposta API** (FE) |
| test Django e smoke che passano i codici corti a questi punti | | da adeguare |

Il frontend: le due risposte API sopra (le chiavi di traduzione e i confronti che leggono quei valori).

### 11.5 La prova (2026-10-19, scratch `zeroerp_ruoli`, come owner, in transazione annullata)

* **Censimento dal catalogo vivo** di dbdev: 55 funzioni che scrivono un codice corto o portano montaggi
  coi codici corti, più le tre che ricevono `p_documento` e lo passano
  (`fn_check_indirizzi_documento_cliente`, `fn_doc_indirizzo_default`, `fn_doc_fornitura_da_anagrafica`).
  Ogni letterale classificato (124 righe): nel 2a la grammatica delle testate; il resto nel §11.3.
  Nessun seed, nessun `CHECK` e nessuna vista del 2a (quelli trovati sono di 2b, 2d, lotto 3).
* SQL estratto dei 40 changeSet: applicato senza errori. Le 13 funzioni ricreate hanno una sola firma,
  `character varying`; **i `RETURNS` di tutte e 40 identici a quelli vivi** (`pg_get_function_result`
  prima e dopo); `plpgsql_check` a zero errori; `search_path`, `SECURITY DEFINER` e postura (`EXECUTE`
  revocato a PUBLIC per i due dei legami) come prima; nessun montaggio col primo argomento corto, fuori da
  note e ambito.
* ⚠️ **Due difetti trovati dalla prova e corretti prima della consegna**: il `RETURNS` di
  `fn_get_stato_testata_documento` era preso da uno YAML vecchio (mancava `nata_in_transazione`, aggiunta
  l'11-10: il `DROP` + `CREATE` non l'avrebbe segnalato, l'ha visto `plpgsql_check`); il `REVOKE` a PUBLIC
  non usciva perché il generatore cercava `=X/` e lo trovava dentro `zeroerp_owner=X/`.
* **113 pgTAP** (ogni file che nomina una funzione, un montaggio o un codice corto del 2a, più i presidi
  trasversali), prima e dopo. **13 regressioni, tutte dei test** che passavano i codici corti (le chiamate
  dirette ai lettori e ai legami, la GUC del ritiro, i montaggi attesi del lock, la firma inchiodata di
  `fn_get_testata_id_di_riga`): adeguati, ciascuno con la nota di revisione in testa. Dopo: **esiti identici
  a prima** in tutti i 113. Il test 12 del pgTAP del lotto 1 passa all'etichetta senza ponte.
* Rossi **già prima**, uguali dopo (fixture o scope da owner, non dal lotto): fra gli altri
  `script/test-fn-available-actions-ddt-reason-catch-all-v1` (16), `vendite/test-annullo-documento-con-legami-v1`
  (27), `vendite/test-fn-list-ddt-da-pushare-v1`, `test-fn-resolve-prezzo-listino-v2-v1`,
  `test-vw-dash-fatturazione-v1`, `test-vw-preventivi-smistamento-v1`.
* Cancelli statici verdi.
* Non provato prima dell'apply: i pgTAP **come app** (li lancia Tid) e il giro BE/FE del §11.4.
* **Dopo l'apply su dbdev (2026-10-19), corsa di Tid come app**: `script/test-capability-motivi-e-nessuna-azione-v1`
  rosso, perché passava `'ORDINE'`/`'DDT'` a `fn_documento_legami`. Era nel censimento ma non fra le
  regressioni della prova: sullo scratch, da owner, era rosso già prima per la fixture, e il confronto
  prima/dopo non poteva vederlo. Adeguato, 13/13 come app. Ricercate di nuovo in tutti i pgTAP e nel
  backend le chiamate coi codici corti, anche su più righe: nessuna (resta, voluta, la chiamata con
  `'ORDINE'` che `test-testata-dopo-emissione-rdb-v1` usa per provare il rifiuto).

### 11.6 Il giro BE/FE (sessione BE/FE, 2026-10-19)

* **Indirizzi**: `_indirizzi_documento` dei cinque repository è la costante `SORGENTE_*` di
  `apps/config/sorgenti.py` (anche per preventivo e contratto, già uguali nel valore). `_indirizzi_ambito`
  resta fino al 2d.
* **Annullo con legami**: le costanti `DOCUMENTO_*` di `_annullo_con_legami.py` sono **ritirate**, non
  ridefinite: coi codici delle sorgenti sarebbero state un secondo nome dello stesso codice. I cinque service
  passano `SORGENTE_*`; la traduzione verso il tipo del lineage (`_TIPO_LINEAGE_DEL_DOCUMENTO`) è ritirata,
  resta quella dell'`origine` (`_TIPO_LINEAGE_DELL_ORIGINE`) fino al 2b. Il campo `documento` della risposta
  dei legami porta ora il codice della sorgente: il frontend legge solo `COMMESSA`, invariato.
* **IVA**: `TIPI_DOCUMENTO_AMMESSI` e i loader sono `PREVENTIVO`, `ORDINE_VENDITA`, `DDT_VENDITA`; i tre
  `*RigaForm.vue` passano `SORGENTE_CODES.*`. Presidio nuovo in `test_iva_contesto_documento` (12): i corti
  sono un rifiuto col campo `documento_tipo`.
* **Situazione merce**: `contesto` vale `ORDINE_VENDITA` / `DDT_VENDITA`; lato FE `CONTESTO_MERCE` legge i
  valori da `SORGENTE_CODES`, i consumatori non cambiano.
* `apps/config/sorgenti.py`: il commento non mette più il `p_documento` di `fn_documento_legami` fra i
  vocabolari diversi (lo è l'`origine`, fino al 2b), e dice che la grammatica delle testate è questa.
* Test adeguati: `test_annullo_con_legami`, `test_situazione_merce_service`, `test_ddt_service` e
  `test_ordini_service` (le chiamate attese al BB), `test_indirizzi_seguono_cliente_db` (la sonda della firma:
  `character varying`, non più `text`), lo spec del dialog dei legami. Doc: `api_iva_resolve.md`,
  `api_situazione_merce.md`, voce `legami_del_documento` del catalogo BB. Gli smoke non passano codici del 2a
  (`smoke-test-ordini-giro-commessa.sh` legge l'`origine`, del 2b).
* Prova: 2516 test Django di `vendite` e `config`, 207 e2e di `vendite/tests/db` su dbdev (nessuno saltato),
  mypy a cricchetto pulito, 136 test FE di `vendite` e `documenti`, lint, `npm run guards`, build. Chiamata
  **reale** su dbdev, in transazione annullata: `fn_documento_legami` e `fn_doc_indirizzo_default` accettano i
  cinque codici delle sorgenti, e rifiutano `DDT`, `ORDINE`, `OFFERTA`. ⚠️ ruff non è installato in locale: lo
  vede il pre-commit. Worker gunicorn del dev ricaricati.
* Da vedere a video (Tid): pannello indirizzi alla creazione di ordine, offerta e bolla; finestra dell'annullo
  con legami di bolla e ordine; IVA proposta nel form di riga di preventivo, ordine e bolla; pannello situazione
  merce dall'ordine e dalla bolla (il conto deve uscire: con un `contesto` non riconosciuto il FE conta zero).

#### 11.6.1 Revisione critica dello stesso giro (2026-10-19)

* 🔴 **Un punto che il §11.4 non elencava**: `richiedi_righe_in_bozza` (`_righe_bozza_guard.py`), il pre-check
  Python di `E_RIGA_DOC_NON_BOZZA`, scrive nel `context` «le chiavi e i valori del trigger»
  `trgfn_doc_righe_lock_fuori_bozza`. Ricavava `documento` dal maiuscolo della parola dell'etichetta
  («Ordine» → `ORDINE`); dopo il `20261019-69` il trigger scrive `ORDINE_VENDITA`, e lo stesso rifiuto
  arrivava al diario in due lingue. Ora il chiamante passa il codice della sorgente (`SORGENTE_*`, tipo
  `DocumentoRighe`), che va nel contesto com'è; la parola dell'etichetta è `PAROLA_ETICHETTA`, una tabella
  sola al posto dei 17 letterali nei chiamanti (DDT, ordini, preventivi, contratti, resi).
* 🔴 **Divergenza già esistente, corretta nello stesso modulo**: il DB scrive «Preventivo <numero> rev. <rev>»,
  il Python scriveva «Preventivo <numero>». Ora porta la revisione; `load_componente_with_scope` del
  preventivo legge anche `p.rev`. L'etichetta si compone solo sul ramo del rifiuto (in bozza non serve).
* `legami_del_documento(documento: DocumentoLegami, …)`: ritirate le `DOCUMENTO_*`, l'elenco dei documenti
  che il lettore conosce resta come tipo. Controprova: `"DDT"`, `SORGENTE_FATTURA` e `"Ordine"` passati ai due
  BB sono errori di mypy.
* IVA: `TIPI_DOCUMENTO_AMMESSI` è `tuple(_LOADER)`; i tre codici erano scritti due volte (chiavi del registro e
  whitelist). Il registro è una mappa costante di loader con import locali; ritirato `_registry()`.
* Due fixture di test portavano ancora `documento: "DDT"` (`test_ddt_service`, `test_ddt_api`).
* Presidi nuovi in `test_righe_bozza_guard`: documento fuori catalogo, revisione del preventivo,
  `PAROLA_ETICHETTA` ⇔ `DocumentoRighe`, e (e2e) ogni `DocumentoRighe` accettato da
  `script.fn_get_stato_testata_documento` sul DB vero.
* Prova finale sullo stato committato: 2521 test di `vendite` e `config`, 220 e2e su dbdev (compresi i tre del
  guard), mypy a cricchetto pulito; 136 test FE di `vendite` e `documenti`, lint. Worker gunicorn ricaricati.
* ✅ **La copia dell'etichetta ha il suo presidio** (stesso giorno, ok Tid): `RigheBozzaGuardEtichettaE2ETests`
  in `test_righe_bozza_guard` costruisce una testata per ciascun `DocumentoRighe` (ordine e preventivo dagli
  stampi `dbops.fn_pgtap_crea_*`, DDT dal service, contratto con un INSERT come nei pgTAP, reso sopra una
  bolla consegnata) e confronta la frase del guard con quella composta sull'`etichetta` di
  `script.fn_get_stato_testata_documento` per la stessa riga. Un documento nel `Literal` senza stampo è
  rosso, non saltato. Prove di mutazione: una parola cambiata («Ordine» → «Ordini», «Reso» → «Resi»), la
  revisione cambiata, il `numero` ignorato: ciascuna rossa (il ramo col numero lo coprono ordine, preventivo
  e contratto; DDT e reso nascono senza numero e provano il ripiego `#id`).
* Regola del 2: la bolla consegnata dei test sul DB è lo stampo `vendite/tests/db/_ddt_consegnato.py`
  (`crea_ddt_consegnato`, voce nel catalogo BB backend); `test_resi_create_db` lo usa e la sua copia è
  ritirata. ⚠️ Lascia tabelle temporanee: una chiamata per transazione.
* Nello stesso giro: la descrizione OpenAPI di `contesto` (`situazione_merce_views.py`) dice i codici delle
  sorgenti; lato FE `DOCUMENTO_LEGAMI` è ritirato, il dialog dei legami confronta `SORGENTE_CODES.COMMESSA`
  (aggiunto a `SORGENTE_CODES`, con la voce del catalogo BB frontend).
* ⚠️ **Limite dichiarato**: il presidio legge la testata dalla tabella, non dai lettori del backend. Prova
  che l'etichetta si compone come nel DB, non che ogni lettura usata dai service porti `numero` e `rev`. Una
  lettura del preventivo senza `rev` è un `KeyError` (rumoroso); una lettura senza `numero` ripiegherebbe su
  `#id` senza errore.

## 12. Lotto 2b — origine e destinazione (team DB, 2026-10-19)

Numeri `20261019-87` … `-99`. Scritto, provato in transazione e ✅ **applicato su dbdev il 2026-10-19** (pgTAP
verdi come app, §12.6). Il giro BE/FE del §12.4 è ✅ fatto lo stesso giorno (§12.7).

### 12.1 Che cosa contiene

Il vocabolario V7 passa ai codici di `config.sorgenti`: l'origine dell'ordine (`OFFERTA` →
`OFFERTA_COMMERCIALE`), la destinazione della natura (`ORDINE` → `ORDINE_VENDITA`), l'origine dei legami
(`ORDINE` → `ORDINE_VENDITA`, `RESO` → `RESO_VENDITA`, `OFFERTA` → `OFFERTA_COMMERCIALE`; nel ramo della
commessa anche `DDT` → `DDT_VENDITA` e `CONSUMI` → `ATTIVITA_CONSUMI`, che il §11.3 non elencava).

| ChangeSet | Che cosa |
| --- | --- |
| `-87` (`00_schema`) | `vendite.ordini.documento_origine_tipo` convertita sul posto: `varchar(50)`, FK verso `config.sorgenti(codice_interno)` al posto del `CHECK`, `uq_ordini_v_documento_origine_offerta` col predicato nuovo. Prima toglie ciò che legge la colonna: la funzione lineage (BEGIN ATOMIC), la sua vista, `vw_ordini_lista`, la catena della dashboard |
| `-88` (`00_schema`) | `config.nature_vendita.destinazione_tipo`, stessa forma; toglie le quattro viste dello smistamento, `vw_dash_fatturazione_preventivi`, `catalogo.vw_articoli_dettaglio` |
| `-89` | `vendite.fn_documento_lineage_archi` ricreata, l'origine dell'offerta col codice nuovo (tre rami) |
| `-90` … `-94` | le 14 viste ricreate: `vw_documento_lineage_archi`, `vw_ordini_lista`, smistamento (4), dashboard (7), `vw_articoli_dettaglio`. Cambiano i letterali in quattro; le altre tornano identiche |
| `-95` | `vendite.fn_documento_legami`: `origine` è il codice della sorgente, ancorata in `RETURNS TABLE` (DROP + CREATE) |
| `-96` … `-99` | i lettori coi letterali: `fn_documento_ritira_legami`, `fn_offerta_documenti_vivi`, `catalogo.trgfn_articoli_guard_onere_natura`, `script.fn_check_articolo_riga_su_contesto` |

CSV: `nature_vendita.csv` (`MERCE` → `ORDINE_VENDITA`; il seed è `runOnChange`), e il testo tecnico di tre
codici in `codici_errore.csv`/`messaggi_errore.csv`.

pgTAP: nuovo `vendite/test-grammatica-origine-destinazione-sorgenti-v1` (12), adeguati 15 file (nota di
revisione in testa a ciascuno).

### 12.2 Le scelte

* **Conversione sul posto** (`ALTER COLUMN … TYPE … USING CASE`): DDL, nessun trigger di riga, nessun momento
  con due vocabolari. Il prezzo è il giro delle dipendenze: ogni vista che legge le due colonne, anche a
  cascata, si toglie in `00_schema` e torna in `20_code`, nella stessa corsa (forma del `20261001-42`). `DROP`
  senza `CASCADE`: un dipendente nuovo e non censito ferma il migrate invece di sparire.
* **Le FK in `00_schema`**, come quella del lotto 0 (`20261019-15`): da zero le tabelle sono vuote, e il
  mirror delle sorgenti gira prima del seed delle nature.
* **La FK al posto del `CHECK` (G-3).** Il `CHECK` diceva anche *quali* sorgenti possono essere un'origine (due)
  o una destinazione (tre); la FK dice solo che il codice esiste. Chi sceglie fra le sorgenti sono gli
  scrittori (`fn_push_preventivo_a_ordine`, il backend dell'ordine da offerta, il CSV delle nature) e i
  lettori, che riconoscono i loro codici. È G-3 così com'è stata decisa: un tipo nuovo è una riga del CSV,
  non un `CHECK` da riscrivere.
* **L'automazione ATTIVO non lega queste FK**: salta le colonne che non finiscono in `_id`
  (`ATTIVO_SKIP_FK_NO_ID`). Provato sullo scratch: nessun trigger nuovo su ordini, nature, sorgenti. La FK
  lega il nome, non l'accensione, come quella del lotto 0.
* **`ONERE` resta.** È l'origine di una riga di commessa senza sorgente per progetto
  (`chk_commesse_attivita_senza_sorgente_onere_rettifica`): non un codice corto da migrare, ma l'assenza
  dell'origine detta con un nome. `origine` è quindi «il codice della sorgente, oppure `ONERE`», ed è scritto
  nel commento del corpo e nel COMMENT.
* **`%TYPE`** in firma, `DECLARE` e `RETURNS TABLE` dove c'è una colonna: `origine` su
  `config.sorgenti.codice_interno`, `p_offerta_id` e `tipo` di `fn_offerta_documenti_vivi` (prima nudi),
  `v_uid` e `v_sorgente_uid` su `commesse_attivita.sorgente_uid`. Restano nudi, col motivo scritto accanto, i
  campi polimorfi (righe e testate di tabelle diverse), i vocabolari propri di una funzione (`natura`), i
  testi liberi, gli array (`%TYPE[]` non esiste).
* **Corpi dal catalogo vivo** di dbdev; la funzione lineage dal `20261011-92`, verificato uguale al vivo.

### 12.3 Restano ad altri giri — e una lacuna del censimento del 2a

* Numeratori (G-5, 2c), aree e ambito degli indirizzi (G-6, 2d), chiavi del push (G-8, 2e), note (lotto 3):
  come nel §11.3.
* ⚠️ **Il censimento del 2a non vedeva le funzioni `BEGIN ATOMIC`**: il loro corpo non sta in `prosrc`, e la
  ricerca dei letterali leggeva solo quello. Rifatta col testo di `pg_get_functiondef`, ne escono quattro:
  `fn_documento_lineage_archi` (V7, chiusa qui) e tre che non sono del 2a:

  | Funzione | Letterale | Che cos'è |
  | --- | --- | --- |
  | `vendite.fn_ddt_push_diagnosi` | `'RESO'` | lo stato `RESO` della bolla, non un tipo di documento: resta |
  | `vendite.fn_af_merce_per_riga` | `'DDT'` | il prefisso di `segment_key`: **2e** (G-8) |
  | `vendite.fn_partite_merce` | `corsia = 'DDT'`; `origine` `NESSUNA` \| `MULTIPLA` \| `ORDINE` | la corsia viene dal `segment_key` (**2e**); l'`origine`: **correzione decisa da Tid, §12.8** (`ORDINE` → `ORDINE_VENDITA`) |

  Chi censisce i sotto-giri successivi legge `pg_get_functiondef`, non `prosrc`.

### 12.4 Richiesta al backend e al frontend (stesso apply)

| Dove | Oggi | Dopo |
| --- | --- | --- |
| `ordini_service.py:737, 757`: scrive `ordini.documento_origine_tipo` e risponde `documento_origine.tipo` | `"OFFERTA"` | `SORGENTE_OFFERTA_COMMERCIALE`. ⚠️ **Cambia una risposta API** (FE); dopo l'apply `"OFFERTA"` è rifiutato dalla FK |
| `vw_ordini_lista.documento_origine_tipo` (lista ordini, colonna `col_documento_origine`); `ordine_document_context_builder.py:201` | `OFFERTA` | `OFFERTA_COMMERCIALE`: da controllare chi lo traduce a video o in stampa |
| `_annullo_con_legami.py`: `_TIPO_LINEAGE_DELL_ORIGINE` | traduce `ORDINE`, `RESO`, `OFFERTA`, `DDT`… | **si ritira**: `origine` è già il codice della sorgente. Resta da dire quali origini sono documenti da aprire: non `ONERE`, non `ATTIVITA_CONSUMI` (prima `CONSUMI`, fuori dalla mappa) |
| `preventivi_repository.py:1214` (righe dello smistamento, `destinazione_tipo`) | `ORDINE` | `ORDINE_VENDITA`. ⚠️ **Cambia una risposta API** (FE) |
| `catalogo_repository.py:205` (`natura_vendita_destinazione_tipo`) | `ORDINE` | `ORDINE_VENDITA`: da controllare chi lo legge a video |
| FE `constants.js`: `DESTINAZIONE_SMISTAMENTO.ORDINE`, `ORIGINE_LEGAME.RESO` | `'ORDINE'`, `'RESO'` | i codici delle sorgenti (`SORGENTE_CODES`); il routing di «Smista selezionate» confronta la destinazione |
| FE dialog dei legami: il ripiego `vendite.annullo_legami.origine_<origine>` quando l'origine non è un documento da aprire | chiavi dei codici corti (`origine_ordine`, `origine_reso`, `origine_offerta`, `origine_ddt`, `origine_consumi`…) | il vocabolario del lineage, `vendite.lineage.tipo_<sorgente>` (per i consumi `tipo_attivita_consumi`; `ONERE` non è una sorgente e non ha chiave). ⚠️ **Cambia una risposta API** (il campo `origine` dei legami) |
| `error_policies_generated.py` | testo di due codici | si rigenera dal CSV |
| test Django, `smoke-test-ordini-giro-commessa.sh` (legge l'`origine`) | codici corti | da adeguare |

### 12.5 La prova (2026-10-19, scratch `zeroerp_ruoli`, come owner, in transazione annullata)

* **SQL estratto dei 13 changeSet, avanti e indietro**: applicato senza errori, poi i 13 rollback in ordine
  inverso. Fotografia del catalogo (definizioni, `RETURNS`, ACL, COMMENT di viste, colonne, funzioni, indici,
  vincoli; trigger; valori) prima, dopo, e dopo il ritorno:
  * prima → dopo: cambiano **solo** i letterali e le colonne del §12.1, i tipi delle due colonne (e delle
    colonne di vista che le espongono), `origine` di `fn_documento_legami` (`text` → `character varying`),
    i vincoli (`CHECK` → FK), il predicato dell'indice unico, i COMMENT. La funzione lineage dal
    `20261011-92` coincide col corpo vivo a meno del letterale. `ix_ordini_documento_origine`, ricostruito da
    `ALTER TYPE`, conserva il suo COMMENT;
  * prima → ritorno: identici, a meno dell'ordine delle voci nell'ACL della funzione lineage e della forma
    stampata dei due `CHECK` (stessi valori).
* `plpgsql_check` sulle quattro plpgsql: nessun errore; restano i due avvisi di prima (`PERFORM` di
  `fn_log_and_raise_error` in una `STABLE`).
* `dbops.fn_run_automations_attivo('AUTO', ARRAY['vendite','config'], false)` dopo il giro: nessun trigger
  nuovo (§12.2).
* **pgTAP**: 84 file (ogni file che nomina un oggetto, una colonna o un codice del 2b), ciascuno com'è e con
  l'SQL estratto dopo la riga `BEGIN;`. **8 regressioni, tutte dei test**: fixture che scrivono l'origine
  `OFFERTA` (ora rifiutata dalla FK), nature cercate con `destinazione_tipo = 'ORDINE'`, legami letti coi
  codici corti, le asserzioni sul vecchio `CHECK`. Adeguati, insieme ad altri sette file che usavano gli
  stessi codici senza cambiare esito (fra questi `test-fn-genera-ddt-riconsegna-eredita-v1`, che col filtro
  `<> 'ORDINE'` avrebbe preso anche la merce). Dopo: **ognuno dei 15 torna, sul DB del 2b, all'esito che
  aveva sul DB di oggi**, compresi i tre rossi già prima (fixture o scope da owner:
  `test-articolo-usato-struttura-v1` 17, `test-annullo-documento-con-legami-v1` 30,
  `test-vw-preventivi-smistamento-v1` 1). Il test nuovo: 12/12 col 2b, rosso senza.
* Cancelli statici verdi; `guardrail_pgtap_preambolo` era rosso anche per il pgTAP del lotto 1 (mancava
  `SET CONSTRAINTS ALL IMMEDIATE`): corretto, 12/12. Resta rosso per
  `dbops/test-automazioni-guasto-ambiente-rilanciato-v1`, di un altro cantiere.
* Su dbdev, in lettura (2026-10-19): gli ordini hanno origine `OFFERTA`, `PREVENTIVO` o nessuna; le nature
  `ORDINE`, `COMMESSA`, `CONTRATTO`. Sono tutti valori che la conversione conosce: all'apply la FK non trova
  valori fuori dalle sorgenti.
* Non provato prima dell'apply: i pgTAP **come app** (li lancia Tid) e il giro BE/FE del §12.4.

### 12.6 L'apply (Tid, 2026-10-19)

* Applicato su dbdev: i 13 changeSet `20261019-87` … `-99` sono in `databasechangelog`. pgTAP come app: verdi.
* Da qui il DB parla i codici delle sorgenti anche per origine e destinazione. Fino al giro BE/FE del §12.4
  (✅ §12.7, stesso giorno) la creazione di un ordine da offerta (`ordini_service`, `"OFFERTA"`) era rifiutata
  da `fk_ordini_documento_origine_tipo_sorgenti`, e il dialog dei legami e quello dello smistamento ricevevano
  valori che il frontend non riconosceva (`ORIGINE_LEGAME.RESO`, `DESTINAZIONE_SMISTAMENTO.ORDINE`).

### 12.7 Il giro BE/FE (sessione BE/FE, 2026-10-19)

* **Origine dell'ordine da offerta**: `crea_ordine_da_offerta` scrive e risponde `SORGENTE_OFFERTA_COMMERCIALE`
  (`documento_origine.tipo` della risposta API). Il preventivo era già `SORGENTE_PREVENTIVO`.
* **Legami**: `_TIPO_LINEAGE_DELL_ORIGINE` è **ritirata**. Al suo posto `_ORIGINI_DOCUMENTO`, l'elenco delle
  origini che sono un documento da aprire (ordine, reso, preventivo, offerta, commessa, contratto, bolla): per
  queste il tipo del lineage è l'origine stessa. Fuori `ATTIVITA_CONSUMI` e `ONERE`, e ogni sorgente nuova che il
  lettore imparasse a dare finché non si dichiara qui (senza tipo la finestra la nomina, senza link).
* **Smistamento**: il backend passa `destinazione_tipo` com'è (nessun codice nel Python, solo commenti); lato
  FE `DESTINAZIONE_SMISTAMENTO` legge i valori da `SORGENTE_CODES` (`ORDINE_VENDITA`, `COMMESSA`): il routing di
  «Smista selezionate» e il tag della colonna confrontano la costante, i consumatori non cambiano.
* **Dialog dei legami**: `ORIGINE_LEGAME` è **ritirata** (come `DOCUMENTO_LEGAMI` nel 2a); il reso «da
  accreditare» confronta `SORGENTE_CODES.RESO_VENDITA` (aggiunto, con la voce del catalogo BB frontend). Il
  vocabolario di ripiego `vendite.annullo_legami.origine_*` è **ritirato** per intero (revisione dello stesso
  giorno): dal 2b l'origine è un codice di `config.sorgenti`, come il tipo del lineage, e tenere due vocabolari
  della stessa cosa era una seconda copia (regola del 2). Ogni origine si nomina con `lineageDocumentoLabel`; i
  consumi con `vendite.lineage.tipo_attivita_consumi` («Consumi»), spostata lì da `origine_attivita_consumi`. `origine_onere`, aggiunta nello stesso giro, è
  **tolta** nella revisione dello stesso giorno (sotto): i legami `ONERE` hanno natura `ANNULLO`, esistono solo
  sulla commessa, e lì la finestra li conta a parte (`oneri_annullati`) senza mai nominarli.
* `catalogo_repository` (`natura_vendita_destinazione_tipo`): nessun lettore a video né nel backend; cambia solo
  il valore della risposta, documentato in `api_catalogo.md`.
* `error_policies_generated.py` rigenerato dal DB: cambiano solo i commenti di due codici.
* `apps/config/sorgenti.py`: il commento non mette più l'`origine` dei legami fra i vocabolari diversi, e dice che
  origine e destinazione sono questo vocabolario dal 2b.
* **Due punti che il §12.4 non elencava**, entrambi silenziosi: `_smoke_documenti.sh` (`smoke_articolo_merce`,
  il BB che dà l'articolo merce agli smoke) e `smoke-push-termine-documento-commessa.py` cercavano la natura con
  destinazione `ORDINE`: dopo l'apply non avrebbero trovato più nessun articolo. Adeguati, con
  `smoke-test-ordini-giro-commessa.sh`.
* **Presidio nuovo, sul DB vero** (`vendite/tests/db/test_origine_ordine_sorgente_db.py`): su un ordine dello
  stampo, la provenienza scritta da `set_documento_origine` con `SORGENTE_OFFERTA_COMMERCIALE` è accettata e i
  legami del BB la riportano col tipo da aprire; `OFFERTA` è rifiutato da
  `fk_ordini_documento_origine_tipo_sorgenti`. In `test_annullo_con_legami` un caso nuovo: una sorgente fuori
  da `_ORIGINI_DOCUMENTO` resta senza tipo e senza nome anche se il lineage la vede. Nello spec del dialog: i
  consumi della commessa si nominano con `vendite.lineage.tipo_attivita_consumi` (con la chiave sbagliata
  uscirebbe il codice grezzo). Il test sul DB vero usa i BB di `db_e2e` (`apri_transazione_annullata`), non un
  `Annulla` ricopiato.
* Doc: `api_offerte`, `api_ordini`, `api_preventivi`, `api_ddt`, `api_contratti`, `api_commessa_stato`,
  `push_preventivo_handler`, `api_catalogo`, le guide di ordini e offerte, i due cataloghi BB.
* Prova: 2574 test Django di `vendite`, `config`, `catalogo`; e2e di `vendite/tests/db` e `config` su dbdev
  (nessuno saltato; i 5 saltati sono di `catalogo`, per il DB usa-e-getta); mypy a cricchetto pulito; 137 test FE
  di `vendite` e `documenti`, lint, `npm run guards`, `check_i18n_keys`, build. Worker gunicorn ricaricati.
  ⚠️ Gli smoke bash non sono stati lanciati (scrivono dati veri): `smoke-test-ordini-giro-commessa.sh` è quello
  che passa dai legami della commessa.
* ⚠️ **L2b-1, per Tid — la provenienza nella stampa dell'ordine.** Le versioni di modello «stampa ordine
  vendita» (le pubblicate sono la 264 e la 3113 su dbdev) stampano `{{ ordine.origine.tipo }}` così com'è: sulla
  carta usciva già un **codice** (`PREVENTIVO`, `OFFERTA`), e dal 2b esce `OFFERTA_COMMERCIALE`. Non è un difetto
  nuovo del 2b, che lo rende solo più visibile. Strade: (a) il context builder dell'ordine porta anche
  l'etichetta della sorgente (`origine.etichetta`, dalla descrizione di `config.sorgenti`) e i modelli la usano;
  (b) si lascia il codice. La (a) cambia il contratto di stampa e i modelli a DB: non l'ho fatta senza il tuo via.
  ✅ **Decisa da Tid il 2026-10-19: (a)**, con l'etichetta in una colonna a DB (§12.9).
* Da vedere a video (Tid): «Genera ordine» da un'offerta accettata (prima del giro era un rifiuto della FK); la
  finestra dell'annullo con legami di un ordine nato da offerta («Offerta …, torna trasformabile», col link) e di
  una commessa con righe da reso e da consumi; il pannello di smistamento di un preventivo misto (tag
  Ordine/Commessa, «Smista tutto» / «Smista selezionate» e il routing verso ordine e commessa).
* **Revisione critica dello stesso giro** (2026-10-19, su richiesta di Tid):
  * `ordini_service._crea_testata_ordine_da_origine` è **rientrato** in `crea_ordine_da_offerta`. Si diceva
    «condiviso da preventivo e offerta (regola del 2)», ma il preventivo passa da
    `vendite.fn_push_preventivo_a_ordine`, che la provenienza la scrive da sé: un BB con un solo consumatore.
    Col 2b il nome dell'operazione nei log si costruiva dal codice d'origine (`crea_ordine_da_offerta_commerciale`)
    e non era più quello della funzione; ora è fisso (`crea_ordine_da_offerta`). I due test mockano `crea_ordine`
    e provano che `set_documento_origine` riceve `OFFERTA_COMMERCIALE`.
  * Il commento prometteva un errore «parlante» se la FK rifiuta il tipo: la FK e il `CHECK` di co-presenza non
    sono nelle mappe del traduttore e cadono sul fallback generico. Scritto com'è, col motivo: il tipo è una
    costante del codice, un rifiuto è un difetto del codice e non dell'operatore.
  * `origine_onere` tolta da `it.json`/`en.json` (sopra); commenti stantii (`(OFFERTA, id)`, una riga lunga in
    `sorgenti.py`); nel presidio e2e un `getattr(…, None)` che non proteggeva niente.
* **Prova sullo stato attuale** (dopo la revisione, 2026-10-19): 2448 test Django di `vendite` e `config`, 211
  e2e di `vendite/tests/db` su dbdev (nessuno saltato), 697 test FE di `vendite`, `documenti` e `core`, lint:
  verdi.

### 12.8 Correzione richiesta: l'`origine` della partita (`vendite.fn_partite_merce`) — team DB

> ✅ **Scritta il 2026-10-20** (`20261020-24`, §12.10), applicata su dbdev il 2026-10-19 sera.
>
> **Chi scrive:** sessione BE (`dev/backend-tid`), 2026-10-19, su decisione di Tid. **A chi:** il team DB, poi la
> sessione BE per la ricaduta.

**Il caso.** `vendite.fn_partite_merce` (e la sua proiezione `vendite.vw_partite_merce`) restituisce per ogni
partita un'`origine` a tre valori, calcolata nel `SELECT` finale:

| Valore | Che cosa dice |
| --- | --- |
| `NESSUNA` | la riga di DDT non evade nessuna riga d'ordine |
| `MULTIPLA` | la riga di DDT evade più righe d'ordine |
| `ORDINE` | la riga di DDT evade una riga d'ordine |

Il §12.3 la lasciava «da classificare nel 2e». Classificata: **`ORDINE` nomina un tipo di documento** (il
documento da cui la merce parte) ed è il codice corto di `ORDINE_VENDITA`, lo stesso caso dell'`origine` dei
legami chiusa in questo lotto. Non ha niente del `segment_key` (quella è la `corsia`, che resta al 2e).
`NESSUNA` e `MULTIPLA` **non** sono sorgenti: dicono l'assenza e l'ambiguità dell'origine, come `ONERE` nei
legami (§12.2), e restano.

**Che cosa si chiede (changeSet in `20_code`, nuovo file).**

* Nel `CASE` di `origine`: `'ORDINE'` → `'ORDINE_VENDITA'`. `NESSUNA` e `MULTIPLA` invariati.
* L'`origine` diventa quindi «il codice della sorgente, oppure `NESSUNA` | `MULTIPLA`»: va scritto nel commento
  del corpo e nel COMMENT, come per `fn_documento_legami`. Il tipo in `RETURNS TABLE` segue la stessa scelta
  del `-95` (ancorato a `config.sorgenti.codice_interno%TYPE` col motivo accanto, o nudo col motivo): la decide
  il team DB, purché sia la stessa delle due funzioni.
* Corpo **dal catalogo vivo** (`pg_get_functiondef`), non da uno YAML. Se `vw_partite_merce` va ricreata
  (cambia solo un letterale, non il tipo, quindi probabilmente no), nella stessa corsa.
* **Censimento dei lettori su `pg_get_functiondef`** (§12.3): chi confronta `origine = 'ORDINE'` o
  `<> 'ORDINE'` cambia nello stesso changeSet. Già noto: `vendite.fn_situazione_merce_ordine` legge solo
  `origine = 'MULTIPLA'` (non cambia).
* pgTAP: un caso che **costruisce** una riga di DDT legata a una riga d'ordine e verifica `ORDINE_VENDITA`
  (rosso senza la correzione); i file che leggono l'`origine` delle partite
  (`test-fn-partite-merce-chiusura-v1`, `test-vw-partite-merce-v1`, quelli della situazione merce) rilanciati,
  con nota di revisione dove cambia un'attesa.

**Ricaduta sul backend e sul frontend (stesso apply).**

| Dove | Oggi | Dopo |
| --- | --- | --- |
| `vendite_repository.py` (proiezione `partite`, campo `origine`) | passa il valore com'è | nessun codice da cambiare. ⚠️ **Cambia una risposta API**: `partite[].origine` della situazione merce |
| `vendite_service.py:2563` (commento) | `origine <> 'ORDINE'` | `origine <> 'ORDINE_VENDITA'` |
| `api_situazione_merce.md:87` (esempio), `dbzero/vendite/manual/fn_partite_merce.md` | `origine ORDINE` | `origine ORDINE_VENDITA` |
| Frontend | non legge il valore (il pannello usa `stato`, `misurabile`, `differenza`) | nessuna modifica; da riverificare con un grep al giro |
| `apps/config/sorgenti.py` (commento dei vocabolari) | non nomina l'origine della partita | aggiungerla fra quelle che sono questo vocabolario (tranne `NESSUNA`/`MULTIPLA`) |

**Quando.** È un residuo del 2b (lo stesso vocabolario V7, origine), indipendente dai sotto-giri 2c … 2e: si può
fare da solo prima del 2c. Il momento lo decide Tid.

### 12.9 L2b-1: l'etichetta della sorgente nella stampa (team DB, poi sessione BE)

> ✅ **Lato DB scritto il 2026-10-20** (`20261020-22`, `-23`, `-25`, §12.10), applicato su dbdev il 2026-10-19 sera. ⚠️ Due punti di questa
> richiesta sono cambiati nello sviluppo: si evolve lo **standard**, non le versioni 264 e 3113 degli emittenti
> (§12.10.2), e il contesto dell'ordine passa alla **forma 3** (§12.10.4).
>
> **Chi scrive:** sessione BE (`dev/backend-tid`), 2026-10-19. **Decisione di Tid:** L2b-1 = (a), e
> l'etichetta sta **in una colonna a DB** (non nel backend, non nella `descrizione` ripulita). **A chi:** il team
> DB, poi la sessione BE.

**Il caso.** Le versioni pubblicate del modello «Ordini vendita» (su dbdev la 264, `template_documento_id` 75, e
la 3113, `template_documento_id` 2531; `context_schema` vuoto) stampano la provenienza così:

```
{% if ordine.origine.tipo or ordine.origine.codice %}
      <strong>{{ ordine.origine.tipo or "Documento origine" }}</strong>
```

`ordine.origine.tipo` è `vendite.ordini.documento_origine_tipo`, cioè un **codice**: sulla carta usciva
`PREVENTIVO`/`OFFERTA`, dal 2b esce `OFFERTA_COMMERCIALE`. Nessuna fonte di oggi va bene per la carta:
`config.sorgenti.descrizione` è una nota tecnica («Offerta commerciale (testata)», «Commessa (root pipeline
attivita fatturabili)»), e l'etichetta leggibile c'è solo nel frontend (`config.tipi_entita.*` nei locales): il
backend non ha traduzioni per la stampa, e una mappa in Python sarebbe la seconda copia delle stesse
etichette. La stampa prende le parole dal catalogo del DB, come fa già la fattura col suo tipo
(`tipo_doc_fiscale.descrizione`).

**Che cosa si chiede al team DB.**

* **`config.sorgenti.etichetta`**: il nome del tipo di documento come lo legge una persona, sulla carta
  («Preventivo», «Offerta», «Ordine», «DDT», «Reso», «Contratto», «Commessa», «Fattura», …). Il nome della colonna
  lo decide il team DB secondo le linee guida; qui la chiamo `etichetta`.
  * **`NOT NULL`, per ogni riga** (anche `RIGA` e le altre categorie): una sorgente nuova senza il suo nome non
    deve poter entrare. Il valore sta nel CSV `sorgenti.csv` (`80_data`), non in un `UPDATE`.
  * `descrizione` resta com'è: è la nota tecnica.
  * Una sola lingua, l'italiano, come le altre parole di stampa nel catalogo. Il giorno delle stampe in più
    lingue è un cantiere suo, non di questa colonna.
* **I modelli dell'ordine**, nuova versione e pubblicazione come nei `20260816-01`/`-02`: nelle due righe sopra
  `ordine.origine.tipo` diventa `ordine.origine.etichetta` (nell'`if` e nel testo). Il ripiego «Documento origine»
  resta. Se le versioni pubblicate sono più di quelle due nel momento del changeSet, si leggono tutte quelle
  di codice «Ordini vendita» che usano `origine.tipo`.
* pgTAP: la colonna è `NOT NULL` e ogni riga del seed ha un'etichetta; la versione pubblicata del modello
  dell'ordine non legge più `origine.tipo`.

**Ricaduta sul backend (dopo l'apply).**

| Dove | Oggi | Dopo |
| --- | --- | --- |
| `OrdiniRepository.get_ordine` (la testata della stampa e del dettaglio) | `v.*` di `vw_ordini_lista` | + `LEFT JOIN config.sorgenti` su `documento_origine_tipo`, colonna `documento_origine_etichetta` (NULL quando l'ordine non ha origine) |
| `ordine_document_context_builder._shape_ordine` | `origine: {tipo, codice}` | + `etichetta`; `tipo` resta (il codice, per chi lo confronta) |
| test del builder, `api_ordini.md` (contratto di stampa) | | il campo nuovo |

Il frontend non cambia: il dettaglio dell'ordine non mostra il tipo dell'origine.

**Fuori da questa richiesta, trovato strada facendo.** Anche i modelli della fattura (le pubblicate 2334 e 3097
su dbdev) hanno il blocco `fattura.origine.tipo`, ma `VenditeRepository.get_fattura_testata` non porta né
`origine_tipo` né `origine_codice`: il blocco non si vede mai. Una fattura può nascere da più documenti, quindi
non è «la stessa correzione»: è da decidere a parte (togliere il blocco dal modello, o dire che cosa una fattura
chiama «origine»).

## 12.10 Il giro DB dei §12.8 e §12.9 (team DB, 2026-10-20)

Via di Tid il 2026-10-19 sera: i due giri insieme, un solo apply. Numeri `20261020-22` … `-25` (il 19 è pieno
fino a `-99`).

### 12.10.1 Che cosa contiene

| ChangeSet | Che cosa |
| --- | --- |
| `-22` (`00_schema`) | `config.sorgenti.etichetta` `varchar(60)`, **nullable qui**, col `CHECK` di non-vuoto (`chk_sorgenti_etichetta_non_vuota`) e il COMMENT |
| CSV `sorgenti.csv` + loader `20251002-21` | la colonna `etichetta` per tutte le 29 righe; il loader esteso sul posto, come per `area` e `label_selector` |
| `-23` (`90_end`) | il `NOT NULL`, dopo il mirror: in `00_schema` la tabella ha già righe (le INSERT dei `20260928-62`/`-85`), stessa sede e forma del `20260904-42`; se una riga è scoperta lo dice con una frase, non con un `23502` |
| `-24` (`20_code`) | `vendite.fn_partite_merce`: `origine` `ORDINE` → `ORDINE_VENDITA` (§12.8); `NESSUNA` e `MULTIPLA` restano |
| `-25` (`80_data/changelog`) | lo **standard** «Ordine di vendita», versione 2: stampa `ordine.origine.etichetta` al posto di `ordine.origine.tipo`, dichiara la **forma dei dati 3**, pubblicata dalla data operativa |

pgTAP: nuovo `config/test-grammatica-etichetta-sorgenti-v1` (8); `vendite/test-fn-partite-merce-chiusura-v1` passa
a 16 (il 16 costruisce la riga che evade una riga d'ordine e vuole `ORDINE_VENDITA`). Doc: `dbzero/config/manual/sorgenti.md`
(la colonna, e la nota del 20-08 sulle `*_RIGA` fuori dal CSV, superata: il CSV ha tutte le 29 righe),
`dbzero/vendite/manual/fn_partite_merce.md` (i tre valori di `origine`).

### 12.10.2 Le scelte

* **Le etichette** sono quelle che il brief proponeva per i documenti di vendita, cioè le stesse del lineage a
  video (`vendite.lineage.tipo_*`: «Preventivo», «Offerta», «Ordine», «DDT», «Reso», «Contratto», «Commessa»,
  «Fattura», «Consumi»); per il resto quelle di `config.tipi_entita.*` («Ordine d'acquisto», «Riga di DDT»,
  «Prelievo»…). Si cambiano nel CSV.
* ⚠️ **Il §12.9 chiedeva di ripubblicare le versioni 264 e 3113: superato.** Dal 2026-10-19 vale la regola del
  brief dei modelli standard ([brief-db-modelli-documento-standard](brief-db-modelli-documento-standard.md) §4.1
  Q-5): *i changeSet di evoluzione scrivono solo sullo standard*. Le 264 e 3113 sono le copie degli emittenti
  32 e 44, dati dell'applicazione: il changeSet non le tocca.
* **Forma dei dati 3.** `etichetta` è una chiave **nuova** del contesto dell'ordine, e il render gira con
  `StrictUndefined`: un modello che la legge, reso da un builder che non la produce, fallisce. Il patto della
  forma (`documenti.fn_guard_versione_contesto`) esiste per questo, e il precedente c'è: la chiave nuova
  `annotazioni` della fattura è stata la forma 3 → 4 (2026-10-02). Quindi la versione 2 dello standard dichiara
  la forma 3, e il builder dell'ordine passa a `CONTEXT_VERSION = 3` (§12.10.4).
* **La versione 2 si copia, non si riscrive**: dalla pubblicata valida oggi, per sostituzione contata (due
  occorrenze di `ordine.origine.tipo`, né una di più né una di meno), nella forma del `20260816-01`. Un modello
  ritoccato nel frattempo ferma il changeSet. Idempotente; una bozza dello standard già presente lo ferma.
* **Pubblicata da `script.fn_data_operativa()`**, la data con cui il backend sceglie la versione da stampare
  (`get_versione_pubblicata_attiva`), non da `current_date`, che dipende dal fuso della sessione.
* **`fn_partite_merce`**: corpo dal `20261012-32`, verificato uguale al vivo; `RETURNS TABLE` ancorato con
  `%TYPE` dove la colonna esiste (`origine` su `config.sorgenti.codice_interno`: il tipo resta
  `character varying`, quindi `CREATE OR REPLACE` senza `DROP`, e `vw_partite_merce` con le funzioni
  `BEGIN ATOMIC` che la leggono restano in piedi); `SECURITY INVOKER` scritto. Lettori censiti su
  `pg_get_functiondef`: nessuno confronta `'ORDINE'` (`fn_situazione_merce_ordine` legge solo `MULTIPLA`).

### 12.10.3 La conseguenza della forma 3 — L2b-2, per Tid

Fatto di dbdev, letto il 2026-10-20: l'ordine si stampa oggi con tre modelli, tutti in forma 2. Lo standard
(template 2731, versione 1) e le copie degli emittenti 32 (template 75, versione 264) e 44 (template 2531,
versione 3113); le due copie leggono `origine.tipo`.

* **Fra l'apply e il giro BE**: lo standard ha solo la versione 2 (forma 3), il builder produce ancora la 2 → lo
  standard non stampa (409 `E_DOCUMENTI_VERSIONE_CONTESTO_DIVERSA`, non un PDF sbagliato). Su dbdev non lo usa
  nessuno: la risoluzione a due livelli del BE non c'è ancora (brief dei modelli standard, §6).
* **Dopo il giro BE**: le copie in forma 2 non stampano più (409), finché qualcuno non ne pubblica una versione
  in forma 3. `documenti.vw_template_personalizzati_scarto` le mostra `CONTESTO_SUPERATO`. È il patto che fa il
  suo lavoro, come per la fattura il 2026-10-02.

**L2b-2 — le due copie di dbdev.** (a) Tid le ripubblica dall'app (Clona → `origine.tipo` → `origine.etichetta`
nelle due righe → «Legge i dati nella forma» = 3 → Pubblica), come la fattura v6 del 2026-10-02; (b) le spegne,
quando il BE avrà la risoluzione a due livelli, e gli emittenti 32 e 44 passano allo standard; (c) un SQL una
tantum a mano su dbdev, che il team DB prepara (non un changeSet: sono dati dell'applicazione).
**Proposta: (a) o (c)**, perché (b) dipende da un giro BE di un altro brief.
✅ **Decisa da Tid il 2026-10-20: (c).** Lo script è
[sql-una-tantum-l2b2-copie-ordine-forma-3.sql](sql-una-tantum-l2b2-copie-ordine-forma-3.sql) (accanto a questo
brief; si cancella all'archiviazione). Cerca per criterio, non per id: i modelli d'ordine degli emittenti la cui
versione stampata oggi è in forma 2 e legge `origine.tipo`. Li copia, sostituisce le due occorrenze, li porta
alla forma 3 e li pubblica dalla data operativa. Si ferma, annullando tutto, se un modello ha già una bozza attiva
o se le occorrenze non sono due; rilanciato non fa niente. **Si lancia subito dopo il riavvio del backend in
forma 3** (`psql -X -v ON_ERROR_STOP=1 -f …`, come owner). Provato su dbdev il 2026-10-20 in transazione annullata,
con un secondo giro nella stessa transazione: le copie 75 (emittente 32) e 2531 (emittente 44) passano dalla
versione 4 alla 5 (forma 3), il secondo giro non trova niente, e dopo il giro tutti e tre i modelli che stampano
l'ordine sono in forma 3 e nessuno legge il codice. ⚠️ Se invece Tid preferisce che una
chiave aggiunta **non** cambi la forma (forma 2 «estesa»), cambiano un letterale nel `-25` e il test 8 del pgTAP
nuovo, e le copie non si fermano; ma il patto smette di dire quali chiavi un modello può leggere, e il precedente
della fattura va nell'altro verso.

### 12.10.4 Richiesta al backend (stesso apply) — aggiorna la tabella del §12.9 e del §12.8

| Dove | Oggi | Dopo |
| --- | --- | --- |
| `OrdiniRepository.get_ordine` | `v.*` di `vw_ordini_lista` | + `LEFT JOIN config.sorgenti` su `documento_origine_tipo`, colonna `documento_origine_etichetta` (NULL quando l'ordine non ha origine) |
| `ordine_document_context_builder` | `CONTEXT_VERSION = 2`; `origine: {tipo, codice}` | ⭐ **`CONTEXT_VERSION = 3`**; `origine: {tipo, codice, etichetta}`, chiave **sempre presente** (`None` senza origine: `StrictUndefined`); `tipo` resta (il codice, per chi lo confronta) |
| test del builder, `api_ordini.md` (contratto di stampa) | | la forma 3 e il campo nuovo |
| §12.8: `vendite_service.py:2563` (commento), `api_situazione_merce.md:87` (esempio), `apps/config/sorgenti.py` (commento dei vocabolari) | `ORDINE` | `ORDINE_VENDITA`; ⚠️ cambia `partite[].origine` nella risposta della situazione merce; il FE non legge il valore (da riverificare con un grep) |

Il frontend non cambia per il §12.9: il dettaglio dell'ordine non mostra il tipo dell'origine.

### 12.10.5 La prova (2026-10-20, scratch `zeroerp_ruoli`, come owner, in transazione annullata)

* **SQL estratto** dei quattro changeSet (non riscritto), nell'ordine del migrate: `-22`, il mirror del CSV
  simulato con 29 `UPDATE` per id, `-23`, `-24`, `-25`. Passa: `etichetta` `NOT NULL`; lo standard ha la
  versione 1 `OBSOLETA` fino a ieri e la 2 `PUBBLICATA` (forma 3) da oggi. Il `-25` lanciato una seconda volta
  non fa niente (idempotente). ⚠️ **Non provato: il loader vero** (`loadUpdateData` del `20251002-21`), che il
  seed simulato non copre; il CSV è confrontato col DB colonna per colonna prima della modifica (0 differenze).
* **`-24`**: il corpo del `20261012-32` è identico al vivo (definizione e COMMENT); dopo il `-24` l'unica
  differenza della definizione è il letterale, ACL invariata, `origine` resta `character varying`,
  `vw_partite_merce` in piedi; il rollback riporta definizione e COMMENT al vivo.
* **pgTAP**: 64 file (chi nomina le partite e i loro lettori, `config.sorgenti`, i modelli e la forma dei dati),
  ciascuno com'è e con l'SQL estratto dopo la riga `BEGIN;`, uno alla volta. **43 verdi prima e dopo, 19 rossi
  identici prima e dopo** (fixture senza `billing_account`, test di scope e `-app` rossi da owner per
  costruzione). Cambiano solo i due di questo giro: il nuovo, rosso senza (la colonna non c'è) e 8/8 con;
  `test-fn-partite-merce-chiusura-v1`, il caso 16 rosso senza e verde con (gli resta rosso lo scope, rosso da
  owner come prima).
* Cancelli statici verdi; `guardrail_pgtap_preambolo` resta rosso solo per
  `dbops/test-automazioni-guasto-ambiente-rilanciato-v1`, di un altro cantiere (§12.5).
* Non provato prima dell'apply: i pgTAP **come app** (li lancia Tid), il loader del CSV, il giro BE del §12.10.4.
* ✅ **Apply su dbdev** (Tid, 2026-10-19 sera): i quattro changeSet `EXECUTED`. Il `-23` è passato, quindi il
  loader vero ha dato l'etichetta a ogni riga. Lo standard dell'ordine stampa la versione 2, in forma 3.
* ✅ **pgTAP come app** (Tid, 2026-10-20): verdi, nessuna regressione.
