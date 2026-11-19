# Brief DB — Revisione dello schema `ui`: la documentazione, i difetti di codice, i metadati

## ⏭️ Chi riparte — aggiornato al 2026-11-20

**Riparte: Tid**, col via al giro 1. Le decisioni Q1-Q26 sono prese (2026-11-18 … 2026-11-20, §7 e le schede dei
difetti), l'ordine dei giri è deciso (§2). Il giro 0 è fatto: le 32 pagine `manual/`
sono allo standard (28 riscritte, 4 nuove), la guida `configurazione-liste` è riallineata al codice, il censimento è
scritto (§3-§6). Nessun changeSet è scritto: lo sviluppo parte col via di Tid.

| # | Chi | Che cosa | Dove | Aspetta |
| --- | --- | --- | --- | --- |
| 1 | ✅ sessione DB | Giro 0: 32 pagine `ui/manual/` allo standard, guida `configurazione-liste` riallineata, link della mappa concentrica | §8 | — |
| 2 | ✅ sessione DB | Censimento in sola lettura: difetti, metadati, pgTAP, ricadute BE/FE | §3-§6 | — |
| 3 | Tid | Doc auto-generata rigenerata: le schede delle 4 funzioni con la pagina nuova non la includono ancora, e `ui/index.md` porta ancora «(scritta il 30-09-2026)» come descrizione | §8.3 | 1 |
| 4 | ✅ Tid | Le decisioni Q1-Q26 e l'ordine dei giri, prese dal 2026-11-18 al 2026-11-20 | §2, §7 | 2 |
| 5 | team BE | Le ricadute «subito» (BE1-BE4), che non aspettano il DB | §6 | — |
| 6 | Tid | Il via al giro 1 | §2 | 4 |
| 7 | sessione DB | I giri 1-6, uno per volta, ciascuno con apply e pgTAP di Tid | §2 | 6 |
| 8 | team BE/FE | Le ricadute di ogni giro, dopo il suo apply | §6 | 7 |
| 9 | sessione DB | Archiviazione in `work-done/` | §10 | 7, 8 |

**Decisioni di Tid:** tutte prese — Q1-Q11 il 2026-11-18, Q12-Q25 il 2026-11-19, Q26 il 2026-11-20 (registrate in §7 e nelle schede dei difetti). **Da committare:** le 32 pagine di `docs/it/dbzero/ui/manual/`,
`docs/it/guide/configurazione-liste.md`, `docs/it/mappa-concentrica.md` (un link), `.codex/PROJECT_CONTEXT.md` (una riga), questo brief. ⚠️ Le altre modifiche
nell'albero (CSV di `config` e `dbops`, pgTAP di altri schemi) sono di un'altra sessione.

> **Chi scrive:** sessione DB (`dev/db-tid`), 2026-11-18; decisioni registrate fino al 2026-11-20. **A chi:** Tid e team DB.
> **Origine:** revisione della documentazione dello schema `ui` chiesta da Tid: allinearla allo standard e alle
> funzionalità, togliere le parti stantie, segnalare dove il codice non rispetta ciò che è scritto. Metodo dei brief di
> revisione di `catalogo`, `dbops` e `documenti`
> ([brief-db-revisione-documenti](../work-done/brief-db-revisione-documenti.md)).
> **Brief vicini verificati:** [sviluppo-personalizzazioni-liste_def](sviluppo-personalizzazioni-liste_def.md) tiene
> gli sviluppi non fatti delle liste (viste nominate, condivisione) e la domanda sulle dashboard: sono funzionalità
> nuove, non revisione, e qui non si toccano. [piano-be-fe-endpoint-senza-porta](piano-be-fe-endpoint-senza-porta.md)
> cita una lista di `ui` solo come fatto. Nel [registro dei residui](registro-residui-aperti.md) nessuna voce ha per
> oggetto le tabelle o le funzioni di `ui`.

⚠️ Il DDL e il corpo di ogni oggetto si prendono dalla doc auto-generata (`docs/it/dbzero/ui/…`), rigenerata il
2026-11-14. Nessun changeSet successivo tocca gli oggetti di `ui` (verificato il 2026-11-18). Il giro 0 ha letto i corpi
dal catalogo di dbdev. Prima di scrivere un giro si riverifica: un changeSet successivo sull'oggetto rende stantia la
doc auto-generata.

## 1. Il perimetro

Lo schema `ui` ha 13 tabelle in tre famiglie e 19 funzioni (8 funzioni e 11 trigger function); non ha viste:

* **le liste**: definizione, colonne, permessi di colonna, preset, composizione del preset, preferenza dell'utente;
* **le misure di pagina**: il catalogo delle righe per pagina;
* **le dashboard**: definizione, catalogo dei widget, pool, preset, composizione, preferenza.

Si contano anche i trigger generici montati sulle tabelle (regola ATTIVO, audit), le eccezioni ATTIVO di `dbops` che le
riguardano e le copie della stessa regola trovate nel backend.

Ogni difetto si regge sul **modello**: che cosa ammettono colonne, vincoli e corpi. Nessun conteggio di righe entra come
motivo; dove compare un numero, è un fatto datato al 2026-11-18.

**Un fatto del modello, non un difetto.** `ui` non segue il modello «una scrittura = un verbo»: `zeroerp_app` ha
INSERT, UPDATE e DELETE diretti su tutte le tabelle tranne `misure_pagina`, che legge soltanto, e nessuna tabella ha
RLS. Il dominio ci passerà quando un cantiere toccherà le sue scritture (PROJECT_CONTEXT, «I domini nuovi nascono con il
permesso applicato dal DB»). Diversi difetti qui sotto sono regole che oggi tiene solo il backend: su un dominio a verbi
starebbero nel verbo.

## 2. Il piano: i giri proposti

Deciso da Tid il 2026-11-19 (Q24): i sei giri nell'ordine della tabella. L'ordine è per gravità. I lavori sugli stessi oggetti vanno insieme, perché ogni tabella si apra una
volta sola, e liste e dashboard si correggono nello stesso giro: dove sono gemelle, una copia corretta da sola
diverge dall'altra. Ogni giro comprende changeSet, pgTAP che costruiscono i propri soggetti, COMMENT e pagine `manual/`
riallineati (la riga di «⚠️ Che cosa oggi non copre» del difetto chiuso si toglie); poi l'apply di Tid e il via al giro
dopo.

| Giro | Classe | Contenuto | Ricadute BE/FE | Perché insieme |
| --- | --- | --- | --- | --- |
| 1 | A + B + C | **Il preset di base e il banner.** U1-U9; il ritiro di `is_default` (Q26) | BE5, BE6, BE7, BE22 | I due resolver, i due trigger z90, `trgfn_preset_*`: la scelta del preset di base e il flag del preset aggiornato |
| 2 | A + B | **La forma della preferenza e i widget nuovi.** U10-U14 | BE8, BE9 | Il guard di forma comune a liste e dashboard, il conteggio dei nuovi, ordinamento e filtri, i legami fra preset, colonne e pool |
| 3 | A + B + C | **Le misure.** U15-U21 | BE10, BE11, FE1 | `misure_pagina`, i guard di `pagina_dimensione`, `dimensione_max` della dashboard |
| 4 | B + C | **Il catalogo delle liste.** U22-U30 | BE12-BE16 | `lista_definizione`, `lista_colonna`, i loro trigger e i permessi di colonna |
| 5 | B + C | **Il catalogo delle dashboard.** U31-U36; in chiusura la guida `configurazione-dashboard` (Q25) | BE17 | Le cinque tabelle che l'app non scrive, il widget |
| 6 | C | **Pulizia.** Metadati (§4), codici errore, pgTAP deboli (§5), U37-U39 | BE18 | Ciò che nessun giro precedente ha già aperto |

## 3. I difetti di codice

Forma compatta: **fatto** · **correzione proposta** · **presidio**. Le classi sono quelle dei brief precedenti:

* **A**: contraddice un contratto deciso, oppure è sbagliato ogni volta che il ramo si percorre;
* **B**: un caso che il modello ammette e che non è gestito;
* **C**: pulizia, doppie sedi.

La colonna «Aree» rimanda ai rapporti del giro 0 (A catalogo delle liste, B preset e risoluzione, C misure, D
dashboard, E guida). Dove due aree hanno trovato lo stesso difetto, qui è una voce sola.

| Classe | Difetti |
| --- | --- |
| **A** | U1, U10, U15 |
| **B** | U2, U3, U4, U5, U6, U7, U11, U12, U13, U14, U16, U17, U18, U20, U21, U22, U23, U24, U25, U26, U27, U28, U29, U31, U32 |
| **C** | U8, U9, U19, U30, U33, U34, U35, U36, U37, U38, U39 |

### 3.1 Giro 1 — il preset di base e il banner

**U1 (A) — Il trigger z90 cancella lo snapshot appena scritto** · aree B, D · Q1.

* **Fatto.** `trgfn_ui_lista_preferenza_utente_z90_clear_preset_base_ts` e il gemello delle dashboard sono
  `BEFORE UPDATE OF preset_base_id`: se il preset di base cambia, azzerano `preset_base_contenuto_aggiornato_il` e
  `preset_aggiornato_ignored_at`. L'upsert del BE (`backend/apps/ui/db/ui_repository.py:346`,
  `dashboard_repository.py:136-140`) scrive nella stessa istruzione il preset nuovo e il suo snapshot, e il trigger
  azzera lo snapshot. Così, ogni volta che un salvataggio cambia il preset di base, il banner del preset aggiornato
  resta muto fino al salvataggio successivo. Verificato sul corpo il 2026-11-18. Un pgTAP
  (`test-fn-resolve-lista-config-cascata-per-chiave-v1.sql:321-325`) lo aggira con un secondo UPDATE. I due corpi sono
  identici riga per riga.
* **Correzione proposta.** (a) Il trigger azzera lo snapshot solo se lo stesso UPDATE non ne porta uno nuovo. (b) Lo
  snapshot lo scrive il DB, leggendo il contenuto del preset di base. **Raccomandata (b)**, insieme a U2. In tutte e due
  le strade c'è una funzione sola, montata sulle due tabelle.
* **Decisione (Q1, Tid, 2026-11-18).** (b): lo snapshot lo scrive il DB, leggendolo dal preset di base; una funzione sola sulle due tabelle.
* **Presidio.** Due preset costruiti: una preferenza su A, poi l'upsert su B. Lo snapshot deve essere quello di B, e il
  flag si deve accendere quando B cambia.

**U2 (B) — Il preset di base salvato non è quello usato: la cascata ha una copia nel BE** · aree B, D · Q2.

* **Fatto.** Il resolver non espone il preset di base. Il BE lo ricalcola con una copia sua della cascata
  (`ui_repository.py:69-145`, `fetch_preset_base_snapshot`, che si dichiara «drift risk»). La copia prende il primo
  preset di default acceso; il DB prende il primo con una colonna o un widget acceso. In più `_GUC_VESTE_EXPR` (`:32`)
  fallisce su una veste fuori dominio, dove `fn_veste_corrente` ripiega su NULL. Quando le due scelte differiscono, il
  banner confronta un preset diverso da quello che l'utente vede.
* **Correzione proposta.** Il resolver espone una chiave additiva `preset_base` (id e data del contenuto), per le liste e
  le dashboard. Il BE salva quella e ritira la copia nello stesso cantiere (regola del 2).
* **Decisione (Q2, Tid, 2026-11-18).** Sì: chiave additiva `preset_base` nei due resolver; il BE ritira la sua copia della cascata nello stesso cantiere.
* **Presidio.** Un preset di ruolo senza colonne accese e uno di sistema: `preset_base` deve essere quello di sistema.

**U3 (B) — La scelta del preset di base guarda il primo preset di ruolo, e non il pool** · aree B, D.

* **Fatto.** Al passo del ruolo, `ORDER BY pa.priorita LIMIT 1` prende il preset del profilo più prioritario. Se quel
  preset non ha colonne accese, la cascata scende all'azienda senza guardare i profili successivi, mentre COMMENT ed
  eccezione ATTIVO dicono «il primo con colonne». Se nessun preset ha colonne, le colonne vengono dal catalogo, ma
  ordinamento, filtri e misura (con la loro `origine`) vengono dall'ultimo preset trovato. Nella dashboard la base
  chiede solo «almeno un widget acceso», non che il widget stia nel pool: un preset fatto di widget fuori dal pool
  vince, e la home mostra solo le card aggiunte, spente.
* **Correzione proposta.** Il filtro «almeno una colonna accesa», e per la dashboard «almeno un widget acceso nel pool»,
  dentro la query di ogni livello, prima del `LIMIT`. Un solo preset di base per la risoluzione, oppure nessuno.
* **Presidio.** Due profili costruiti, il primo con un preset senza colonne accese: deve vincere il secondo. Un preset di
  ruolo della dashboard con widget fuori dal pool: deve vincere quello di sistema.

**U4 (B) — A parità di priorità il preset di ruolo è scelto a caso** · aree B, D.

* **Fatto.** Né i due resolver né la copia del BE (`ui_repository.py:95`) hanno uno spareggio. Con la veste NULL,
  `script.fn_get_profili_accesso_applicabili` può dare due PORTALE di uguale priorità (lo dice il suo commento). Il
  COMMENT del resolver delle dashboard dice «deterministico per priorita».
* **Correzione proposta.** Lo spareggio esplicito, sull'id del preset.
* **Presidio.** Due binding PORTALE costruiti, veste NULL: deve vincere sempre lo stesso preset.

**U5 (B) — Il banner legge il preset salvato anche se è spento o non è più la base** · aree B, D · Q3.

* **Fatto.** Il passo del flag legge `contenuto_aggiornato_il` per `id = preset_base_id`, senza guardare `attivo` né se
  quel preset è ancora la base dell'utente. Un preset spento, o non più base, accende il banner se cambia. Il motivo
  dell'eccezione ATTIVO («ripiegano già sul livello successivo») vale per la cascata, non per il flag.
* **Correzione proposta.** (a) Il flag tace se il preset salvato non è la base di oggi. (b) Un esito suo, «base
  cambiata», che propone il riallineamento. **Raccomandata (b)**, come chiave additiva.
* **Decisione (Q3, Tid, 2026-11-18).** (b): un esito suo, «base cambiata», come chiave additiva.
* **Presidio.** Un preset spento dopo il salvataggio, poi modificato: il flag resta spento, oppure dà l'esito nuovo.

**U6 (B) — Il banner si accende per chiavi che seguono già il preset** · area B · Q4.

* **Fatto.** La cascata è per chiave, ma la data del contenuto è una per tutto il preset. Una preferenza di sola misura
  vede il banner quando cambia l'ordinamento, che le arriva già.
* **Correzione proposta.** (a) Una data del contenuto per chiave (colonne, ordinamento, filtri, misura), e il flag guarda
  solo le chiavi di origine `preferenza`. (b) Resta per preset intero. **Raccomandata (a).**
* **Decisione (Q4, Tid, 2026-11-18).** (a): una data del contenuto per chiave sul preset; il flag guarda solo le chiavi di origine `preferenza`.
* **Presidio.** Una preferenza di sola misura e un cambio di `ordinamento_default`: il flag resta spento.

**U7 (B) — Il preset di un'azienda spenta si applica** · area D (e le liste, stessa forma) · Q5.

* **Fatto.** Il passo dell'azienda confronta `p_emittente_fiscale_id` senza guardare `emittenti_fiscali.attivo`. I
  motivi delle eccezioni ATTIVO dei preset d'azienda dicono che quel preset «non si applica già». Per i profili è vero,
  perché li filtra `fn_get_profili_accesso_applicabili`; per l'azienda no.
* **Correzione proposta.** (a) Il join sull'azienda accesa. (b) Il motivo dell'eccezione corretto. **Raccomandata (a).**
* **Decisione (Q5, Tid, 2026-11-18).** (a): il passo dell'azienda considera solo le aziende accese, nelle due cascate.
* **Presidio.** Il preset di un'azienda spenta: si ripiega sul sistema.

**U8 (C) — La data del contenuto del preset si scrive a mano** · area B.

* **Fatto.** `contenuto_aggiornato_il` si scrive con un INSERT o un UPDATE dell'app senza toccare il contenuto (lo fa
  anche un pgTAP del flag).
* **Correzione proposta.** Un lucchetto: la colonna la scrivono solo i due trigger `trgfn_preset_*`.
* **Presidio.** UPDATE diretto della colonna come app, rifiutato.

**U9 (C) — La lettura del preset è scritta tre volte in ogni resolver** · aree B, D.

* **Fatto.** In ciascuno dei due resolver i tre livelli (ruolo, azienda, sistema) ripetono la stessa sotto-query.
  `fn_get_profili_accesso_applicabili` è chiamata due volte nello stesso resolver delle liste. Il calcolo del flag è
  ripetuto fra liste e dashboard.
* **Correzione proposta.** Si unifica nel giro 1, che riapre comunque le due funzioni: un BB per la scelta del preset di
  base e uno per il flag, letti dai due resolver.

### 3.2 Giro 2 — la forma della preferenza e i widget nuovi

**U10 (A) — Il badge dei widget nuovi conta anche quelli che l'utente non può vedere** · area D.

* **Fatto.** Il passo 3 di `fn_resolve_dashboard_config` conta i widget accesi del pool assenti dalla configurazione,
  prima del filtro per area e azione del passo 4, e non ricalcola dopo. Il gemello delle liste ricalcola dopo il filtro
  (passo 5-bis): le due copie hanno divergito. Verificato sul corpo il 2026-11-18.
* **Correzione proposta.** Il conteggio dopo il filtro, come nelle liste.
* **Presidio.** Un utente senza l'area, un widget di quell'area nel pool e un preset che non lo nomina:
  `widget_nuovi = 0`.

**U11 (B) — Una voce senza codice spegne l'aggiunta di colonne e widget nuovi** · area D.

* **Fatto.** Le colonne o i widget nuovi si cercano con `codice NOT IN (SELECT elem->>'codice' …)`. Se una voce della
  preferenza o del preset non ha codice, l'elenco contiene un NULL, il `NOT IN` non è mai vero e nessun elemento nuovo
  entra più. Vale per tutti e due i resolver.
* **Correzione proposta.** `NOT EXISTS`. La voce senza codice si chiude anche con U12.
* **Presidio.** Una preferenza con una voce senza codice e un elemento nuovo nel catalogo: il nuovo arriva.

**U12 (B) — La forma della preferenza la verifica solo il backend** · aree B, D · Q6.

* **Fatto.** Della `configurazione` il DB verifica solo la misura di pagina delle liste; della dashboard niente. Una riga
  con `ordine` o `larghezza` non interi, o con `widget` che non è un array, fa fallire il resolver con un 22P02 grezzo:
  quella lista, o la home, non si apre più per quell'utente. Una voce senza `visibile` esce con `visibile: null`, e un
  codice ripetuto esce due volte. Oggi la regola vive in `lista_preferenza_service.py:231` e in
  `dashboard_preferenza_service.py:161-253`.
* **Correzione proposta.** (a) Un guard di forma sulle due preferenze, comune (oggetto, chiavi ammesse, voci con codice
  unico e tipi giusti). (b) Un resolver tollerante, che scarta le voci malformate. **Raccomandata (a)**, più i cast
  sicuri nei resolver per le righe scritte prima del guard.
* **Decisione (Q6, Tid, 2026-11-18).** (a): un guard di forma comune alle due preferenze, più i cast sicuri nei resolver per le righe scritte prima del guard; la copia della regola nel BE si ritira.
* **Presidio.** Un `throws_ok` per ogni forma rifiutata; un resolver che non cade su una riga scritta senza il trigger.

**U13 (B) — Ordinamento e filtri passano senza filtro** · area B · Q7.

* **Fatto.** L'ordinamento e i filtri della preferenza o del preset passano così come sono. Possono nominare colonne
  spente, non `ordinabile` o non `filtrabile`, o BLOCCATO per l'utente: un ordinamento su una colonna sensibile resta
  nel JSON.
* **Correzione proposta.** Nel resolver si tolgono le voci di colonne spente, non ammesse o BLOCCATO. Prima va decisa la
  convenzione di `col`, codice o campo sorgente (Q7). Fatto datato, 2026-11-18: su dbdev, dove codice e campo sorgente
  differiscono, i 5 ordinamenti dei preset usano il campo sorgente; il FE ordina per campo sorgente (`sortField` di
  PrimeVue); un test BE (`test_lista_preferenza_service.py:63`) scrive il codice.
* **Decisione (Q7, Tid, 2026-11-18).** `col` è il **codice** della colonna: identità stabile, stessa chiave delle voci
  `colonne`. Le 5 righe del seed che usano il campo sorgente si convertono; il resolver espone in uscita anche il campo
  sorgente, che il FE usa per ordinare; la traduzione all'ingresso la fa il guard di forma (Q6) o il BE (BE20, §6).
* **Presidio.** Un ordinamento su una colonna spenta e uno su una sensibile senza grant: escono tolti.

**U14 (B) — Nessun vincolo lega fra loro preset, colonne, pool e preferenza** · aree B, D · Q8.

* **Fatto.** Quattro legami che il modello non chiede:
  * la riga di `lista_preset_colonna` può citare una colonna di un'altra lista; il resolver riabbina per codice, e con
    un codice uguale prende ordine e larghezza di un'altra colonna;
  * la riga di `dashboard_preset_widget` può proporre un widget fuori dal pool della dashboard (la vecchia pagina lo
    chiamava «vincolo di seed»), e togliere un widget dal pool non tocca i preset che lo propongono;
  * il `preset_base_id` di una preferenza può essere il preset di un'altra lista o di un'altra dashboard;
  * `lista_id`, `ambito`, il profilo e l'azienda della testata di un preset si possono cambiare: lo rifiuta solo il
    servizio.
* **Correzione proposta.** FK composite (l'id con la lista o la dashboard) dove la chiave lo consente, altrimenti un
  guard; un lucchetto di colonna sulla testata del preset; per il pool, il DELETE di un widget citato da un preset
  bloccato, oppure in cascata (Q8).
* **Decisione (Q8, Tid, 2026-11-18).** Il DELETE di un widget dal pool è **bloccato** finché un preset lo propone; il
  messaggio nomina i preset. Stessa regola delle colonne delle liste oggi (FK NO ACTION): Q18 va tenuta coerente.
* **Presidio.** Un INSERT incrociato rifiutato per ciascuno dei quattro legami; l'UPDATE di `lista_id` del preset
  rifiutato.

### 3.3 Giro 3 — le misure

**U15 (A) — `lista_preset.pagina_dimensione` ha `DEFAULT 25`, il COMMENT dice «NULL = il default»** · aree B, C · Q9.

* **Fatto.** Un INSERT che non nomina la colonna scrive 25 fisso, non NULL: il preset non segue più il default `PAGINA`
  del catalogo, e se 25 esce dal catalogo quell'INSERT è rifiutato. È una seconda sede del default. Verificato il
  2026-11-18. Il BE passa la colonna esplicita (`ui_admin_repository.py:622-644`), quindi lo scatto riguarda il seed e
  ogni scrittura futura che non la nomina.
* **Correzione proposta.** `DROP DEFAULT`. Le righe del seed che scrivono 25 o 10 esplicitamente si decidono una per una:
  quelle che intendono «il default» passano a NULL (Q9).
* **Decisione (Q9, Tid, 2026-11-18).** Sì `DROP DEFAULT`. Le righe del seed per gruppo, non una per una (fatto
  datato, dbdev 2026-11-18: 113 preset, 70 a 25, 36 a 10, 3 a 50, 4 NULL):
  * **25 → NULL**: seguono lo standard `PAGINA`;
  * **50 → NULL** anche loro (le liste fornitori, soggetti e «fondi fattura da decidere»): Tid li porta allo standard;
  * **10 → NULL**, con la lista che dichiara l'uso `COMPATTA` (Q11 decisa (a)).
* **Presidio.** Un INSERT senza la colonna: `pagina_dimensione IS NULL`.

**U16 (B) — Una misura citata solo da preferenze si toglie, e poi la preferenza non si aggiorna più** · area C · Q10.

* **Fatto.** La FK verso il catalogo arriva solo dai preset. Una misura citata solo da preferenze si toglie o si
  riscrive senza rifiuto. Il guard della preferenza (`INSERT OR UPDATE OF configurazione`) giudica il valore che resta:
  da quel momento ogni UPDATE della preferenza è rifiutato, anche se tocca solo le colonne. Il resolver, invece, scarta
  la misura e risponde lo standard.
* **Correzione proposta.** (a) Il guard giudica solo un valore nuovo. (b) Il ritiro di una misura dal catalogo toglie la
  chiave dalle preferenze. **Raccomandata (b)**: per il resolver una misura ritirata non è già più una scelta.
* **Decisione (Q10, Tid, 2026-11-18).** (b): il ritiro di una misura dal catalogo toglie la chiave dalle preferenze che la
  citano; il resto della preferenza non si tocca.
* **Presidio.** Una misura di prova, una preferenza che la cita, la misura tolta, poi l'UPDATE delle sole colonne.

**U17 (B) — `misure_pagina.misura` «non si riscrive», ma niente lo impedisce** · area C.

* **Fatto.** Il COMMENT lo dice, ma nessun lucchetto lo impone. Se nessun preset cita la misura, l'UPDATE passa: le
  preferenze che la citano restano orfane, e `uso_default` resta sulla riga, che ora ha il numero nuovo.
* **Correzione proposta.** Un lucchetto di colonna, nel registro dei lucchetti già usato dagli altri cataloghi.
* **Presidio.** L'UPDATE di `misura` è rifiutato.

**U18 (B) — Il catalogo può restare senza un default** · area C.

* **Fatto.** `uq_misure_pagina_uso_default` dice «al più una» riga per uso, non «esattamente una». Togliere il default
  riesce. Da quel momento `fn_get_misure_pagina` solleva `E_UI_MISURA_PAGINA_DEFAULT_MANCANTE`, e il FE si ferma nel
  guard del router a ogni pagina (`router/index.js:766-778`).
* **Correzione proposta.** Un constraint trigger differito: a fine transazione `COMPATTA` e `PAGINA` hanno una riga
  ciascuna.
* **Presidio.** Togliere l'uso `PAGINA` senza spostarlo è rifiutato al commit; spostarlo nella stessa transazione passa.

**U19 (C) — Tre regole per la stessa misura scritta nel JSONB** · area C.

* **Fatto.** Il guard vuole un numero di al più nove cifre. Il resolver delle liste accetta anche la stringa `"25"`, che
  il guard rifiuta. Il resolver della dashboard ha una terza espressione.
* **Correzione proposta.** Un BB `ui` «la misura di un JSONB, o niente», letto dal guard e dai due resolver. Si scrive
  nel giro 2, se il guard di forma di U12 nasce prima.

**U20 (B) — La lista ripiega sempre sul default `PAGINA`** · area C · Q11.

* **Fatto.** Il ripiego del resolver è sempre il default `PAGINA`. Una lista configurabile mostrata compatta (in un
  drawer o in un dialog) non può dire `COMPATTA`: il 10 sta scritto nei preset del seed, e se `COMPATTA` si sposta quei
  preset restano a 10.
* **Correzione proposta.** (a) `lista_definizione` dichiara l'uso (`COMPATTA` o `PAGINA`) e il resolver ripiega su quel
  default. (b) Resta così.
* **Decisione (Q11 e Q11-bis, Tid, 2026-11-18).** (a): `lista_definizione` dichiara l'uso (`COMPATTA` o `PAGINA`,
  iniziale `PAGINA`; le liste di righe segnate `COMPATTA` nel seed) e il resolver ripiega sul default di quell'uso. Con
  Q9, i preset a 10 diventano NULL. Q11-bis: le liste configurabili prendono la misura dal DB; `DEFAULT_LIMIT` del BE
  resta solo per gli endpoint fuori catalogo, dichiarato come regola dell'API (BE10).

**U21 (B) — Il massimo di card della dashboard non ha una sede** · aree C, D · Q12.

* **Fatto.** `dimensione_max` è un tetto («al più N card»), non una scelta del paginatore: non è una seconda sede di
  `misure_pagina`, e la regola del 2 non si applica. Però:
  * sul preset la colonna è nullable, ha `DEFAULT 8` e nessun CHECK: 0 e i negativi passano, e il FE li tratta come
    «nessun tetto» (`useDashboardConfig.js:185`, `DashboardWidgetModal.vue:81`), un significato che il DB non dichiara;
  * nella preferenza la verifica la fa solo il BE (`dashboard_preferenza_service.py:205-220`, un tetto di 100 preso da
    una costante che il suo commento dice di un'altra regola);
  * l'8 sta in quattro sedi: il default della colonna, una costante del resolver, `useDashboardConfig.js:173` e
    `DashboardWidgetModal.vue:37`. Il resolver non risponde mai NULL, quindi i ripieghi del FE non servono.
* **Correzione proposta.** (a) `CHECK (dimensione_max > 0)` sul preset, dove NULL vuol dire lo standard; il guard di forma
  sulla preferenza (U12); l'8 in una sede DB sola. (b) Un catalogo di scelte come `misure_pagina`. **Raccomandata (a).**
  Da decidere anche se il tetto 100 sta nel DB e se «≤0 = nessun tetto» resta (raccomandato: no).
* **Decisione (Q12, Tid, 2026-11-19).** (a): `CHECK (dimensione_max > 0)` sul preset, NULL = lo standard, l'8 in una
  sede DB sola; il tetto 100 sta nel DB (guard di forma, Q6), il tetto vale fra 1 e 100; «≤0 = nessun tetto» non
  esiste. BE e FE ritirano le loro copie dell'8 e del 100 (BE11, FE1).
* **Presidio.** Un preset a 0 è rifiutato; nella preferenza sono rifiutati `"abc"`, 0 e -1.

### 3.4 Giro 4 — il catalogo delle liste

**U22 (B) — Una lista con colonne o preset accesi non si spegne** · area A · Q13.

* **Fatto.** I trigger `trg_lista_definizione_a10_lista_colonna_block_deact_upd` e `…_lista_preset_block_deact_upd`
  rifiutano lo spegnimento di una lista con figli accesi. Per spegnerla si spengono prima tutte le colonne e tutti i
  preset, e alla riaccensione non resta traccia di quali erano accesi. Una lista spenta già non risponde
  (`fn_lista_da_codice`). Fino al giro 0 la guida diceva il contrario («preset, colonne e preferenze sopravvivono»);
  ora descrive il blocco.
* **Correzione proposta.** (a) Le FK `lista_id` di colonne e preset fra le eccezioni ATTIVO: la lista spenta sospende le
  sue parti, come la decisione del 2026-11-08 sulle righe di composizione. (b) Il blocco resta, e la guida lo dice già.
  **Raccomandata (a).**
* **Decisione (Q13, Tid, 2026-11-19).** (a): la lista spenta sospende colonne e preset senza toccarli; le FK `lista_id`
  entrano fra le eccezioni ATTIVO, nella forma della decisione del 2026-11-08. Alla riaccensione tutto torna com'era.
* **Presidio.** Una lista costruita con colonna e preset accesi si spegne (`lives_ok`) e `fn_lista_da_codice` la
  rifiuta; dopo la riaccensione le colonne sono intatte.

**U23 (B) — Le dichiarazioni del seed le può cambiare l'app** · area A · Q14.

* **Fatto.** Il guard «solo il proprietario» copre `multi_emittente` e nient'altro:
  * `perimetro_emittente`: il COMMENT dice «mai da interfaccia», ma l'app ha UPDATE e niente la sorveglia. Portarla a
    `false` apre la schermata senza chiedere l'azienda, cioè lo stesso effetto che il guard impedisce su
    `multi_emittente`;
  * il `codice`, la `vista_sql` e lo `schema_dati` di una lista certificata: rinominarli sposta la certificazione su
    un'altra schermata o un'altra vista (il BE li ammette, `lista_definizione_admin_service.py:76-80`);
  * il `codice` di una colonna, che è la chiave delle preferenze e dei preset (JSONB per codice): il BE lo ammette
    (`ui_admin_repository.py:473-479`).
* **Correzione proposta.** `perimetro_emittente` nello stesso guard di `multi_emittente` (una funzione sola, con l'elenco
  delle colonne); il codice della lista e quello della colonna immutabili; il cambio di vista di una lista certificata
  solo dall'owner. `ricerca_min_caratteri` a scelta di Tid.
* **Decisione (Q14, Tid, 2026-11-19).** Tutte e cinque: `perimetro_emittente` nello stesso guard di `multi_emittente`
  (una funzione sola, con l'elenco delle colonne); il codice della lista immutabile; il codice della colonna
  immutabile; vista e schema dati di una lista certificata solo dall'owner; `ricerca_min_caratteri` resta all'app
  (è una regolazione, non una dichiarazione del codice).
* **Presidio.** Come app, ciascun UPDATE è rifiutato; come owner passa.

**U24 (B) — Un'azione può avere un campo sorgente, e allora entra nella ricerca** · area A.

* **Fatto.** Il COMMENT dice «campo_sorgente NULL per azione», ma il modello lo ammette valorizzato, e
  `valida_campo_sorgente` salta le azioni. Un'azione con un campo inventato e `ricercabile_full` entra in
  `fn_lista_colonne_ricerca_full`, e la ricerca interroga un campo che non c'è.
* **Correzione proposta.** `CHECK (tipo_colonna <> 'azione' OR campo_sorgente IS NULL)`, e il salto nel trigger si ritira.
* **Presidio.** Un'azione con un campo sorgente è rifiutata.

**U25 (B) — Una colonna composta esportabile esce vuota** · area E.

* **Fatto.** Una colonna con `campo_sorgente` NULL, tipo diverso da `azione` ed `esportabile = true` (il default) è
  ammessa. Il BE la esporta come una colonna di celle vuote (`lista_export_service.py:205-212`), mentre il contratto
  dice che le composte non si esportano, come le azioni. Oggi lo tiene solo il seed.
* **Correzione proposta.** Un CHECK gemello di `chk_ui_lista_colonna_azione_non_esportabile`: senza campo sorgente,
  non esportabile.
* **Presidio.** Il CHECK su una colonna composta esportabile.

**U26 (B) — I nomi della lineage passano su qualunque lista** · area A · Q15.

* **Fatto.** `valida_campo_sorgente` accetta, per ogni lista, anche i nomi di `vendite.vw_documento_lineage_sintesi_colonne`.
  Il catalogo non sa quali colonne non stanno nella vista, quindi ricerca, filtri e ordinamento le trattano come
  colonne della vista. Il guard di `ui` dipende da una vista di `vendite`.
* **Correzione proposta.** (a) La lista dichiara che legge la lineage, e i nomi si ammettono solo lì. (b) Un marcatore
  sulla colonna (vista oppure lineage), letto dal guard e da `ricerca_full`. **Raccomandata (b).**
* **Decisione (Q15, Tid, 2026-11-19).** (b): un marcatore sulla colonna (vista oppure lineage), letto dal guard e da
  `ricerca_full`; filtri e ordinamento escludono le colonne lineage. Per rifiutare un nome della lineage su una lista non
  documentale serve il lato lista: prima del giro si cerca se il DB sa già quali liste sono documentali (per esempio
  dalla configurazione delle sorgenti che il BE legge, `config.sorgenti`); se c'è si usa quella, altrimenti la
  dichiarazione (a). La dipendenza del guard di `ui` da una vista di `vendite` si ritira.
* **Presidio.** Un nome della lineage su una lista non documentale è rifiutato.

**U27 (B) — Le colonne non si riverificano quando la vista cambia, né su una lista spenta** · area A · Q16.

* **Fatto.**
  * Né un cambio di `vista_sql` o di `schema_dati`, né una vista che perde colonne riverificano le colonne. Le vede solo
    il pgTAP del catalogo, e sulle sole righe del seed; un cambio fatto dalla pagina tecnica gli sfugge. Il test spiega
    perché la verifica non sta nel trigger della definizione: l'ordine di carico dei CSV.
  * Il gemello della vista salta sulle liste spente, `valida_campo_sorgente` no. Su una lista spenta registrata prima
    della sua vista (un percorso che la guida descrive) non entrano colonne con un campo sorgente.
  * Tutti e due i trigger ammettono viste, viste materializzate e tabelle, ma non le tabelle partizionate, che esistono.
* **Correzione proposta.** (a) Per le scritture che non vengono dall'owner, un controllo immediato al cambio di vista; il
  salto sulle liste spente, con la verifica all'accensione; le partizionate ammesse. Il tutto in un BB «relazione e
  attributo di una lista», letto dai due trigger e dal pgTAP. (b) Solo il presidio pgTAP. **Raccomandata (a).**
* **Decisione (Q16, Tid, 2026-11-19).** (a): controllo immediato al cambio di vista per le scritture dell'app (il seed
  resta al pgTAP); salto sulle liste spente con la verifica all'accensione (coerente con Q13); partizionate ammesse; un
  BB «relazione e attributo di una lista» letto dai due trigger e dal pgTAP.
* **Presidio.** Come app, un cambio di vista che lascia orfana una colonna è rifiutato; su una lista spenta la colonna è
  accolta e rifiutata all'accensione; una lista su una partizionata è accolta.

**U28 (B) — Testi vuoti ammessi su liste, dashboard e widget** · aree A, D.

* **Fatto.** `lista_colonna` ha i CHECK «non vuoto»; `lista_definizione` no (`vista_sql`, `schema_dati`, `codice`,
  `descrizione`, `note`), e nemmeno le testate delle dashboard e il widget (`codice`, `etichetta`,
  `etichetta_i18n_key`, `contatore_key`). Una `vista_sql = ''` su una lista spenta entra, e da lì fa rifiutare ogni
  colonna con un campo sorgente.
* **Correzione proposta.** I CHECK «non vuoto», con una bonifica se il catalogo ne ha.
* **Presidio.** Una stringa vuota per colonna, rifiutata.

**U29 (B) — Con la veste NULL, il permesso di colonna lo decide l'identità più permissiva** · area A · Q17.

* **Fatto.** Se `p_veste` è NULL, in `fn_lista_colonne_livello` concorrono i profili di tutte le identità dell'utente: un
  AD_HOC `TUTTO` dell'identità di portale scavalca un REPARTO `BLOCCATO` dell'operatore. I due chiamanti passano NULL
  quando la variabile di sessione manca o è fuori dominio. Un ripiego pensato per la presentazione fa da permesso di
  riservatezza.
* **Correzione proposta.** (a) Nessun permesso, come senza utente. (b) Per ogni colonna, il livello più restrittivo fra
  le vesti. (c) Resta così. **Raccomandata (b)**: non allarga mai, e la schermata si apre lo stesso.
* **Decisione (Q17, Tid, 2026-11-19).** (b): con la veste NULL, per ogni colonna vale il livello più restrittivo fra le
  vesti dell'utente; il ripiego non allarga mai.
* **Presidio.** Un utente con due identità, la variabile vuota: la colonna resta BLOCCATO.

**U30 (C) — La cancellazione di una colonna in un preset: il commento dice cascata, la FK blocca** · aree A, E · Q18.

* **Fatto.** `fk_lista_preset_colonna_lista_colonna` è NO ACTION: una colonna che sta in un preset non si cancella. Il
  commento del BE (`lista_colonna_admin_service.py:276-279`, `ui_admin_repository.py:509-510`) dice «CASCADE». Il
  controllo preventivo conta solo le preferenze, quindi il caso del preset finisce nel ripiego generico dell'errore
  d'integrità. Il messaggio di `E_UI_COLONNA_IN_USO` cita anche i permessi, che invece vanno a cascata.
* **Correzione proposta.** (a) CASCADE: la riga del preset è di composizione, come il permesso. (b) NO ACTION, con il
  controllo preventivo che conta anche i preset, il commento e il testo corretti. **Raccomandata (a).**
* **Decisione (Q18, Tid, 2026-11-19).** (b): la FK resta NO ACTION, coerente con Q8 (il widget tolto dal pool). Il
  controllo preventivo conta anche i preset; il messaggio di `E_UI_COLONNA_IN_USO` nomina i preset e non i permessi
  (che vanno a cascata); i commenti del BE si correggono. Il gesto ordinario resta lo spegnimento della colonna.

### 3.5 Giro 5 — il catalogo delle dashboard

**U31 (B) — L'app ha la scrittura sulle tabelle che nessun servizio scrive** · area D · Q19.

* **Fatto.** `zeroerp_app` ha DML su `dashboard_definizione`, `dashboard_widget`, `widget`, `dashboard_preset` e
  `dashboard_preset_widget`. Il backend scrive solo `dashboard_preferenza_utente` (verificato: `dashboard_repository.py`
  `:127`, `:164`, `:179`). L'header dei due pgTAP delle dashboard dice «il SELECT-only del ruolo applicativo è corretto»,
  ma il GRANT dice il contrario.
* **Correzione proposta.** Le cinque tabelle nella lista delle tabelle in sola lettura per l'app, come la Q10 di
  `documenti`.
* **Decisione (Q19, Tid, 2026-11-19).** Sì: le cinque tabelle di catalogo in sola lettura per l'app; le preferenze restano
  scrivibili. Una futura pagina admin delle dashboard riapre la scrittura, insieme a sé, sulle sole tabelle che scrive.
* **Presidio.** `throws_ok` 42501 come app.

**U32 (B) — «La home non è mai vuota» non ha presidio** · area D · Q20.

* **Fatto.** Il catalogo dichiara che una dashboard ha sempre una card da mostrare, ma nessun vincolo chiede che il
  pool abbia un widget acceso senza area né azione. Fatto datato (dbdev, 2026-11-18): l'unico widget senza area né
  azione è spento.
* **Correzione proposta.** Un presidio `dbops` («dashboard senza un widget sempre visibile»), non un trigger.
* **Decisione (Q20, Tid, 2026-11-19).** Un presidio `dbops` («dashboard senza un widget sempre visibile»), non un
  trigger: la regola attraversa pool, widget e interruttore, e un trigger bloccherebbe i passaggi intermedi legittimi.
  Nel giro 5, sul seed: accendere o creare il widget senza area né azione, che il presidio altrimenti segnala.

**U33 (C) — Area e azione del widget possono dire due cose** · area D · Q21.

* **Fatto.** `widget.area_id` può essere un'area diversa da quella dell'azione `azione_id`.
* **Correzione proposta.** Se c'è l'azione, l'area è nulla oppure quella dell'azione.
* **Decisione (Q21, Tid, 2026-11-19).** Se c'è l'azione, l'area è nulla oppure quella dell'azione (la versione
  tollerante, non «solo nulla»). Fatto datato, dbdev 2026-11-19: nessuno dei 4 widget ha un'azione.

**U34 (C) — «La dashboard accesa per codice» sta in due posti** · area D.

* **Fatto.** Il passo 0 del resolver e `dashboard_repository.py:66-78`. Le liste hanno il BB `fn_lista_da_codice`.
* **Correzione proposta.** Un BB `ui.fn_dashboard_da_codice`, e il BE lo chiama.

**U35 (C) — `dashboard_preset.emittente_fiscale_id` è `integer`** · area D.

* **Fatto.** `emittenti_fiscali.id` e il gemello `lista_preset.emittente_fiscale_id` sono `bigint`.
* **Correzione proposta.** Allineare il tipo.

**U36 (C) — Le due preferenze non hanno audit** · area D · Q22.

* **Fatto.** `lista_preferenza_utente` e `dashboard_preferenza_utente` non hanno né il trigger d'audit né `user_*`, e
  `data_update` la scrive il BE.
* **Correzione proposta.** Da confermare se è voluto (la preferenza è dell'utente che la scrive). Se sì, lo dice il
  COMMENT; se no, il trigger d'audit.
* **Decisione (Q22, Tid, 2026-11-19).** Voluto: le due preferenze restano senza audit (dato personale, di un solo
  utente, ad alta frequenza) e il COMMENT delle due tabelle lo dichiara. `data_update` la scrive il DB, non il BE: una
  sede sola, come lo snapshot del preset di base (Q1). Ricaduta: il BE smette di scriverla.

### 3.6 Giro 6 — pulizia

| # | Dove | Fatto | Correzione proposta |
| --- | --- | --- | --- |
| U37 | `trgfn_ui_lista_colonna_a10_valida_campo_sorgente` | Testa ancora `= ''`: è un ramo morto (il CHECK vieta il vuoto), e il commento che lo giustifica col seed CSV è stantio | Si toglie alla prima riscrittura (giro 4) |
| U38 | `fn_lista_colonne_ricerca_full`, guard multi-emittente | Un filtro ripete il CHECK del campo sorgente; l'id utente è ancorato a una colonna di un'altra tabella; una variabile utente non numerica dà un 22P02 grezzo. Il guard multi passa un codice d'area diverso dagli altri (`'ui'` e il nome senza schema) | Filtro tolto, ancora propria, il caso della variabile deciso; codici d'area allineati |
| U39 | `fn_lista_da_codice`, BE | Due copie di «lista accesa per codice» nel BE (`ui_repository.py:218-226`, `core/db/lista_catalogo_repository.py:64-70`): il BB rifiuta, e quei lettori vogliono «niente» | Q23, deciso da Tid il 2026-11-19: il BE chiama il BB e intercetta `E_UI_LISTA_NON_TROVATA`; nessun BB nuovo |

**Che cosa si ritira** (riepilogo): `DEFAULT 25` (U15); la copia BE della cascata (U2); le copie dell'8 nel FE (U21);
le due copie BE della lista per codice (U39); il ramo `= ''` (U37); il secondo trigger z90 (U1).

### 3.7 Chiusi senza modifiche (proposti)

| Che cosa | Perché si chiude |
| --- | --- |
| `dashboard_widget` e `dashboard_preset_widget` non hanno la regola «figlio chiede padre acceso» né il blocco dello spegnimento | È voluto: righe di composizione, eccezioni ATTIVO decise il 2026-11-08 |
| Lo spegnimento di un widget, di un'area o di un'azione | Già coperto: un'area o un'azione non si spengono con widget accesi, e il widget chiede area e azione accese |
| L'unicità del preset di default di una dashboard | Garantita da `uq_ui_dashboard_preset_default` |
| Il DELETE di una misura citata da un preset dà il 23503 grezzo | Il catalogo lo scrive solo l'owner, con un changeSet. Q10 (decisa (b), 2026-11-18) riguarda le preferenze, non questo caso |
| `dimensione_max` della dashboard come seconda sede delle misure | Non lo è: è un tetto, non una scelta del paginatore (U21) |
| Un preset di ruolo prevale su un preset di emittente | È l'ordine del resolver e della sua pagina; l'emittente è il ripiego di chi non ha un preset di ruolo. La guida ora lo dice. Chiuso da Tid il 2026-11-19 (Q24-bis) |
| Il super-admin non vede una colonna sensibile senza permesso | Il livello di colonna non ha bypass: una colonna sensibile lo è per tutti. La guida ora lo dichiara |

## 4. I metadati

Nessuno cambia il comportamento: ognuno dice il falso, oppure fa cronaca a chi legge. Si correggono nel giro che apre
l'oggetto, il resto nel giro 6. Il COMMENT si riscrive intero, secondo `linee-guida-sql.md` §5d.

### 4.1 Dicono il falso

| # | Dove | Che cosa |
| --- | --- | --- |
| M1 | COMMENT `lista_preset.pagina_dimensione` | «NULL = il default», con `DEFAULT 25` (U15); porta il nome del brief |
| M2 | COMMENT `misure_pagina` | «sede UNICA per DB, backend e frontend»: il default ha una copia nel preset (U15) e una nel BE (BE10); porta decisioni datate, brief e il percorso del CSV |
| M3 | COMMENT `misure_pagina.misura` | «Non si riscrive»: niente lo impone (U17) |
| M4 | COMMENT `dashboard_preset.dimensione_max` | «mirror di `lista_preset.pagina_dimensione`»: ha un altro significato e nessun controllo; «Seed preset sistema = 8» è cronaca |
| M5 | COMMENT `lista_preferenza_utente.preset_aggiornato_ignored_at` | Confronta con `data_update`: si confronta con `contenuto_aggiornato_il`; porta «DEF-2» |
| M6 | COMMENT `fn_resolve_lista_config` e suo corpo | «il primo con colonne fra ruolo…» (U3); «AD_HOC prio 1 prevale su REPARTO/PORTALE prio 2»: PORTALE è 3 |
| M7 | COMMENT `fn_resolve_dashboard_config` | «deterministico per priorita» (U4) |
| M8 | Motivi delle eccezioni ATTIVO dei preset d'azienda delle dashboard | «non si applica già»: si applica (U7) |
| M9 | COMMENT `lista_definizione.perimetro_emittente` | «Sette liste globali al 18-09»: una fotografia stantia; porta id di changeSet, due brief e «Piano: …» |
| M10 | COMMENT `lista_colonna.campo_sorgente` | «NULL per azione»: nessun vincolo lo impone (U24) |
| M11 | COMMENT dei due trigger di validazione | `valida_campo_sorgente` tace lo schema e la lineage; `valida_vista_sql` tace lo schema e, nel corpo, dice «view o table», mentre ammette anche le viste materializzate |
| M12 | `config.messaggi_errore` | `E_UI_CAMPO_SORGENTE_NON_TROVATO`: tace la lineage, il rimedio contiene una query SQL, il messaggio dice «prima di inserire» e vale anche per l'UPDATE. `E_UI_COLONNA_IN_USO`: cita i permessi, che vanno a cascata (U30) |
| M13 | Pagine `manual/` e header dei due pgTAP delle dashboard | «il SELECT-only del ruolo applicativo è corretto»: l'app ha il DML (U31) |
| M14 | COMMENT `lista_preset.filtri_default` | «Definirlo prima di seedare i preset»: è un promemoria di cantiere |

### 4.2 Senza COMMENT

* Le colonne di quasi tutte le tredici tabelle: in particolare `id`, le FK, `attivo`, l'audit; `lista_preset` e
  `dashboard_preset` quasi per intero; `lista_preset_colonna` tranne `visibile`; `lista_colonna` tranne una manciata.
* Tutti i CHECK, gli UNIQUE, le FK e gli indici dello schema, compresi `uq_ui_lista_preset_default` e
  `uq_misure_pagina_uso_default`.
* Tutti i trigger dello schema, tranne `trg_ui_lista_definizione_a10_guard_multi_emittente_ins_upd`.
* I COMMENT di tabella di `lista_definizione`, `lista_colonna`, `lista_colonna_permesso` sono di una riga, generici e
  senza accenti; quello di `dashboard_definizione` porta «(prima: home)», quello di `dashboard_preferenza_utente` un
  generico «JSONB per resilienza».

### 4.3 Marcatori, nomi di brief, id

* **COMMENT di funzione:** tutte e diciannove portano nomi di brief, date o sigle: «P-2b», «Q1», «§11.5», «D-V1», «DEF-2»,
  «DB-A», «rev 2026-11-08 (brief-db-revisione-dbops…)», «estratta il…», «Richiesta del team BE/FE … §n», id di
  changeSet (`trgfn_ui_lista_preset_guard_pagina_dimensione`: «nasce in 90_end/…»).
* **Corpi:** `fn_resolve_lista_config` (DB-3, DB-4, F.2, DEF-2, DB-A, P-2b, «brief §4-ter», «passo 5-ter», cronaca per
  date); `fn_resolve_dashboard_config` («brief §3c», «§3b», «§4.6», «§3d», DEF-2, date); `valida_campo_sorgente`
  («rev 2026-09-27», «rev 2026-10-11 (… D-B2)»); `valida_vista_sql` («rev 2026-09-27»); `ricerca_full` («2026-09-25:
  …»). Si toccano solo nei giri che riscrivono comunque la funzione: non si apre un `CREATE OR REPLACE` per un commento.
* **Colonne e trigger:** `multi_emittente` («P-2a», brief, «Q1 e §7 punto 3»), `ricerca_min_caratteri` (brief),
  `lista_colonna_permesso.profilo_accesso_id` («PermissionResolver», una classe del BE), `widget.codice` («§3d»), il
  trigger multi («P-2b strato 1», «BE-3»).
* **Eccezioni ATTIVO** delle tabelle di `ui`: «Decisione Tid 2026-11-08, brief-db-revisione-dbops, giro 7-bis blocco c
  (§23.12)».
* **`config.codici_errore`:** `E_UI_LISTA_NON_TROVATA` («messaggi_errore.csv id 427», «trigger B1/B2»),
  `E_UI_PREFERENZA_NON_TROVATA` («DEF-2»), `E_UI_MULTI_EMITTENTE_NON_SCRIVIBILE` («P-4», brief, «ci_apply», e «si
  accende SOLO dal seed»: il guard rifiuta all'app anche lo spegnimento), `E_UI_MISURA_PAGINA_NON_AMMESSA` («il caso del
  28-09», brief), `E_UI_MISURA_PAGINA_DEFAULT_MANCANTE` (percorso del CSV, brief), `E_UI_DASHBOARD_NON_TROVATA` («gemello
  del precedente», senza referente, e residui «·»). Senza note: `E_UI_PRESET_NON_TROVATO`, `E_UI_PRESET_VALIDAZIONE`,
  `E_UI_PREFERENZA_VALIDAZIONE`, `E_UI_VISTA_SQL_NON_TROVATA`, `E_UI_CAMPO_SORGENTE_NON_TROVATO`. Le note finiscono nei
  commenti di `error_policies_generated.py`: si correggono nel CSV, e il BE rigenera (BE18).

## 5. I pgTAP

Si scrivono o si correggono nel giro che apre l'oggetto; il resto nel giro 6.

* **Iterano su ciò che c'è** (verdi per sottrazione su un DB da zero, o rossi senza dichiararlo):
  * `test-fn-resolve-lista-config.sql` test 11 e `test-fn-resolve-dashboard-config.sql` test 10 prendono «dal DB reale»
    un profilo di priorità >1: se non c'è, l'INSERT dà zero righe e l'asserzione passa senza aver provato niente.
    `test-fn-resolve-lista-config.sql` scrive a mano 10, 50 e 100; il suo header dice «non usa
    `fn_pgtap_set_contesto_operatore`», e la chiama;
  * `test-fn-resolve-lista-config-contatore-colonne-nuove-v1.sql`: la prima lista accesa e un campo dal seed, con rami
    `skip` se manca l'utente;
  * `test-fn-resolve-lista-config-cascata-per-chiave-v1.sql:56-65`: tre misure dal catalogo, senza `skip()` se non ci
    sono; `:321-325` aggira lo z90 (U1);
  * `test-fn-resolve-lista-config-preset-aggiornato-v1.sql` caso F: prova lo z90 attraverso un banner che, col preset a
    NULL, è comunque spento;
  * `test-misure-pagina-v1.sql`: la prima lista attiva del seed come fixture, il test 2 tautologico, il test 13 su
    `max(misura)`;
  * `test-lista-colonna-campo-sorgente-in-vista-v1.sql` (test 1-3 sul seed, test 5 con `skip` se manca
    `storico.comuni`), `test-lista-definizione-multi-emittente-v1.sql` (la prima lista non certificata del seed),
    `test-lista-definizione-perimetro-emittente-v1.sql` test 2-4, `test-fn-lista-colonne-ricerca-full-v1.sql`
    fixture 2.
* **Casi non costruiti:** il preset di emittente nella cascata; il secondo profilo di ruolo; lo spareggio; lo z90 delle
  dashboard (nessun test) e lo z90 col cambio di preset e lo snapshot insieme; il preset di base spento; la preferenza
  malformata; ordinamento e filtri su colonne spente o bloccate; i legami incrociati di U14; la data del contenuto
  scritta a mano; `widget_nuovi` dopo il filtro; il filtro per azione e il widget visibile col permesso; la dashboard
  spenta; la misura uscita dal catalogo; l'UPDATE di `misura`; il catalogo senza default; i valori non validi di
  `dimensione_max`; `fn_lista_colonne_livello` chiamata direttamente (REPARTO, veste NULL con due identità);
  `fn_lista_da_codice` col codice NULL; la cascata dei permessi alla cancellazione della colonna; i CHECK
  `azione_non_esportabile` e `priorita_non_negativa`; lo spegnimento della lista con figli accesi; la FK NO ACTION della
  composizione; il salto di `valida_vista_sql` sulle liste spente, il cambio del solo `schema_dati`, i relkind `m` e
  `r`.
* **Header con id di changeSet e nomi di brief:** `test-fn-resolve-lista-config.sql`, `…-cascata-per-chiave-v1`,
  `…-contatore-colonne-nuove-v1`, `…-preset-aggiornato-v1`, `test-fn-resolve-dashboard-config.sql` (con un motivo del
  runner falso, M13), `test-fn-resolve-dashboard-config-cascata-per-chiave-v1.sql`, `test-ui-nell-ambito-v1`,
  `test-liste-preset-default-v1`, `test-misure-pagina-v1`, `test-lista-colonna-campo-sorgente-in-vista-v1`,
  `test-lista-definizione-multi-emittente-v1`, `test-lista-definizione-perimetro-emittente-v1`,
  `test-lista-ricerca-min-caratteri-v1`, `test-fn-lista-colonne-ricerca-full-v1`, `test-lista-colonna-testi-non-vuoti-v1`.

## 6. Ricadute su BE e FE

Da passare al team quando il giro DB corrispondente è applicato, salvo quelle «subito». ⛔ Questa sessione non tocca
`backend/` né `frontend/`.

| # | Giro | Che cosa |
| --- | --- | --- |
| BE1 | subito | `backend/apps/ui/services/lista_preset_admin_service.py:254-257`: il commento dice che dopo la cancellazione di un preset si lavora «sul catalogo grezzo»; vale il preset di base di oggi |
| BE2 | subito | `backend/apps/ui/db/dashboard_repository.py:13-15`: il commento cita `fn_resolve_livello_area` e `fn_check_azione_processo`, il resolver usa `fn_get_user_permissions_map` e `fn_get_user_actions_map`. `:38-41` e `services/dashboard_service.py:56-57`: il «Risultato» non elenca `dimensione_max_standard` e `origine` |
| BE3 | subito | `ui_admin_repository.py:733` (`replace_preset_colonne`): la composizione si salva con DELETE di tutte le righe più INSERT, quindi anche un salvataggio identico sposta la data del contenuto e accende il banner a tutti. Va fatto il diff |
| BE4 | subito | U30, Q18 decisa (b) il 2026-11-19: il controllo preventivo della cancellazione di una colonna conta anche i preset (`ui_admin_repository.py:528-543`); il commento «CASCADE» (`lista_colonna_admin_service.py:26`, `:276-279`; `ui_admin_repository.py:509-510`) si corregge |
| BE5 | 1 | U2: `fetch_preset_base_snapshot` (`ui_repository.py:32-35`, `:64-145`) si ritira; `lista_preferenza_service.py:91-98` e `dashboard_preferenza_service.py:94-100` leggono `preset_base` dalla risoluzione |
| BE6 | 1 | U1, Q1 decisa (b): l'upsert (`ui_repository.py:346`, `dashboard_repository.py:138`) non scrive più lo snapshot |
| BE7 | 1 | U5, Q3 decisa (b): il banner con l'esito «base cambiata»: servizio, FE e i18n |
| BE8 | 2 | U12: `lista_preferenza_service.py:188-231` e `dashboard_preferenza_service.py:161-253`: con Q6 la regola di forma sta nel guard DB, e la copia del BE si ritira nello stesso cantiere (regola del 2); il codice del guard nuovo va in policy e fallback |
| BE9 | 2 | U13: il FE non ripulisce più ordinamento e filtri da sé; va verificato chi applica oggi l'ordinamento risolto alle API di lista |
| BE10 | 3 | `backend/apps/core/api/constants.py:16-19`: `DEFAULT_LIMIT = 25` ricopia il default `PAGINA`, e il suo commento cita una costante del FE ritirata. Q11-bis, deciso da Tid il 2026-11-18: le liste configurabili prendono la misura dal DB; la costante resta solo per gli endpoint fuori catalogo, dichiarata come regola dell'API, e il commento sulla costante FE ritirata si toglie |
| BE11 | 3 | U21: `dashboard_preferenza_service.py:205-220`, il tetto 100 preso da `_MAX_WIDGET_PAYLOAD`: Q12 decisa: il tetto 100 sta nel DB (guard di forma), il BE ritira `_MAX_WIDGET_PAYLOAD` per questa regola |
| FE1 | 3 | U21: `useDashboardConfig.js:173` (`?? 8`) e `DashboardWidgetModal.vue:37` si tolgono; il ramo `max > 0` (`useDashboardConfig.js:185`, `DashboardWidgetModal.vue:81`) si toglie: «≤0 = nessun tetto» non esiste (Q12). Minore: il terzo ripiego di `ListaConfigurabile.vue:566-569` |
| BE12 | 4 | U23: `codice` esce da `UPDATE_KEYS` (`lista_definizione_admin_service.py:76-80`; `ui_admin_repository.py:246-248`) e da `_COLONNA_UPDATE_COLS` (`ui_admin_repository.py:473-479`; `lista_colonna_admin_service.py:96`); il codice d'errore nuovo si mappa |
| BE13 | 4 | U24, U25: i CHECK nuovi in `_CHECK_CONSTRAINTS` (`lista_colonna_admin_service.py:127`); nel drawer delle colonne (`ListaColonnaDrawer.vue`, vicino a `:155-160` e `:345`) «Esportabile» spento quando manca il campo sorgente, come già per le azioni; `lista_export_service.py:205-221` |
| BE14 | 4 | U26: `backend/apps/core/db/_helpers.py:315-330`, la ricerca libera riceve anche i campi della lineage: con Q15 (b) si escludono le colonne marcate lineage |
| BE15 | 4 | U22, Q13 decisa (a): il toggle «attivo» di una definizione con figli accesi smette di fallire; il ramo che intercetta `E_ATTIVO_BLOCK_CHILDREN_ACTIVE` per le liste si ritira |
| BE16 | 4 | Facoltativo: il campo emittente del drawer dei preset è un `InputNumber` con l'id grezzo (`ListaPresetDrawer.vue:252-261`), non una combo |
| BE17 | 5 | U34: `get_dashboard_id` (`dashboard_repository.py:66-78`) chiama il BB |
| BE18 | 6 | `error_policies_generated.py` da rigenerare dopo la pulizia delle note (§4.3): oggi le righe di `E_UI_*` (fra cui `:1979`, `:1994-1997`) portano brief, date, «il caso del 28-09». U39: `get_lista_id` e `fetch_flag_perimetro` passano dal BB |
| BE19 | — | U31 e U23 (`perimetro_emittente`): verificato che il BE non scrive quelle tabelle né quella colonna. Niente da fare, salvo il fallback del codice nuovo |
| BE20 | 2 | Q7: `col` di ordinamento e filtri è il codice della colonna. Il FE ordina per campo sorgente (`sortField` di PrimeVue, `ListaConfigurabile.vue:619-668`): il salvataggio della preferenza e del preset traduce il campo in codice, se non lo fa il guard di forma (Q6); in lettura il resolver dà anche il campo sorgente. Il test `test_lista_preferenza_service.py:63` già scrive il codice |
| BE21 | 5 | Q22: `data_update` delle due preferenze la scrive il DB; l'upsert del BE (`ui_repository.py`, `dashboard_repository.py:127-179`) smette di passarla |
| BE22 | 1 | Q26: `is_default` esce dai preset di liste e dashboard. Il BE lo toglie da `_schema_ui.py:31`, `ui_admin_repository.py:56`, `:621-658`, dal drawer dei preset e dai messaggi dell'UNIQUE; la copia della cascata in `ui_repository.py:93-132` si ritira già con Q2 |

## 7. Le decisioni di Tid

| # | Domanda | Raccomandazione |
| --- | --- | --- |
| Q1 | U1: chi scrive lo snapshot del preset di base | ✅ **Deciso da Tid il 2026-11-18: (b) il DB**, letto dal preset, insieme a U2; una funzione z90 sola |
| Q2 | U2: il preset di base esposto dal resolver | ✅ **Deciso da Tid il 2026-11-18: sì.** **Chiave additiva `preset_base`** per liste e dashboard, la copia BE ritirata |
| Q3 | U5: la base salvata è spenta o non è più quella di oggi | ✅ **Deciso da Tid il 2026-11-18:** **(b) un esito «base cambiata»**, chiave additiva |
| Q4 | U6: il banner per chiave | ✅ **Deciso da Tid il 2026-11-18:** **(a) una data del contenuto per chiave** sul preset |
| Q5 | U7: il preset di un'azienda spenta | ✅ **Deciso da Tid il 2026-11-18:** **(a) il filtro** sull'azienda accesa |
| Q6 | U12: la forma della preferenza | ✅ **Deciso da Tid il 2026-11-18:** **(a) un guard DB comune** a liste e dashboard, più i cast sicuri |
| Q7 | U13: la convenzione di `col` (codice o campo sorgente), prima di filtrare l'ordinamento nel DB | ✅ **Deciso da Tid il 2026-11-18: il codice** della colonna (l'identità, la stessa chiave delle voci `colonne`); il resolver aggiunge il campo sorgente in uscita per il FE |
| Q8 | U14: un widget tolto dal pool, se un preset lo propone | ✅ **Deciso da Tid il 2026-11-18: bloccato**: si toglie prima dal preset |
| Q9 | U15: `DROP DEFAULT 25`, e le righe del seed che scrivono 25 o 10 | ✅ **Deciso da Tid il 2026-11-18: sì `DROP DEFAULT`**; i 25 e i 50 diventano NULL (seguono `PAGINA`); i 10 diventano NULL con l'uso `COMPATTA` dichiarato dalla lista se Q11 è (a), altrimenti restano 10 |
| Q10 | U16: la misura ritirata e le preferenze | ✅ **Deciso da Tid il 2026-11-18:** **(b) il ritiro toglie la chiave** dalle preferenze |
| Q11 | U20: la lista dichiara l'uso della misura (`COMPATTA` o `PAGINA`) | ✅ **Deciso da Tid il 2026-11-18: (a) sì, e sì a Q11-bis.** **(a) sì**, se ci sono liste configurabili mostrate in drawer o dialog. **Q11-bis** (BE10): `DEFAULT_LIMIT` del BE lo legge dal catalogo |
| Q12 | U21: il tetto della dashboard | ✅ **Deciso da Tid il 2026-11-19: (a), il tetto 100 nel DB, «≤0 = nessun tetto» no.** **(a) `CHECK > 0`**, NULL = lo standard, l'8 in una sede DB; il tetto 100 e «≤0 = nessun tetto» da decidere (raccomandato: no) |
| Q13 | U22: spegnere una lista sospende colonne e preset | ✅ **Deciso da Tid il 2026-11-19:** **(a) sì**, eccezioni ATTIVO (forma della decisione del 2026-11-08) |
| Q14 | U23: che cosa del seed scrive solo l'owner | ✅ **Deciso da Tid il 2026-11-19, tutte e cinque come raccomandato:** `perimetro_emittente` nel guard; codici di lista e di colonna immutabili; la vista di una lista certificata solo dall'owner; `ricerca_min_caratteri` resta all'app |
| Q15 | U26: la sede dei nomi della lineage | ✅ **Deciso da Tid il 2026-11-19: (b)**, più il lato lista da una sede esistente o, se manca, da (a). **(b) un marcatore sulla colonna** |
| Q16 | U27: riverificare le colonne | ✅ **Deciso da Tid il 2026-11-19:** **(a)**: controllo immediato per l'app, salto sulle liste spente con verifica all'accensione, le partizionate, un BB |
| Q17 | U29: i permessi di colonna con la veste NULL | ✅ **Deciso da Tid il 2026-11-19:** **(b) il livello più restrittivo** fra le vesti |
| Q18 | U30: la composizione del preset alla cancellazione della colonna | ✅ **Deciso da Tid il 2026-11-19: (b) bloccato** (NO ACTION), coerente con Q8; controllo preventivo che conta anche i preset, messaggio e commenti veri. La raccomandazione iniziale era (a) CASCADE |
| Q19 | U31: le cinque tabelle di catalogo delle dashboard in sola lettura per l'app | ✅ **Deciso da Tid il 2026-11-19: sì** |
| Q20 | U32: «la home non è mai vuota» | ✅ **Deciso da Tid il 2026-11-19: un presidio `dbops`**, non un trigger |
| Q21 | U33: area e azione del widget | ✅ **Deciso da Tid il 2026-11-19:** se c'è l'azione, l'area è nulla oppure quella dell'azione |
| Q22 | U36: le preferenze senza audit | ✅ **Deciso da Tid il 2026-11-19: voluto.** Il COMMENT lo dice; `data_update` la scrive il DB, non il BE |
| Q23 | U39: «lista accesa per codice» per chi vuole «niente» | ✅ **Deciso da Tid il 2026-11-19:** **il BE chiama il BB** e intercetta il codice, nessun BB nuovo |
| Q24 | L'ordine dei giri (§2) | ✅ **Deciso da Tid il 2026-11-19: come in §2, e Q24-bis: il ruolo resta prima dell'emittente.** Come in §2. **Q24-bis:** il preset di ruolo che prevale sull'emittente resta (§3.7) |
| Q25 | Una guida delle dashboard: oggi non c'è (§9) | ✅ **Deciso da Tid il 2026-11-19: (a), scritta a fine giro 5.** **Una guida `configurazione-dashboard`** sua, che rimanda alla guida delle liste per il meccanismo comune |
| Q26 | `dashboard_preset.is_default = false`: uno stato senza lettori | ✅ **Deciso da Tid il 2026-11-20: `is_default` si ritira, su liste e dashboard.** Un preset per posto, vale se acceso; la bozza si prepara spenta. Il gemello delle liste è uguale (trovato il 2026-11-19). I preset alternativi, se verranno, nascono nel brief delle viste nominate. Nel giro si riallinea la guida `configurazione-liste` (§2.3 e il passo 5 di §10), che oggi descrive `is_default` |

## 8. Giro 0 — la documentazione, 2026-11-18 (fatto)

L'ha scritto la sessione DB su richiesta di Tid, con quattro agenti per l'area dello schema (A catalogo delle liste, B
preset e risoluzione, C misure, D dashboard) e uno per la guida (E). Le pagine sono lette dai corpi
(`pg_get_functiondef`, `pg_get_triggerdef`), da `pg_constraint`, dai COMMENT e dai GRANT di dbdev, dalle schede
auto-generate e dai pgTAP. Descrivono il comportamento di oggi, difetti compresi. Ogni difetto sta al presente in una
sezione «⚠️ Che cosa oggi non copre», che si toglie quando il giro che lo corregge è applicato. I difetti di classe A (U1,
U10, U15) sono verificati sul catalogo anche dalla sessione che coordina.

### 8.1 Che cosa è scritto

* **Le 32 pagine `docs/it/dbzero/ui/manual/`.** Le 28 esistenti sono riscritte nella cornice: nove erano nel formato
  vecchio (titolo `#`, più `##`, firma e DDL in blocchi `sql`) e sono rifatte da capo; 24 non avevano la firma. Le
  quattro nuove: `trgfn_preset_contenuto_aggiornato`, `trgfn_preset_riga_tocca_preset` (descritte per le due famiglie,
  liste e dashboard), `trgfn_ui_lista_preset_guard_pagina_dimensione`,
  `trgfn_ui_lista_preferenza_utente_guard_pagina_dimensione`.
* **`guide/configurazione-liste.md`**, riallineata al codice (§8.2).
* **`mappa-concentrica.md`:** il link alla §12 della guida, che aveva cambiato titolo. La data del documento non è
  toccata: dice a quando valgono le sue misure, e il link non è una misura.
* **Nessun blocco comune.** Le tre famiglie hanno regole diverse.

### 8.2 Le parti stantie e false tolte

* **Comuni a tutte le pagine:** «(scritta il 30-09-2026)» e «(latest review 18-08-26)» come primo paragrafo, che
  finivano nell'indice; Vedi anche senza `>` o con etichette in grassetto; firme, parametri, tabelle di colonne e di
  ritorno, DDL ed esempi; DEF-n, «brief §n», id di changeSet nel corpo.
* **Di contenuto, nelle pagine:**
  * lo z90 delle liste «azzera solo quando diventa NULL»: scatta a ogni cambio e azzera due campi; lo z90 delle dashboard
    «a differenza di quello delle liste…»: i due corpi sono identici;
  * il preset di base «il primo con colonne, di ruolo…»: per il ruolo conta solo il primo (U3); «AD_HOC prio 1 prevale
    su REPARTO/PORTALE prio 2»: PORTALE è 3;
  * «unico default per combinazione»: conta anche i preset spenti; «la preferenza si legge sempre completa in una
    query»; «la lettura passa sempre dalla funzione» (il BE legge la tabella); «una preferenza senza chiavi si cancella»
    (lo fa il BE, il DB la ammette);
  * «vincolo di seed» per i widget del preset fuori dal pool: è un buco senza presidio (U14);
  * il guard multi-emittente «impedisce che venga acceso»: rifiuta all'app ogni cambio; `valida_vista_sql` «solo UPDATE
    OF vista_sql, attivo» e «nome grezzo come relname»: parte anche su `schema_dati` e cerca nello schema della lista;
  * `misure_pagina`: «sede unica per DB, BE e FE», falso (U15, BE10); la tabella «oggi 10/25/50/100», una fotografia;
    la ricetta per spostare un default in due passaggi, che fra l'uno e l'altro lascia il catalogo senza default; «una
    misura non si toglie finché un preset la usa», che taceva le preferenze;
  * il CHECK dell'azione «impone il sorgente NULL»: impone solo che l'azione non si esporti.
* **Di contenuto, nella guida:**
  * la cascata: l'emittente era prima del ruolo, ed era descritta come «intera preferenza»: è per chiave; il catalogo
    grezzo prende tutte le colonne accese, non solo le `informazione`;
  * `LETTURA` «visibile ma non personalizzabile»: è visibile e non esportabile;
  * lo spegnimento della lista come un gesto unico (U22); la cancellazione di una colonna «a cascata» sui preset (U30);
  * «i permessi sono sempre restrittivi»: vince il profilo più specifico, e su una colonna sensibile il permesso apre;
  * il banner del preset aggiornato e l'export «in roadmap»: esistono; l'export «nell'ordine di `ordine_default`»: è
    nell'ordine dell'utente, senza le colonne nascoste né quelle in LETTURA;
  * la modale «permette di fissare le colonne»: non lo permette;
  * il bollino multi-emittente «oggi spento su tutte le liste»: è acceso su più liste;
  * la §12 «Roadmap» con DEF-n e un link a `work-in-progress/`: diventa «Che cosa le liste oggi non fanno», cinque
    limiti al presente; le funzionalità chiuse entrano nella sezione del loro tema; le due spiegazioni ripetute (lista
    in sviluppo, fallback i18n) diventano una;
  * aggiunte le misure di pagina (§2.6), che la guida non descriveva.

### 8.3 Le verifiche

* Su tutte le 32 pagine passano i sei controlli di `standard-guide.md` §«Verifica di una pagina `manual/`», rilanciati
  dalla sessione che coordina il 2026-11-18. In più: nessun link `/dbzero/…` o `/guide/…` morto, e la data è il 18
  novembre 2026 ovunque. L'unico blocco di codice è un `mermaid` in `fn_resolve_lista_config`.
* La guida passa la checklist di `standard-guide.md`; l'unico anchor esterno cambiato è quello corretto nella mappa
  concentrica.
* **La doc auto-generata non è rigenerata** (passo 3): le schede delle quattro funzioni con la pagina nuova non la
  includono ancora, e `ui/index.md` porta ancora «(scritta il 30-09-2026)» come descrizione delle misure.
* La build della doc non è lanciata.

## 9. Fuori perimetro — segnalazione per Tid

**Le dashboard non hanno una guida.** In `docs/it/guide/` nessuna guida descrive le dashboard di `ui` (catalogo dei
widget, pool, preset, contatori, permessi per area e azione): `configurazione-liste` parla solo delle liste, e
`cruscotti-fatturazione` parla d'altro. Oggi il significato sta solo nelle otto pagine `manual/`. Deciso da Tid il
2026-11-19 (Q25): una guida sua, `configurazione-dashboard`, che rimanda a `configurazione-liste` per il meccanismo
comune (cascata, preset di base, banner) senza ricopiarlo. Si scrive **a fine giro 5**, quando la home ha preso la
forma corretta. La domanda «le dashboard
seguono la stessa strada delle liste?» è aperta anche in
[sviluppo-personalizzazioni-liste_def](sviluppo-personalizzazioni-liste_def.md).

## 10. Alla chiusura

* Ogni pagina `manual/` toccata passa la verifica di `standard-guide.md` con la data aggiornata, e perde la riga di «⚠️
  Che cosa oggi non copre» del difetto chiuso.
* I pgTAP nuovi costruiscono i propri soggetti: nessuno itera su ciò che c'è.
* Il brief va in `work-done/` quando i giri sono applicati e le ricadute BE/FE chiuse o passate a un brief BE.
