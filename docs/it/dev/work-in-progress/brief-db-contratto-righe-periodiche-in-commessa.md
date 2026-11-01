# Brief DB — Le righe di contratto che non sono «una volta»: canone, orario e consumo in commessa

## ⏭️ Chi riparte — aggiornato al 2026-11-01 (passo 4 e 3-ter applicati, pgTAP verdi)

**Riparte il team BE/FE** con la richiesta del §7.13.4 (tre punti). Lato DB il giro è chiuso: Tid ha
lanciato su dbdev lo script di F-10, applicato `20261101-04` … `-06` e i CSV, e i pgTAP sono verdi
(2026-11-01, §7.13.5). L18, la documentazione del giro del §7, è scritta (§7.12): solo testo.

**Cosa resta lato DB** (§7.8):
* ~~L17~~ applicato (§7.9);
* ~~la periodicità della quota fissa ferma fuori dalla bozza~~ applicata (§7.10);
* ~~la documentazione del giro del §7~~ scritta (§7.12, L18);
* ~~il passo 4~~ e ~~la colonna «Periodicità» della lista 37~~ applicati, pgTAP verdi (§7.13);

I lotti L1 … L9 lato DB restano finiti (§6.3).

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
| 1-vicies quater | BE/FE (in corso) | la richiesta: fatto quanto non aspetta il DB, il resto dopo i punti 2 e 3 | §7.6 | 1-vicies ter |
| 1-vicies quinquies | ✅ Tid | D-1 … D-4 del passaggio BE/FE (2026-10-31) | §7 | 1-vicies ter |
| 1-vicies sexies | ✅ Tid | D-1-ter (A) e D-2-bis (B); via allo sviluppo (2026-10-31) | §7.1, §7.2 | 1-vicies quinquies |
| 2 | ✅ team DB (L10 … L16 scritti e provati, 2026-10-31; L17 proposto) | D-1 nota di credito dal segno del documento, con le fatture citate (D-1-ter); D-2 componenti del kit dal listino; D-2-bis il kit sul listino con la sua periodicità; D-3 controllo all'attivazione della versione e quota fissa che sparisce; D-5 i due campi del canone nella whitelist di `fn_create_contratto`; D-6 la periodicità nel lookup; D-7 periodicità e generazione nella preview delle righe | §7.1 … §7.5, §7.7 | 1-vicies sexies |
| 2-bis | ✅ Tid | apply di `20261031-28` … `-43` e dei CSV, pgTAP verdi (2026-10-31) | §7.7 | 2 |
| 2-bis-bis | ✅ Tid | ok alla forma di L17 (2026-10-31) | §7.7 | 2-bis |
| 2-ter | ✅ team DB | L17 (D-1, D-1-ter) scritto e provato (2026-10-31) | §7.9 | 2-bis-bis |
| 2-ter-bis | ✅ Tid | apply di `20261031-44` … `-48` (2026-10-31) | §7.9 | 2-ter |
| 2-ter-ter | ✅ team DB | la quota fissa non perde la periodicità fuori dalla bozza, decisione di Tid; `-49` … `-52` scritti e provati (2026-10-31) | §7.10 | 2-ter-bis |
| 2-ter-quater | ✅ Tid | apply di `20261031-49` … `-52`, pgTAP verdi, nessuna regressione (2026-10-31) | §7.10 | 2-ter-ter |
| 2-quater | ✅ team DB | documentazione del giro del §7 (L18), scritta (2026-11-01) | §7.12 | 2-bis |
| 3 | ✅ BE/FE | i nove punti del §7.7 e del §7.9 e il codice del §7.10, provati (2026-10-31) | §7.11 | 2-bis |
| 3-bis-bis | ✅ BE/FE | revisione critica del passo 3: BB `_campi_canone` (regola del 2, ok Tid) e note minori, provati (2026-10-31) | §7.11.4 | 3 |
| 3-bis | Tid | commit del passo 3; collaudo a video alla fine | §7.11 | 3-bis-bis |
| 3-ter | ✅ team DB | la colonna «Periodicità» nella lista 37 (`vendite.listini_righe`), scritta (2026-11-01) | §7.13.1 | 3 |
| 4 | ✅ team DB | l'obbligo della periodicità sulla riga a canone (guard + CHECK), scritto e provato (2026-11-01) | §7.13.2 | 3 |
| 4-bis | ✅ Tid | su dbdev lo script di F-10, poi l'apply di `20261101-04` … `-06` e dei CSV; pgTAP verdi (2026-11-01) | §7.13.5 | 4 |
| 4-ter | BE/FE | la richiesta del §7.13.4 (codice nuovo, test DB, collaudo del form) | §7.13.4 | 4-bis |
| 5 | Tid | archiviazione del brief | — | 4-ter |

Decisioni aperte di Tid: nessuna. Da committare su `dev/db-tid`: L18 (§7.12), il passo 3-ter e il passo 4 (§7.13). Il passo 3 BE/FE è entrato in `be8579d0c` (PR #1989). La forma di L17 e la periodicità ferma della quota fissa decise il 2026-10-31. D-1-ter (A) e D-2-bis (B) prese il 2026-10-31. F-1 … F-10 prese il 2026-10-29, F-11 … F-13 il 2026-10-30, F-14 e F-15 il 2026-10-31, D-1 … D-4 il 2026-10-31. G-0 … G-11 prese il 2026-10-28. Lavoro committato il 2026-10-31 su `dev/db-tid` (un commit: L1 … L9): i changeSet `20261029-10` …
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

**pgTAP a valle sfuggiti al censimento (rossi da Tid, 2026-10-31).** Asserivano ancora il giudizio
sospeso. `test-vw-dash-backlog-v1` era già allineato.
* `vendite/test-vw-dash-aperto-v1`, test 8 e 9. Senza niente da mandare il contratto è transitato:
  l'ATTIVO usciva dallo stock e il CESSATO non era più il caso (b), cioè chiuso ma non transitato. I due
  contratti stanno ora su un listino QUOTA_FISSA con una quota mensile: i canoni maturati non sono in
  commessa, quindi sono fermi (`CANONE_NON_GENERATO`).
* `vendite/test-vw-dash-fatturazione-v1`, test 12 e 13. Il contratto non ha niente da mandare: è transitato
  (1, motivo NULL), sempre in una riga.

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

## 7. Il passaggio BE/FE: quattro domande e tre richieste al team DB (2026-10-31)

> **Chi scrive:** team BE/FE (`dev/backend-tid`), 2026-10-31, alla presa in carico. **A chi:** il team
> DB. Le decisioni sono di Tid, 2026-10-31. I fatti vengono dalla doc auto-generata e dal codice BE, alla
> stessa data.

| # | Domanda | Decisione di Tid (2026-10-31) | Chi |
| --- | --- | --- | --- |
| **D-1** | Un documento a totale negativo, per esempio una commessa di soli storni | **è sempre una nota di credito**, comunque siano nate le righe; anche il documento misto | DB (§7.1) |
| **D-2** | Il kit senza componenti negoziati (quota fissa del listino, ADESIONE) | **(c)**: una funzione DB dà i componenti dal listino, l'espansore BE la legge | DB, poi BE (§7.2) |
| **D-3** | La periodicità della riga di listino di una quota fissa | **(b)**: un controllo all'attivazione della versione | DB (§7.3) |
| **D-4** | «Aderisci» sulla riga di listino | **(a)**: un dialog con quantità e periodicità, proposte dal listino | BE/FE |
| **D-5** | La creazione del contratto scarta i due campi del canone | difetto trovato dal BE, nessuna scelta: la madre li deve ammettere | DB (§7.4) |
| **D-6** | La periodicità non è nel lookup | difetto trovato dal BE/FE: una riga in `tabelle_gestibili` | DB, poi BE (§7.5) |
| **D-7** | La preview delle righe non porta periodicità e generazione | difetto trovato dal BE/FE: due colonne in uscita | DB (§7.5) |

### 7.1 D-1 — la natura del documento la dà il segno del totale

**Il difetto (struttura, 2026-10-31).**
* Lo storno del lister nasce con la natura di default (FATTURA) e la quantità negativa:
  `vendite.fn_list_contratti_da_pushare` non ha una natura nel suo RETURNS TABLE.
* `vendite.fn_build_fattura_key` legge la natura **riga per riga** (`attivita_fatturabili.natura_doc_id`),
  e da lì escono testata, registro e serie.
* Se il documento ha solo storni, la testata è una FATTURA a totale negativo. La settima condizione del
  controllo D-K in `fn_assign_numero_fattura` (natura diversa da NOTA_CREDITO e `totale_a_pagare < 0`)
  ne rifiuta la numerazione, e la fattura resta ferma.

**Perché non è un caso limite.** Un canone anticipato già fatturato, su un contratto che cessa a metà
periodo, produce sempre questo documento. La commessa fatturata è chiusa (G-6), e lo storno apre la
commessa nuova da solo.

**Perché non si marca lo storno al push.** Se il pezzo stornato non è ancora fatturato, lo storno si
compensa nella stessa fattura. Una nota di credito su un addebito mai fatturato sarebbe sbagliata, e il
push non può sapere come finirà.

**La regola (Tid).**
* **Il segno si guarda sul documento**, cioè sul gruppo che diventa una testata, non sulla commessa: una
  commessa può dare più documenti.
* Si somma il gruppo. **Se il totale è negativo, le righe di natura FATTURA del gruppo diventano
  NOTA_CREDITO**, e il documento nasce nota di credito, con il suo registro e la sua serie.
* **Il documento misto** (per esempio uno storno di −300 e una tantum di +50) è **una** nota di credito
  da −250, con dentro la riga positiva.
* **La regola si applica prima della chiave della testata**, perché natura, registro e serie si scelgono
  lì. La sede esatta (la selezione delle attività fatturabili o la chiave) la sceglie il team DB.
* Vale **per ogni sorgente**, non solo per il contratto: un documento che somma negativo è una nota di
  credito, da dovunque venga.

**D-1-bis — quello che non cambia.** Le righe che nascono già NOTA_CREDITO (l'accredito del reso, con la
riga di fattura rettificata) restano tali. Se le battezzasse il segno, un accredito in una commessa con
altri addebiti finirebbe compensato in una TD01 e perderebbe il `DatiFattureCollegate` (D-NC,
`work-done/brief-design-note-credito-resi.md`, 2026-08-18). Resta anche l'altra metà della settima
condizione: una NOTA_CREDITO a totale positivo non si numera.

**Il tracciato (Tid).** In catena il segno sta nel numero (D-NC-2: le quantità negative). Nella FatturaPA
il segno lo dà il TD04, e le righe si **invertono**: le negative si scrivono positive, le positive
negative. È un requisito del generatore del tracciato, che nel repo oggi non scrive le righe: non va
ricopiato nella catena.

**D-1-ter — decisa (Tid, 2026-10-31): (A), la nota di credito cita le fatture.** Quando il pezzo
stornato è già fatturato, lo storno porta la riga di fattura che lo ha addebitato
(`attivita_fatturabili.fattura_riga_rettificata_id`, lo stesso canale dell'accredito del reso), e la
nota di credito cita quelle fatture. Se il pezzo non è fatturato, lo storno si compensa nella stessa
fattura e il riferimento resta vuoto. La domanda, com'era: lo storno sa quale pezzo storna (la base della chiave, `<base>#STO`), quindi
si può risalire alla riga di fattura che lo ha addebitato. La guida della fatturazione dice che una nota di
credito cita il documento che corregge (`DatiFattureCollegate`). La domanda: la nota di credito nata dal
segno deve citare le fatture dei pezzi che storna (una o più), o basta senza?

**pgTAP da costruire:** il documento di soli storni, il misto a netto negativo, il misto a netto positivo
(resta FATTURA con una riga negativa), un accredito di reso dentro una commessa con addebiti (resta una
nota di credito a sé).

### 7.2 D-2 — i componenti del kit dal listino

**Il fatto (BE, 2026-10-31).** Il `BoMComponentExpander` di
`backend/apps/vendite/services/commesse_source_handlers.py` legge i componenti **negoziati sulla riga del
documento** (`vendite.contratti_righe_componenti`, attraverso `riga_sorgente_id`). Se non li trova, passa
il kit intero in commessa con un warning nel log. Succede in due casi:
* **la quota fissa del listino**: `riga_id` è NULL (già nel §6.12);
* **l'ADESIONE su un kit**: la riga c'è, ma l'inizializzazione dei componenti è volutamente vuota
  sull'ADESIONE (`20261029-42`), quindi la lista torna vuota. Non era nel §6.12.

Gli storni sono già a posto: il lister storna riga per riga, componenti compresi.

**La regola (Tid, la (c)).** Il §6.10 dice che il kit aderito prende prezzo e componenti dal listino: la
sede è `vendite.listini_righe_componenti` della versione del contratto, alla data del pezzo.
* **DB:** una funzione che, dati il contratto (o la versione di listino), l'articolo padre e la data,
  restituisce i componenti nella **stessa forma** che l'espansore già legge dalle `*_righe_componenti`:
  componente, unità operativa, coefficiente, prezzo unitario, esposizione in fattura, origine del prezzo.
  Il prezzo lo dice il DB, con la variazione globale del contratto come per il padre.
* **BE:** l'espansore la legge quando la riga non ha componenti negoziati. Nessun prezzo calcolato in
  Python.
* Scartate: (a) l'espansore che legge da solo il listino (logica di prezzo nel BE); (b) il lister che
  emette già i `#CMP` (due sedi per l'espansione dei kit, contro la regola del 2).

**Da dire nella risposta del DB:** se anche l'una tantum ADESIONE su un kit passa di qui (stesso caso, un
ramo diverso del lister).

**D-2-bis — decisa (Tid, 2026-10-31): (B), una tabella del kit sul listino.** Una riga per versione e
kit (versione, kit, periodicità). Resta valida la decisione del modello unificato dei componenti
(`work-done/brief-db-componenti-modello-unificato.md`, 2026-05): il padre non ha una riga in
`listini_righe`, e il prezzo del kit resta la somma dei componenti. Scartate: (A) la riga del padre in
`listini_righe` senza prezzo, che revocava quella decisione e toglieva il `NOT NULL` a
`listini_righe.prezzo`; (C) la periodicità sull'articolo, contro G-0-bis (la periodicità è una condizione
del listino). Il problema, com'era: il kit sul listino non ha una riga, quindi nemmeno una periodicità. Trovato
dal BE il 2026-10-31, aggiungendo la periodicità alla riga di listino. La doc di
`vendite.listini_righe_componenti` lo dice: *«non esiste una riga in `listini_righe` per il padre (bloccato
da guard dedicati)»*. Il kit sul listino è solo l'insieme dei prezzi dei componenti. Due conseguenze, sul
modello:
* **un kit su un listino di quota fissa non si addebita mai, e nessuno lo dice.**
  `fn_contratti_addebiti_maturati` prende le quote fisse da `listini_righe`, dove il padre non c'è, e non
  produce nemmeno uno `scarto`;
* **un kit aderito non eredita la periodicità**: il trigger del L4b la cerca sulla riga di listino
  dell'articolo, che per il padre non esiste. Lo stesso per «Aderisci», che la propone dalla riga di
  listino.

La domanda è dove vive la periodicità di un kit sul listino, cioè se il padre ha un posto suo sul listino
(una riga in `listini_righe` senza prezzo, il prezzo restando la somma dei componenti) o se la periodicità
sta altrove. D-2 (c), i componenti dal listino, resta valida in tutti e due i casi: decide solo da dove si
legge il ritmo.

### 7.3 D-3 — la periodicità della quota fissa, all'attivazione della versione

**I fatti (struttura, 2026-10-31).**
* La riga di listino è una quota fissa se l'articolo ha una tipologia con `e_quota_fissa`.
  `vendite.listini_righe.periodicita` è nullable, e nessun guard la controlla.
* Fuori dalla bozza la riga di listino non si tocca più. Una versione attivata senza periodicità non si
  corregge: serve una versione nuova, e intanto ogni contratto del listino che non la esclude resta in
  `CANONE_NON_GENERABILE` (§6.13).

**La regola (Tid, la (b)).** Una versione di listino **non si attiva** se ha una riga di quota fissa a
canone senza periodicità. La bozza resta libera di essere incompleta, e l'errore esce prima che un
contratto la usi. Codice d'errore nuovo, se serve, con policy e ripiego.

**⚠️ Il buco trovato nello stesso giro.** In `vendite.fn_contratti_addebiti_maturati` la quota fissa
del listino entra solo se l'erogazione di default dell'articolo è un canone (`JOIN LATERAL` su
`fn_articolo_erogazioni` con `e_default` e `CANONE`). Una quota fissa con un altro default **sparisce in
silenzio**: niente addebito e niente `scarto`, quindi nemmeno la dashboard la vede. Due strade, da
scegliere nel giro DB: uno `scarto` in più nel lister, oppure un vincolo per cui la tipologia di quota
fissa ha sempre un canone come default. La seconda chiude il caso alla sorgente, la prima lo rende
visibile.

**Ricaduta FE:** il campo periodicità sulla riga di listino. Che sia obbligatorio lo dice il DB (il
controllo all'attivazione e il suo errore): il form non ricopia la regola.

### 7.4 D-5 — la creazione del contratto scarta i due campi del canone (trovato dal BE, 2026-10-31)

**Il difetto.** La whitelist interna di `vendite.fn_create_contratto` (`v_testata_allowed`) non contiene
`generazione_canone` né `mese_partenza_canone`, colonne nuove del L5 (`20261029-15`). Il filtro **scarta**
le chiavi che non conosce, senza rifiutarle: un contratto creato con «canoni normali, da febbraio»
nascerebbe con i default (anticipati, gennaio), e la risposta sarebbe 200. È lo stesso difetto già
pagato su `fatturazione_immediata` (2026-07-27) e sui codici dell'atto (2026-08-31).

**Perché il BE non può aggirarlo.** Il drawer del contratto mette il payload della modifica dentro quello
della creazione. Il guardrail `ContrattiCatenaUpdateTests.test_update_keys_accettate_anche_in_create` vieta
quindi una chiave ammessa in modifica e non in creazione. Ammetterla in creazione, con la madre che la
scarta, vorrebbe dire scartare la scelta dell'operatore senza dirlo.

**La richiesta.** Le due chiavi nella whitelist della madre, con un pgTAP che crea un contratto con
`FINE_PERIODO` e un mese diverso da 1 e li ritrova sulla testata. L'offerta non ha il problema: si crea con
una scrittura diretta, e il passaggio offerta → contratto le copia già (`20261029-21`).

**Nel frattempo (BE, 2026-10-31):** sul contratto i due campi si **leggono** nel dettaglio e non si scrivono
dall'app. Entrano in creazione e modifica, insieme, quando la madre li ammette. Sull'offerta si scrivono
già.

### 7.5 D-6 e D-7 — il form non ha da dove leggere la periodicità (trovato dal BE/FE, 2026-10-31)

**D-6 — il vocabolario non è nel lookup.** `config.periodicita` non è in `config.tabelle_gestibili`, la sede
del lookup generico (`GET /core/lookup/codici/?rel=…`). Le sei periodicità non arrivano a nessuna tendina:
né sulla riga a canone (F-9: sull'AGGIUNTA la scrive l'operatore) né sulla riga di listino (§7.3). Ricopiarle
nel frontend vorrebbe dire una seconda copia del vocabolario.
* **DB:** una riga in `tabelle_gestibili.csv` (`lookup` true, `pannello` false: il vocabolario è del modello,
  non una configurazione).
* **BE, nello stesso giro:** la voce in `_LOOKUP_SPECIALIZZATE` (`has_codice_interno`, `has_attivo` e
  `has_obsoleto` a false; `mesi` come colonna extra). Il valore della tendina è il `codice`, quello della FK.
  ⚠️ Prima della riga DB la voce BE farebbe rosso `test_lookup_specializzate`, che le prova tutte sul DB.

**D-7 — la riga del form non sa che cosa è scritto.** Il form delle righe si apre dalla riga di lista, cioè
da `vendite.fn_documento_righe_preview` (via `fn_contratto_righe_preview` e `fn_offerta_righe_preview`), e
non c'è una lettura della singola riga. La preview porta erogazione e fonte, ma non `periodicita` né
`generazione_canone`. In modifica il form non saprebbe il valore scritto, e rimandandolo vuoto
cancellerebbe una periodicità o una generazione forzata.
* **DB:** le due colonne nell'uscita della preview, prese dalla riga di eccezione; per la riga di listino
  senza eccezione, la `periodicita` della riga di listino, che è la proposta di «Aderisci».

**Nel frattempo (BE/FE, 2026-10-31):** periodicità e generazione sulla riga entrano nel form **insieme**,
quando arrivano D-6 e D-7. L'ADESIONE parte già: senza indicazione la periodicità la mette il trigger
dalla riga di listino (L4b).

### 7.6 Il passaggio BE/FE — stato al 2026-10-31 (committato in `9f3a16904`, PR #1985)

**Fatto:**
* la commessa del contratto si apre senza periodo (G-6, `commesse_source_handlers`, `_commessa_per_periodo`);
* `competenza_canone` ritirata dal BE; `generazione_canone` tolta dalle combinazioni d'erogazione;
* ADESIONE fra i tipi di riga su contratto e offerta: senza prezzo, fuori dal gate dei prezzi, senza
  componenti propri; nel drawer delle righe «Aderisci» (D-4 (a): il form con quantità, articolo e UdM dalla
  riga di listino) e «Rimuovi adesione»;
* la fonte `DURATA` nelle costanti e nelle etichette; i due motivi della dashboard nei locales;
* testata dell'offerta: `generazione_canone` e `mese_partenza_canone` in lettura e scrittura nel BE, coi
  CHECK tradotti sul campo;
* riga di listino: `periodicita` in lettura e scrittura nel BE;
* testata dell'offerta, FE: «Addebito dei canoni» e «Mese di partenza dei periodi» (vuoti in creazione = il
  default del DB); i nomi dei mesi dal BB `nomiMesi` di `core/utils/date`, estratto da `useDashMesiNav`
  (regola del 2, ok Tid 2026-10-31).

**Aspetta:**
* il DB: D-1, D-2, D-3, D-5, D-6, D-7 (§7.1 … §7.5);
* ~~Tid: D-1-ter e D-2-bis~~ decise il 2026-10-31 (§7.1, §7.2).

### 7.7 Il giro DB del §7 (team DB, 2026-10-31; via di Tid lo stesso giorno)

**Verifica del push BE (2026-10-31, contro dbdev e doc auto-generata).** I nomi che il BE traduce sul
campo esistono tutti: le tre FK `fk_*_periodicita` e i CHECK `chk_offerte_commerciali_*` e `chk_contratti_*`.
`competenza_canone` non c'è più su nessuna tabella. L'uscita di `fn_documento_riga_erogazioni` è senza
`generazione_canone`, e l'app ha i grant di colonna su tutto ciò che scrive. Confermati, sul corpo vivo, i
fatti di D-1, D-3, D-5, D-6 e D-7. ⚠️ La CI di GitHub non è partita per nessuna corsa del 31-10, nemmeno
per quelle di `dev/db-tid`: il motivo è la fatturazione dell'account, non i test. Il push BE è entrato in
`Tito-dev` senza `validate` né `frontend`.

**Trovato nel giro (struttura, 2026-10-31).**
* `vendite.fn_clona_versione_listino` copia le righe senza `periodicita` (la colonna è del L1, il clone
  le copia per nome): una versione clonata da un listino di quota fissa la perde. Si corregge qui.
* Il prezzo di un kit aderito non c'è. Il lister chiede al resolver il prezzo del **padre**, ma il padre
  non ha una riga di listino: per l'ADESIONE su un kit (una tantum o canone) il resolver non trova niente,
  e la riga esce `SENZA_PREZZO`. Il prezzo del kit è la somma dei componenti, ciascuno al prezzo che il
  resolver dà nel contesto del padre (`p_articolo_padre_contesto`, origine `LISTINO_BUNDLE`).
* ⚠️ Il §7.2 dice «con la variazione globale del contratto come per il padre». Il resolver, oggi, sul
  componente di un bundle **non** applica la variazione (`LISTINO_BUNDLE`), e così l'anteprima
  (`fn_espandi_listino_versione`). La funzione nuova non ricopia la regola: chiede il prezzo al
  resolver. Se la variazione sul kit deve cambiare, cambia lì, in un posto solo.

**I lotti.**

| Lotto | Che cosa | changeSet |
| --- | --- | --- |
| **L10** (D-5) | `fn_create_contratto`: le due chiavi del canone nella whitelist | `20261031-28` |
| **L11** (D-6) | `config.periodicita` in `tabelle_gestibili.csv` (riga 93, lookup sì, pannello no) | seed `20260925-30` |
| **L12** (D-2-bis) | la tabella `vendite.listini_kit` (versione, kit, periodicità NOT NULL; RLS della famiglia dei listini); il guard (solo in bozza, solo su un composito) e il suo montaggio; la sede della periodicità di un articolo sul listino, kit compresi (regola del 2: ritira la copia del default della riga e quella del lister); il default della riga a canone legge la sede; elimina, eliminabile e clona della versione portano il kit; il clone porta anche la periodicità delle righe, che perdeva | `-29` … `-33`, `-36` … `-38` |
| **L13** (D-2) | `vendite.fn_contratto_kit_componenti(contratto, kit, data)`: i componenti del kit sul listino del contratto, nella forma dell'espansore, col prezzo del resolver nel contesto del padre | `-34` |
| **L14** | il lister: la quota fissa di un kit (da `listini_kit`; senza, `SENZA_PERIODICITA`), il prezzo del kit non negoziato (quota fissa, ADESIONE) = la somma dei componenti, la periodicità dalla sede, lo scarto nuovo `QUOTA_FISSA_SENZA_CANONE` (§7.3, la strada «visibile»: l'erogazione la dice il catalogo, che può cambiare dopo l'attivazione) | `-35` |
| **L15** (D-3) | `fn_check_versione_listino_attivabile`, motivo 3: una quota fissa a canone senza periodicità, riga o kit, ferma l'attivazione (`E_LISTINO_VERSIONE_QUOTA_FISSA_SENZA_PERIODICITA`) | `-39` |
| **L16** (D-7) | `periodicita` e `generazione_canone` in coda: il lettore delle eccezioni, l'anteprima (sulla riga DA_LISTINO la periodicità del listino, la proposta di «Aderisci»), i due involucri; 26 colonne | `-40` … `-43` |
| **L17** (D-1, D-1-ter) | la natura del documento dal segno; la nota di credito cita le fatture | `-44` … `-48` (§7.9) |

Catalogo (stesso giro): `codici_errore.csv` e `messaggi_errore.csv` con `E_LISTINO_KIT_NON_COMPOSITO`
(DATO_ERRATO) e `E_LISTINO_VERSIONE_QUOTA_FISSA_SENZA_PERIODICITA` (NON_ESEGUIBILE);
`automation_lock_columns.csv` con l'identità di `listini_kit` (kit e versione, `E_LISTINO_RIGA_IDENTITA_IMMUTABILE`,
come la riga di listino). Riusati: `E_RIGA_LISTINO_VERSIONE_CHIUSA` (fuori dalla bozza, come i componenti).

**Applicato da Tid il 2026-10-31**, `20261031-28` … `-43` e i CSV; pgTAP verdi.

**Prova (2026-10-31, dbdev, owner, transazione annullata; SQL estratto dai changeSet `-28` … `-43`, seed
simulato con le righe nuove dei CSV).**
* Il giro intero si applica nell'ordine e torna indietro; dopo ogni corsa le funzioni vive sono identiche
  (impronta di `vendite`, `script`, `catalogo`, `config`, `dbops` prima e dopo).
* **Nuovo** `vendite/test-listino-kit-e-periodicita-v1`: 18 test, tutto costruito. Un listino di quota fissa
  con una quota (mensile) e un kit (2 × 10 + 30 = 50, trimestrale), due contratti. Copre la struttura, il
  lookup, la sede, i due guard, i tre casi dell'attivazione, clona ed elimina, i componenti dal listino, la
  quota fissa del kit addebitata a 50, l'ADESIONE sul kit (periodicità ereditata, prezzo 50), l'anteprima e
  lo scarto nuovo. 18/18; sul corpo vivo non gira (la tabella non c'è).
* `vendite/test-fn-create-contratto-v1`: 16-18 nuovi (i due campi riletti, i default, il null rifiutato);
  sul vivo rossi il 16 e il 18, attesi.
* **Prima/dopo su 60 pgTAP** che toccano i pezzi cambiati, più i presidi trasversali (riferimenti morti,
  rubinetto del primo motivo, catalogo dei messaggi, motivo nominato, storico, `user_update`, perimetro RLS,
  struttura delle policy). Differenze, tutte spiegate e portate:
  * `test-contratto-righe-lista-uom-riga-v1`, 9: la firma passa da 24 a 26 colonne (atteso, aggiornato);
  * quattro fixture attivavano un listino di quota fissa senza periodicità: è l'effetto di D-3.
    `test-righe-eccezioni-articolo-ammesso-v1` e `offerte_commerciali/test_offerte_eccezioni_componenti`
    scelgono la tipologia «pescando» la prima della utility con certe erogazioni, e oggi la pesca dà la quota
    fissa: la fixture dà la periodicità a righe e kit in bozza. `test-righe-periodicita-da-listino-v1` e
    `test-vw-dash-contratti-giudizio-v1` costruiscono **apposta** una quota senza periodicità: la tolgono
    dopo l'attivazione (vedi il trovato sotto). Dopo: verdi.
* Seconda tornata prima/dopo sui 140 pgTAP che costruiscono un listino o un mondo cliente, fuori dalla
  lista: nessuna differenza, test per test.

**Trovato nel giro — la periodicità si toglie da una versione ATTIVA.** `vendite.trgfn_listini_righe_guard_stato`
ammette in ATTIVA la rettifica di una riga non propagata, e la periodicità non è nel lucchetto: una quota
fissa può perdere la periodicità dopo l'attivazione, e il controllo di D-3 non la vede. È il caso che la
dashboard segnala (F-15), e resta segnalato. Decisione di Tid (2026-10-31): si chiude, §7.10.

**Richiesta al team BE/FE (passo 3), elenco chiuso, dopo l'apply.**
1. **Espansore dei kit** (`BoMComponentExpander`): quando la riga non ha componenti negoziati (la quota
   fissa del kit arriva con `riga_id` NULL; l'ADESIONE su un kit non ne ha), legge
   `vendite.fn_contratto_kit_componenti(contratto, kit, data del pezzo)`: stesse colonne che già legge
   (`componente_id`, `uom_operativa_id`, `coeff_qta_snapshot`, `prezzo_unitario`, `esposizione_in_fattura`,
   `origine_prezzo`). Nessun prezzo in Python. Vale anche per l'una tantum ADESIONE su un kit.
2. **Kit sul listino** (form della riga di listino del kit, il badge «N componenti»): la periodicità si
   scrive in `vendite.listini_kit` (INSERT, UPDATE, DELETE solo in bozza; il DB rifiuta il resto).
   Il BE la traduce sul campo: `fk_listini_kit_periodicita` e `uq_listini_kit_versione_articolo`; i codici
   `E_LISTINO_KIT_NON_COMPOSITO` ed `E_RIGA_LISTINO_VERSIONE_CHIUSA`.
3. **Creazione del contratto**: `generazione_canone` e `mese_partenza_canone` in creazione e modifica
   (D-5); `null` non si manda (NOT NULL col default).
4. **Lookup** (D-6): la voce `config.periodicita` in `_LOOKUP_SPECIALIZZATE`, come scritto nel §7.5.
5. **Anteprima** (D-7): le due colonne in coda (26 colonne), nel form delle righe in modifica; sulla riga
   DA_LISTINO la periodicità è la proposta di «Aderisci».
6. **Attivazione**: il motivo nuovo `QUOTA_FISSA_SENZA_PERIODICITA` (reason_key
   `vendite.listini.azione_reason.quota_fissa_senza_periodicita`, campo `periodicita`) nei locales.
7. **Dashboard**: lo scarto nuovo `QUOTA_FISSA_SENZA_CANONE` esce come gli altri, in `CANONE_NON_GENERABILE`;
   se il BE elenca gli scarti per nome, va aggiunto.
8. **Catalogo errori**: rigenerare `error_policies_generated.py` per i due codici nuovi.

**L17 — la proposta del team DB (2026-10-31); forma accettata da Tid lo stesso giorno, scritta nel §7.9.**

*Perché non è nel giro.* Le testate le costruisce l'orchestratore BE, un'attività alla volta
(`fatture_righe_service.generate_fatture_righe`: segna le attività in lavorazione, poi
`batch_get_or_create_fattura_headers` → `vendite.fn_get_or_create_fattura_header` → `fn_build_fattura_key`).
La chiave nasce per attività, e il totale del gruppo, cioè del documento, a quel punto non esiste. Calcolarlo
dentro la chiave vorrebbe dire ricalcolare le chiavi di tutto il lotto a ogni attività (N² chiamate ai
risolutori). Ricopiare a mano gli elementi della chiave sarebbe una seconda chiave, contro la regola del 2.

*La forma proposta.*
1. **Un verbo DB, chiamato una volta per lotto:** `vendite.fn_lotto_natura_dal_segno(p_lotto_id)`. Il BE lo
   chiama fra «in lavorazione» e «testate». Per ogni attività del lotto calcola la chiave della testata con
   `fn_build_fattura_key`, la stessa di sempre. Raggruppa per chiave le sole attività di natura FATTURA e
   somma quantità × prezzo. Nei gruppi a somma negativa porta le attività a NOTA_CREDITO. Le testate poi
   nascono nota di credito dalla chiave, con il loro registro e la loro serie.
2. **Reversibile:** l'attività battezzata dal segno porta una marca (colonna `natura_dal_segno`). Quando
   torna libera (lotto annullato o riportato in bozza, fatture ripulite) riprende la natura FATTURA. La
   prossima composizione del lotto decide di nuovo. Un building block, chiamato da quei verbi.
3. **D-1-bis resta:** le attività nate NOTA_CREDITO (l'accredito del reso) sono un gruppo loro, e restano
   una nota di credito a sé.
4. **D-1-ter, la nota di credito cita le fatture:** il passo di pipeline che già proietta il legame fra
   documenti (`vendite.fn_popola_fatture_rettifiche`, solo DB) aggiunge le fatture dei pezzi stornati.
   Il cammino è lo storno, poi `meta.storno_di_attivita_id`, poi l'attività fatturabile del pezzo, poi la
   sua `fattura_riga_id`, poi la fattura. Le righe dello storno restano NORMALE: non sono rettifiche di
   una riga (quelle prendono prezzo e IVA dalla riga rettificata, e il guard BE pretende la coppia
   RETTIFICA + puntatore). La citazione è del documento (`fatture_rettifiche`, da cui esce
   `DatiFattureCollegate`). Se il pezzo non era fatturato, lo storno si compensa nella stessa fattura e non
   c'è niente da citare.

*Che cosa serve da Tid:* l'ok alla forma, perché aggiunge una chiamata nel giro del BE (passo 1) e una
colonna su `attivita_fatturabili` (passo 2). Poi il team DB la scrive con i pgTAP del §7.1: soli storni,
misto negativo, misto positivo, accredito di reso dentro una commessa con addebiti.

**Il collegamento di D-1-ter, i fatti (2026-10-31).** Il canale per riga esiste già:
`commesse_attivita.fattura_riga_rettificata_id`, poi `attivita_fatturabili` (lo copia
`fn_emit_attivita_fatturabili_da_commessa`), poi `fatture_righe.riga_rettificata_id`. Quello per documento
è `vendite.fatture_rettifiche`, scritto da `fn_popola_fatture_rettifiche` a partire dalle righe.

### 7.8 Che cosa resta lato DB (2026-10-31, dopo l'apply del giro del §7)

| # | Che cosa | Aspetta | Dove |
| --- | --- | --- | --- |
| 1 | ~~**L17**~~ applicato (§7.9) | — | §7.9 |
| 2 | ~~**L18**~~ scritta (§7.12). La documentazione del giro: `guide/gestione-listini.md` (il kit sul listino e la sua periodicità, il motivo nuovo dell'attivazione, il clone che porta periodicità e kit), `guide/gestione-contratti.md` §4-bis (la quota fissa del kit, il prezzo del kit aderito, lo scarto `QUOTA_FISSA_SENZA_CANONE`), i manual di `listini_kit`, `fn_listino_periodicita_articolo`, `fn_contratto_kit_componenti` e quelli stantii di `fn_contratti_addebiti_maturati` e della preview | — | — |
| 3 | ~~**Passo 4**~~ scritto e provato (§7.13): l'obbligo della periodicità sulla riga a canone (guard col campo + CHECK) e lo script di F-10 sui dati di prova | il passo 3 del BE/FE (il form la chiede) | §6.11 |
| 4 | ~~la periodicità di una quota fissa ferma fuori dalla bozza~~ applicata (§7.10) | — | §7.10 |

Fuori da questo brief, per decisione: ORARIO e CONSUMO aspettano le loro sorgenti (G-4); il default per
utility della finestra del giro non è deciso (G-2).

### 7.9 L17 — la nota di credito dal segno, scritto (2026-10-31)

Forma del §7.7 accettata da Tid il 2026-10-31 (la chiamata nel giro del BE e la colonna).

| changeSet | Che cosa |
| --- | --- |
| `00_schema/vendite/20261031-44-alter-attivita-fatturabili-natura-dal-segno` | `attivita_fatturabili.natura_dal_segno boolean NOT NULL DEFAULT false`: la natura NOTA_CREDITO l'ha decisa il segno del documento |
| `20_code/vendite/20261031-45-create-fn-lotto-natura-dal-segno` | il verbo `vendite.fn_lotto_natura_dal_segno(lotto)`: le attività FATTURA del lotto (lucchetto del lotto, non fatturate), raggruppate per chiave di testata con `fn_build_fattura_key`, si sommano (quantità × prezzo); nei gruppi negativi diventano NOTA_CREDITO con la marca. Rieseguibile: prima ritira le marche del lotto. Ritorna quante. EXECUTE a `zeroerp_app` |
| `-46` `fn_libera_attivita_fatturabili` | la primitiva che libera (l'unica): l'attività marcata riprende FATTURA, la marca cade |
| `-47` `fn_emit_attivita_fatturabili_da_commessa` | la riemissione riscrive la natura dalla commessa e toglie la marca (l'unico scrittore di righe di `attivita_fatturabili`, censito) |
| `-48` `fn_popola_fatture_rettifiche` | D-1-ter: sulla nota di credito, anche le fatture dei pezzi di canone stornati (storno → `meta.storno_di_attivita_id` → pezzo → attività fatturabile → riga di fattura → fattura). Le righe dello storno restano NORMALE |

**Prova (2026-10-31, dbdev, owner, transazione annullata; SQL estratto dai changeSet `-44` … `-48`).**
* **Nuovo** `vendite/test-lotto-natura-dal-segno-v1`: 11 test, tutto costruito (commesse, attività emesse
  dalla madre, lotti, testate dalla chiave). Soli storni → nota di credito, e la testata nasce nota di
  credito; misto negativo (-300 + 50) → una nota di credito sola; misto positivo (+300 - 50) → FATTURA;
  D-1-bis (l'attività nata nota di credito non si tocca); rieseguibile; libera; lotto inesistente;
  D-1-ter (la nota di credito dello storno cita la fattura del pezzo, idempotente). 11/11.
  Controprova: senza `-46` e `-48` sono rossi il 7 e il 10.
* Il giro si applica nell'ordine e torna indietro; funzioni vive invariate dopo ogni corsa.
* **Prima/dopo su 93 pgTAP** che toccano attività fatturabili, emissione, liberazione, testate, rettifiche e
  natura, più i presidi trasversali (riferimenti morti, rubinetto del primo motivo, catalogo dei messaggi,
  motivo nominato, `user_update`, storico): nessuna differenza, test per test.

**Richiesta al team BE (si aggiunge a quella del §7.7).**
9. **La chiamata nel giro**: in `fatture_righe_service.generate_fatture_righe`, dopo
   `mark_attivita_running` e prima di `batch_get_or_create_fattura_headers`,
   `SELECT vendite.fn_lotto_natura_dal_segno(%s)` col lotto, nella stessa transazione. Niente regola nel BE.
   Finché manca, tutto resta come oggi: un documento di soli storni nasce FATTURA e non si numera.

### 7.10 La quota fissa non perde la periodicità fuori dalla bozza (decisione di Tid, 2026-10-31; applicato)

Sul trovato del §7.7: fuori dalla bozza la riga di una quota fissa a canone non resta senza periodicità.
Cambiarla con un'altra resta una rettifica, come il prezzo (la regola di `trgfn_listini_righe_guard_stato`
non cambia).

| changeSet | Che cosa |
| --- | --- |
| `20_code/vendite/20261031-49-create-fn-articolo-quota-fissa-a-canone` | `vendite.fn_articolo_quota_fissa_a_canone(articolo)`: tipologia di quota fissa ed erogazione di default CANONE. Sede unica (regola del 2) |
| `20_code/script/20261031-50-…-attivabile-quota-fissa-dalla-sede` | il motivo 3 dell'attivazione legge la sede; la copia scritta nel `-39` si ritira. Comportamento invariato |
| `20_code/vendite/20261031-51-create-trgfn-listini-righe-guard-periodicita-quota-fissa` | il guard: periodicità che va a NULL su una versione non in bozza, articolo quota fissa a canone → `E_LISTINO_QUOTA_FISSA_PERIODICITA_FERMA` (CONFLITTO_STATO, campo `periodicita`) |
| `20_code/vendite/20261031-52-create-trigger-listini-righe-periodicita-quota-fissa` | montaggio BEFORE UPDATE OF periodicita, WHEN da un valore a NULL; il nome viene dopo `_a10_guard_stato_upd_dlt` (sulla versione CHIUSA parla lei) |
| `codici_errore.csv`, `messaggi_errore.csv` | il codice nuovo |

⚠️ **Resta una strada sola** per una quota senza periodicità su una versione attiva: il catalogo che cambia
dopo l'attivazione (la tipologia dell'articolo, o la sua erogazione di default). La dashboard la segnala:
`SENZA_PERIODICITA`, o `QUOTA_FISSA_SENZA_CANONE` se la quota smette di essere un canone.

**Prova (2026-10-31, dbdev, owner, transazione annullata; SQL estratto da `-49` … `-52`, seed simulato).**
* `vendite/test-listino-kit-e-periodicita-v1`: due test in più, ora 20. Il 9: toglierla su una versione
  ATTIVA si rifiuta. Il 10: cambiarla con un'altra passa. 20/20; sul vivo è rosso il solo 9, atteso.
* `test-righe-periodicita-da-listino-v1` e `test-vw-dash-contratti-giudizio-v1` costruivano la quota senza
  periodicità togliendola dopo l'attivazione, e il guard ora lo vieta. La costruiscono dall'unica strada che
  resta: in bozza la tipologia QUOTA_FISSA non si eroga a canone (vocabolario cambiato nella transazione),
  la versione si attiva, poi il catalogo torna com'era. Prima/dopo: verdi identici.
* Prima/dopo su 43 pgTAP che toccano righe di listino, attivazione, periodicità e vocabolario delle
  erogazioni, più i presidi trasversali: l'unica differenza è il test 9 nuovo, rosso sul vivo e verde dopo.

**Ricaduta BE/FE:** il codice nuovo nelle error policies (rigenerare) e sul campo `periodicita` della riga
di listino.

### 7.11 Il passo 3 BE/FE — fatto (team BE/FE, 2026-10-31)

> **Chi scrive:** team BE/FE (`dev/backend-tid`), 2026-10-31, dopo l'apply di `20261031-28` … `-52`.
> **A chi:** Tid (collaudo e commit), poi il team DB (§7.11.3).

**7.11.1 La richiesta, punto per punto.**

| # | Punto | Dove | Fatto |
| --- | --- | --- | --- |
| 1 | Espansore dei kit | `commesse_source_handlers.BoMComponentExpander` | secondo lettore `componenti_listino_loader`: quando la riga non ha componenti negoziati (quota fissa senza riga, ADESIONE su un kit) legge `vendite.fn_contratto_kit_componenti` alla `data_attivita` del pezzo, la stessa a cui il lister prezza il kit. Lo inietta il solo `HandlerContratti` (`ContrattiRepository.list_componenti_kit_dal_listino`, contratto dal `sorgente_uid`). Nessun prezzo in Python |
| 2 | Kit sul listino | `PUT …/listini/<l>/versioni/<v>/bundle/<kit>/` `{periodicita}` | scrive o toglie (`null`) la riga di `vendite.listini_kit`; la lista delle righe la porta sulla riga del composito; il DELETE del bundle toglie anche il kit. FE: «Periodicità del kit» nel kebab della riga del composito (in bozza). FK e `E_LISTINO_KIT_NON_COMPOSITO` / `E_RIGA_LISTINO_VERSIONE_CHIUSA` tradotti |
| 3 | Creazione del contratto | `contratti_service` | i due campi nei tre anelli (whitelist, mapper — dal §7.11.4 il BB `campi_canone` —, colonne); `null` si omette; i due `chk_contratti_*` sul campo. FE: la sezione «Canoni» anche sul contratto |
| 4 | Lookup | `_LOOKUP_SPECIALIZZATE` | `config.periodicita`, extra `mesi` (la tendina ordina sul ritmo) |
| 5 | Anteprima a 26 colonne | `RigheEccezioniDrawer` | periodicità e generazione nel form della riga a canone: in modifica come scritte, su «Aderisci» la periodicità del listino. La riga di listino ha il campo periodicità |
| 6 | Motivo d'attivazione | locales | `vendite.listini.azione_reason.quota_fissa_senza_periodicita` |
| 7 | Dashboard | — | niente da fare: la vista giudica `scarto IS NOT NULL` e nessuno elenca gli scarti per nome |
| 8 | Catalogo errori | `error_policies_generated.py` | rigenerato (tre codici, `--check` pulito) e i tre ripieghi senza `%s` |
| 9 | La chiamata nel giro | `fatture_righe_service.generate_fatture_righe` | `fn_lotto_natura_dal_segno` dopo «in lavorazione» e **prima** dei group input e delle testate (repository `applica_natura_dal_segno`) |

**Building block (regola del 2, ok Tid 2026-10-31).** `vendite/_shared/canoni/`: `campiCanone.js` e
`CampiCanoneTestata.vue` (la sezione «Canoni» di contratto e offerta; le chiavi i18n passano a
`vendite.canoni.*`, quelle dell'offerta ritirate), `PeriodicitaSelect.vue` (la tendina, tre consumatori:
riga a canone, riga di listino, kit). Registrati nel catalogo FE.

**7.11.2 Prove (2026-10-31, dbdev).** Backend: i test dei moduli toccati e i nuovi, col DB vero acceso
(`ZEROERP_TEST_DB_E2E=1`), fra cui `vendite/tests/db/test_listino_kit_periodicita_db.py` (7 test, mondo
costruito: scrive, cambia, toglie, lista, delete del bundle, semplice rifiutato, fuori vocabolario sul
campo, fuori bozza, il lettore dell'espansore legato alla funzione); il guardrail della whitelist della
madre del contratto; mypy e ruff puliti. Frontend: vitest 1062/1062, lint e guard i18n puliti. ⚠️ Il
guard `capability` è rosso su `catalogo/stores/articoloUom.js` e `ArticoloUomDrawer.vue`, file non toccati
da questo giro: è nel HEAD di partenza. Suite intera del backend (7090 test, DB vero acceso): verde per
questo giro; 12 rossi del giro DB `11d434949` (brief-db-liste-datatable-grezze-secondo-giro: `tipo_valore`
dei parametri, due codici nuovi, `lista_colonna`), applicato su dbdev e non ancora nel branch BE.
`error_policies_generated.py` qui è rigenerato **prima** di quel giro (1153 voci): ⛔ non si rigenera col
DB avanti rispetto a git.

**7.11.3 Richiesta al team DB.** La lista delle righe di listino (`ui.lista_definizione` 37,
`vendite.listini_righe`) non ha la colonna della periodicità: il dato arriva (`periodicita`, anche sul
composito), ma a video non si vede. Una riga in `lista_colonna.csv` (campo `periodicita`, etichetta
`vendite.canoni.field_periodicita`), e se va ordinabile la voce in `RIGHE_ORDER_COLUMNS` la aggiunge il BE.
Con questo e il passo 4 il brief arriva alla chiusura.

**7.11.4 Revisione critica del passo 3 (team BE/FE, 2026-10-31).** Nessun bug nel codice del passo 3.
Verificati sulla doc auto-generata e col DB vero: il guard di `vendite.listini_kit` copre anche il DELETE
(togliere la periodicità a un kit fuori bozza è rifiutato senza un controllo Python); la firma di
`fn_lotto_natura_dal_segno(bigint)`; il PATCH del contratto fuori bozza manda i soli riferimenti
dell'atto, quindi i campi del canone non arrivano al lock di testata. Corretto:

| # | Cosa | Dove |
| --- | --- | --- |
| 1 | ⭐ **Regola del 2 (ok Tid)**: i due campi del canone in testata erano in due copie già divergenti. Il contratto normalizzava (maiuscolo, mese intero, `null` omesso); l'offerta passava i valori grezzi: «fine_periodo» era un 400 del CHECK, `null` un NULL su una colonna NOT NULL. Ora un BB solo: `campi_canone` / `con_campi_canone` (la lettura) e `check_campi_canone(tabella, code)` (i due `chk_<tabella>_*` sul campo). Ritirati `_apply_campi_canone`, `_CAMPI_CANONE` e le due mappe CHECK scritte a mano. Registrato nel catalogo BE | `apps/vendite/services/_campi_canone.py`; `contratti_service`, `offerte_service` |
| 2 | Il dialog della periodicità del kit ha il suo gestore d'errore: un errore sul campo non accende più anche il form della riga, e viceversa | `VersioneDrawer.vue` |
| 3 | Il lettore dei kit dal listino legge una volta per (contratto, kit, data) nel giro di push: l'handler nasce a ogni giro (`_build_handlers`), la memoria non vede un listino vecchio | `HandlerContratti._componenti_listino_loader` |
| 4 | Pulizie: il `nextTick` ridondante all'apertura del dialog del kit (lo fa `useFotografiaDialog`), le firme di `_kit_db_errors` e dell'override del lettore, l'indice dei test dell'espansore (57–61), `PeriodicitaSelect` registrato nel catalogo FE | — |

Prove (2026-10-31, dbdev, `ZEROERP_TEST_DB_E2E=1`): suite `apps.vendite` 2644 test verdi, fra cui i nuovi
`test_campi_canone` (6), `test_offerte_service` 68–69 e `test_kit_dal_listino_una_lettura_per_pezzo`;
ruff e mypy puliti. Frontend: vitest `src/vendite` 195/195, lint pulito. ⚠️ Dopo l'aggiornamento serve
il `kill -HUP` al master di gunicorn: il comportamento Python dell'offerta è cambiato.

### 7.12 L18 — la documentazione del giro del §7, scritta (team DB, 2026-11-01)

Solo testo: nessun changeSet. Copre il giro del §7 per intero, L17 e §7.10 compresi (il §7.8 era stato
scritto prima). Fatti presi dalla doc auto-generata alla stessa data.

| File | Che cosa |
| --- | --- |
| `guide/gestione-listini.md` | §2.1: il kit sul listino (`listini_kit`) e la sua periodicità, la sede `fn_listino_periodicita_articolo`; la quota fissa a canone che deve avere la periodicità (attivazione, ferma fuori bozza, la strada del catalogo); il terzo motivo dell'attivazione; clone ed eliminazione che portano periodicità e kit. §5.2: il kit non negoziato prende i componenti dal listino. §9 tre garanzie, §10 quattro codici |
| `guide/gestione-contratti.md` | §4-bis.1 la quota fissa del kit; §4-bis.3 il prezzo del kit non negoziato (somma dei componenti, oggi senza variazione globale: la regola del resolver); §4-bis.4 lo storno che fa nota di credito e cita le fatture; §4-bis.5 lo scarto `QUOTA_FISSA_SENZA_CANONE` |
| `guide/fatturazione.md` | sezione nuova «La natura la dà il segno del documento» (L17, D-1, D-1-bis, D-1-ter) |
| `guide/cruscotti-fatturazione.md` | §4.2: il rosso dei contratti con i motivi di oggi |
| `vendite/manual/listini_kit.md`, `fn_listino_periodicita_articolo.md`, `fn_contratto_kit_componenti.md`, `fn_articolo_quota_fissa_a_canone.md`, `fn_lotto_natura_dal_segno.md` | nuovi |
| `vendite/manual/fn_contratti_addebiti_maturati.md` | stantio dal L14: il kit di quota fissa, il prezzo del kit, lo scarto nuovo, la periodicità dalla sede |
| `vendite/manual/fn_documento_righe_preview.md` | stantio dal L4a e dal L16: l'origine ADESIONE e i suoi verbi, «Aderisci», le due colonne in coda (26) |
| `vendite/manual/fn_clona_versione_listino.md`, `fn_elimina_versione_listino.md`, `script/manual/fn_check_versione_listino_eliminabile.md`, `script/manual/fn_check_versione_listino_attivabile.md`, `vendite/manual/listini_righe.md` | il kit, la periodicità del clone, il motivo 3, il guard della quota fissa ferma |
| `vendite/manual/attivita_fatturabili.md`, `fn_libera_attivita_fatturabili.md`, `fn_popola_fatture_rettifiche.md` | la marca `natura_dal_segno` e la citazione delle fatture (L17) |
| `vendite/manual/vw_dash_fatturazione_contratti.md` | lo scarto nuovo fra i motivi del rosso |

Link verificati: ogni bersaglio esiste sotto `docs/`; le ancore nuove verso le guide (`#21-listino`,
`#4-bis3-il-canone`, `#4-bis4-…`) lette dal sito già costruito, senza lanciare la build.

### 7.13 Il passo 3-ter e il passo 4 — scritti e provati (team DB, 2026-11-01; via di Tid lo stesso giorno)

#### 7.13.1 La colonna «Periodicità» nella lista 37 (la richiesta del §7.11.3)

* `lista_colonna.csv`, riga **1165**: lista 37, `periodicita`, etichetta `vendite.canoni.field_periodicita`,
  dopo il prezzo (ordine 45), `informazione`/`string`, esportabile. **Non ordinabile e non filtrabile**:
  `RIGHE_ORDER_COLUMNS` non la conosce, e `test_whitelist_copre_le_colonne_ordinabili` farebbe rosso
  sull'`ordinabile = t` senza la voce BE. Se va ordinata, la voce BE e il flag si accendono insieme.
* `lista_preset_colonna.csv`: la colonna visibile nel preset di default della lista (37, 1165, 45).
* Nessun changeSet: i due CSV li carica il loro mirror (`runOnChange`).

#### 7.13.2 Il passo 4 — la periodicità obbligatoria sulla riga a canone

Decisioni di Tid: G-0-bis (2026-10-28), F-9 e la (b) del Lotto 4b (2026-10-29: l'obbligo entra col form,
che dal passo 3 la chiede).

| changeSet | Che cosa |
| --- | --- |
| `00_schema/vendite/20261101-04-alter-righe-eccezione-chk-canone-periodicita` | `chk_contrighe_canone_periodicita` e `chk_offerte_eccezioni_canone_periodicita`: `tipo_erogazione IS DISTINCT FROM 'CANONE' OR periodicita IS NOT NULL` (nessuna metà vale NULL). Due vincoli nuovi, non una riscrittura di `chk_*_coerenza_canone`: un vincolo, un campo |
| `20_code/script/20261101-05-create-trgfn-righe-guard-periodicita-canone` | `script.trgfn_righe_guard_periodicita_canone`: la riga CANONE senza periodicità → `E_RIGA_CANONE_SENZA_PERIODICITA` (DATO_ERRATO, campo `periodicita`). Gemello di `trgfn_righe_guard_erogazione_obbligatoria`; una funzione per le due tabelle. Aggiorna anche il COMMENT del default (diceva «l'obbligo non è qui») |
| `20_code/vendite/20261101-06-create-trigger-righe-guard-periodicita-canone` | i due montaggi, BEFORE INSERT OR UPDATE OF `tipo_erogazione`, `periodicita`, WHEN canone e senza periodicità. **Il nome governa l'ordine**: dopo i default (erogazione, periodicità dal listino) e dopo i guard dell'erogazione («guard_p» dopo «guard_e»: a una riga fuori perimetro parla prima il perimetro), prima della quantità per fonte |
| `codici_errore.csv`, `messaggi_errore.csv` | il codice nuovo, messaggio 1419 (frase chiusa) |

⚠️ **Trovato nel giro.** Il primo nome, `guard_canone_periodicita`, ordinava **prima** del perimetro: a una
riga che non può essere a canone il guard diceva «manca la periodicità». Lo ha visto il prima/dopo
(il test 8 di `test-righe-erogazione-da-articolo-v1`, il 9 di `test-righe-esclusione-solo-non-si-vende-v1`,
l'8 di `test-righe-quantita-per-fonte-v1`). Rinominato prima di consegnare, e il test 5 del pgTAP nuovo
ne presidia l'ordine.

Chi copia le righe porta già la periodicità: `fn_push_offerta_a_contratto` e `fn_crea_revisione_offerta`
(corpo vivo). Nessun builder `dbops` e nessun seed scrive righe di contratto o di offerta: su un DB da zero
il CHECK nasce su tabelle vuote.

**Prova (2026-11-01, dbdev, owner, transazione annullata; SQL estratto dai changeSet `-04` … `-06`, seed
simulato con le due righe nuove dei CSV, script di F-10 in testa).**
* L'SQL si applica nell'ordine e torna indietro; dopo F-10 nessuna riga a canone senza periodicità e
  nessun trigger spento.
* **Nuovo** `vendite/test-righe-canone-periodicita-obbligatoria-v1`: 14 test, tutto costruito (CHECK, montaggi,
  ordine, rifiuto col codice e col campo su contratto e offerta, UPDATE che la toglie, una tantum che passa).
  14/14; sul corpo vivo rosso, atteso.
* `vendite/test-righe-periodicita-da-listino-v1`: il 2 e il 3 dicevano «vuota, e si salva»; ora «si rifiuta».
  Prima 4/6, dopo 6/6.
* **Prima/dopo su 75 pgTAP**: i 44 che scrivono le due tabelle, i 15 che le nominano in altra forma, i
  presidi trasversali (catalogo dei messaggi, identità dei codici, motivo nominato, valore atteso, rubinetto
  del primo motivo, riferimenti morti, `user_update`, search_path, viste invoker, struttura delle tabelle).
  Sette fixture creavano righe a canone senza periodicità, e nessuna ne faceva il soggetto: la scrivono
  (MENSILE), con una riga di revisione in testa. Dopo: uguali, test per test.
  * `test-vw-dash-contratti-giudizio-v1`: **K2 sì** ne faceva il soggetto (un'ADESIONE che dal listino
    ereditava una periodicità vuota, per il rosso). Il modello non lo ammette più: il rosso di K2 viene ora
    dalla quota P del listino senza periodicità, l'unica strada che resta (il catalogo che cambia dopo
    l'attivazione). Attese invariate.
  * `test-righe-eccezioni-articolo-ammesso-v1`: la fixture «pesca» la tipologia e oggi la pesca dà una quota
    fissa; la riga che eredita un canone scrive la periodicità.
* Guardrail statici puliti sui file nuovi (licenza, run_on_change, precondition_seed, ddl su trigger
  d'automazione, grant ai batch, letterali, timestamp). Il preambolo pgTAP segnala due violazioni in
  `config/test-grammatica-presidio-tipo-documento-v1.sql`: non di questo giro.

#### 7.13.3 Per Tid: lo script di F-10, prima dell'apply

Su dbdev ci sono righe di prova a canone senza periodicità (2026-11-01, fatto datato: 10 di contratto, 12 di
offerta): il CHECK del `-04` le rifiuta, e l'apply si ferma. Lo script (F-10, §6.10; Tid, 2026-10-29), da
owner, **prima** dell'apply:

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

In CI non serve: il DB nasce vuoto.

#### 7.13.4 Richiesta al team BE/FE, elenco chiuso, dopo l'apply (apply fatto: si parte)

1. **Catalogo errori**: rigenerare `error_policies_generated.py` e il ripiego per
   `E_RIGA_CANONE_SENZA_PERIODICITA` (DATO_ERRATO, campo `periodicita`, nessun segnaposto). Il form della
   riga a canone accende il campo; nessuna regola ricopiata nel form.
2. **Test DB** (`ZEROERP_TEST_DB_E2E=1`): i test che scrivono righe a canone senza periodicità diventano rossi
   per costruzione. Da guardare per primo `vendite/tests/db/test_righe_erogazione_obbligatoria_db.py` (righe
   che ereditano CANONE/FISSA); poi la suite `apps.vendite`, e gli smoke in `backend/scripts/tests/` se
   creano righe di contratto o di offerta.
3. **Lista 37**: la colonna «Periodicità» arriva dal seed (§7.13.1). Se la si vuole ordinabile, la voce in
   `RIGHE_ORDER_COLUMNS` e `ordinabile = t` nel CSV vanno insieme (lo chiede `test_liste_configurabili_seed`).
   Collaudo a video: la colonna mostra il codice del vocabolario; se serve la descrizione, va detto.

Con questo il brief arriva all'archiviazione.

#### 7.13.5 Apply e pgTAP (Tid, 2026-11-01)

* Primo apply fermo sul `-04` (`chk_contrighe_canone_periodicita` violato): F-10 non era ancora passato.
  Liquibase non ha registrato nulla del giro, nessun trigger è rimasto spento.
* Script di F-10 da owner (§7.13.3), poi apply: `20261101-04`, `-05`, `-06` `EXECUTED` nel
  `databasechangelog`, con i CSV (`E_RIGA_CANONE_SENZA_PERIODICITA` in `config.codici_errore`, colonna
  1165 nella lista 37).
* Dopo l'apply, fatto datato: 0 righe a canone senza periodicità su `vendite.contratti_righe` e su
  `vendite.offerte_commerciali_eccezioni`.
* pgTAP verdi, compreso il nuovo `test-righe-canone-periodicita-obbligatoria-v1`.

Da committare su `dev/db-tid`: L18 (§7.12), il passo 3-ter e il passo 4 (§7.13), questo documento.
