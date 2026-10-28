# Brief DB — Le righe di contratto che non sono «una volta»: canone, orario e consumo in commessa

## ⏭️ Chi riparte — aggiornato al 2026-10-28

**Riparte: team DB**, con l'analisi della forma sulle decisioni del §4.1. Il via allo sviluppo lo dà
Tid dopo l'analisi. I fatti sono stati ricontrollati il 2026-10-28 contro il lavoro dal 13-10 (§2-bis).

| # | Chi | Che cosa | Dove | Aspetta |
| --- | --- | --- | --- | --- |
| 1 | ✅ Tid | decisioni G-0 … G-11 (2026-10-28), verificate contro guide e doc | §4.1, §4.3 | — |
| 2 | DB | analisi della forma scelta e consegna | — | 1 |
| 3 | BE/FE | da definire dopo la forma (l'orchestratore del push, la lista dei contratti) | — | 2 |

Decisioni aperte di Tid: nessuna (G-0 … G-11 prese il 2026-10-28, G-0 rivista dopo la verifica del §4.3). Lavoro da committare: questo documento (il giro che lo ha aperto,
`20261013-24`, è nella risposta al team BE del 2026-10-13).

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
| **G-10** | Le ore: il **pacchetto di ore fisse al periodo** (per esempio 10 ore al mese) entra nel giro come canone `FISSA` sull'unità di misura **ORA**, che si aggiunge al catalogo (oggi ci sono GIORNO e MESE, non l'ora: solo KILOWATT ORA, dbdev 2026-10-28). Le **ore lavorate** (`ORARIO/TIMESHEET`) aspettano il timesheet (G-4): fino ad allora non arrivano in commessa. |
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

* Il lister dei contratti manda solo le UNA_TANTUM (`20261013-24`). Il presidio è
  `vendite/test-push-contratto-dalla-madre-v1` (parte D) e
  `vendite/test-righe-erogazione-obbligatoria-v1` (19, 21).
* ⚠️ Quando la generazione arriva, il filtro `cr.tipo_erogazione = 'UNA_TANTUM'` del lister si
  allarga, e i due test sopra cambiano con lui: non vanno «aggiustati», raccontano la regola.
