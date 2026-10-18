# Brief DB — Una sola grammatica per i tipi di documento

## ⏭️ Chi riparte — aggiornato al 2026-10-19

**Riparte: la sessione BE** (il §9.4: consegnare il giro del lotto 1). Il DB del lotto 1 è applicato su dbdev
senza regressioni (Tid, 2026-10-19): finché il BE non passa `OFFERTA_COMMERCIALE`, sul dev il form delle
erogazioni e il listino operativo dell'offerta rispondono `E_DOC_TIPO_NON_GESTITO`.

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
| 6-bis | sessione BE | Il giro BE del lotto 1: `DocumentoEccezioni` e i due punti di `offerte_service` sui codici delle sorgenti. ⏳ Al 2026-10-19 non ancora su `origin/dev/backend-tid` | §9.4 | 6 |
| 6-ter | ✅ **Tid** | Apply del lotto 1 su dbdev e corsa dei pgTAP come app: nessuna regressione (2026-10-19) | §9.5 | 6 |
| 6-quater | team DB + sessione BE/FE | Lotti 2 e 3 (il 3 anticipabile): DB e backend nello stesso giro; col lotto 2 il SQL a mano delle chiavi (G-8) | §5 G-4, §3.2, §7.9 | 6-bis |
| 7 | chi chiude | Lotto 4: presidio, ritiro del ponte di `fn_articolo_riga_contesto` (se non già nel 2), riga di PROJECT_CONTEXT, archiviazione | §5 G-4 | 6-quater |

**Decisioni aperte di Tid:** nessuna (K-1 e i nomi decisi il 2026-10-19, §8.3). Da committare: il lotto 1 (§9). ⚠️ Mancano ancora i rimandi del §6.1 in
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
