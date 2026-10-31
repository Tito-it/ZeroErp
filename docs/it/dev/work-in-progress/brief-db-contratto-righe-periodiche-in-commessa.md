# Brief DB — Le righe di contratto che non sono «una volta»: canone, orario e consumo in commessa

## ⏭️ Chi riparte — aggiornato al 2026-10-31 (fine L9)

**Riparte: il team BE/FE**, con la richiesta di questo brief. **Lato DB i lotti sono finiti** (L1 … L9,
§6.3): L8 applicato e verde, L9 (la documentazione, §6.14) scritto il 2026-10-31.

**Cosa resta:**
* **BE/FE** (la richiesta, da scrivere come elenco chiuso a giro DB provato):
  * la commessa del contratto si apre **senza periodo** (§6.12, G-6): senza, dal secondo pezzo di
    canone il push va in errore;
  * i campi nuovi nei form: tipo `ADESIONE` e le azioni `ADERISCI` / `RIMUOVI_ADESIONE` (§6.10), il
    mese di partenza e anticipato/normale sulla testata di contratto e offerta (§6.6), la periodicità
    sulla riga di listino;
  * i due motivi nuovi della dashboard (`CANONE_NON_GENERATO` arancio, `CANONE_NON_GENERABILE`
    rosso, §6.13), e il contratto attivo che esce dalla situazione aperta;
  * gli altri punti del §6.12: kit sulle quote fisse del listino, riga negativa sola in fattura.
* **DB, col passaggio BE/FE e non prima:** l'obbligo della periodicità sulla riga a canone (guard +
  CHECK) e lo script di F-10 sui dati di prova (§6.11).

| # | Chi | Che cosa | Dove | Aspetta |
| --- | --- | --- | --- | --- |
| 1 | ✅ Tid | decisioni G-0 … G-11 (2026-10-28), verificate contro guide e doc | §4.1, §4.3 | — |
| 1-bis | ✅ team DB | la forma e i lotti (2026-10-29) | §6.1 … §6.3 | 1 |
| 1-ter | ✅ team DB | Lotto 1 scritto e provato in transazione | §6.5 | 1-bis |
| 1-quater | ✅ Tid | domande F-1 … F-7 (2026-10-29) | §6.4 | 1-bis |
| 1-quinquies | ✅ Tid | F-5 e apply del Lotto 1 (2026-10-29) | §6.5 | 1-ter |
| 1-sexies | ✅ team DB | Lotto 5 scritto e provato in transazione | §6.6 | 1-quater |
| 1-septies | ✅ Tid | apply del L5 e pgTAP verdi (2026-10-29) | §6.6 | 1-sexies |
| 1-octies | ✅ team DB | Lotto 6 scritto e provato in transazione | §6.7 | 1-septies |
| 1-nonies | ✅ Tid | apply del L6 e pgTAP verdi; lock della testata fuori bozza confermato (2026-10-29) | §6.7 | 1-octies |
| 1-decies | ✅ team DB | Lotto 3 scritto e provato in transazione | §6.8 | 1-nonies |
| 1-undecies | ✅ Tid | apply del L3 e pgTAP verdi (2026-10-29) | §6.8 | 1-decies |
| 1-duodecies | ✅ team DB | Lotto 2 scritto e provato in transazione | §6.9 | 1-undecies |
| 1-terdecies | ✅ Tid | L2 applicato e verde (con `-34`/`-35`); F-8 decisa | §6.9 | 1-duodecies |
| 1-quaterdecies | ✅ team DB | Lotto 4a (ADESIONE) scritto | §6.10 | 1-terdecies |
| 1-quindecies | ✅ Tid | L4a applicato; F-9, F-10 e (b) del L4b decise (2026-10-29) | §6.10 | 1-quaterdecies |
| 1-sedecies | ✅ team DB | Lotto 4b (default della periodicità) scritto e provato | §6.11 | 1-quindecies |
| 1-septendecies | ✅ Tid | L4b applicato; tutti i pgTAP verdi, nessuna regressione (2026-10-29) | §6.11 | 1-sedecies |
| 1-duodevicies | ✅ Tid | F-11: basta quantità × prezzo, la fattura non si tocca (2026-10-30) | §6.4, §6.7 | 1-septendecies |
| 1-undevicies | ✅ team DB | il lister L7 scritto e provato (2026-10-30) | §6.12 | 1-duodevicies |
| 1-vicies | ✅ Tid | L7 applicato, pgTAP verdi (2026-10-30) | §6.12 | 1-undevicies |
| 1-vicies semel | ✅ team DB | L8: i casi limite del lister e la dashboard, scritti e provati (2026-10-31) | §6.13 | 1-vicies |
| 1-vicies bis | ✅ Tid | F-15 (a); L8 applicato, pgTAP verdi (2026-10-31) | §6.4, §6.13 | 1-vicies semel |
| 1-vicies ter | ✅ team DB | L9 (documentazione) scritto (2026-10-31) | §6.14 | 1-vicies bis |
| 1-vicies quater | BE/FE | la richiesta (commessa senza periodo, form, dashboard) | testa, §6.12, §6.13 | 1-vicies ter |
| 2 | DB | analisi della forma scelta e consegna | — | 1 |
| 3 | BE/FE | da definire dopo la forma (l'orchestratore del push, la lista dei contratti) | — | 2 |

Decisioni aperte di Tid: nessuna; F-1 … F-10 prese il 2026-10-29, F-11 … F-13 il 2026-10-30, F-14 e F-15 il 2026-10-31. G-0 … G-11 prese il 2026-10-28. Lavoro committato il 2026-10-31 su `dev/db-tid` (un commit: L1 … L9): i changeSet `20261029-10` …
`-45`, `20261030-01` e `20261031-01` … `-04` (§6.5 … §6.13, applicati su dbdev), i CSV e i seed
toccati, i pgTAP nuovi e aggiornati, la documentazione del L9 (§6.14), questo documento. Il giro che lo ha aperto, `20261013-24`, è nella risposta al team BE del 2026-10-13.

> **Chi scrive:** team DB (`dev/db-tid`), 2026-10-13. **A chi:** Tid, poi il team DB.
> **Origine:** decisione D-2 (a) di Tid, 2026-10-13, sulla segnalazione BE del push batch CONTRATTO
> (registro 2724: un contratto senza `valido_al` cadeva sul NOT NULL di
> `commesse_attivita.competenza_al`). Registro: **D31** di
> [migliorie-generali-da-test-valutazione](migliorie-generali-da-test-valutazione.md).

## 1. Il caso

Una riga di contratto dice **come si eroga** (`vendite.contratti_righe.tipo_erogazione`, vocabolario
`config.erogazioni_fonti`): `UNA_TANTUM`, `CANONE`, `ORARIO`, `CONSUMO`. Solo la prima è «una riga,
una volta». Le altre tre hanno un ritmo o una fonte:

* **CANONE** — una riga per periodo. Il contratto lo dice già: `periodicita`, `generazione_canone`
  (`INIZIO_PERIODO`, `FINE_PERIODO`, `PRORATA`, obbligatoria per `chk_contrighe_coerenza_canone`),
  `competenza_canone`;
* **ORARIO** — la quantità viene dalle ore (`TIMESHEET`, `MANUALE`) o è fissa (`FISSA`);
* **CONSUMO** — la quantità viene dalle letture (`LETTURE`) o è manuale.

Fino al 2026-10-13 `vendite.fn_list_contratti_da_pushare` le mandava **tutte una volta sola**, nel
mese di `valido_dal`, con la quantità della riga e una competenza uguale a **tutta la validità del
contratto**. Un canone mensile di un contratto annuale diventava una riga sola, con un prezzo, per
dodici mesi. Nessuno genera i periodi: né il DB né `HandlerContratti`, e `generazione_canone` viaggia
in `meta` senza un lettore.

Dal `20261013-24` (D-2 di Tid) il lister manda **solo le UNA_TANTUM**, con la competenza del giorno di
attivazione. Il push smette di produrre righe sbagliate, ma le altre tre erogazioni **non arrivano più in
commessa**: è il lavoro di questo brief.

## 2. I fatti di struttura (2026-10-13)

* `vendite.contratti.valido_dal` NOT NULL, `valido_al` nullable: un contratto può non finire, e la
  generazione per periodo non può contare su una fine.
* `vendite.commesse_attivita`: `competenza_mese` (primo del mese, CHECK), `competenza_dal` e
  `competenza_al` NOT NULL con `competenza_dal <= competenza_al`.
* Il segmento della riga di contratto è `CONTRATTO:<uid>:R:<riga>:M:<AAAA-MM>` (composto da
  `script.fn_segment_key` dal `20261020-90`; prima `CONTR:`): ha già il mese, quindi la forma «una riga
  per periodo» c'è nel nome, e `script.fn_get_stato_push_segment` la classifica per segmento.
* I consumi hanno già un loro push (`vendite.fn_list_consumi_da_pushare`, da
  `vendite.attivita_consumi`), che oggi non arriva in commessa per un altro motivo: `articolo_id`
  NULL contro una colonna NOT NULL, e lo smistamento per componente è uno stub rimandato da Tid il
  2026-06-16.

## 2-bis. Che cosa è cambiato dal 13-10 (ricontrollato il 2026-10-28)

Il lister `vendite.fn_list_contratti_da_pushare` è cambiato una volta sola, nella chiave (`20261020-90`,
grammatica unica): il filtro UNA_TANTUM e la competenza del `-24` sono intatti. Gli altri giri hanno
toccato il contorno, e cinque cose entrano nel lavoro di questo brief:

1. **Il contratto ha uno stato CESSATO e un verbo per arrivarci** (giro 8 del modello del documento,
   `20261026-03…-10`): `vendite.fn_cessa_contratto(id, valido_al)` (oggi → CESSATO; data futura → solo la
   data, `programmata`), il job `vendite.fn_cessa_contratti_scaduti` (ATTIVO con `valido_al` passata →
   CESSATO), il guard che verso CESSATO vuole `valido_al` arrivata. Il lister legge **solo ATTIVO**: un
   periodo che matura **dopo** la cessazione non si genera più (il canone posticipato dell'ultimo periodo,
   o un periodo non ancora mandato). La generazione deve leggere anche i CESSATO, fino a `valido_al`
   (domanda G-2). Aperto nel brief del modello: il lettore dello stato di cessazione (passo
   4-bis-nonies-octies).
2. **Un contratto vincolante non si sovrappone a un altro** dello stesso cliente, punto di fornitura,
   utility e ambito (`20261020-19…-21`, `script.fn_check_contratto_sovrapposto`): «Attiva» è spento sopra
   un sovrapposto. Due canoni sullo stesso periodo fra contratto vecchio e successore li evita già
   l'attivazione, per i vincolanti; per i non vincolanti no.
3. **L'erogazione di un articolo ha una sede unica**, `vendite.fn_articolo_erogazioni` (`20261021-44…-61`,
   brief dell'offerta): la tipologia di listino dell'articolo, o in mancanza la natura di vendita, dà le
   coppie (erogazione, fonte), il default e la `generazione_canone`. **Non dà la periodicità**: non c'è in
   nessun vocabolario (domanda G-0-bis).
4. **Il kit si vende solo con quantità FISSA** (I-D6, `20261021-48`, `DERIVATA_COMPONENTI` ritirata): un
   canone composito ha sempre la quantità sulla riga, e i componenti `#CMP` si ripetono per periodo dalla
   stessa quantità.
5. **La riga di commessa che cita un contratto** deve essere del billing account della commessa
   (`20261021-64…-66`, `E_ATTIVITA_CONTRATTO_INCOERENTE`): la generazione la rispetta già, perché la
   commessa del push nasce sul BA del contratto.

Fuori da qui, senza effetto sul brief: lo stato iniziale e i passaggi permessi del contratto (giri del
modello), la versione di listino al modello (giro 12, sullo stato della versione, non sulle righe). I tre
pgTAP del §5 sono stati portati ai builder (17-10, 26-10, 28-10) senza cambiare la regola che raccontano.

## 2-ter. Analisi critica (2026-10-28)

* **Le righe di contratto sono solo eccezioni** (`tipo_eccezione`: OVERRIDE, AGGIUNTA, ESCLUSIONE): un
  canone pagato a prezzo di listino non ha una riga. Un generatore che legge solo `contratti_righe` non
  lo vede: è la domanda che viene prima di G-1 (G-0).
* **I parametri del canone non hanno un vocabolario**: `periodicita` e `competenza_canone` sono `varchar`
  senza CHECK né FK (i valori stanno nel COMMENT); `periodicita` è facoltativa anche sulle CANONE (il CHECK
  `chk_contrighe_coerenza_canone` pretende solo `generazione_canone`); il listino non dice la periodicità.
* **Tre colonne, due assi**: `generazione_canone` mescola *quando* si addebita (`INIZIO_PERIODO`,
  `FINE_PERIODO`) e *come* si tratta il periodo parziale (`PRORATA`); `competenza_canone`
  (`MESE_CORRENTE`, `MESE_SUCCESSIVO`) ripete il «quando», e su un trimestrale non ha un senso solo.
* **ORARIO e CONSUMO non hanno la fonte**: nel DB non c'è un timesheet né una tabella di letture, e
  `vendite.attivita_consumi` è per BA e mese, senza articolo né riga di contratto.
* **La chiave col mese dà già l'idempotenza per periodo**: un lister che calcola i periodi maturati a
  ogni giro non ha bisogno di un calendario, che andrebbe riscritto a ogni cessazione o annullo.
* **La genealogia** (contratto → commessa 1:N, una per periodo) e **D-12** (una commessa viva per
  sorgente, il link resta come storia) stanno insieme se la commessa del contratto si chiude e la
  successiva ne apre un'altra: va detto quando si chiude (G-6).

## 3. Le domande

1. **Chi genera i periodi del canone, e quando.** Una riga per periodo «maturato» a ogni giro del push
   (il lister li calcola fino a oggi) o un calendario scritto all'attivazione del contratto?
2. **Fino a quando.** Con `valido_al` NULL la generazione non ha una fine: si ferma a «oggi», al
   periodo corrente, o a un orizzonte dichiarato?
3. **La competenza di un periodo.** `INIZIO_PERIODO` / `FINE_PERIODO` / `PRORATA` dicono quando si
   addebita e come si tratta il primo periodo parziale: la regola va scritta in un posto solo.
4. **ORARIO e CONSUMO.** Le loro quantità non stanno sul contratto: il contratto dà il prezzo, la
   quantità arriva da timesheet e letture. Passano dal contratto o dalle loro sorgenti (consumi), con
   il contratto come listino?

## 4. Decisioni di Tid

### 4.1 Prese (Tid, 2026-10-28)

| # | Decisione |
| --- | --- |
| **G-0** *(rivista il 2026-10-28, §4.3)* | Del listino del contratto si addebitano in automatico **solo le quote fisse** (righe il cui articolo è di tipologia con `e_quota_fissa`), meno le ESCLUSIONE, con l'OVERRIDE al posto della riga che ritocca. Gli altri canoni si addebitano solo se il contratto ha una riga: **ADESIONE** (G-0-ter) per un articolo del listino, **AGGIUNTA** per uno fuori listino. Il prezzo di una riga di listino passa dalla **variazione globale** del contratto. |
| **G-0, quantità** | Una quota fissa senza eccezione vale **1 per periodo**; una quantità diversa si scrive con un'eccezione sul contratto. |
| **G-0-ter** | Un quarto tipo di riga, **ADESIONE**: il cliente prende un articolo **del listino** al prezzo **del listino** (con la variazione globale); sulla riga solo quantità e periodicità (ereditata dalla riga di listino). OVERRIDE resta «prezzo personalizzato», AGGIUNTA resta «fuori listino». |
| **G-0-bis** | La periodicità sta **sulla riga di listino**, obbligatoria sui canoni, da un vocabolario controllato; il contratto la cambia con un'eccezione. |
| **G-1** | I periodi li genera **il giro del push**: a ogni giro i periodi maturati e non ancora mandati (idempotenza dalla chiave `:M:`). Nessun calendario all'attivazione. |
| **G-2** | La finestra del giro: **da** = il giorno dopo l'ultimo addebito della riga (al primo giro, l'inizio del contratto); **a** = da un parametro, **fine del mese della data fattura** oppure **fine del mese precedente**. Il parametro sta **sul contratto**; un default per utility, che il contratto eredita, è possibile ma non deciso per ora. |
| **G-2, cessati** | Un contratto CESSATO genera i periodi mancanti **fino a `valido_al`**, non oltre. |
| **G-3** | Se un periodo già iniziato si addebita lo dice **la riga**: inizio periodo = subito e intero, fine periodo = a periodo chiuso. Il primo e l'ultimo periodo incompleti si addebitano **sempre in proporzione ai giorni**. |
| **G-4** | Questo brief fa **solo il canone**. ORARIO e CONSUMO aspettano le loro sorgenti (timesheet, letture), in un lavoro a parte. |
| **G-5** | Un canone già addebitato in anticipo su un contratto che cessa a metà periodo: **storno automatico** della parte non goduta (in proporzione ai giorni), una riga negativa per la fattura successiva. |
| **G-6** | **Una commessa aperta alla volta** per contratto: i canoni si accumulano nella commessa viva; fatturata e chiusa, il periodo dopo ne apre una nuova (coerente con D-12). ⚠️ **Revoca** la riga F di `work-done/brief-design-genealogia-transiti-vendite.md` §3.2 («una commessa per periodo», mai costruita): confermato da Tid il 2026-10-28. |
| **G-7** | `PRORATA` si **ritira** da `generazione_canone`, che resta `INIZIO_PERIODO` (in anticipo, all'inizio del periodo) / `FINE_PERIODO` (a consuntivo, a periodo chiuso). |
| **G-8** | `competenza_canone` si **ritira**: la finestra la dà il parametro del contratto (G-2). |
| **G-9** | `CANONE/MANUALE` si **ritira** (nessuno ricorda che cosa caricare ogni periodo). Entra nel giro una fonte nuova, **«dalla durata del periodo»**: il prezzo è al giorno o al mese, e la quantità la conta il sistema dal calendario, nell'unità di misura dell'articolo (giorni o mesi coperti dal periodo). Il periodo incompleto è già nella quantità: il prorata non si applica sopra. Restano quindi due fonti per il canone: `FISSA` e la durata. |
| **G-10** | Le ore: il **pacchetto di ore fisse al periodo** (per esempio 10 ore al mese) entra nel giro come canone `FISSA` sull'unità di misura delle ore. ⚠️ Corretto il 2026-10-29: l'unità **esiste già**, `HH` «ORE», tipo `TEMPO` come `GG` e `MESE` (il censimento del 28-10 cercava per codice e descrizione e non l'ha vista): niente da aggiungere al catalogo. Le **ore lavorate** (`ORARIO/TIMESHEET`) aspettano il timesheet (G-4): fino ad allora non arrivano in commessa. |
| **G-11** | **L'offerta cambia con il contratto, nello stesso giro**: le righe dell'offerta hanno gli stessi campi e il passaggio offerta → contratto li copia. Ritiri (G-7, G-8, G-9), prezzo a durata (G-9) e ADESIONE (G-0-ter) valgono anche per `vendite.offerte_commerciali_eccezioni`, i suoi form e la sua guida. |

**Da verificare nell'analisi:** con il pacchetto di ore come canone, che cosa resta di `ORARIO/FISSA` e
`ORARIO/MANUALE` in `config.erogazioni_fonti` (per esempio un pacchetto di ore una tantum).

### 4.3 Verifica contro guide e documentazione (2026-10-28)

Le decisioni confrontate con `guide/gestione-contratti`, `guide/gestione-offerte-commerciali`,
`guide/gestione-preventivi` e le pagine `manual` di contratto, righe, tipologie e nature.

* ⛔ **G-0 nella prima forma cambiava il significato del listino del contratto.** Il listino è un elenco
  di **prezzi** («condizioni quadro: listino + variazione + eccezioni»; preventivi e ordini lo usano per
  dare il prezzo, origine `CONTRATTO_LISTINO`; `fn_contratto_righe_preview` mostra gli articoli del
  listino come visibili, senza erogazione), non di servizi sottoscritti: addebitare ogni canone del
  listino li avrebbe addebitati a tutti i clienti con quel listino. Corretto da Tid: in automatico solo
  le quote fisse (`config.listini_tipologie.e_quota_fissa`, «canone o quota periodica indipendente dal
  consumo»), gli altri con l'ADESIONE (G-0-ter), perché oggi nessun tipo di riga dice «lo prende al prezzo
  di listino» (AGGIUNTA vietata su un articolo del listino, OVERRIDE vuole un prezzo e salta la variazione
  globale).
* ⚠️ **G-6 revoca** la riga F della genealogia («una commessa per periodo»), che contraddiceva anche D-12.
* ⚠️ **G-7, G-8, G-9 toccano l'offerta** (stessi campi, copiati dal passaggio a contratto): G-11.
* ✅ Coerenti: G-2 sui CESSATO con il principio «le date comandano, lo stato è un flag» del manual del
  contratto (§7c; era il lister a contraddirlo); G-9 con la matrice delle fonti, che segna CANONE/MANUALE
  come rara; G-4 e G-10 con «TIMESHEET: modulo futuro».
* 📄 Documentazione già stantia, non per queste decisioni: `vendite/manual/contratti.md` §cessazione («non
  esiste un'azione per cessare, si scrive `valido_al`»: superata da `fn_cessa_contratto`, 26-10);
  `vendite/manual/contratti_righe.md` §Scopo («ogni riga rappresenta un articolo/servizio»: contraddice il
  modello a eccezioni). Da correggere nel giro.

### 4.2 Le domande, con la proposta del team DB (2026-10-28)

* **G-0** — che cosa si addebita a ogni periodo: (a) solo le righe del contratto; (b) il listino
  congelato espanso — le righe periodiche del listino, con gli OVERRIDE al loro posto, più le AGGIUNTA,
  meno le ESCLUSIONE; (c) un tipo di riga nuovo, «sottoscrizione». (Proposta: **b**; da dire la quantità
  di una riga di listino per periodo.)
* **G-0-bis** — dove vive la periodicità di una riga di listino (riga, tipologia, articolo), e se
  `periodicita` e `competenza_canone` diventano vocabolari con FK, con `periodicita` obbligatoria sulle
  CANONE;
* **G-1** — chi genera i periodi del canone (domanda 1). (Proposta: il lister, periodi maturati a ogni
  giro, idempotenza dalla chiave `:M:`.)
* **G-2** — l'orizzonte per un contratto senza scadenza (domanda 2), e i contratti CESSATO (§2-bis.1).
  (Proposta: fino al periodo che contiene la data del giro — corrente se anticipato, solo chiusi se
  posticipato; i CESSATO generano fino a `valido_al`.)
* **G-3** — la sede della regola di competenza del periodo (domanda 3). (Proposta: due assi, momento
  `ANTICIPATO`/`POSTICIPATO` e periodo parziale `INTERO`/`PRORATA`, `competenza_canone` ritirata; una
  funzione che data la riga e una data dà i periodi, letta dal lister e dalla dashboard.)
* **G-4** — ORARIO e CONSUMO: dal contratto o dalle loro sorgenti (domanda 4). (Proposta: fuori da questo
  brief TIMESHEET e LETTURE, che non hanno sorgente; per le MANUALE dire dove si scrive la quantità.)
* **G-5** — il canone anticipato di un contratto che cessa a metà periodo: storno del rateo in commessa,
  o fuori da questo brief;
* **G-6** — la commessa del contratto: i periodi si accumulano in quella viva finché non si fattura e
  chiude, oppure una commessa per periodo.

## 5. Cosa resta valido nel frattempo

* ~~Il lister dei contratti manda solo le UNA_TANTUM (`20261013-24`).~~ Superato dal L7 (`20261030-01`,
  §6.12): il canone parte a periodi. Il presidio era
  `vendite/test-push-contratto-dalla-madre-v1` (parte D) e
  `vendite/test-righe-erogazione-obbligatoria-v1` (19, 21).
* ⚠️ Quando la generazione arriva, il filtro `cr.tipo_erogazione = 'UNA_TANTUM'` del lister si
  allarga, e i due test sopra cambiano con lui: non vanno «aggiustati», raccontano la regola.
  **Esito (2026-10-30, L7):**
  * la parte D è riscritta (§6.12);
  * i test 19 e 21 di `test-righe-erogazione-obbligatoria-v1` restano verdi. Il 19 (un OVERRIDE a
    CONSUMO non si lista) ora passa per **due** ragioni: CONSUMO non è generato (G-4), e l'OVERRIDE non si
    addebita più (F-1). La sua descrizione «solo UNA_TANTUM» è ritoccata nel L9 (§6.14).

## 6. La forma (team DB, 2026-10-29; via di Tid all'analisi e all'inizio dello sviluppo)

### 6.1 I fatti di struttura che la forma usa (dbdev e doc auto-generata, 2026-10-29)

* `vendite.tipo_eccezione_contratto` (OVERRIDE, ESCLUSIONE, AGGIUNTA) è **un tipo solo** per contratto e
  offerta: ADESIONE si aggiunge una volta e vale per le due (G-11).
* Il tipo è letto da **20 funzioni** (resolver `fn_resolve_prezzo_listino_v2` e `_esito`, picker
  `catalogo.fn_articoli_ammessi`, le check `fn_check_articolo_riga*`, `fn_check_riga_*`, le preview
  `fn_contratto_righe_preview`, `fn_offerta_righe_preview`, `fn_documento_righe_*`, la capability
  `fn_available_actions_contratto`, `trgfn_contratti_freeze_listino_versione`, il lister), più due
  indici unici parziali per tabella (`uq_*_one_eccezione_per_articolo` su OVERRIDE/ESCLUSIONE,
  `uq_*_one_aggiunta_per_articolo`).
* `competenza_canone` la leggono 4 funzioni (`script.trgfn_righe_guard_esclusione_senza_dati`,
  `vendite.fn_crea_revisione_offerta`, `vendite.fn_list_contratti_da_pushare`,
  `vendite.fn_push_offerta_a_contratto`) e i CHECK `chk_*_esclusione_senza_dati`; `periodicita` e
  `generazione_canone` le stesse più `trgfn_righe_default_erogazione_da_articolo`,
  `fn_articolo_erogazioni`, `fn_documento_riga_erogazioni`. Lato BE: `contratti_repository`,
  `offerte_repository`, `_documento_eccezioni_repo`, `contratti_service`, `offerte_service`,
  `_schema_da_contratto`, `_riga_erogazioni_views`, `types.py`; lato FE `erogazioniRiga.js`.
* ⚠️ **Il CHECK `chk_*_coerenza_canone` non ha mai reso obbligatoria `generazione_canone`**: con
  `generazione_canone` NULL l'espressione vale NULL e un CHECK che vale NULL passa. Su dbdev
  (2026-10-29, fatto datato) 10 righe di contratto e 12 di offerta a canone hanno `generazione_canone`
  e `periodicita` vuote. Il difetto è sul modello: si corregge col CHECK riscritto (Lotto 1).
* Le unità di misura hanno un tipo (`catalogo.uom_tipi`): `GG`, `MESE` e `HH` sono `TEMPO`. Quale
  unità si conta dal calendario (giorni o mesi) non lo dice nessuna colonna.
* `vendite.listini_righe` non ha colonne d'erogazione; la riga di listino eredita l'erogazione
  dall'articolo (`fn_articolo_erogazioni`). La tipologia `QUOTA_FISSA` (`e_quota_fissa`) esiste.

### 6.2 La forma, pezzo per pezzo

| Pezzo | Forma |
| --- | --- |
| **Periodicità** (G-0-bis) | vocabolario `config.periodicita` (codice, descrizione, `mesi` divisore di 12, ordine), FK da `contratti_righe`, `offerte_commerciali_eccezioni` e dalla colonna nuova `listini_righe.periodicita` |
| **Regola del canone sulla riga** (G-7) | `chk_*_coerenza_canone` riscritto senza il NULL che passa: su una riga CANONE `generazione_canone` in (`INIZIO_PERIODO`, `FINE_PERIODO`) **e** `periodicita` valorizzata (quest'ultima nel Lotto 4, §6.5). PRORATA esce. Stesso dominio sui vocabolari `listini_tipologie_erogazioni` e `nature_vendita_erogazioni` |
| **Periodicità della riga di listino** | obbligatoria sulla riga di una **quota fissa** (guard sulla riga di listino: dipende dall'articolo, non è un CHECK); sulle altre è il default che l'ADESIONE eredita |
| **Fonte «durata»** (G-9) | `config.erogazioni_fonti`: via `CANONE/MANUALE`, entra `CANONE/DURATA`; la quantità non sta sulla riga (`script.fn_fonte_porta_quantita` = false); l'articolo deve avere un'unità che si conta dal calendario: colonna nuova su `catalogo.unita_misura` (`conta_dal_calendario`: `GIORNO` / `MESE` / NULL), il guard la legge, il generatore pure |
| **Ritiro di `competenza_canone`** (G-8) | colonna via da contratto e offerta, i 4 lettori e i 2 CHECK riscritti nello stesso giro |
| **ADESIONE** (G-0-ter) | valore nuovo dell'enum; prezzo NULL (`chk_*_prezzo_per_tipo_eccezione`); solo su un articolo del listino (le check di ammissione, come l'OVERRIDE); esclusiva con OVERRIDE ed ESCLUSIONE sullo stesso articolo (indice unico parziale allargato); il resolver la tratta come la riga di listino (prezzo del listino + variazione globale); periodicità di default dalla riga di listino; verbo «aderisci» nella capability delle righe di listino; offerta, revisione dell'offerta e passaggio a contratto la portano |
| **Finestra del giro** (G-2) | colonna sul contratto, `fine_finestra_canone` (`FINE_MESE_FATTURA` / `FINE_MESE_PRECEDENTE`), NOT NULL con default; il default per utility è rimandato (G-2) |
| **La regola dei periodi** (G-3) | **una** funzione pura: data la riga (inizio, fine contratto, periodicità, momento, fonte, unità) e la finestra, restituisce i periodi da addebitare con `periodo_dal`, `periodo_al`, la frazione in proporzione ai giorni e, per la durata, la quantità contata. La leggono il lister e la dashboard (`CANONE_NON_GENERATO`) |
| **Il lister** (G-1, G-2) | tre rami: UNA_TANTUM come oggi; i periodi del canone dalle righe (quote fisse del listino, ADESIONE, OVERRIDE, AGGIUNTA a canone); gli storni (G-5). Legge ATTIVO e CESSATO, con le date. La chiave resta col mese di inizio periodo; per le quote fisse del listino, che non hanno una riga di contratto, la chiave nomina la riga di listino (grammatica di `script.fn_segment_key` da estendere) |
| **Lo storno** (G-5) | una riga negativa della parte non goduta, chiave del periodo con un suffisso proprio, quando `valido_al` cade dentro un periodo già addebitato in anticipo |
| **La commessa** (G-6) | niente di nuovo: la madre e `fn_get_or_create_commessa` già tengono una commessa viva per sorgente |

### 6.3 I lotti

| Lotto | Che cosa | Dipende da |
| --- | --- | --- |
| **L1** ✅ applicato | periodicità (vocabolario, FK, colonna del listino), CHECK del canone riscritto (generazione obbligatoria, PRORATA via) | dati dbdev (§6.4, F-5) |
| **L2** ✅ applicato | fonte DURATA: vocabolario, colonna sull'unità di misura, guard, `fn_fonte_porta_quantita` | — |
| **L3** ✅ applicato | ritiro di `competenza_canone` | — |
| **L4a** ✅ applicato · **L4b** ✅ applicato | ADESIONE (l'OVERRIDE non si addebita più, F-1); periodicità obbligatoria sulla riga a canone, col default dalla riga di listino | F-1 ✅ |
| **L5** ✅ applicato | testata di contratto e offerta: mese di partenza (F-2) e anticipato/normale (F-7) con la riga che segue la testata; `chk_*_coerenza_canone` del `-14` riscritto (NULL ammesso); default dall'articolo e da tipologia/natura ritirato. ~~Finestra~~ (F-4 superata) | F-2 ✅, F-7 ✅ |
| **L6** ✅ applicato | la regola dei periodi (funzione pura + pgTAP): mese di partenza, parziale a giorni a inizio e fine, spezzatura al 31/12, importi a mesi con resto sull'ultima riga; competenza `competenza_mese` = mese del giro, `dal`/`al` = periodo | F-2 ✅, F-6 ✅ |
| **L7** ✅ applicato (§6.12) | il lister (tre rami, chiave delle quote fisse, prezzo, storni); richiesta BE: commessa del contratto senza periodo | L1 … L6 |
| **L8** ✅ applicato (§6.13) | lo storno come differenza (la fine che si sposta); la sede `fn_contratti_addebiti_maturati`; la dashboard dei contratti (`CANONE_NON_GENERATO`, `CANONE_NON_GENERABILE`) | L6, L7 |
| **L9** ✅ scritto (§6.14) | documentazione: guide di contratti, offerte, listini e cruscotti; manual stantii (§4.3) e quelli del L7/L8; pgTAP del §5 | tutti |
| BE/FE | richiesta a giro DB provato, elenco chiuso | L7 |

### 6.4 Domande che l'analisi fa emergere (per Tid)

* **F-1 — L'OVERRIDE si addebita?** Oggi il push manda in commessa, all'attivazione, le OVERRIDE e le
  AGGIUNTA una tantum. Ma l'OVERRIDE dà anche il prezzo agli acquisti puntuali del cliente (preventivi
  e ordini, origine `CONTRATTO_OVERRIDE`): se Rossi ha un prezzo suo per «intervento tecnico» e il
  contratto glielo addebita all'attivazione, poi glielo riaddebita il preventivo. Con l'ADESIONE la
  domanda diventa: OVERRIDE = «lo prende a un prezzo suo» (si addebita, come l'ADESIONE) oppure =
  «solo il suo prezzo, se e quando lo compra» (non si addebita)?
  **Deciso (Tid, 2026-10-29): l'OVERRIDE è solo il prezzo del cliente, il contratto non lo
  addebita.** Chi si addebita è l'ADESIONE. Il push smette di mandare le OVERRIDE in commessa (L4/L7).
* **F-2 — I periodi seguono il calendario o l'inizio del contratto?** Calendario: trimestri gen/apr/lug/ott,
  anno solare, e il primo periodo è parziale (in proporzione). Inizio del contratto: il trimestre parte
  dal giorno di attivazione e il primo periodo è sempre intero; il parziale c'è solo alla fine.
  (Proposta: calendario — è il caso che le decisioni G-3 e G-5 descrivono.)
  **Deciso (Tid, 2026-10-29):** calendario con un **mese di partenza** sul **contratto** (default
  gennaio = calendario normale). I periodi cominciano sempre il giorno 1 del mese; il mese di partenza
  dice da quale mese si conta (trimestrale da febbraio: feb-apr, mag-lug, ago-ott, nov-gen). Il periodo
  incompleto si paga a giorni sia all'**inizio** sia alla **fine** del contratto. Un periodo che scavalca
  il 31/12 si **spezza in due righe di commessa**, una per anno (dic-feb → dic + gen-feb), per la
  competenza contabile: è un calcolo della funzione dei periodi (L6), non un dato. Ricade su L5 (colonna
  sul contratto) e L6.
  **Importi (Tid, 2026-10-29):** i mesi interi si dividono **a mesi** (trimestre dic-feb da 300 € →
  dic 100, gen-feb 200); i **giorni** solo per il mese a metà (inizio o fine contratto); l'arrotondamento
  va sull'**ultima** riga, la somma torna esatta al centesimo.
* **F-3 — Le periodicità:** MENSILE, BIMESTRALE, TRIMESTRALE, QUADRIMESTRALE, SEMESTRALE, ANNUALE
  (i divisori di 12: con il calendario un periodo non scavalca l'anno). Proposta, scritta nel CSV del L1.
  **Deciso (Tid, 2026-10-29): le sei restano.** Biennale/triennale non servono come periodicità: un
  contratto di più anni con canone annuale si addebita ogni anno da solo. Il caso «pago una volta per
  tre anni» non è un canone periodico (una tantum).
* **F-4 — Il default della finestra sul contratto:** `FINE_MESE_FATTURA` (proposta) o
  `FINE_MESE_PRECEDENTE`.
  **Superata (Tid, 2026-10-29): la finestra si TOGLIE — revoca del «fino a» di G-2.** La finestra e
  `generazione_canone` rispondevano alla stessa domanda («quando si addebita un periodo?») e due
  combinazioni su quattro davano il risultato sbagliato. Decide solo la riga: `INIZIO_PERIODO`
  (canoni anticipati) = il periodo si addebita appena **cominciato**; `FINE_PERIODO` (canoni normali) =
  appena **finito**, rispetto alla data del giro. Il «da» di G-2 resta (giorno dopo l'ultimo addebito:
  i periodi arretrati si recuperano). Esempio di Tid: bimestrale, contratto dal 15/01, giro di marzo →
  normale 15/01-28/02; anticipato 15/01-28/02 + 01/03-30/04 (una riga per periodo). L5 non ha più la
  colonna della finestra: resta il mese di partenza (F-2).
* **F-5 — Le righe di prova di dbdev** (10 di contratto, 12 di offerta, a canone senza generazione e
  periodicità): il CHECK nuovo non si applica finché ci sono. Sono dati di sviluppo: correggerle a mano
  o cancellarle è più veloce di un changeSet di bonifica (regola di AGENTS.md). Le righe dei contratti
  attivi sono ferme per i guard: la correzione si fa da owner.
* **F-6 — Che cos'è la «data fattura» della finestra:** il push gira prima della fattura e non la
  conosce. Proposta: la data di riferimento del giro (il mese passato al push, o l'oggi aziendale).
  **Deciso (Tid, 2026-10-29): la data del giro.** Competenza della riga di commessa (confermata):
  `competenza_mese` = mese del giro (la fattura prende le righe con competenza `<=` il suo mese, quindi
  anche gli arretrati); `competenza_dal`/`_al` = il periodo addebitato, una riga per anno se scavalca.

* **F-7 — Anticipato o normale: testata o riga?** **Deciso (Tid, 2026-10-29): revoca di G-3 (28-10) e del
  default di `generazione_canone` dall'articolo e da tipologia/natura (`20261007-51`, `-62`).** Il valore
  sta sulla **testata** di contratto e offerta (colonna nuova NOT NULL, default `INIZIO_PERIODO` =
  anticipato; il passaggio offerta → contratto la copia, G-11). La riga **resta**: `generazione_canone`
  vuota = **segue la testata** (ereditarietà viva, scelta (a): cambiando la testata cambiano le righe non
  forzate); valorizzata = forzata su quella riga. Ricadute: il `chk_*_coerenza_canone` del `-14` si
  riscrive (NULL ammesso, PRORATA resta fuori); `trgfn_righe_default_erogazione_da_articolo` smette di
  scrivere `generazione_canone`; i vocabolari tipologia/natura perdono la colonna (o il valore; da
  decidere nel lotto, censendo i lettori); il lister legge `coalesce(riga, testata)`. BE/FE: il campo
  entra nella testata, sulla riga diventa facoltativo.

* **F-8 — Canone su un articolo a giorni o a mesi: quale fonte si propone?** Se l'operatore sceglie
  «canone» senza la fonte, oggi l'eredità prende `DURATA` (i giorni o i mesi li conta il sistema) e non
  `FISSA` (quantità scritta sulla riga), ma per ordine alfabetico. Proposta: `DURATA` di proposito, scritto
  nella regola dell'ordine. **Deciso (Tid, 2026-10-29): sì, regola scritta** (`20261029-35`): dove la durata
  c'è, per il canone viene prima della FISSA e, se il default della base è un canone, è lei il default.

* **F-9 — La periodicità di un canone fuori listino (AGGIUNTA).** ADESIONE e OVERRIDE la prendono dalla
  riga di listino; un'AGGIUNTA non ha una riga di listino. Proposta: obbligatoria, la scrive l'operatore
  (il form la deve chiedere). **Deciso (Tid, 2026-10-29): (a), obbligatoria, la scrive l'operatore.** Un
  default «mensile» farebbe passare in silenzio l'errore (un canone annuale fatturato dodici volte).
* **F-10 — Le righe di prova senza periodicità** (dbdev: 10 di contratto, 12 di offerta): correggerle a
  mano con MENSILE, come F-5, o cancellarle. **Deciso (Tid, 2026-10-29): lo script** (§6.10, provato in
  transazione annullata), da lanciare da owner prima dell'apply del L4b.

* **F-11 — L'importo del periodo spezzato al centesimo.** La riga di commessa porta quantità (6 decimali)
  e prezzo, non un importo: il «resto sull'ultima riga» è applicato alla frazione (§6.7), e l'euro lo
  arrotonda la fattura riga per riga. Un centesimo di scarto su un periodo spezzato non è escluso. Da
  decidere prima del lister: basta così, o serve un importo sulla riga di commessa?
  **Deciso (Tid, 2026-10-30): (a), basta così.** La riga di commessa resta quantità × prezzo, la fattura
  non si tocca. Perché un importo sulla commessa non basterebbe: la fattura non lo legge, somma le
  attività in una riga e ricalcola l'imponibile col trigger `trg_fatture_righe_a20_importo_ins_upd`
  (un valore passato da fuori viene sovrascritto, `pipeline_repository.batch_insert_righe_and_mark`).
  Perché lo scarto è quasi nullo: la spezzatura è solo al 31/12, quindi al massimo **due** pezzi con
  frazioni che sommano 1; con due pezzi l'arrotondamento perde il centesimo solo se tutti e due gli
  importi cadono esattamente sul mezzo centesimo. Da riaprire se un periodo si spezzasse in tre o più.

* **F-12 — Che cosa è il L8 (decisa da Tid il 2026-10-30: (a); i dati attuali restano come sono, nessuna correzione).** Il brief nomina la dashboard ma non ne ha mai deciso la
  forma. Cosa c'è oggi (dbdev, doc auto-generata):
  * `vendite.vw_dash_fatturazione_contratti` (dashboard di pre-fatturazione, area CONTRATTO) ha il
    giudizio di transito **sospeso** dal `20260707-03`: `motivo_fermo` NULL per tutti, «finché non esiste
    il push ricorrente», perché senza push ogni contratto sarebbe stato un falso allarme perenne. Il
    Backlog non vede i contratti;
  * il codice `CANONE_NON_GENERATO` è nel seed di `config.motivi_fermo` **apposta**, per la riaccensione
    (classe FISIOLOGICO, nessuna azione), e nessuna vista lo produce.

  Il push ricorrente adesso esiste (L7). La domanda:
  * **(a)** riaccendere il giudizio in quella vista: il contratto è fermo se ha un pezzo di canone
    maturato che non è in commessa. I contratti tornano nel Backlog;
  * **(b)** una lista a parte, solo per le righe che il lister salta (senza periodicità, senza prezzo,
    durata su unità non a calendario), e la vista resta sospesa.

  Proposta del team DB: **(a)**. Le domande che seguono (i motivi, la classe) dipendono da questa.

* **F-13 — La classe di `CANONE_NON_GENERATO` (decisa da Tid il 2026-10-30: (a)).** Il Backlog esclude a monte la classe
  FISIOLOGICO (`vw_dash_backlog_documenti`, filtro `classe <> 'FISIOLOGICO'`; `vw_dash_backlog_riepilogo`
  idem). Con la classe di oggi il contratto fermo comparirebbe nella situazione aperta ma **non** nel
  Backlog, contro quanto detto nella (a) di F-12.
  * **(a)** RECUPERABILE, azione «Esegui il push dei canoni», come `PUSH_NON_ESEGUITO` degli ordini: il
    contratto con un pezzo maturato non in commessa entra nel Backlog;
  * **(b)** resta FISIOLOGICO: si vede solo nella situazione aperta.

  Proposta del team DB: **(a)**. Il pezzo maturato è fatturabile e non è in commessa: è lo stesso caso
  dell'ordine confermato senza push.

* **F-14 — Un secondo motivo per le righe che il lister salta (decisa da Tid il 2026-10-31: (a)).** Il lister non manda
  la riga a canone senza periodicità, quella senza prezzo alla data e quella a durata su un'unità che non
  si conta dal calendario (§6.12). Il push non le sistema: va corretta la riga.
  * **(a)** un motivo nuovo in `config.motivi_fermo` (per esempio `CANONE_NON_GENERABILE`), RECUPERABILE,
    azione «Completa la riga del contratto». La vista ha una riga per contratto, quindi un motivo solo:
    se il contratto ha entrambi i casi vince questo, perché il push da solo non lo chiude;
  * **(b)** nessun motivo nuovo: anche queste righe danno `CANONE_NON_GENERATO`, e chi apre il contratto
    scopre perché.

  Proposta del team DB: **(a)**. Le due azioni sono diverse (lanciare il push o correggere la riga), e la
  dashboard deve dire quale.

* **F-15 — L'azione del motivo per le righe saltate non si può fare (decisa da Tid il 2026-10-31: (a)).** ⚠️ Corregge
  la proposta del team DB su F-14. L'azione «Completa la riga del contratto» presupponeva una riga
  modificabile, ma fuori dalla bozza le righe del contratto sono chiuse, in ogni stato (§6.13). Su un
  contratto ATTIVO la riga senza periodicità non si completa più. Il motivo resta giusto, l'azione no.
  * **(a)** classe ANOMALIA con l'azione «Rivedi il contratto», come `FIGLIO_ABORTITO` («Rivedi
    l'offerta»): la segnalazione dice che il canone non partirà, e il rimedio è fuori dalla riga (un
    contratto nuovo, o un prezzo nel listino quando manca quello);
  * **(b)** si apre la riga fuori dalla bozza per le colonne del canone (periodicità, prezzo): è una
    **revoca** della regola «le righe si toccano solo in bozza» (`E_RIGA_DOC_NON_BOZZA`, 2026-09-22).

  Proposta del team DB: **(a)**. Col passaggio BE/FE la periodicità diventa obbligatoria e il L2 già
  rifiuta la durata su un'unità che non si conta dal calendario: questa segnalazione riguarderà
  soprattutto il prezzo che manca alla data, e i contratti attivati prima dell'obbligo.
### 6.5 Lotto 1 — scritto (2026-10-29)

Numerazione: dal primo numero libero del giorno (Tid, 2026-10-29), `20261029-10` … `-14`. ⚠️ Un'altra
sessione scrive oggi i `20261029-0x` del listino: prima dell'apply va ricontrollato che nessuno dei due
abbia preso gli stessi numeri.

| changeSet | Che cosa |
| --- | --- |
| `00_schema/config/20261029-10-create-periodicita` | `config.periodicita`: codice, descrizione, `mesi` (divisore di 12, CHECK), `ordine`; niente `attivo` (è ciò che il modello ammette, come `erogazioni_fonti`) |
| `00_schema/vendite/20261029-11-alter-listini-righe-periodicita` | colonna `listini_righe.periodicita` (nullable; la FK in 80_data). Le righe fuori dalla BOZZA restano ferme dal guard di stato |
| `80_data/changelog/20261029-12-seed-periodicita` + `80_data/sql/config/periodicita.csv` | i sei valori di F-3 |
| `80_data/changelog/20261029-13-fk-periodicita` | le tre FK verso il vocabolario (in 80_data, dopo il seed: forma di `20261007-54`); i COMMENT delle colonne gemelle rimandano al vocabolario |
| `80_data/changelog/20261029-14-check-coerenza-canone` | `chk_contrighe_coerenza_canone` e `chk_offerte_eccezioni_coerenza_canone` riscritti con lo stesso nome (la generazione obbligatoria sulle righe CANONE senza il NULL che passava, PRORATA via); dominio di `generazione_canone` sui due vocabolari dell'erogazione. ⚠️ Su dbdev si applica solo dopo F-5 |

**Cambio rispetto alla forma (§6.2): l'obbligo della periodicità sulla riga a canone non è nel
Lotto 1.** Il frontend oggi non manda la periodicità (`erogazioniRiga.js` non la conosce): con l'obbligo,
nessuna riga a canone si salverebbe più dall'app. Arriva nel Lotto 4 (ADESIONE), insieme al default dalla
riga di listino e al passaggio BE/FE. La generazione invece si rende obbligatoria subito: se manca la
prende già dall'articolo `script.trgfn_righe_default_erogazione_da_articolo`, e nessuno deve mandarla.

**Prova (2026-10-29, dbdev, come owner, transazione annullata; SQL estratto dai changeSet, seed simulato
dal CSV — il loader vero lo prova l'apply):**

* `-10` … `-13` passano; `-14` si ferma su `chk_contrighe_coerenza_canone` per le righe di prova (F-5),
  come atteso;
* con la correzione di F-5 nella stessa transazione passano tutti;
* casi negativi: riga CANONE senza generazione rifiutata, `PRORATA` rifiutato, periodicità fuori
  vocabolario rifiutata (FK), `mesi = 5` rifiutato; `TRIMESTRALE` / `FINE_PERIODO` accettati;
* censimento: nessun pgTAP, backend o frontend usa `PRORATA` o una periodicità fuori dai sei valori; i
  pgTAP che scrivono righe a canone senza generazione la ricevono dal trigger dell'articolo. La corsa
  pgTAP come app resta di Tid.

**F-5, la correzione dei dati di prova su dbdev** (da owner, prima dell'apply del `-14`). I guard di riga
tengono ferme le righe fuori dalla bozza anche per l'owner: i trigger si spengono solo per la durata della
transazione (provato nella stessa prova):

```sql
BEGIN;
ALTER TABLE vendite.contratti_righe DISABLE TRIGGER USER;
ALTER TABLE vendite.offerte_commerciali_eccezioni DISABLE TRIGGER USER;
UPDATE vendite.contratti_righe
   SET generazione_canone = 'INIZIO_PERIODO'
 WHERE tipo_erogazione = 'CANONE' AND generazione_canone IS NULL;
UPDATE vendite.offerte_commerciali_eccezioni
   SET generazione_canone = 'INIZIO_PERIODO'
 WHERE tipo_erogazione = 'CANONE' AND generazione_canone IS NULL;
ALTER TABLE vendite.contratti_righe ENABLE TRIGGER USER;
ALTER TABLE vendite.offerte_commerciali_eccezioni ENABLE TRIGGER USER;
COMMIT;
```

In alternativa, le 22 righe si cancellano (sono dati di prova).

### 6.6 Lotto 5 — applicato (2026-10-29)

La testata del documento dice come si addebitano i canoni (F-2, F-7); la riga vuota la segue.
Numerazione: `20261029-15` … `-24` (primo libero dopo il L1).

| changeSet | Che cosa |
| --- | --- |
| `00_schema/vendite/20261029-15-alter-contratti-offerte-testata-canone` | su `vendite.contratti` e `vendite.offerte_commerciali`: `generazione_canone` NOT NULL default `INIZIO_PERIODO` (dominio INIZIO/FINE) e `mese_partenza_canone` NOT NULL default 1 (1-12) |
| `00_schema/config/20261029-16-drop-check-erogazioni-generazione-canone` | via `chk_*_canone` e `chk_*_generazione_canone` dai vocabolari tipologia/natura. In 00_schema perché da zero il seed `20261007-53` non scrive più la colonna |
| `20_code/vendite/20261029-17-update-fn-articolo-erogazioni-senza-generazione` | DROP + CREATE senza `generazione_canone` nell'uscita (`%TYPE` dall'ultimo YAML, GRANT come prima) |
| `20_code/vendite/20261029-18-update-fn-documento-riga-erogazioni-senza-generazione` | idem per la lettura del form |
| `20_code/script/20261029-19-update-trgfn-righe-default-erogazione-senza-generazione` | il trigger d'eredità non scrive più la generazione (né su INSERT né su UPDATE OF tipo_erogazione) |
| `20_code/vendite/20261029-20-remount-trg-doc-testata-lock-canone` | le due colonne nuove fra le condizioni ferme fuori dalla bozza (`E_DOC_CONDIZIONI_FUORI_BOZZA`), su contratto e offerta |
| `20_code/vendite/20261029-21-update-fn-push-offerta-a-contratto-testata-canone` | il push copia le due colonne della testata |
| `20_code/vendite/20261029-22-update-fn-crea-revisione-offerta-testata-canone` | la revisione dell'offerta le copia |
| `80_data/changelog/20261029-23-check-coerenza-canone-riga-segue-testata` | `chk_*_coerenza_canone` senza l'obbligo: vuota = segue la testata; resta il dominio, PRORATA fuori |
| `80_data/changelog/20261029-24-drop-erogazioni-generazione-canone` | via la colonna dai due vocabolari. In 80_data perché da zero i changeSet vecchi di 20_code ne prendono il tipo (`%TYPE`) e il seed `-53` e il `-14` vengono prima |

**Toccati changeSet esistenti (non ancora committati, o con `validCheckSums ANY`):**

* `20261029-14`: tolto il dominio sui vocabolari (da zero la colonna non ci sarebbe più); aggiunto
  `validCheckSums: ANY`, perché su dbdev è già applicato e non si ripete;
* `20261007-53` (seed, `runOnChange` + `ANY`) e i due CSV `listini_tipologie_erogazioni.csv`,
  `nature_vendita_erogazioni.csv`: senza la colonna `generazione_canone`.

**Scelta del team DB, confermata da Tid (2026-10-29):** fuori dalla bozza le due colonne della testata sono **ferme**,
come listino e validità. Cambiarle su un contratto attivo cambierebbe i periodi già addebitati.

**Le righe di oggi:** le righe CANONE già scritte hanno la generazione che l'articolo (o F-5) ci aveva
messo, e restano **forzate** con quel valore. Non si sa quali fossero scelte dell'operatore e quali il
default. Sui dati di sviluppo, se si vuole che seguano la testata, si svuotano a mano.

**Prova (2026-10-29, dbdev, owner, transazione annullata, SQL estratto dai changeSet; sorgenti dei corpi
confrontati col catalogo vivo, identici):** tutto si applica. Testate col default; vocabolari senza
colonna; il form restituisce le combinazioni senza generazione; una riga CANONE si svuota in bozza;
PRORATA rifiutata; testata in bozza modificabile, su contratto ATTIVO e offerta ACCETTATA ferma
(`E_DOC_CONDIZIONI_FUORI_BOZZA`); mese 13 rifiutato; la revisione dell'offerta e il push (con
successione) copiano `FINE_PERIODO`/mese; cambiando l'erogazione verso CANONE la generazione resta vuota.

**pgTAP aggiornati (la corsa come app resta di Tid):**

* `vendite/test-righe-erogazione-da-articolo-v1`: test 5 e 18 attendono la generazione vuota; le letture
  del form (16, 21, 22) senza la colonna; **nuovo 23**: il push copia la testata (plan 22 → 23);
* `vendite/test-erogazioni-vocabolario-v1`: il test 8 ora presidia che i vocabolari **non** abbiano la
  colonna (per OID);
* `vendite/test-push-contratto-dalla-madre-v1`: solo un commento.

**⚠️ Rottura BE all'apply (accettata fino a fine cantiere, ma da sapere prima):**
`backend/apps/vendite/db/_documento_eccezioni_repo.py` (`list_erogazioni_riga`) seleziona
`generazione_canone` da `vendite.fn_documento_riga_erogazioni`: dopo il `-18` l'endpoint delle
combinazioni della riga va in errore. Richiesta BE/FE (nel passaggio dopo il L7, o subito se serve il form):

1. togliere `generazione_canone` da `list_erogazioni_riga`, dal serializer di `_riga_erogazioni_views.py`
   e da `types.py`; il FE (`erogazioniRiga.js`) non la preseleziona più dall'articolo;
2. testata di contratto e offerta: i due campi nuovi `generazione_canone` (Anticipati / Normali) e
   `mese_partenza_canone` (1-12), modificabili solo in bozza;
3. riga: `generazione_canone` facoltativa, vuota = «come la testata».

### 6.7 Lotto 6 — applicato (2026-10-29)

| changeSet | Che cosa |
| --- | --- |
| `20_code/vendite/20261029-25-create-fn-canone-periodi` | `vendite.fn_canone_periodi(valido_dal, valido_al, periodicita, mese_partenza, generazione, data_giro, dal = NULL)`: il building block puro della regola dei periodi. Restituisce i pezzi da addebitare (`periodo_dal`/`_al`, `competenza_mese`, `frazione` del periodo intero a 6 decimali, `periodo_intero_dal`/`_al`). STABLE, SECURITY INVOKER, `%TYPE` su parametri, uscita e DECLARE; GRANT solo a `zeroerp_app` |

La regola, come decisa da Tid:

* periodi di calendario dal mese di partenza, dal giorno 1 (F-2);
* anticipati: il periodo si addebita appena **cominciato** (inizio ≤ data del giro); normali: appena
  **finito** (fine < data del giro), con inizio e fine tagliati sulla validità del contratto (F-7);
* il «da» è il giorno dopo l'ultimo addebito; gli arretrati dovuti si recuperano (G-2);
* l'ultimo periodo si taglia alla fine del contratto, anche CESSATO (G-2);
* un periodo che scavalca il 31/12 si spezza, un pezzo per anno (F-2);
* frazione: i mesi interi contano 1, il mese a metà giorni coperti / giorni del mese, diviso i mesi del
  periodo; il resto dell'arrotondamento va sull'ultimo pezzo del periodo (F-2, importi);
* `competenza_mese` = il mese del giro (F-6).

La generazione da passare è quella che **vale**, `coalesce(riga, testata)`: la sceglie chi chiama (il
lister, L7).

**⚠️ Un punto da sapere sugli importi.** La riga di commessa non ha una colonna d'importo: porta
`quantita` (6 decimali) e `prezzo_snapshot`. Il «resto sull'ultima riga» deciso da Tid si applica quindi
alla **frazione**: i pezzi di un periodo sommano esattamente la frazione del periodo. L'importo in euro
lo arrotonda la fattura, riga per riga. Nei casi provati (terzi, mesi a metà) la somma torna al
centesimo; un centesimo di scarto su un periodo spezzato non è escluso in teoria. Se serve l'esattezza
al centesimo garantita, la strada è un importo sulla riga di commessa: è una decisione di Tid, da
prendere col lister (L7).

**Prova (2026-10-29, dbdev, owner, transazione annullata, SQL estratto):** i casi del pgTAP tornano tutti:
* l'esempio di Tid (bimestrale dal 15/01, giro di marzo: normale 15/01-28/02 = 0,774194; anticipato
  anche 01/03-30/04);
* trimestrale da novembre spezzato al 31/12 (2/3 + 1/3 = 1);
* annuale da luglio dal 15/08 (0,379032 + 0,5);
* cessato il 15/03 (15/31);
* il «da»;
* il normale non finito;
* gli errori sui parametri.

**pgTAP nuovo:** `vendite/test-canone-periodi-v1` (15 test, senza fixture): verde come app (Tid, 2026-10-29), dopo la correzione del test 15 (`"char" || text` ambiguo: cast esplicito).

### 6.8 Lotto 3 — applicato (2026-10-29)

Ritiro di `competenza_canone` (G-8). La sostituisce la regola dei periodi del L6; su dbdev la colonna era
vuota su tutte le righe (fatto datato, 2026-10-29).

| changeSet | Che cosa |
| --- | --- |
| `00_schema/vendite/20261029-26-drop-righe-competenza-canone` | DROP COLUMN da `contratti_righe` e `offerte_commerciali_eccezioni`; `chk_*_esclusione_senza_dati` riscritti con lo stesso nome e i nove campi che restano (il DROP COLUMN li avrebbe portati via in silenzio) |
| `20_code/script/20261029-27-update-trgfn-righe-guard-esclusione-senza-competenza` | il guard d'esclusione perde l'ultimo campo dell'elenco (stesso elenco del CHECK) |
| `20_code/vendite/20261029-28-update-fn-crea-revisione-offerta-senza-competenza` | la revisione non la copia più |
| `20_code/vendite/20261029-29-update-fn-push-offerta-a-contratto-senza-competenza` | il push non la copia più |
| `20_code/vendite/20261029-30-update-fn-list-contratti-da-pushare-senza-competenza` | il lister non la mette più nel `meta` (il resto lo riscrive il L7) |
| `80_data/sql/config/codici_errore.csv` | la descrizione di `E_RIGA_ESCLUSIONE_CON_DATI` elenca nove campi |

**In 00_schema perché:** nessun changeSet ne prende il tipo (`%TYPE`); nessuno di 80_data, 85_pgagent o
90_end la nomina, a parte la descrizione del CSV. I corpi sorgente sono stati confrontati col catalogo
vivo e sono identici.

**Prova (2026-10-29, dbdev, owner, transazione annullata):**
* colonna sparita, i due CHECK ci sono;
* nessuna funzione la nomina più (`prosrc`);
* il lister risponde;
* revisione dell'offerta e push (con successione) passano.

**pgTAP:** `vendite/test-righe-esclusione-solo-non-si-vende-v1`, test 1, 2, 6 e 11 coi nove campi.

**Ricaduta BE** (rottura accettata, nella richiesta BE/FE): `contratti_repository.py`,
`offerte_repository.py`, `contratti_service.py`, `offerte_service.py`, `_schema_da_contratto.py`,
`types.py`, `error_policies_generated.py` e il test `test_contratto_esclusione_non_modificabile_db.py`
nominano `competenza_canone`: con l'apply le scritture e le letture che la nominano vanno in errore.

### 6.9 Lotto 2 — applicato (2026-10-29)

La fonte «dalla durata del periodo» (G-9): `CANONE/MANUALE` esce, entra `CANONE/DURATA`.

| changeSet / file | Che cosa |
| --- | --- |
| `00_schema/catalogo/20261029-31-alter-unita-misura-conta-dal-calendario` | `catalogo.unita_misura.conta_dal_calendario` (`GIORNO` \| `MESE` \| NULL, CHECK): l'unità con cui la durata conta la quantità. Le ore no: il pacchetto di ore è un canone FISSA (G-10) |
| `80_data/sql/catalogo/unita_misura.csv` + mirror `20260428-15` | GG → `GIORNO`, MESE → `MESE`, le altre il token `NULL`; la colonna nel loader, che passa a `nullValue: "NULL"`. ⚠️ Il primo apply (2026-10-29) si è fermato sul CHECK: col vecchio `nullValue: ""` la cella vuota diventava `''`. Il giro è stato annullato per intero; nessun'altra cella vuota nel CSV |
| `80_data/sql/config/erogazioni_fonti.csv` | via `2,CANONE,MANUALE`; entra `14,CANONE,DURATA,false` (gli id ritirati non si riusano) |
| `80_data/sql/config/listini_tipologie_erogazioni.csv`, `nature_vendita_erogazioni.csv` | `CANONE/DURATA`, mai di default nel seed, sulle tipologie QUOTA_FISSA e SERVIZI e sulla natura SERVIZIO_RICORRENTE. **Decisione di Tid (2026-10-29):** non su IMPOSTA («un'imposta non è un canone») né su ONERE_SISTEMA («non è detto che lo sia»); IMPOSTA perde anche `CANONE/FISSA` (revoca della tabella §C.5.2 del 2026-10-07; su dbdev nessun articolo IMPOSTA) |
| `80_data/changelog/20261029-34-delete-tipologie-erogazioni-imposta-canone` | il DELETE delle righe uscite dal CSV: IMPOSTA · `CANONE/FISSA` (id 5) e le due `CANONE/DURATA` (id 15 IMPOSTA, 16 ONERE_SISTEMA) che il primo apply aveva già messo; preCondition HALT sulle righe di documento |
| `20_code/vendite/20261029-35-update-fn-articolo-erogazioni-preferenza-durata` | F-8: dove la durata c'è, per il canone viene prima della FISSA nell'ordine e, se il default della base è un canone, è lei il default (CTE `preferenza`) |
| `80_data/changelog/20261029-32-delete-erogazioni-fonti-canone-manuale` | il DELETE della riga (il mirror non cancella); preCondition HALT sulle righe di documento (su dbdev 0, fatto datato). Forma di `20261021-51` |
| `20_code/vendite/20261029-33-update-fn-articolo-erogazioni-durata` | nella sede unica del perimetro: `CANONE/DURATA` solo se l'unità dell'articolo si conta dal calendario |

**Forma:** la regola sta in `vendite.fn_articolo_erogazioni`, quindi l'eredità, il guard e il form la
vedono insieme. Nessun guard e nessun codice nuovo: una riga a durata su un articolo a pezzi è
`E_RIGA_EROGAZIONE_FUORI_PERIMETRO`, col campo `fonte_quantita_attesa`.

`script.fn_fonte_porta_quantita` e i CHECK `chk_*_quantita_per_fonte` trattano già ogni fonte diversa
da FISSA come «a valle»: `DURATA` non porta quantità sulla riga senza cambiarli (il COMMENT della
funzione lo dice: «ogni fonte nuova finché non la si aggiunge qui»).

**Prova (2026-10-29, dbdev, owner, transazione annullata; seed simulato dai CSV, il loader vero lo prova
l'apply):**
* vocabolario CANONE = FISSA, DURATA;
* gli articoli a pezzi, metri e centimetri non vedono la durata;
* un articolo portato a GG la vede;
* i kit restano solo FISSA;
* il predicato del guard rifiuta la durata su un articolo a pezzi (`E_RIGA_EROGAZIONE_FUORI_PERIMETRO /
  fonte_quantita_attesa`).

**pgTAP:**
* `vendite/test-erogazioni-vocabolario-v1`: il test 1 ha `CANONE/DURATA` al posto di
  `CANONE/MANUALE`;
* **nuovo** `vendite/test-canone-durata-v1`: 12 test, tutto costruito (con F-8 e le tipologie);
* le fixture degli altri test creano articoli a pezzi (la prima unità del seed): le loro combinazioni
  non cambiano.

**Da sapere — l'ordine delle fonti.** Su un articolo a giorni o a mesi, se l'operatore sceglie
«canone» senza la fonte, l'eredità prende la prima fonte nell'ordine del perimetro. L'ordine è il
default, poi l'erogazione, poi la fonte in ordine alfabetico, e `DURATA` viene prima di `FISSA`. Per un
articolo a giorni è il caso giusto: il prezzo è al giorno e i giorni li conta il sistema. Ma oggi lo
decideva l'alfabeto: **F-8**, decisa da Tid (regola scritta, `-35`).

**Stato dell'apply (2026-10-29):** `-31`, `-32`, `-33`, i seed `-53` e `20260428-15` applicati alle 12:36
(dopo la correzione del `nullValue`), con la versione del CSV che aveva la durata anche su IMPOSTA e
ONERE_SISTEMA. Le decisioni dopo l'apply sono in **changeSet nuovi** (`-34`, `-35`): il `-33` applicato
non si tocca. Prova di `-34` e `-35` sullo stato applicato (owner, transazione annullata):
* tipologie: IMPOSTA solo `CONSUMO/LETTURE`, ONERE_SISTEMA `CANONE/FISSA` senza durata;
* QUOTA_FISSA a giorni → `CANONE/DURATA*`, a pezzi e kit → `CANONE/FISSA*`;
* SERVIZI a giorni: `DURATA` prima di `FISSA`.

**Ricaduta BE/FE** (nella richiesta):
* `frontend/src/vendite/constants.js` non conosce `DURATA` (etichetta «dalla durata del periodo»);
* `MANUALE` non vale più per il canone;
* il lister del L7 calcola la quantità della durata (giorni o mesi coperti dal pezzo).

### 6.10 Lotto 4a — l'ADESIONE, applicato (2026-10-29)

Il quarto tipo di riga (G-0-ter): un articolo **del** listino al prezzo **del** listino, con la variazione
globale. Sulla riga solo quantità e periodicità. La seconda metà del lotto, cioè la periodicità
obbligatoria col default dalla riga di listino (L4b), aspetta le domande F-9 e F-10.

| changeSet / file | Che cosa |
| --- | --- |
| `00_schema/vendite/20261029-36-alter-tipo-eccezione-add-adesione` | `ADD VALUE 'ADESIONE'` in un changeSet suo: il valore si usa solo dopo il COMMIT (precedente `20260419-02`) |
| `00_schema/vendite/20261029-37-alter-righe-adesione-prezzo-e-unicita` | `chk_*_prezzo_per_tipo_eccezione`: ADESIONE senza prezzo, come l'ESCLUSIONE; `uq_*_one_eccezione_per_articolo` allargato: una sola fra OVERRIDE, ESCLUSIONE e ADESIONE per articolo (stesso nome) |
| `20_code/vendite/20261029-38-update-fn-resolve-prezzo-listino-v2-esito-adesione` | lo stadio 1a del resolver salta l'ADESIONE: l'articolo prende il prezzo del listino del contratto con la variazione (stadio 1b, origine `CONTRATTO_LISTINO`). Prima avrebbe preso il prezzo vuoto della riga |
| `20_code/vendite/20261029-39-update-fn-documento-righe-preview-adesione` | anteprima: la riga di listino con un'ADESIONE ha origine `ADESIONE` e azioni `MODIFICA`, `RIMUOVI_ADESIONE`; la riga di listino senza eccezioni ha anche `ADERISCI` (il verbo di G-0-ter) |
| `20_code/vendite/20261029-40-update-fn-offerta-righe-espanse-adesione` | le righe espanse dell'offerta portano quantità e tipo dell'ADESIONE, al prezzo del listino |
| `20_code/script/20261029-41-update-fn-check-listino-cambiabile-adesione` | l'ADESIONE conta fra le righe che vivono sul listino (ferma la rimozione del listino) |
| `20_code/vendite/20261029-42-…-contratto-riga-componenti-init-adesione`, `-43-…-offerta-eccezione-componenti-init-adesione` | no-op sull'ADESIONE come sull'ESCLUSIONE: inizializzare i componenti scriverebbe un prezzo sul padre; il kit aderito prende prezzo e componenti dal listino. Dichiarazione con `%TYPE` e SECURITY INVOKER esplicito |
| `messaggi_errore.csv`, `codici_errore.csv` | `E_RIGA_ECCEZIONE_SENZA_LISTINO` e `_FUORI_LISTINO` nominano anche l'adesione |

**Censimento** (19 funzioni con un letterale del tipo di riga, `pg_get_functiondef`):
* 13 controllano solo l'ESCLUSIONE: l'ADESIONE vi si comporta come una riga che si fattura, senza
  modifiche;
* le sei sopra cambiano;
* il controllo dell'articolo ammesso (`script.fn_check_articolo_riga_su_contesto`, motivo 5b: «tutto ciò
  che non è AGGIUNTA vive sul listino») copre già l'ADESIONE;
* il passaggio offerta → contratto e la revisione copiano il tipo così com'è.

Corpi sorgente confrontati col catalogo vivo: identici.

**Prova:** prima dell'apply non si può provare l'ADESIONE in transazione: PostgreSQL non lascia usare un
valore nuovo di un enum nella transazione che lo aggiunge. La prova vera è il pgTAP nuovo dopo l'apply.

**pgTAP nuovo:** `vendite/test-righe-adesione-v1`, 13 test, tutto costruito:
* riga accettata e senza prezzo;
* prezzo rifiutato;
* unicità con l'OVERRIDE;
* fuori listino rifiutata;
* anteprima (origine, azioni, prezzo, ADERISCI);
* cambio di listino;
* offerta e righe espanse;
* resolver sul contratto attivo.

**Ricaduta BE/FE** (nella richiesta):
* il tipo `ADESIONE` nei form delle righe, senza prezzo;
* l'azione `ADERISCI` sulla riga di listino, `RIMUOVI_ADESIONE` sulla riga aderita;
* l'origine `ADESIONE` nell'anteprima.

**L4b — da fare dopo F-9 e F-10:** periodicità obbligatoria sulle righe a canone, col default dalla riga di
listino (trigger di valorizzazione + CHECK). Dati dbdev (2026-10-29, fatto datato):
* 10 righe di contratto a canone senza periodicità, di cui 4 AGGIUNTA;
* 12 righe di offerta a canone senza periodicità;
* nessuna riga di listino di quota fissa senza periodicità.

**F-10, la correzione dei dati di prova su dbdev** (da owner, prima dell'apply del L4b; provata il
2026-10-29: dopo, zero righe a canone senza periodicità e nessun trigger spento):

```sql
BEGIN;
ALTER TABLE vendite.contratti_righe DISABLE TRIGGER USER;
ALTER TABLE vendite.offerte_commerciali_eccezioni DISABLE TRIGGER USER;
UPDATE vendite.contratti_righe
   SET periodicita = 'MENSILE'
 WHERE tipo_erogazione = 'CANONE' AND periodicita IS NULL;
UPDATE vendite.offerte_commerciali_eccezioni
   SET periodicita = 'MENSILE'
 WHERE tipo_erogazione = 'CANONE' AND periodicita IS NULL;
ALTER TABLE vendite.contratti_righe ENABLE TRIGGER USER;
ALTER TABLE vendite.offerte_commerciali_eccezioni ENABLE TRIGGER USER;
COMMIT;
```

**pgTAP dopo l'apply del L4a (Tid, 2026-10-29):** `test-righe-esclusione-solo-non-si-vende-v1` rosso sul 21,
atteso: la riga di listino ha ora anche `ADERISCI`. Aggiornati il 21 e il 3 di
`test-contratto-righe-lista-v1`, l'unico altro presidio delle azioni della riga di listino.

### 6.11 Lotto 4b — il default della periodicità, applicato (2026-10-29)

**Decisione di Tid (2026-10-29), la (b):** adesso solo il default dalla riga di listino. L'**obbligo** della
periodicità sulla riga a canone (guard col campo + CHECK) entra **col passaggio BE/FE**, quando il form la
chiede, come già deciso per il Lotto 1. Con l'obbligo subito, dal programma non si sarebbero più salvate
righe a canone: il form non manda la periodicità, e le righe di listino oggi non la dicono. In più una
ventina di pgTAP crea righe a canone senza periodicità. Nel frattempo, la riga a canone senza periodicità
la segnalerà la dashboard (L8). Lo script di F-10 serve quando entra l'obbligo, non prima.

| changeSet | Che cosa |
| --- | --- |
| `20_code/script/20261029-44-create-trgfn-righe-default-periodicita-da-listino` | `script.trgfn_righe_default_periodicita_da_listino`: su ADESIONE e OVERRIDE a canone senza periodicità la prende dalla riga di listino dell'articolo, nella versione operativa del documento (`vendite.fn_documento_listino_operativo`). Riempie solo il vuoto. Generica sulle due gemelle (TG_ARGV: documento, colonna del padre); `%TYPE` e SECURITY INVOKER |
| `20_code/vendite/20261029-45-create-trigger-righe-default-periodicita-da-listino` | i due montaggi, BEFORE INSERT OR UPDATE OF `tipo_erogazione` WHEN canone e senza periodicità; fascia `_a10_`, dopo `default_erogazione_articolo` e `default_fonte_qta` (l'erogazione è già ereditata) |

L'AGGIUNTA (fuori listino) non eredita: la periodicità la scrive l'operatore (F-9).

**Prova (2026-10-29, dbdev, owner, transazione annullata, sul L4a applicato; listino di quota fissa
costruito coi builder pgTAP):**
* ADESIONE a canone → `TRIMESTRALE` dalla riga di listino, prezzo vuoto;
* OVERRIDE su una riga di listino senza periodicità → vuota, e si salva;
* periodicità scritta → vince;
* anteprima: l'ADESIONE al prezzo del listino (100) con `MODIFICA`, `RIMUOVI_ADESIONE`, e la riga di
  listino con `ADERISCI`. È la prima prova vera del L4a.

⚠️ `dbops.fn_pgtap_listino_aggiungi_articoli` riallinea la tipologia dell'articolo a quella del listino, e
`dbops.fn_pgtap_crea_listino` prende la prima tipologia della utility (CONSUMO). Un test a canone deve
costruire il suo listino di quota fissa (lo fa il pgTAP nuovo).

**pgTAP:**
* **nuovo** `vendite/test-righe-periodicita-da-listino-v1`: 6 test, tutto costruito;
* `vendite/test-testata-dopo-emissione-v1`: il test 1 conosce le due colonne nuove del lock di testata
  (rosso dopo il L5: atteso);
* `vendite/test-righe-esclusione-solo-non-si-vende-v1` (21) e `vendite/test-contratto-righe-lista-v1`
  (3): l'azione `ADERISCI` (rossi dopo il L4a: attesi).
* `script/test-rubinetto-primo-motivo-v1` (5): rosso **non di questo brief**. Il giro 12 del listino
  (`brief-modello-documento-vendita` §16) aveva quattro siti nuovi sull'helper non contati (`20261028-09`,
  `-39`, `20261029-02`, `-04`). Conto portato da 44 a 48 su richiesta di Tid (2026-10-29), verificato col
  criterio del test sul catalogo vivo.

### 6.12 Lotto 7 — il lister dei canoni, applicato (2026-10-30)

Applicato da Tid il 2026-10-30; pgTAP verdi.

| changeSet | Che cosa |
| --- | --- |
| `20_code/vendite/20261030-01-update-fn-list-contratti-da-pushare-canoni` | `vendite.fn_list_contratti_da_pushare` in tre rami (sotto). RETURNS TABLE invariato (CREATE OR REPLACE); la regola completa sta nell'intestazione del changeSet e nel COMMENT |

**I tre rami.**
* **Una tantum.** Come prima (una volta, il giorno di attivazione, contratti ATTIVO), con due differenze:
  * l'OVERRIDE non parte più (F-1);
  * l'ADESIONE prende il prezzo del listino alla data di attivazione. Prima arrivava senza prezzo e la
    madre l'avrebbe rifiutata.
* **Canone.** Riguarda i contratti ATTIVO e CESSATO. Si addebita una fonte per articolo:
  * le righe ADESIONE e AGGIUNTA;
  * l'OVERRIDE **solo su una quota fissa**, dove prende il posto della riga di listino (G-0);
  * le **quote fisse del listino** senza una riga del contratto sullo stesso articolo, con quantità 1 e
    la periodicità della riga di listino.

  I pezzi vengono da `vendite.fn_canone_periodi`. Il «da» è il giorno dopo l'ultimo pezzo addebitato di
  quella fonte (G-2), e la generazione è `coalesce(riga, testata)` (F-7).

  Le quantità:
  * a quantità fissa: la riga per la frazione del periodo;
  * a durata: i giorni del pezzo, o i mesi.

  Il prezzo:
  * quello della riga (OVERRIDE, AGGIUNTA);
  * oppure quello del listino del contratto all'inizio del pezzo, con la variazione globale (ADESIONE,
    quota fissa).
* **Storno (G-5).** Un pezzo addebitato che va oltre `valido_al` si storna per la parte non goduta: quanto
  è stato addebitato, meno quanto si sarebbe addebitato con la fine nota (stessa regola di F-2). Lo storno è
  una riga negativa al prezzo addebitato, una per ogni riga addebitata, componenti dei kit compresi.

**La chiave.**
* **Riga del contratto:** `CONTRATTO:<uid>:R:<riga>:M:<mese d'inizio del pezzo>`.
* **Quota fissa del listino:** `CONTRATTO:<uid>:A:<articolo>:M:…`.
  * Nomina l'articolo e non la riga di listino: una versione nuova del listino cambia la riga, non la
    quota.
  * Si compone con `script.fn_segment_key` passando l'uid `<uid>:A:<articolo>`. La firma del costruttore
    non cambia: la leggono sette oggetti.
* **Storno:** `<base del pezzo>#STO`, prima dell'eventuale `#CMP`.

**Non partono, e li segnalerà la dashboard (L8):**
* la riga a canone senza periodicità;
* la riga a durata su un'unità che non si conta dal calendario;
* la riga senza prezzo alla data.

**⚠️ Richiesta al team BE — la commessa del contratto si apre senza periodo (G-6).** L'orchestratore
(`commesse_source_handlers._process_rows`) mette nella chiave della commessa il periodo della riga
(`competenza_dal`/`_al`).
* **Il problema:** con i canoni ogni pezzo ha il suo periodo. Dal secondo pezzo,
  `fn_get_or_create_commessa` apre un'altra commessa, e la madre risponde
  `E_COMMESSA_SORGENTE_ALTRA_COMMESSA`, perché un documento sta in una sola commessa aperta (D-12). Lo
  stesso vale per la una tantum e il primo canone dello stesso contratto. Trovato provando il giro di
  novembre (2026-10-30).
* **La richiesta:** per la sorgente CONTRATTO la commessa si apre con `p_competenza_dal` e
  `p_competenza_al` a NULL: una commessa viva per contratto, che accumula i pezzi finché non si fattura
  (G-6).
* **Lato DB non serve altro:** la competenza della commessa la legge solo `fn_list_commesse_emittibili`,
  in proiezione. Le colonne sono nullable.
* **Fino al passaggio BE:** il primo pezzo di ogni contratto atterra, gli altri finiscono negli errori del
  giro. È una rottura BE accettata fino a fine cantiere.

Altri due punti per il BE:
* sulle quote fisse del listino e sugli storni `riga_id` è NULL, quindi un kit su una quota fissa del
  listino non si espande (l'espansore lo passa intero, con un avviso);
* una riga negativa sola in fattura, per esempio un contratto cessato senza altri addebiti, è un caso
  della fattura (nota di credito) da verificare col passaggio BE.

**Prova (2026-10-30, dbdev, owner, transazione annullata; SQL estratto dal changeSet).** Scenario
costruito: C1 su un listino di quota fissa, C2 su un listino di servizi, dal 15/02/2026, anticipati. I
risultati:
* **giro di ottobre:** 26 righe, tutte come attese, cioè:
  * Q trimestrale 0,5 + 1 + 1 + 1;
  * OVERRIDE mensile 1 + 2 × 8;
  * ADESIONE trimestrale al prezzo del listino;
  * durata in giorni, 259 giorni;
  * nessuna riga per l'ESCLUSIONE e per l'OVERRIDE fuori quota fissa;
* **giro di ottobre rifatto:** niente;
* **giro di novembre:** solo i due mensili nuovi;
* **cessazione al 10/11:** quattro storni. Restano:
  * 17,666666 × 80 = 1.413,33 €;
  * 2,944444 × 100 per la quota e per l'ADESIONE;
  * 269 giorni.

  Dopo gli storni il giro non produce niente.

**pgTAP:**
* **nuovo** `vendite/test-push-contratto-canoni-v1`: 12 test.
  * La parte A è a date fisse nel passato, la parte B (lo storno) a date relative a oggi, perché la
    cessazione non può essere retroattiva.
  * Sul corpo vivo è rosso in 9 test. I test 3, 8 e 12 contano zero righe e sono verdi anche prima.
* `vendite/test-push-contratto-dalla-madre-v1`, parte D (9-12): raccontava «la CANONE non parte» (§5).
  Ora prova il primo pezzo del canone in commessa e che un secondo giro non lo rimanda. Atteso.
* Gli altri cinque pgTAP del lister sono invariati e verdi:
  * `test-fn-list-contratti-da-pushare-v1` e `-v2`;
  * `test-fatturazione-immediata-simmetria-sorgenti-v1`;
  * `test-push-list-stato-obbligatorio-v1`;
  * `test-righe-erogazione-obbligatoria-v1`.
* I 166 pgTAP di `script/` e `config/`, prima/dopo da owner: rossi identici, test per test.
* I 209 pgTAP di `vendite/` che toccano contratti, commesse o push, prima/dopo da owner: nessun rosso
  nuovo (dove c'era un rosso col cambio, era identico, test per test, a quello del corpo vivo).

### 6.13 Lotto 8 — i casi limite del lister e la dashboard, applicato (2026-10-31)

Applicato da Tid il 2026-10-31 (`20261031-01` … `-04` e il seed `20260706-02`); pgTAP verdi.

**I due casi limite del L7.** Verificati il 2026-10-31 su dbdev.
* **Una quota fissa del listino che diventa una riga del contratto: non può capitare.** Fuori dalla bozza
  le righe del contratto e il listino sono chiusi (`vendite.trgfn_doc_righe_lock_fuori_bozza`, montato
  senza colonne ammesse; `listino_id` e `listino_versione_id` nel lucchetto della testata), e un ATTIVO
  non torna in bozza (i passaggi sono DRAFT → ATTIVO, DRAFT → ANNULLATO, ATTIVO → CESSATO).
* **La fine che si sposta dopo il primo storno: difetto vero, corretto.**
  * **Il difetto:** la fine del contratto (`valido_al`) si può scrivere finché è ATTIVO, con
    `fn_cessa_contratto` a un'altra data futura o con un UPDATE che la toglie. Lo storno del L7 aveva una
    chiave sola per pezzo (`#STO`). Provati tre spostamenti: anticipata, spostata avanti, tolta. In tutti
    e tre i casi il lister non produceva niente, e la commessa restava con lo storno del primo taglio.
  * **La regola nuova:** lo storno è la **differenza** fra il dovuto con la fine di oggi e quanto è già
    stornato per quel pezzo. È negativa se la fine arretra, positiva se avanza o sparisce (si riaddebita).
    Il totale del pezzo è sempre quello che darebbe un taglio solo, alla fine di oggi.
  * **La chiave:** `#STO` la prima rettifica, come prima; `#STO:2`, `#STO:3` … le successive.

| changeSet | Che cosa |
| --- | --- |
| `20_code/vendite/20261031-01-update-fn-list-contratti-da-pushare-storno-differenza` | il ramo storno di `vendite.fn_list_contratti_da_pushare`, come sopra. RETURNS TABLE invariato; ritorno indietro al corpo del `20261030-01` |

**Prova (2026-10-31, dbdev, owner, transazione annullata; SQL estratto dal changeSet):**
* `vendite/test-push-contratto-canoni-v1`, parte C nuova (13-15): fine anticipata (`#STO:2`, negativa),
  spostata avanti (`#STO:3`, positiva), tolta (`#STO:4`, si riaddebita tutto, e un altro giro non manda
  niente). 15/15 verdi; sul corpo vivo rossi i tre nuovi.
* Gli altri sei pgTAP del lister, prima/dopo: nessun rosso, invariati.

**La dashboard — scritta e provata (2026-10-31).** Decisioni F-12 … F-15 (§6.4).
* **Dove si legge:** la vista è `vendite.vw_dash_fatturazione_contratti`. La leggono
  `vw_dash_fatturazione_documenti` (union) e, attraverso questa, `vw_dash_aperto_documenti` e
  `vw_dash_backlog_documenti`.
* **Una regola sola (regola del 2):** «c'è un addebito da mandare» e «c'è un canone che non può partire»
  sono due risposte **del push**. Il corpo del lister diventa una funzione, che restituisce anche gli
  scartati con il motivo. Il lister filtra quelli buoni, la vista li legge tutti e due.

| changeSet | Che cosa |
| --- | --- |
| `20_code/vendite/20261031-02-create-fn-contratti-addebiti-maturati` | `vendite.fn_contratti_addebiti_maturati`: il corpo del lister del `-01`, più gli scartati (`scarto`): `SENZA_PERIODICITA` e `DURATA_SENZA_CALENDARIO` (una riga per fonte, senza pezzo), `SENZA_PREZZO` (il pezzo o la una tantum). Fra due righe di listino sullo stesso articolo vince quella con la periodicità. EXECUTE a `zeroerp_app`, tolto a PUBLIC |
| `20_code/vendite/20261031-03-update-fn-list-contratti-da-pushare-dalla-sede` | il lister legge la funzione e tiene `scarto` NULL. Restano qui la sorgente, le colonne costanti della commessa, l'ordine e il limite. Stesse righe del `-01` |
| `20_code/vendite/20261031-04-update-vw-dash-fatturazione-contratti-giudizio-dal-push` | il giudizio torna, per ATTIVO e CESSATO: `CANONE_NON_GENERABILE` se c'è uno scartato (vince), `CANONE_NON_GENERATO` se c'è un addebito da mandare, altrimenti transitato. La bozza resta sospesa (NULL). `data_riferimento`: `valido_dal`; se il contratto è fermo, l'addebito più vecchio che aspetta, mai dopo oggi (l'anzianità del Backlog la conta da qui) |
| `80_data/sql/config/motivi_fermo.csv` (seed `20260706-02`, runOnChange) | `CANONE_NON_GENERATO` → RECUPERABILE, «Esegui il push dei canoni» (F-13); nuova riga 15 `CANONE_NON_GENERABILE`, ANOMALIA, «Rivedi il contratto» (F-15) |

**Cosa cambia a valle:**
* nella situazione aperta un contratto senza niente da mandare **esce**, come un ordine tutto in commessa,
  e rientra quando matura il pezzo dopo;
* nel Backlog entrano i contratti fermi, anche un CESSATO con uno storno da mandare;
* union `vw_dash_fatturazione_documenti`: stesse colonne, niente da ricreare.

**Da sapere:**
* una quota fissa del listino senza periodicità rende `CANONE_NON_GENERABILE` **ogni** contratto del
  listino che non la esclude. È un difetto del listino, e la segnalazione è giusta;
* un CESSATO con una riga scartata resta in ANOMALIA per sempre: la riga è chiusa e il contratto non si
  riapre. Su dbdev, 2026-10-31: 2 contratti CESSATO;
* il costo: una chiamata della funzione per contratto. Su dbdev, 2026-10-31: 339 contratti in 0,16 s
  (vista), Backlog intero 0,3 s. È un fatto datato, non un vincolo.

**Prova (2026-10-31, dbdev, owner, transazione annullata; SQL estratto dai changeSet `-01` … `-04`, seed
simulato con UPDATE della riga 9 e INSERT della 15):**
* su dbdev lo stesso lister di prima (5 righe). La vista: 5 ATTIVO `CANONE_NON_GENERATO`, 247 ATTIVO
  transitati, 2 CESSATO `CANONE_NON_GENERABILE`, 71 CESSATO transitati, 14 bozze sospese;
* i ritorni indietro dei quattro changeSet, applicati dopo i cambi, rimettono lister e vista com'erano
  (stesso md5 della definizione viva);
* **nuovo** `vendite/test-vw-dash-contratti-giudizio-v1`: 11 test. Copre:
  * il contratto da mandare: fermo, Backlog RECUPERABILE, data di riferimento;
  * lo stesso contratto mandato: transitato, fuori dall'aperto e dal Backlog;
  * la riga senza periodicità che vince e resta dopo il push;
  * la quota del listino senza periodicità;
  * la bozza sospesa.

  11/11 verdi; sul corpo vivo rossi i test 1, 2, 5-9 e 11 (3, 4 e 10 verdi anche prima). Ha trovato un
  difetto della prima stesura (`least` ignora i NULL: un contratto transitato prendeva oggi come data di
  riferimento), corretto prima di consegnare;
* `vendite/test-vw-dash-backlog-v1`, test 2: conta le classi del seed. `CANONE_NON_GENERATO` passa da
  verde ad arancio (F-13): 6 RECUPERABILE e 2 FISIOLOGICO. Atteso. Corretto anche il commento della
  fixture del contratto ATTIVO.
* **Prima/dopo, da owner, sui 255 pgTAP** di `vendite/`, `script/` e `config/` che toccano dashboard,
  contratti, commesse o motivi: nessun rosso nuovo. Due file (`test-fn-partite-merce-chiusura-v1`,
  `test-fn-preventivo-ha-residuo-commessa-v1`) sono andati in deadlock: alle 10:36 Tid applicava il giro
  mentre il confronto girava (10:34-10:38), e i CREATE OR REPLACE aspettavano le transazioni di prova.
  Ripassati da soli: rossi identici a prima (il 16 del primo è preesistente). Dopo le 10:36 il «prima» era
  già il giro applicato: il confronto vero è quello dei pgTAP di Tid, verdi.

### 6.14 Lotto 9 — la documentazione, scritto (2026-10-31)

Solo testo: nessun changeSet. La doc auto-generata la rigenera il migrate.

| File | Che cosa |
| --- | --- |
| `guide/gestione-contratti.md` | **§4-bis nuovo**, «Come il contratto si addebita»: che cosa si addebita (ADESIONE, AGGIUNTA, OVERRIDE solo su quota fissa, quote fisse del listino), una tantum, canone (periodicità, mese di partenza, anticipato/normale, periodo incompleto, 31/12, arretrati, quantità, prezzo, esempio), cessazione e storni, che cosa non parte e dove si vede. ADESIONE nella tabella del §2.2 e nel glossario; testata con i due campi del canone; §6.1 rimanda agli storni |
| `guide/gestione-offerte-commerciali.md` | ADESIONE; i campi del canone sulla testata; `competenza_canone` tolta dai parametri di fornitura, rimando al §4-bis del contratto |
| `guide/gestione-listini.md` | la periodicità sulla riga di listino (quota fissa: si addebita da sé; altrove: la proposta all'adesione). §2.4 riscritto: descriveva ancora le modalità A/B/C del contratto, ritirate (codici `E_CONTRATTO_MODALITA_C_*` obsoleti dal 2026-08-07) |
| `guide/cruscotti-fatturazione.md` | **§4.2 nuovo**, i due motivi dei contratti; §5, quando un contratto è nel serbatoio |
| `vendite/manual/fn_contratti_addebiti_maturati.md` | nuovo |
| `vendite/manual/fn_list_contratti_da_pushare.md` | riscritto: il lister è un filtro sulla sede; storia dei giri |
| `vendite/manual/vw_dash_fatturazione_contratti.md` | riscritto: il giudizio riacceso, i due motivi, la data di riferimento, gli effetti a valle |
| `vendite/manual/contratti.md` | §cessazione (stantio dal 26-10, §4.3): `fn_cessa_contratto` e `fn_cessa_contratti_scaduti`, la condizione del passaggio ATTIVO → CESSATO, la fine che si sposta |
| `vendite/manual/contratti_righe.md` | §Scopo (stantio, §4.3): il modello a eccezioni; ADESIONE; periodicità e generazione (vuota = testata); `competenza_canone` e `CANONE/MANUALE` ritirate, `DURATA` |
| `vendite/manual/offerte_commerciali_eccezioni.md` | ADESIONE; i vincoli veri (FK sul vocabolario al posto dei CHECK), `PRORATA` e `competenza_canone` ritirati |
| `config/manual/motivi_fermo.md` | 15 codici; i due motivi dei contratti e il perché delle classi |
| `vendite/manual/vw_dash_backlog_documenti.md`, `vw_dash_fatturazione_documenti.md` | i contratti nel Backlog; la data di riferimento; il vocabolario dei motivi |
| `script/manual/trgfn_righe_default_fonte_qta.md` | la tabella delle combinazioni vietate era scritta a mano: ora quella del vocabolario, con `CANONE/DURATA` |
| `db/pgtap/vendite/test-righe-erogazione-obbligatoria-v1.sql` | descrizioni del 19 e del 21 (§5): solo testo, 21/21 verdi |

Ancore dei rimandi alla guida dei contratti controllate sul sito già costruito (`4-bis-…`,
`4-bis3-…`, `11-…`), senza lanciare la build.
