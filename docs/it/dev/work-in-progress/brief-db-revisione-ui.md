# Brief DB — Revisione dello schema `ui`: la documentazione, i difetti di codice, i metadati

## ⏭️ Chi riparte — aggiornato al 2026-11-21

**Riparte: il team BE/FE**, con le ricadute del giro 1b (la parte 1b di BE7 e BE25, §6; al 2026-11-21 `dev/backend-tid` non le porta ancora) e con R-BE2 insieme alla verifica di BE9 (§3.2-bis, §6), che vengono prima della scrittura del giro 2. **Poi Tid**: Q40-Q42 (§7.1) e il via al giro 2, il cui piano è scritto (§3.2-bis, 2026-11-21). Il residuo di BE22 è chiuso nel CSV (id 665 spento, 2026-11-21), da migrare. Il giro 1b (`20261120-02` … `-11`, §3.1-ter) è applicato su dbdev con i pgTAP verdi (Tid, 2026-11-20), dopo il `/verifica-db` dello stesso giorno (quattro correzioni di testo, nessuna al codice: §3.1-ter, «La verifica»); committato (`986baa5d8d`, PR #172) con la doc auto-generata rigenerata. Alla sessione DB resta il `/verifica-db` del giro 1a, da fare. Il giro 2 parte col via di Tid. Le ricadute del giro 1a (BE5-BE7, BE22-BE24, §6) sono fatte e verdi. Il giro 1a (`20261119-09` … `-14`, §3.1-bis) è applicato su dbdev con i pgTAP verdi (Tid, 2026-11-20). Le tabelle di `ui` sono iscritte al seed di primo impianto (Q27, nel
[brief del seed](../work-done/brief-db-seed-primo-impianto-non-si-riscrive.md) §16.15, changeSet `20261119-01` … `-05`, applicati su
dbdev con i pgTAP verdi il 2026-11-20): i giri che toccano i CSV di `ui` sono sbloccati. Le decisioni Q1-Q36 sono prese
(2026-11-18 … 2026-11-20); Q27-Q36, dall'analisi critica del 2026-11-20, completano o sostituiscono alcune delle prime, e
le scelte superate sono barrate (§7, §7.1 e le schede). Il giro 0 è fatto e committato (`de25065c21`): le 32 pagine
`manual/` allo standard (28 riscritte, 4 nuove), la guida `configurazione-liste` riallineata al codice, il censimento
(§3-§6).

| # | Chi | Che cosa | Dove | Aspetta |
| --- | --- | --- | --- | --- |
| 1 | ✅ sessione DB | Giro 0: 32 pagine `ui/manual/` allo standard, guida `configurazione-liste` riallineata, link della mappa concentrica | §8 | — |
| 2 | ✅ sessione DB | Censimento in sola lettura: difetti, metadati, pgTAP, ricadute BE/FE | §3-§6 | — |
| 3 | ✅ Tid | Doc auto-generata rigenerata (dopo l'1a e dopo l'1b, nel commit `986baa5d8d`) | §8.3 | 1 |
| 4 | ✅ Tid | Le decisioni Q1-Q26 e l'ordine dei giri, prese dal 2026-11-18 al 2026-11-20 | §2, §7 | 2 |
| 4-bis | ✅ Tid | Le decisioni Q27-Q36, prese il 2026-11-20 come raccomandate | §7.1 | 4 |
| 4-ter | sessione DB | Q27: le tabelle di `ui` nel censimento del brief del seed. ✅ Censimento e QU1-QU5 decise; ✅ il giro che le iscrive (`20261119-01` … `-05`) applicato su dbdev, pgTAP verdi (Tid, 2026-11-20) | brief del seed, §16.15 | 4-bis |
| 5 | team BE | Le ricadute «subito» (BE1, BE2, BE4), che non aspettano il DB; e la verifica di BE9 prima del giro 2 (Q35) | §6 | — |
| 6 | ✅ Tid | Il via al giro 1a (2026-11-20) | §2 | 4-ter |
| 6-bis | ✅ Tid | Q37-Q39 decise come raccomandate e il via all'1b (2026-11-20) | §3.1-ter, §7.1 | — |
| 7 | sessione DB | I giri 1a, 1b, 2-6, uno per volta, ciascuno con apply e pgTAP di Tid. ✅ 1a applicato, pgTAP verdi (2026-11-20); ✅ 1b (`20261120-02` … `-11`, §3.1-ter) verificato, applicato, pgTAP verdi (2026-11-20), committato con la doc auto-generata; ✅ il residuo di BE22 (id 665 spento nel CSV, 2026-11-21; ⏳ il migrate); ⏳ il `/verifica-db` dell'1a; ✅ il piano del giro 2 (§3.2-bis, 2026-11-21); ⏳ R-BE2 e BE9 (team BE), Q40-Q42 e il via al giro 2 (Tid) | §2 | 6-bis |
| 8 | team BE/FE | Le ricadute di ogni giro, dopo il suo apply. Giro 1a: ✅ BE5, BE6, BE7 (parte 1a), BE22, BE23, BE24 fatti e verdi (2026-11-20, esito in §6); ⏳ il commit di Tid. Giro 1b: ⏳ BE7 (parte 1b) e BE25, da ora | §6 | 7 |
| 9 | sessione DB | Archiviazione in `work-done/` | §10 | 7, 8 |

**Decisioni di Tid:** Q1-Q11 prese il 2026-11-18, Q12-Q25 il 2026-11-19, Q26 il 2026-11-20 (registrate in §7 e nelle
schede dei difetti), Q27-Q36 il 2026-11-20 (§7.1). Q37-Q39 il 2026-11-20 come raccomandate (§7.1). **Aperte: Q40-Q42** (§7.1, dal piano del giro 2, 2026-11-21). **Da committare:** la riga 665 di `lista_colonna.csv`, il
piano del giro 2, le decisioni aperte e questa testata (2026-11-21). Il giro 1b è nel commit `986baa5d8d`, il giro 1a in
quello che lo porta, l'analisi critica e le decisioni del 2026-11-20 col giro 3 del brief del seed, il giro 0 in `de25065c21`.

> **Chi scrive:** sessione DB (`dev/db-tid`), 2026-11-18; decisioni registrate fino al 2026-11-20. **A chi:** Tid e team DB.
> **Origine:** revisione della documentazione dello schema `ui` chiesta da Tid: allinearla allo standard e alle
> funzionalità, togliere le parti stantie, segnalare dove il codice non rispetta ciò che è scritto. Metodo dei brief di
> revisione di `catalogo`, `dbops` e `documenti`
> ([brief-db-revisione-documenti](../work-done/brief-db-revisione-documenti.md)).
> **Brief vicini verificati:** [sviluppo-personalizzazioni-liste_def](sviluppo-personalizzazioni-liste_def.md) tiene
> gli sviluppi non fatti delle liste (viste nominate, condivisione) e la domanda sulle dashboard: sono funzionalità
> nuove, non revisione, e qui non si toccano. [piano-be-fe-endpoint-senza-porta](piano-be-fe-endpoint-senza-porta.md)
> cita una lista di `ui` solo come fatto. Nel [registro dei residui](registro-residui-aperti.md) nessuna voce ha per
> oggetto le tabelle o le funzioni di `ui`. ⚠️ Mancava, trovato il 2026-11-20:
> [brief-db-seed-primo-impianto-non-si-riscrive](../work-done/brief-db-seed-primo-impianto-non-si-riscrive.md). Le tabelle di catalogo
> di `ui` sono mirror `runOnChange` (`loadUpdateData`) che l'app scrive dalle pagine admin: il suo caso esatto, e il
> suo §7 rimanda il censimento di queste tabelle al suo giro 1. Deciso da Tid il 2026-11-20 (Q27): le tabelle si
> dichiarano nel censimento di quel brief, e i giri di qui che toccano i CSV di `ui` partono dopo.

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

## 2. Il piano: i giri

Deciso da Tid il 2026-11-19 (Q24): i giri nell'ordine della tabella; il giro 1 diviso in 1a e 1b il 2026-11-20 (Q36).
Ogni giro che tocca un CSV di `ui` parte dopo il censimento del brief del seed (Q27). L'ordine è per gravità. I lavori sugli stessi oggetti vanno insieme, perché ogni tabella si apra una
volta sola, e liste e dashboard si correggono nello stesso giro: dove sono gemelle, una copia corretta da sola
diverge dall'altra. Ogni giro comprende changeSet, pgTAP che costruiscono i propri soggetti, COMMENT e pagine `manual/`
riallineati (la riga di «⚠️ Che cosa oggi non copre» del difetto chiuso si toglie); poi l'apply di Tid e il via al giro
dopo.

| Giro | Classe | Contenuto | Ricadute BE/FE | Perché insieme |
| --- | --- | --- | --- | --- |
| 1a | A + B + C | **Il preset di base.** U1 (lo snapshot scritto dal DB), U2, U3, U4 con Q28, U5, U7, U9; il ritiro di `is_default` (Q26) con l'UNIQUE di Q30 | BE5, BE6, BE22 | I due resolver e i due trigger z90: la scelta del preset di base |
| 1b | B + C | **Il banner per chiave.** U6 con la forma di Q29, U8, Q33 col mezzo di Q37, Q38, Q39 (§3.1-ter) | BE7, BE25 | `trgfn_preset_*`, lo snapshot e l'ignorato per chiave, il flag del preset aggiornato |
| 2 | A + B + C | **La forma della preferenza e i widget nuovi.** U10-U14; U19 (il BB della misura, letto dal guard di forma); il tetto 1-100 di `dimensione_max` nella preferenza (U21, parte del guard di forma) | BE8, BE9, BE11, BE20 | Il guard di forma comune a liste e dashboard, il conteggio dei nuovi, ordinamento e filtri, i legami fra preset, colonne e pool |
| 3 | A + B | **Le misure.** U15-U18, U20; U21 sul preset (CHECK, l'8 in una sede) | BE10, FE1 | `misure_pagina`, i guard di `pagina_dimensione`, `dimensione_max` della dashboard |
| 4 | B + C | **Il catalogo delle liste.** U22-U30 (U22 con Q35, U27 con il presidio di Q32); U37 (si riscrive `valida_campo_sorgente`) | BE12-BE15 | `lista_definizione`, `lista_colonna`, i loro trigger e i permessi di colonna |
| 5 | B + C | **Il catalogo delle dashboard.** U31-U36 (U32 col constraint trigger differito di Q31); in chiusura la guida `configurazione-dashboard` (Q25) | BE17 | Le cinque tabelle che l'app non scrive, il widget |
| 6 | C | **Pulizia.** Metadati (§4), codici errore, pgTAP deboli (§5), U38 (con il codice d'errore di Q35), U39 | BE18 | Ciò che nessun giro precedente ha già aperto |

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

### 3.1 Giri 1a e 1b — il preset di base e il banner

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
* **Correzione proposta.** ~~Lo spareggio esplicito, sull'id del preset.~~ Superata il 2026-11-20: un esito che
  dipende da un id è un'ambiguità del modello (Regola zero). La parità nasce dalla veste NULL, e la correzione sta nel
  suo significato, uno solo per preset e permessi.
* **Decisione (Q28, Tid, 2026-11-20).** (a): con la veste NULL il passo del ruolo si salta, e la cascata parte
  dall'azienda; i permessi di colonna restano al più restrittivo fra le vesti (Q17). Il ripiego non allarga mai, e la
  parità non può più nascere. Lo stesso nel resolver delle dashboard, e il COMMENT «deterministico per priorita» (M7)
  si riscrive su questa regola.
* **Presidio.** Due binding PORTALE costruiti, veste NULL: vince il preset d'azienda, o quello di sistema.

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
* **Decisione (Q29, Tid, 2026-11-20), che completa Q4 dal lato della preferenza.** (a): lo snapshot
  (`preset_base_contenuto_aggiornato_il`, scritto dal DB per Q1) e l'ignorato (`preset_aggiornato_ignored_at`) diventano
  un JSONB `{chiave: data}` ciascuno, con le chiavi validate dal guard di forma (Q6). Le chiavi sono quelle della
  `configurazione`: `colonne`, `ordinamento`, `filtri`, `pagina_dimensione` per le liste; `widget`, `dimensione_max` per le
  dashboard. Una chiave nuova non chiede DDL. Giro 1b.
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

### 3.1-bis Il piano del giro 1a (sessione DB, 2026-11-20)

Corpi vivi letti da `pg_get_functiondef` su dbdev il 2026-11-20 (uguali alla doc auto-generata). ChangeSet dal range di
Tid, dopo `20261119-08`.

| Pezzo | Che cosa | Difetti |
| --- | --- | --- |
| `ui.fn_preset_di_base(p_famiglia, p_contenitore_id, p_auth_user_id, p_veste, p_emittente_fiscale_id)` | Il BB della scelta, uno per le due famiglie (`'lista'`, `'dashboard'`): un candidato vale se è acceso e ha contenuto (una colonna attiva; un widget acceso **nel pool**); ruolo solo con la veste valorizzata, azienda solo accesa, poi sistema; ordine per livello e priorità del profilo. Restituisce id, ambito e `contenuto_aggiornato_il`, oppure nessuna riga | U3, U4/Q28, U7, U9 |
| `ui.fn_preset_aggiornato(snapshot, contenuto, ignorato)` | Il BB del flag, IMMUTABLE; il giro 1b lo porta per chiave (Q29) | U9 |
| I due resolver | 2b-2d sostituiti dalla chiamata al BB e da una lettura del preset scelto; il passo 1 (`fn_get_profili_accesso_applicabili`) esce, lo legge il BB. Chiavi additive: `preset_base` (`{id, ambito, contenuto_aggiornato_il}` oppure `null`) e `preset_base_cambiato` (la preferenza ha un preset di base salvato e non è quello di oggi). Il flag si calcola solo quando la base salvata è quella di oggi, dal contenuto che il BB ha già letto | U2, U5/Q3 |
| `ui.trgfn_preferenza_preset_base_snapshot()` | Una funzione sola sulle due preferenze (`TG_ARGV[0]` = la tabella dei preset), `BEFORE INSERT OR UPDATE OF preset_base_id, preset_base_contenuto_aggiornato_il`: lo snapshot lo scrive il DB dal preset di base, quello che arriva dall'app non conta; se la base cambia, l'ignorato si azzera. Sostituisce i due z90, che si tolgono | U1/Q1 |
| `is_default` | Si spengono i preset accesi con `is_default = false` (il resolver non li ha mai applicati: il comportamento resta identico; dbdev 2026-11-20: zero), poi `DROP COLUMN` su liste e dashboard (gli indici `uq_*_default` cadono con lei) e l'UNIQUE parziale `WHERE attivo` sul posto, `NULLS NOT DISTINCT` (linee-guida-sql §8.4-bis). Il loader e il CSV dei due preset senza la colonna; la riga 5 del registro del seed senza `is_default` | Q26, Q30 |
| pgTAP | I quindici che scrivono `is_default` sui preset (tredici in `ui`, due in `vendite`); i presidi di U1-U5, U7; i test dello z90 che lo aggiravano (`…-cascata-per-chiave-v1:321-325`, `…-preset-aggiornato-v1` caso F) | |

**Chi cambia per primo.** Il DB. Dopo l'apply il BE che scrive `is_default` si rompe (BE22): rottura accettata in sviluppo,
la richiesta al team parte con l'apply insieme a BE5, BE6, BE7, BE23.

**Lo stato (2026-11-20).** Scritti `20261119-09` … `-14`, il loader e il CSV dei due preset senza `is_default`, la riga 5
del registro del seed; quindici pgTAP adeguati e `ui/test-fn-preset-di-base-v1` nuovo (20 test). Provato sullo scratch
(`prova_changeset.py`, con uno YAML di prova per la riga del registro e la convergenza): estratto per intero, catalogo
identico dopo il ROLLBACK; il test nuovo 20 ok; dei quindici, tredici con gli stessi verdi o di piu' e nessun rosso nuovo,
`test-fn-resolve-dashboard-config` e `test-misure-pagina-v1` con i rossi che avevano gia' da owner (sono test da app).
⚠️ Corretto dopo l'apply: i rossi 6 e 10 di `test-fn-resolve-dashboard-config` non erano del runner ma di Q28. Il file
girava con la veste NULL, e ora il ruolo non concorre senza veste. Il file dichiara ora CLIENTE_PORTALE, la veste della
sua fixture, come il gemello delle liste: era la domanda che brief-db-pgtap-runner-rls-baseline §11 lasciava al
cantiere `ui`. ✅ Applicato da Tid il 2026-11-20, pgTAP verdi, doc auto-generata rigenerata. Restano al giro 1b U6, U8, Q29, Q33; i marcatori di cronaca dentro i corpi dei
resolver (§4.3) li toglie l'1b, che li riscrive di nuovo: qui sono riscritte la testata e il COMMENT.

⚠️ **Residuo del giro 1a, trovato il 2026-11-20 dalla sessione che prepara l'1b.** I COMMENT di tre colonne non sono
stati riscritti: `preset_base_contenuto_aggiornato_il` delle due preferenze dice ancora «NULL se il preset di base
cambia (trigger z90)»; `lista_preferenza_utente.preset_aggiornato_ignored_at` dice ancora «DEF-2» e «confronta con
`lista_preset.data_update`» (M5); il gemello delle dashboard non ha COMMENT. L'1b cambia la forma di queste colonne e li
riscrive comunque.

### 3.1-ter Il piano del giro 1b (sessione DB, 2026-11-20) — applicato, pgTAP verdi

Corpi vivi letti da dbdev il 2026-11-20 (trigger da `pg_get_triggerdef`, colonne e dipendenze da `pg_attribute` e
`pg_depend`): uguali alla doc auto-generata, rigenerata dopo il giro 1a. Nessun changeSet dopo `20261119-14` tocca
oggetti di `ui` (`20261120-01` è su `vendite`).

**Che cosa ha trovato la verifica, prima di scrivere.**

* **Q33 non regge sul suo controesempio.** Provato su dbdev il 2026-11-20, su tabelle temporanee in una transazione
  annullata. PostgreSQL rifiuta le transition table su un trigger con più di un evento («non si può specificare una
  tabella di transizione per trigger con più di un evento»): servono tre trigger, uno per evento. Il punto che decide è
  un altro: il DELETE + INSERT identico del BE sono **due istruzioni**, e ciascun trigger vede solo la sua. Il DELETE
  vede «tolte tutte», l'INSERT vede «aggiunte tutte», e nessuno dei due può concludere «insieme uguale». Lo stesso
  succede con le due operazioni in un'istruzione sola (CTE scrivibile): i trigger per istruzione scattano separati per
  evento. Un constraint trigger differito, che vedrebbe la fine della transazione, esiste solo `FOR EACH ROW` (errore
  di sintassi su `FOR EACH STATEMENT`). → Q37.
* **`contenuto_aggiornato_il` ha un secondo lettore, che il brief non nominava**: il seed di primo impianto (giro 3 del
  [brief del seed](../work-done/brief-db-seed-primo-impianto-non-si-riscrive.md), §16.15, QU1-QU2). La colonna è
  dell'installazione nella riga 5 del registro, e una scrittura dell'app che la sposta rende personalizzato il preset:
  da quel momento il migrate non riscrive più la sua composizione. Oggi il DELETE + INSERT identico del BE personalizza
  per finta un preset di seed. Q37 corregge anche questo. Ne segue un vincolo per il giro: la colonna **resta** (cambia
  forma, non nome) e ogni colonna nuova del preset entra nella riga 5 del registro, o la tabella diventa
  `NON_CLASSIFICATA`.
* **L'ignorato non serve, se lo snapshot lo scrive il DB.** Il flag di oggi è
  `contenuto > snapshot AND (ignorato IS NULL OR ignorato < contenuto)`, cioè `contenuto > max(snapshot, ignorato)`:
  conta solo il più recente dei due. Dal giro 1a ogni scrittura che nomina `preset_base_id` riallinea lo snapshot al
  contenuto di oggi (Q1). «Ignora» può essere quella scrittura: il banner si spegne e si riaccende al cambio successivo
  del preset, come oggi. Per chiave vale lo stesso: riallineare anche le chiavi che non sono in banner non cambia niente,
  perché quelle hanno già `contenuto ≤ snapshot`, oppure seguono il preset e il flag non le guarda. → Q38.
* **La forma della data per chiave lato preset non è decisa.** Q4 dice «una data per chiave sul preset»; Q29 dà la
  forma solo dal lato della preferenza. → Q39.

**I pezzi** (nella forma di Q37-Q39, decise come raccomandate; le differenze dalla scrittura sono in «Lo stato», qui sotto):

| Pezzo | Che cosa | Difetti |
| --- | --- | --- |
| `contenuto_aggiornato_il` dei due preset | Da `timestamptz` a `jsonb` `{chiave: data}`, stesso nome (Q39): `colonne`, `ordinamento`, `filtri`, `pagina_dimensione` per le liste; `widget`, `dimensione_max` per le dashboard. Le righe esistenti hanno tutte le chiavi alla data che la colonna porta oggi, non a `now()` (il banner resta identico). `DEFAULT` tolto: la scrive il trigger | U6/Q4 |
| `composizione_impronta` dei due preset (Q37) | Colonna nuova, `text NOT NULL`: l'impronta della composizione (le righe del preset, ordinate). Entra fra le colonne dell'installazione nella riga 5 del registro del seed | Q33 |
| `ui.fn_preset_impronta(p_famiglia, p_preset_id)` (Q37) | Il BB dell'impronta, `STABLE`: una sede per i due trigger qui sotto | Q33 |
| `ui.trgfn_preset_contenuto_aggiornato()` | `BEFORE INSERT OR UPDATE`, senza `WHEN`: all'INSERT tutte le chiavi a `now()`; all'UPDATE riparte da `OLD` (il lucchetto di U8: scritto come rifiuto, «Lo stato»), sposta le chiavi le cui colonne sono cambiate e ricalcola l'impronta: se è diversa da `OLD`, sposta `colonne` (o `widget`) | U6, U8 |
| `ui.trgfn_preset_riga_tocca_preset()` (Q37) | Diventa un constraint trigger `DEFERRABLE INITIALLY DEFERRED`, per riga: a fine transazione tocca il preset solo se l'impronta di oggi è diversa da quella salvata. Un DELETE + INSERT identico, e la riscrittura del seed, non spostano niente | Q33 |
| Snapshot delle due preferenze | `preset_base_contenuto_aggiornato_il` da `timestamptz` a `jsonb`, la copia della mappa del preset di base; lo scrive `trgfn_preferenza_preset_base_snapshot` come oggi. Le righe esistenti: ogni chiave a `max(snapshot, ignorato)`, che conserva il banner di oggi | U6/Q29 |
| `preset_aggiornato_ignored_at` delle due preferenze (Q38) | Si ritira (`DROP COLUMN`); «Ignora» è una scrittura che nomina `preset_base_id`. Con Q38 (b): `jsonb` come lo snapshot | Q29 |
| `ui.fn_preset_aggiornato` | Nuova firma `(p_snapshot jsonb, p_contenuto jsonb, p_chiavi text[]) RETURNS text[]`, ~~`IMMUTABLE`~~ `STABLE` («Lo stato», qui sotto): le chiavi del banner, fra quelle di origine `preferenza`. La firma vecchia si toglie (`DROP`), non resta un overload | U6 |
| `ui.fn_preset_di_base` | Restituisce la mappa `jsonb`. `DROP` + `CREATE`: il corpo `BEGIN ATOMIC` dipende dalla colonna, e l'`ALTER TYPE` non passa finché c'è | — |
| I due resolver | Il flag per chiave sulle sole chiavi di origine `preferenza`; chiave additiva `preset_aggiornato_chiavi` (l'elenco); `preset_base.contenuto_aggiornato_il` diventa la mappa. Via i marcatori di cronaca dai corpi (§4.3) e M6, M7 nei COMMENT | U6, M6, M7 |
| COMMENT | Le colonne toccate (compreso il residuo dell'1a qui sopra, M5) e le funzioni riscritte, secondo §5d | M5 |
| pgTAP | I cinque che leggono le tre colonne (`…-cascata-per-chiave-v1` liste e dashboard, `…-preset-aggiornato-v1`, `test-fn-preset-di-base-v1`, `test-ui-nell-ambito-v1`). Presidi nuovi: U6 (preferenza di sola misura, cambia l'ordinamento: flag spento); U8 (l'app scrive la mappa: rifiutata); Q33 (DELETE + INSERT identico: data ferma; un cambio vero: data spostata); Q38 («Ignora» spegne il banner, il cambio dopo lo riaccende). ⚠️ Il trigger differito scatta al commit: i pgTAP che lo provano chiedono `SET CONSTRAINTS … IMMEDIATE` | |
| Doc | Le pagine `manual/` delle funzioni e delle tabelle toccate, `fn_preset_impronta` nuova; la guida `configurazione-liste` dove parla del banner | |

**Ordine dentro il giro.** Prima i `DROP` di ciò che dipende dalle colonne (i due trigger dello snapshot, che le nominano
in `UPDATE OF`; `fn_preset_di_base`; la firma vecchia di `fn_preset_aggiornato`). Poi gli `ALTER` con la conversione
delle righe, poi le funzioni e i trigger nuovi.

**Garanzie ritirate** (AGENTS.md, «Una garanzia ritirata si censisce in tutti i lettori»):

| Oggetto | La proprietà che i lettori davano per scontata | Lettori lato DB, con l'esito |
| --- | --- | --- |
| `contenuto_aggiornato_il` dei preset | È un `timestamptz`, uno per preset | I due resolver, `fn_preset_di_base`, `fn_preset_aggiornato`, i tre trigger di `ui`: si riscrivono nel giro. Il meccanismo del seed la legge per nome dal registro, non per tipo: non ne dipende |
| La stessa colonna | Dopo una scrittura della composizione è già spostata, nella stessa transazione | Il seed (QU2): la personalizzazione si registra al commit della transazione dell'app; nella stessa transazione non c'è un migrate che la legga. Non ne dipende |
| `preset_base_contenuto_aggiornato_il` | È un `timestamptz` | I due resolver e il trigger dello snapshot: si riscrivono nel giro |
| `preset_aggiornato_ignored_at` | Esiste, e la scrive il BE | Nessun lettore DB oltre ai resolver, riscritti nel giro |

Lato BE/FE la richiesta è BE7 riscritta (§6): **«censisci i lettori di `contenuto_aggiornato_il` (preset),
`preset_base.contenuto_aggiornato_il` (resolver), `preset_base_contenuto_aggiornato_il` e
`preset_aggiornato_ignored_at` (preferenze) che contano su un `timestamptz`, o sull'esistenza dell'ignorato»**.

**Chi cambia per primo.** Il DB. Dopo l'apply si rompe il BE che scrive `preset_aggiornato_ignored_at` (rottura
accettata in sviluppo); la richiesta parte con l'apply.

**Lo stato (2026-11-20).** Scritti `20261120-02` … `-11`:

| ChangeSet | Che cosa |
| --- | --- |
| `-02` (`00_schema`) | `composizione_impronta` nasce nuda sui due preset |
| `-03` (`20_code`) | `ui.fn_preset_impronta`, col risultato ancorato alla colonna (`%TYPE`) |
| `-04` (`00_schema`) | i `DROP` di ciò che blocca l'`ALTER TYPE`; le tre colonne a `jsonb` con la conversione delle righe; il backfill dell'impronta coi trigger spenti per nome; `NOT NULL`; via l'ignorato; i COMMENT di colonna (compreso il residuo dell'1a) |
| `-05` | `ui.trgfn_preset_contenuto_aggiornato`: guard e derivazione, `BEFORE INSERT OR UPDATE` senza `WHEN`, rimontato per funzione coi nomi storici |
| `-06` | `ui.trgfn_preset_riga_tocca_preset`: constraint trigger differito, scrive l'impronta solo se è cambiata |
| `-07` | `ui.fn_preset_aggiornato(jsonb, jsonb, text[]) RETURNS text[]`, la firma vecchia tolta |
| `-08` | `ui.fn_preset_di_base` ricreata, corpo identico |
| `-09` | `ui.trgfn_preferenza_preset_base_snapshot` senza l'ignorato; i due trigger rimontati |
| `-10`, `-11` | i due resolver: banner per chiave, `preset_aggiornato_chiavi`, via i marcatori di cronaca dei corpi (§4.3), M6, M7 |
| `80_data` | riga 5 del registro del seed con `composizione_impronta` fra le colonne dell'installazione; `E_UI_PRESET_CONTENUTO_DERIVATO` in `codici_errore.csv` e `messaggi_errore.csv` (id 1517) |

Quattro scelte della scrittura che il piano non diceva, sul modello:

* **Il lucchetto di U8 rifiuta, non ignora** (`E_UI_PRESET_CONTENUTO_DERIVATO`, come diceva il presidio di U8; il
  piano qui sopra diceva «ignorata»). Il trigger del seed (`a00`) giudica la personalizzazione sul valore scritto,
  prima della derivazione: una scrittura ignorata personalizzerebbe per finta un preset di seed. Rifiuta chi scrive
  la data, e chi scrive un'impronta diversa da quella della composizione di oggi; l'impronta vera la scrive solo il
  trigger differito, ed è il valore che il seed vede cambiare.
* **L'ora è `clock_timestamp()`, non `now()`.** Con `now()` un cambio del preset nella stessa transazione dopo lo
  snapshot ha la stessa data dello snapshot, e il banner non lo vede mai. Ne segue che i pgTAP non retrodatano più:
  salvano la mappa e guardano le chiavi che si spostano.
* **La colonna nasce prima della funzione** (`-02`, poi `-03`), perché la funzione ancori il risultato con `%TYPE`
  (Tid, 2026-11-20). Il giro ha preso un numero in più del piano.
* **`ui.fn_preset_aggiornato` è `STABLE`, non `IMMUTABLE`** come diceva il piano: legge le date dalla mappa con
  `::timestamptz` da testo, una conversione che dipende dalla sessione (`TimeZone`, `DateStyle`). Trovato dal
  `/verifica-db` del 2026-11-20, che allinea qui il piano al codice.

**Le prove.** `scripts/prova_changeset.py` sullo scratch, i dieci changeSet più uno YAML di prova (nello scratchpad)
che fa ciò che fanno i mirror di `80_data` e la rete di `90_end`: la riga 5 del registro, il runner del seed, il
codice d'errore. Estratto eseguito per intero, catalogo identico dopo il ROLLBACK. pgTAP (da owner):

| pgTAP | Senza → con l'estratto |
| --- | --- |
| `ui/test-ui-nell-ambito-v1` (adeguato) | 6/2 rossi, interrotto → 10/0 |
| `ui/test-fn-resolve-dashboard-config-cascata-per-chiave-v1` (adeguato, 11 → 13) | 5/0, interrotto → 13/0 |
| `ui/test-fn-resolve-lista-config-cascata-per-chiave-v1` (adeguato, 19 → 22) | 10/0, interrotto → 22/0 |
| `ui/test-fn-preset-di-base-v1` (adeguato, 20 → 24) | 0/0, interrotto → 24/0 |
| `ui/test-fn-resolve-lista-config-preset-aggiornato-v1` (riscritto) | 4/2 → 6/0 |
| `ui/test-seed-primo-impianto-ui-installazione-v1` (18 → 19) | 13/6 → 13/6: i sei rossi di prima, da owner (test da app) |
| `ui/test-seed-primo-impianto-ui-software-v1`, `ui/test-fn-resolve-dashboard-config` | 16/0 → 16/0; 12/0 → 12/0 |
| `script/test-catalogo-messaggi-errore-completo`, `dbops/test-riferimenti-morti-v1` | 7/0 → 7/0; 12/0 → 12/0 |

⚠️ Il caso 18 di `…-lista-config-cascata-per-chiave-v1` asseriva il contrario di U6 (preferenza di sole colonne, cambia la
misura del preset, banner acceso): è riscritto come presidio di U6. I presidi nuovi: U6 sulle due famiglie; U8 come app
(data e impronta finta rifiutate); Q33 coi vincoli differiti (DELETE + INSERT identico fermo, un ordine cambiato
sposta `colonne`); Q38 («Ignora» chiude, il cambio dopo riaccende); il seed (composizione riscritta uguale dall'app: il
preset resta intatto, il caso 15, che da owner passa per costruzione e va letto come app). Guardrail dei changeSet e
del preambolo pgTAP verdi.

**La doc.** Riscritte le pagine `manual/` di `fn_preset_aggiornato`, `trgfn_preset_contenuto_aggiornato`,
`trgfn_preset_riga_tocca_preset`, `trgfn_preferenza_preset_base_snapshot`; nuova `fn_preset_impronta`; riallineate
`fn_preset_di_base`, i due resolver, i due preset, le due composizioni, le due preferenze (le righe «⚠️ Che cosa oggi non
copre» di U6, U8 e della sostituzione in blocco tolte), le pagine del seed `automazione_seed_primo_impianto` e
`trgfn_seed_primo_impianto`, la guida `configurazione-liste` §10.5. La doc auto-generata e `ui/index.md` li rigenera
Tid dopo l'apply.

**La verifica (`/verifica-db`, sessione nuova, 2026-11-20).** Nessun difetto di codice: corpi dei resolver confrontati con
quelli vivi su dbdev, catena delle `preConditions`, censimento dei lettori delle colonne (funzioni, `BEGIN ATOMIC` da
`pg_depend`, viste, fasi tardive), nessun clone dei preset, nessun caricamento di `80_data` coi trigger spenti; la
prova ripetuta su ventidue pgTAP, nessun rosso nuovo. Corretti quattro testi:

* l'avvertenza di `-06` e della pagina `trgfn_preset_riga_tocca_preset` sugli eventi trigger in sospeso: bloccano
  l'`ALTER` della composizione, che li accoda, non del preset (provato su tabelle temporanee);
* la nota di `E_UI_PRESET_CONTENUTO_DERIVATO` in `codici_errore.csv`, senza apostrofi;
* «tutte le chiavi alla data di oggi» (testata di `-04` e tabella dei pezzi qui sopra): è la data che la colonna porta,
  non `now()`;
* `fn_preset_aggiornato` `STABLE` e non `IMMUTABLE`, allineato nel piano.

Limiti dichiarati, non chiusi: il caricamento dei CSV dei preset da zero passa dal trigger (senza `DEFAULT`) e lo
prova solo la CI; per le dashboard «Ignora» e il DELETE + INSERT identico non hanno un pgTAP proprio (la funzione è
quella delle liste; lo dichiara la pagina `dashboard_preferenza_utente`).

**L'apply.** ✅ `20261120-02` … `-11` applicati su dbdev da Tid il 2026-11-20 (23:55), pgTAP verdi. Parte la richiesta
al team BE/FE: la parte 1b di BE7 e BE25 (§6).

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
  sorgente, che il FE usa per ordinare. All'ingresso (Q34, Tid, 2026-11-20): il guard di forma rifiuta un `col` che non
  è un codice della lista, e la traduzione dal campo sorgente la fa il BE (BE20); un guard non riscrive in silenzio ciò
  che riceve.
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

### 3.2-bis Il piano del giro 2 (sessione DB, 2026-11-21) — da decidere, non iniziato

Corpi vivi letti da dbdev il 2026-11-21 (`pg_get_functiondef`, `pg_get_triggerdef`, `pg_constraint`): i due resolver
sono quelli di `20261120-10` e `-11`, uguali alla doc auto-generata rigenerata dopo l'1b. Nessun changeSet dopo
`20261120-11` tocca oggetti di `ui`. Prima di scrivere si riverifica.

**Che cosa ha trovato la lettura, prima di scrivere.**

* **La forma di `filtri` non è scritta da nessuna parte.** Il COMMENT di `lista_preset.filtri_default` dice «formato
  JSONB condiviso con il componente Vue filtri. Definirlo prima di seedare i preset»; la guida non lo descrive; il
  COMMENT di `configurazione` lo nomina e basta. Un guard di forma (Q6) e il filtro delle voci (U13) chiedono una
  forma: senza, il DB può solo dire «un oggetto», e non sa quali chiavi siano colonne. La forma la conosce il BE, che
  la valida oggi (la copia di BE8). → R-BE2, prima di scrivere il guard.
* **Il DB non sa che cosa il BE accetta oggi, voce per voce.** Il guard di Q6 sostituisce la copia del BE
  (`lista_preferenza_service.py`, `dashboard_preferenza_service.py`): se la regola del DB è più stretta, una scrittura
  che oggi passa si rompe; se è più larga, la copia ritirata portava via una garanzia. Quali campi della voce sono
  obbligatori (`larghezza` può mancare?), quali chiavi ammesse, se il codice deve essere della lista: lo dice il BE.
  → R-BE2, insieme alla forma di `filtri`.
* **La traduzione da campo sorgente a codice (Q34) è ambigua nel modello.** Nessun vincolo impedisce a due colonne
  della stessa lista di avere lo stesso `campo_sorgente`; allora il campo che il FE manda non dice quale colonna.
  Fatto datato, 2026-11-21: su dbdev nessuna lista ne ha due, e 164 colonne hanno codice diverso dal campo. → Q40.
* **Il `col` di cinque preset del seed è un campo sorgente** (Q7). Fatto datato, 2026-11-21: i preset 1, 18, 90, 95,
  107 (`ragione_sociale_completa` → `ragione_sociale`, `comune_descrizione` → `comune`, `revisione_numero` → `rev`,
  `tipo_prestazione_descrizione` → `tipo_prestazione`). `ordinamento_default` è una colonna dell'installazione nella
  riga 5 del registro del seed: il CSV corretto raggiunge le righe intatte, non quelle personalizzate. La conversione
  delle personalizzate (e delle preferenze, dove il FE scrive oggi il campo sorgente) è un backfill di forma, come
  quello di `-04` dell'1b: nel changeSet di schema, coi trigger spenti per nome, prima del guard.
* **Un UPDATE che non cambia la `configurazione` non deve passare dal guard.** «Ignora» (Q38) e il riallineamento
  riscrivono la preferenza; se l'upsert del BE rimanda la `configurazione` com'è, una riga scritta prima del guard
  verrebbe rifiutata proprio mentre l'utente chiude il banner. Il guard giudica l'UPDATE solo se
  `NEW.configurazione IS DISTINCT FROM OLD.configurazione`.
* **I legami di U14 si chiudono con FK composite**, che valgono per costruzione da tutti e due i lati: la preferenza ha
  già `lista_id` e `dashboard_id`, e `ON DELETE SET NULL (preset_base_id)` (PostgreSQL 15+, dbdev è 18) tiene la
  regola di oggi. Le composizioni dei preset no: `lista_preset_colonna` e `dashboard_preset_widget` non portano la
  lista né la dashboard. → Q41. Fatto datato, 2026-11-21: zero righe che violano i quattro legami; il changeSet
  bonifica lo stesso (il modello le ammette), prima dei vincoli.

**I pezzi** (nella forma raccomandata di Q40-Q42; R-BE2 può cambiarli):

| Pezzo | Che cosa | Difetti |
| --- | --- | --- |
| `ui.fn_intero_da_jsonb(p_valore jsonb)` | Il BB della misura (U19): un `number` intero di al più nove cifre, altrimenti NULL; mai un cast che cade. `IMMUTABLE`. Lo leggono il guard di forma, `fn_guard_misura_pagina` e i due resolver: la stringa `"25"`, che il resolver delle liste oggi accetta e il guard rifiuta, non vale più in nessuna sede | U19 |
| `ui.fn_dimensione_max_ammessa(p_valore integer)` | Il tetto 1-100 della dashboard, in una sede (Q12): lo leggono il guard di forma e il resolver delle dashboard. L'8 e il CHECK sul preset restano al giro 3 | U21 (preferenza) |
| `ui.fn_guard_forma_preferenza(p_famiglia, p_contenitore_id, p_configurazione)` | Il guard di forma comune (Q6): un oggetto; le chiavi ammesse della famiglia (`colonne`, `ordinamento`, `filtri`, `pagina_dimensione`; `widget`, `dimensione_max`); `colonne`/`widget` un array di oggetti con `codice` testo non vuoto, unico, del contenitore (una colonna della lista, un widget del pool), `ordine` intero, `visibile` e `fissata` booleani, `larghezza` intera (o null, secondo R-BE2); `ordinamento` un array di `{col, dir}` con `col` codice della lista (Q34) e `dir` `asc`/`desc`; `filtri` nella forma di R-BE2; `pagina_dimensione` col guard di oggi; `dimensione_max` col BB del tetto. Un codice d'errore nuovo, `E_UI_PREFERENZA_FORMA`, segnaposto la chiave e il motivo | U12, U21, Q34 |
| Il trigger del guard sulle due preferenze | `BEFORE INSERT OR UPDATE OF configurazione`, l'UPDATE giudicato solo se la `configurazione` cambia. Sulle liste sostituisce `trg_ui_lista_preferenza_utente_a10_guard_pagina_ins_upd` e la sua funzione, che si tolgono (la misura la giudica il guard di forma) | U12 |
| Il guard di `ordinamento_default` e `filtri_default` dei preset | Le stesse regole di `ordinamento` e `filtri`, dal BB del guard (Q7, Q34: anche il preset scrive un codice). Sul trigger `a10` del preset, accanto a quello della misura | U13, Q34 |
| I due resolver | Il conteggio di `widget_nuovi` dopo il filtro di area e azione, come le liste al passo 5-bis (U10); `NOT EXISTS` al posto di `NOT IN` nel merge (U11); i cast di `ordine`, `larghezza`, `visibile`, `fissata` dal BB, una voce senza codice scartata, un codice ripetuto preso una volta (le righe scritte prima del guard); ordinamento e filtri senza le voci di colonne spente, non `ordinabile`/`filtrabile` o BLOCCATO per l'utente, e ogni voce d'ordinamento con il suo `campo_sorgente` (chiave additiva, Q7) | U10, U11, U12, U13 |
| I legami (Q41 (a)) | FK composite `(preset_base_id, lista_id)` → `lista_preset (id, lista_id)` e il gemello delle dashboard, `ON DELETE SET NULL (preset_base_id)`, al posto delle FK di oggi; `lista_id` su `lista_preset_colonna` e `dashboard_id` su `dashboard_preset_widget`, scritte dal DB dal preset, con le FK composite verso il preset, la colonna della lista e il pool (`dashboard_widget`, la sua PK). Gli UNIQUE `(id, lista_id)` e `(id, dashboard_id)` che le FK chiedono | U14 |
| Il pool (Q8) | `BEFORE DELETE` su `dashboard_widget`: rifiutato finché un preset propone il widget, il messaggio nomina i preset (codice nuovo); la FK composita resta la rete | U14, Q8 |
| La testata del preset | Un lucchetto: `lista_id`/`dashboard_id`, `ambito`, profilo e azienda non cambiano dopo l'INSERT (codice nuovo). Il CSV li riscrive uguali, e passa | U14 |
| Seed e backfill | `lista_preset.csv`: i cinque `col` col codice (Q7). Nel changeSet di schema, coi trigger spenti per nome: il `col` delle preferenze e dei preset personalizzati tradotto dove il campo dice una colonna sola, la voce tolta dove non la dice; le voci di U14 incrociate tolte e le basi altrui a NULL. La riga 6 del registro del seed (la composizione figlia) resta: `lista_id` è derivata, non dell'installazione | Q7, U14 |
| COMMENT e doc | `configurazione`, `ordinamento_default`, `filtri_default` (la forma scritta, non più «da definire»); le pagine `manual/` delle funzioni e delle tabelle toccate; la guida `configurazione-liste` dove descrive preferenza, ordinamento e filtri; la pagina nuova di ogni BB | M |
| pgTAP | Il guard: un `throws_ok` per ogni forma rifiutata, sulle due famiglie, e un UPDATE di sola base su una riga malformata che passa. I resolver: U10 (utente senza l'area, widget di quell'area nel pool: `widget_nuovi = 0`), U11 (voce senza codice scritta senza il trigger, colonna nuova in catalogo: arriva), U12 (riga malformata scritta senza il trigger: il resolver non cade), U13 (ordinamento su colonna spenta e su sensibile senza grant: tolti; `campo_sorgente` in uscita). U14: un INSERT incrociato rifiutato per legame, l'UPDATE della testata rifiutato, il DELETE dal pool rifiutato col nome del preset. Da adeguare gli otto che scrivono preferenze (`ui/test-fn-resolve-*`, `test-fn-preset-di-base-v1`, `test-misure-pagina-v1`, `test-ui-nell-ambito-v1`) e gli otto che scrivono composizioni | |

**Garanzie ritirate.**

| Oggetto | La proprietà che i lettori davano per scontata | Lettori lato DB, con l'esito |
| --- | --- | --- |
| `ordinamento` e `filtri` dei due resolver | Escono come la preferenza o il preset li ha salvati | Nessun lettore DB oltre al resolver. Lato BE è BE9: chi applica l'ordinamento risolto alle API di lista |
| `pagina_dimensione` della preferenza | Il resolver delle liste accetta anche la stringa `"25"` | Solo il resolver. Il guard la rifiutava già: vale per le righe scritte prima del guard |
| `widget_nuovi` | Conta anche i widget che l'utente non vede | Solo il resolver |

Lato BE/FE la richiesta è **«censisci i lettori di `ordinamento`, `filtri` e `widget_nuovi` del resolver che contano su
ciò che è stato salvato, o su un conteggio prima del filtro»**, accanto a BE8, BE9, BE11, BE20.

**Chi cambia per primo.** Il DB, salvo R-BE2, che viene prima di scrivere. Dopo l'apply un salvataggio
dell'ordinamento col campo sorgente è rifiutato finché il BE non traduce (BE20): rottura accettata in sviluppo, come
all'1a; la richiesta parte con l'apply.

**Prima di scrivere: R-BE2 al team BE (con la verifica di BE9, Q35).** Che forma ha oggi, voce per voce, ciò che il BE
accetta nella `configurazione` delle due preferenze e in `ordinamento_default`/`filtri_default` dei preset: le chiavi
ammesse, i campi obbligatori di ogni voce e i loro tipi, se il codice deve essere della lista o del pool, e la forma di
`filtri` che il FE manda. Senza, il guard o rompe una scrittura che oggi passa o ritira una garanzia senza saperlo.

**Le decisioni di questo piano** (§7.1): Q40, Q41, Q42.

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
  nel giro 2, insieme al guard di forma di U12 che lo legge (§2).

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
* **Decisione (Q35, Tid, 2026-11-20), che completa Q13.** Le preferenze della lista spenta restano, e si sospendono con
  la lista. Una riaccensione rifiutata dalla verifica di Q16 nomina le colonne orfane.
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
  immutabile; ~~vista e schema dati di una lista certificata solo dall'owner~~ (superata da QU4); `ricerca_min_caratteri`
  resta all'app (è una regolazione, non una dichiarazione del codice).
* **Decisione (Q27, Tid, 2026-11-20), che completa Q14.** Il mirror `runOnChange` di `lista_definizione` carica anche
  `ricerca_min_caratteri`, e il migrate riscriverebbe la regolazione dell'app al primo cambio del CSV. La colonna si
  dichiara d'installazione nel censimento del brief del seed, con le altre tabelle di `ui` che l'app scrive.
* **Decisione (QU4 del brief del seed, §16.15, Tid, 2026-11-20).** Una lista certificata nasce sempre dal seed, e sulle
  righe di seed `codice`, `schema_dati`, `vista_sql` e i due flag sono colonne del software (`E_SEED_COLONNA_DEL_SOFTWARE`).
  Di Q14 resta qui ciò che il seed non copre: `codice` della lista e della colonna immutabili, `multi_emittente` e
  `perimetro_emittente` solo dal migratore, su ogni riga. «Vista e schema dati di una lista certificata solo dall'owner»
  si ritira: la tiene il seed per colonna, e due guard per la stessa regola divergono.
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
* **Decisione (Q32, Tid, 2026-11-20), che completa Q16.** Una vista che perde colonne (un DDL sulla vista, che nessun
  trigger di `ui` vede): un presidio `dbops` confronta le colonne di ogni lista con la sua relazione, e legge il BB
  «relazione e attributo di una lista». Copre anche le liste create dall'app, che il pgTAP sul seed non vede.
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
  vesti dell'utente; il ripiego non allarga mai. La stessa regola vale per la cascata dei preset, che con la veste NULL
  salta il passo del ruolo (Q28, 2026-11-20, U4).
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
* **Correzione proposta.** ~~Un presidio `dbops` («dashboard senza un widget sempre visibile»), non un trigger.~~
  Superata da Q31: un constraint trigger differito.
* **Decisione (Q20, Tid, 2026-11-19).** ~~Un presidio `dbops` («dashboard senza un widget sempre visibile»), non un
  trigger: la regola attraversa pool, widget e interruttore, e un trigger bloccherebbe i passaggi intermedi
  legittimi.~~ Superata da Q31.
* **Decisione (Q31, Tid, 2026-11-20).** Lo stesso strumento di U18: un constraint trigger differito. A fine transazione
  ogni dashboard accesa ha nel pool un widget acceso senza area né azione. Il differito ammette i passaggi intermedi, e
  dopo Q19 anche questo catalogo lo scrive solo l'owner, come `misure_pagina`. Il trigger si monta su pool, widget e
  definizione. Nel giro 5, sul seed: accendere o creare il widget senza area né azione, senza il quale il trigger
  rifiuta il commit.

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
| U38 | `fn_lista_colonne_ricerca_full`, guard multi-emittente | Un filtro ripete il CHECK del campo sorgente; l'id utente è ancorato a una colonna di un'altra tabella; una variabile utente non numerica dà un 22P02 grezzo. Il guard multi passa un codice d'area diverso dagli altri (`'ui'` e il nome senza schema) | Filtro tolto, ancora propria; codici d'area allineati. La variabile non numerica (Q35, Tid, 2026-11-20): un codice d'errore dedicato, non il 22P02 |
| U39 | `fn_lista_da_codice`, BE | Due copie di «lista accesa per codice» nel BE (`ui_repository.py:218-226`, `core/db/lista_catalogo_repository.py:64-70`): il BB rifiuta, e quei lettori vogliono «niente» | Q23, deciso da Tid il 2026-11-19: il BE chiama il BB e intercetta `E_UI_LISTA_NON_TROVATA`; nessun BB nuovo |

**Che cosa si ritira** (riepilogo): `DEFAULT 25` (U15); il secondo trigger z90 (U1); la copia BE della cascata (U2);
`is_default` di liste e dashboard e i due indici `uq_*_default` (Q26, sostituiti dall'UNIQUE parziale di Q30); il diff
del BE sulla composizione del preset, mai scritto (BE3, Q33); la regola di forma della
preferenza nel BE (U12, BE8); il tetto 100 da `_MAX_WIDGET_PAYLOAD` (U21, BE11); le copie dell'8 e il ramo «≤0 = nessun
tetto» nel FE (U21, FE1); `data_update` delle preferenze scritta dal BE (Q22, BE21); la dipendenza del guard di `ui` da
`vendite.vw_documento_lineage_sintesi_colonne` (U26); la copia BE di «dashboard accesa per codice» (U34); le due copie BE
della lista per codice (U39); il ramo `= ''` (U37).

### 3.7 Chiusi senza modifiche (proposti)

| Che cosa | Perché si chiude |
| --- | --- |
| `dashboard_widget` e `dashboard_preset_widget` non hanno la regola «figlio chiede padre acceso» né il blocco dello spegnimento | È voluto: righe di composizione, eccezioni ATTIVO decise il 2026-11-08 |
| Lo spegnimento di un widget, di un'area o di un'azione | Già coperto: un'area o un'azione non si spengono con widget accesi, e il widget chiede area e azione accese |
| ~~L'unicità del preset di default di una dashboard~~ | ~~Garantita da `uq_ui_dashboard_preset_default`~~. Superata da Q26: l'indice è `WHERE is_default`, che si ritira. «Un preset per posto» lo garantisce l'UNIQUE parziale `WHERE attivo` (Q30, 2026-11-20), su liste e dashboard: non è più un caso chiuso, è lavoro del giro 1a |
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

I numeri `BEn` restano quelli già citati nelle schede; il lato si legge in testa alla voce: **BE**, **FE**, o
**BE + FE** quando la voce tocca tutti e due.

| # | Giro | Che cosa |
| --- | --- | --- |
| BE1 | subito | **BE.** `backend/apps/ui/services/lista_preset_admin_service.py:254-257`: il commento dice che dopo la cancellazione di un preset si lavora «sul catalogo grezzo»; vale il preset di base di oggi |
| BE2 | subito | **BE.** `backend/apps/ui/db/dashboard_repository.py:13-15`: il commento cita `fn_resolve_livello_area` e `fn_check_azione_processo`, il resolver usa `fn_get_user_permissions_map` e `fn_get_user_actions_map`. `:38-41` e `services/dashboard_service.py:56-57`: il «Risultato» non elenca `dimensione_max_standard` e `origine` |
| BE3 | ritirata | ~~**BE.** `ui_admin_repository.py:733` (`replace_preset_colonne`): … Va fatto il diff~~. Ritirata il 2026-11-20 (Q33, col mezzo di Q37 (a)): la regola «la data si sposta solo se il contenuto cambia» la tiene il DB dal giro 1b (`trgfn_preset_riga_tocca_preset`, constraint trigger differito, che confronta l'impronta della composizione a fine transazione), e il DELETE + INSERT identico del BE non sposta più niente, purché stia in una transazione sola. Il BE non cambia |
| BE4 | subito | **BE.** U30, Q18 decisa (b) il 2026-11-19: il controllo preventivo della cancellazione di una colonna conta anche i preset (`ui_admin_repository.py:528-543`); il commento «CASCADE» (`lista_colonna_admin_service.py:26`, `:276-279`; `ui_admin_repository.py:509-510`) si corregge |
| BE5 | 1a | **BE.** U2: `fetch_preset_base_snapshot` (`ui_repository.py:32-35`, `:64-145`) si ritira; `lista_preferenza_service.py:91-98` e `dashboard_preferenza_service.py:94-100` leggono `preset_base` dalla risoluzione: `{"id", "ambito", "contenuto_aggiornato_il"}` oppure `null`, e salvano `preset_base.id` in `preset_base_id` ✅ **Fatto (BE, 2026-11-20).** Il BB `fetch_preset_base_snapshot` è ritirato; i due service leggono la base con `preset_base_id_di_oggi(risoluzione)` (`apps/ui/services/_preferenza.py`), dalla stessa risoluzione e con lo stesso emittente della lettura a video. Provato sul DB vero (`test_audit_ui_dal_trigger_db`) |
| BE6 | 1a | **BE.** U1, Q1 decisa (b): l'upsert (`ui_repository.py:346`, `dashboard_repository.py:138`) non scrive più lo snapshot: lo scrive il trigger a ogni scrittura che nomina `preset_base_id` (il salvataggio è il riallineamento), e un valore passato dall'app non conta ✅ **Fatto (BE, 2026-11-20).** I due upsert non nominano più lo snapshot; `preset_base_id` resta nel SET di proposito, perché è la colonna che fa scattare il trigger. Provato sul DB vero: snapshot uguale alla data del contenuto, e riallineato al secondo salvataggio con la stessa base |
| BE7 | 1a, 1b | **BE + FE.** U5, Q3 decisa (b): dal giro 1a i due resolver rispondono `preset_base_cambiato` (boolean): la base salvata non è quella di oggi, e allora `preset_aggiornato` è falso. Il banner propone il riallineamento (salvare con `preset_base.id`): servizio, FE e i18n. Dal giro 1b snapshot e ignorato sono JSONB per chiave (Q29): il BE scrive l'ignorato della chiave che l'utente chiude ✅ **Parte 1a fatta (BE + FE, 2026-11-20)** sulle liste: `useListaConfig` espone `presetBaseCambiato` e `riallineaPresetBase` (risalva la preferenza: il BE ci scrive la base di oggi); `ListaConfigurabile` mostra il banner «base cambiata» con «Riallinea», i18n it/en. Il servizio non cambia. ✅ **Dashboard, gemelle delle liste (decisione di Tid, 2026-11-20).** Prima non avevano nessun banner, nemmeno quello del preset aggiornato (`presetAggiornato` non lo leggeva nessuna vista). Ora `useDashboardConfig` espone anche `presetBaseCambiato` e `riallineaPresetBase`, e `HomeView` mostra i due banner sopra le card (testi `home.*`; «Vedi novità» apre la modale delle card). Il markup è il BB `BannerPreset`, estratto da `ListaConfigurabile` (regola del 2, ok Tid). **Parte 1b, da fare ora: `20261120-02` … `-11` (Q37-Q39, §3.1-ter) applicati su dbdev, pgTAP verdi (Tid, 2026-11-20).** Che cosa cambia nel contratto: (1) `preset_aggiornato_ignored_at` non c'è più sulle due preferenze: «Ignora» è un salvataggio che nomina `preset_base_id` con il valore che ha già (il trigger riallinea lo snapshot), e una scrittura della colonna ritirata fallisce; (2) `preset_base_contenuto_aggiornato_il` delle preferenze, `contenuto_aggiornato_il` dei preset e `preset_base.contenuto_aggiornato_il` dei due resolver sono una mappa `{chiave: data}` (`colonne`, `ordinamento`, `filtri`, `pagina_dimensione`; `widget`, `dimensione_max`), non più un `timestamptz`; (3) chiave additiva `preset_aggiornato_chiavi` (elenco, vuoto se nessuna) nei due resolver: il banner può dire quali parti sono cambiate, e `preset_aggiornato` vale «almeno una»; (4) chi scrive `contenuto_aggiornato_il` o `composizione_impronta` di un preset riceve `E_UI_PRESET_CONTENUTO_DERIVATO` (BE25); (5) la composizione si confronta a fine transazione: il DELETE + INSERT di `replace_preset_colonne` resta corretto se sta in una transazione sola. **Il percorso da censire, elenco chiuso:** l'endpoint «ignora» (`POST …/preferenza/ignore-preset-update/` e il gemello delle dashboard, se c'è) e il suo repository, che oggi scrivono l'ignorato; ogni lettore delle tre colonne e di `preset_base.contenuto_aggiornato_il` che conta su un `timestamptz` (serializer, confronti, test Django); le scritture admin del preset che nominano `contenuto_aggiornato_il`; il FE che legge `presetAggiornato` (liste e `HomeView`), che può mostrare le parti cambiate da `preset_aggiornato_chiavi`; le pagine `docs/it/backend/ui/manual/api_ui_liste.md` e `api_ui_dashboard.md`, che descrivono l'ignorato |
| BE8 | 2 | **BE.** U12: `lista_preferenza_service.py:188-231` e `dashboard_preferenza_service.py:161-253`: con Q6 la regola di forma sta nel guard DB, e la copia del BE si ritira nello stesso cantiere (regola del 2); il codice del guard nuovo va in policy e fallback |
| BE9 | 2 | **FE.** U13: il FE non ripulisce più ordinamento e filtri da sé. Chi applica oggi l'ordinamento risolto alle API di lista lo verifica la sessione BE prima del giro 2 (Q35, 2026-11-20), e risponde qui: la voce diventa la richiesta chiusa, con l'elenco dei file. **Con R-BE2 (2026-11-21, §3.2-bis), prima che il giro 2 si scriva:** la forma che il BE accetta oggi, voce per voce, nella `configurazione` delle due preferenze e in `ordinamento_default`/`filtri_default` dei preset (chiavi, campi obbligatori e tipi, codice della lista o del pool), e la forma di `filtri` che il FE manda; e se il FE può mandare l'ordinamento per codice (Q40) |
| BE10 | 3 | **BE.** `backend/apps/core/api/constants.py:16-19`: `DEFAULT_LIMIT = 25` ricopia il default `PAGINA`, e il suo commento cita una costante del FE ritirata. Q11-bis, deciso da Tid il 2026-11-18: le liste configurabili prendono la misura dal DB; la costante resta solo per gli endpoint fuori catalogo, dichiarata come regola dell'API, e il commento sulla costante FE ritirata si toglie |
| BE11 | 2 | **BE.** U21 (il tetto della preferenza sta nel guard di forma del giro 2): `dashboard_preferenza_service.py:205-220`, il tetto 100 preso da `_MAX_WIDGET_PAYLOAD`: Q12 decisa: il tetto 100 sta nel DB (guard di forma), il BE ritira `_MAX_WIDGET_PAYLOAD` per questa regola |
| FE1 | 3 | **FE.** U21: `useDashboardConfig.js:173` (`?? 8`) e `DashboardWidgetModal.vue:37` si tolgono; il ramo `max > 0` (`useDashboardConfig.js:185`, `DashboardWidgetModal.vue:81`) si toglie: «≤0 = nessun tetto» non esiste (Q12). Minore: il terzo ripiego di `ListaConfigurabile.vue:566-569` |
| BE12 | 4 | **BE.** U23: `codice` esce da `UPDATE_KEYS` (`lista_definizione_admin_service.py:76-80`; `ui_admin_repository.py:246-248`) e da `_COLONNA_UPDATE_COLS` (`ui_admin_repository.py:473-479`; `lista_colonna_admin_service.py:96`); il codice d'errore nuovo si mappa |
| BE13 | 4 | **BE + FE.** U24, U25: i CHECK nuovi in `_CHECK_CONSTRAINTS` (`lista_colonna_admin_service.py:127`); nel drawer delle colonne (`ListaColonnaDrawer.vue`, vicino a `:155-160` e `:345`) «Esportabile» spento quando manca il campo sorgente, come già per le azioni; `lista_export_service.py:205-221` |
| BE14 | 4 | **BE.** U26: `backend/apps/core/db/_helpers.py:315-330`, la ricerca libera riceve anche i campi della lineage: con Q15 (b) si escludono le colonne marcate lineage |
| BE15 | 4 | **BE + FE.** U22, Q13 decisa (a): il toggle «attivo» di una definizione con figli accesi smette di fallire; il ramo che intercetta `E_ATTIVO_BLOCK_CHILDREN_ACTIVE` per le liste si ritira |
| BE17 | 5 | **BE.** U34: `get_dashboard_id` (`dashboard_repository.py:66-78`) chiama il BB |
| BE18 | 6 | **BE.** `error_policies_generated.py` da rigenerare dopo la pulizia delle note (§4.3): oggi le righe di `E_UI_*` (fra cui `:1979`, `:1994-1997`) portano brief, date, «il caso del 28-09». U39: `get_lista_id` e `fetch_flag_perimetro` passano dal BB |
| BE19 | — | **BE.** U31 e U23 (`perimetro_emittente`): verificato che il BE non scrive quelle tabelle né quella colonna. Niente da fare, salvo il fallback del codice nuovo |
| BE20 | 2 | **BE + FE.** Q7: `col` di ordinamento e filtri è il codice della colonna. Il FE ordina per campo sorgente (`sortField` di PrimeVue, `ListaConfigurabile.vue:619-668`): il salvataggio della preferenza e del preset traduce il campo in codice nel BE, e il guard di forma rifiuta un `col` che non è un codice (Q34); in lettura il resolver dà anche il campo sorgente. Il test `test_lista_preferenza_service.py:63` già scrive il codice |
| BE21 | 5 | **BE.** Q22: `data_update` delle due preferenze la scrive il DB; l'upsert del BE (`ui_repository.py`, `dashboard_repository.py:127-179`) smette di passarla |
| BE22 | 1a | **BE + FE.** Q26: `is_default` esce dai preset di liste e dashboard. Il BE lo toglie da `_schema_ui.py:31`, `ui_admin_repository.py:56`, `:621-658`, dal drawer dei preset e dai messaggi dell'UNIQUE; la copia della cascata in `ui_repository.py:93-132` si ritira già con Q2 ✅ **Fatto (BE + FE, 2026-11-20).** `is_default` esce da schema, repository, service (whitelist: ora è un 400), drawer, pannello e i18n. ⚠️ Resta a DB la colonna di catalogo `is_default` della lista admin dei preset (`lista_colonna.csv`, id 665): domanda nata nel brief del seed (§16.15, esito del BE), passata qui alla sua archiviazione (2026-11-20): ✅ **Spenta (sessione DB, 2026-11-21)**: `attivo = f` sulla riga 665 di `lista_colonna.csv`. Riga di seed intatta su dbdev, `attivo` è dell'installazione (riga 4 del registro): il mirror `runOnChange` (`20260806-15`) la porta al migrate. La lista 58 non ha vista, quindi il controllo del campo sorgente non scatta sul campo che non c'è più; la riga di composizione del preset 58 resta (figlia, la colonna spenta il resolver la salta). ⏳ Il migrate di Tid |
| BE23 | 1a | **BE + FE.** Q30: un posto (lista o dashboard, ambito, profilo, azienda) ha al più un preset acceso. Accendere un secondo preset nello stesso posto è rifiutato dall'UNIQUE `uq_ui_lista_preset_posto` (o `uq_ui_dashboard_preset_posto`): il servizio lo mappa (`_CHECK_CONSTRAINTS` o il ripiego dell'integrità in `lista_preset_admin_service.py`), e il drawer dice di spegnere prima quello acceso. La bozza nasce spenta. File: `backend/apps/ui/services/lista_preset_admin_service.py`, `ListaPresetDrawer.vue` ✅ **Fatto (BE + FE, 2026-11-20).** `uq_ui_lista_preset_posto` mappato sul campo `attivo` col messaggio «spegnilo prima»; la bozza nasce spenta (default `attivo=false` in service, repository e drawer) |
| BE25 | 1b | **BE.** Codice d'errore nuovo `E_UI_PRESET_CONTENUTO_DERIVATO` (TECNICO, segnaposto: il codice del preset): `error_policies_generated.py` e `error_messages_fallback.py` da rigenerare, la riga in §Tassonomia errori di `docs/it/dev/api.md`. Lo produce solo un chiamante rimasto alla forma in cui la data del contenuto si scriveva. Il codice `E_UI_PREFERENZA_NON_TROVATA` ha una nota che parla dell'endpoint «ignora» (DEF-2): resta valido se l'endpoint resta, e la nota si pulisce nel giro 6 |
| BE24 | 1a | **BE.** La pagina `docs/it/backend/ui/manual/api_ui_liste.md` (righe 445, 514, 534) descrive il trigger z90 e la sua funzione, tolti dal giro 1a: lo snapshot lo scrive `ui.trgfn_preferenza_preset_base_snapshot` (BE6) ✅ **Fatto (BE, 2026-11-20).** `api_ui_liste.md` descrive il trigger nuovo, `preset_base` e `preset_base_cambiato`; `api_ui_admin_personalizzazioni.md` è senza `is_default` e con la superficie del seed |

## 7. Le decisioni di Tid

| # | Domanda | Decisione |
| --- | --- | --- |
| Q1 | U1: chi scrive lo snapshot del preset di base | ✅ **Deciso da Tid il 2026-11-18: (b) il DB**, letto dal preset, insieme a U2; una funzione z90 sola |
| Q2 | U2: il preset di base esposto dal resolver | ✅ **Deciso da Tid il 2026-11-18: sì.** **Chiave additiva `preset_base`** per liste e dashboard, la copia BE ritirata |
| Q3 | U5: la base salvata è spenta o non è più quella di oggi | ✅ **Deciso da Tid il 2026-11-18:** **(b) un esito «base cambiata»**, chiave additiva |
| Q4 | U6: il banner per chiave | ✅ **Deciso da Tid il 2026-11-18:** **(a) una data del contenuto per chiave** sul preset; lato preferenza, snapshot e ignorato JSONB per chiave (Q29) |
| Q5 | U7: il preset di un'azienda spenta | ✅ **Deciso da Tid il 2026-11-18:** **(a) il filtro** sull'azienda accesa |
| Q6 | U12: la forma della preferenza | ✅ **Deciso da Tid il 2026-11-18:** **(a) un guard DB comune** a liste e dashboard, più i cast sicuri |
| Q7 | U13: la convenzione di `col` (codice o campo sorgente), prima di filtrare l'ordinamento nel DB | ✅ **Deciso da Tid il 2026-11-18: il codice** della colonna (l'identità, la stessa chiave delle voci `colonne`); il resolver aggiunge il campo sorgente in uscita per il FE; all'ingresso il guard rifiuta, il BE traduce (Q34) |
| Q8 | U14: un widget tolto dal pool, se un preset lo propone | ✅ **Deciso da Tid il 2026-11-18: bloccato**: si toglie prima dal preset |
| Q9 | U15: `DROP DEFAULT 25`, e le righe del seed che scrivono 25 o 10 | ✅ **Deciso da Tid il 2026-11-18: sì `DROP DEFAULT`**; i 25 e i 50 diventano NULL (seguono `PAGINA`); i 10 diventano NULL con l'uso `COMPATTA` dichiarato dalla lista (Q11 decisa (a)) |
| Q10 | U16: la misura ritirata e le preferenze | ✅ **Deciso da Tid il 2026-11-18:** **(b) il ritiro toglie la chiave** dalle preferenze |
| Q11 | U20: la lista dichiara l'uso della misura (`COMPATTA` o `PAGINA`) | ✅ **Deciso da Tid il 2026-11-18: (a) sì, e sì a Q11-bis.** La lista dichiara l'uso (iniziale `PAGINA`, le liste di righe `COMPATTA`) e il resolver ripiega sul suo default. **Q11-bis** (BE10): le liste configurabili prendono la misura dal DB; `DEFAULT_LIMIT` del BE resta solo per gli endpoint fuori catalogo, dichiarato come regola dell'API |
| Q12 | U21: il tetto della dashboard | ✅ **Deciso da Tid il 2026-11-19: (a).** `CHECK (dimensione_max > 0)` sul preset, NULL = lo standard, l'8 in una sede DB; il tetto vale fra 1 e 100 e sta nel DB (guard di forma, Q6); «≤0 = nessun tetto» non esiste |
| Q13 | U22: spegnere una lista sospende colonne e preset | ✅ **Deciso da Tid il 2026-11-19:** **(a) sì**, eccezioni ATTIVO (forma della decisione del 2026-11-08) |
| Q14 | U23: che cosa del seed scrive solo l'owner | ✅ **Deciso da Tid il 2026-11-19, tutte e cinque come raccomandato:** `perimetro_emittente` nel guard; codici di lista e di colonna immutabili; ~~la vista di una lista certificata solo dall'owner~~ (la tiene il seed per colonna, QU4); `ricerca_min_caratteri` resta all'app, colonna d'installazione nel censimento del seed (Q27) |
| Q15 | U26: la sede dei nomi della lineage | ✅ **Deciso da Tid il 2026-11-19: (b)**, più il lato lista da una sede esistente o, se manca, da (a). **(b) un marcatore sulla colonna** |
| Q16 | U27: riverificare le colonne | ✅ **Deciso da Tid il 2026-11-19:** **(a)**: controllo immediato per l'app, salto sulle liste spente con verifica all'accensione, le partizionate, un BB; la vista che perde colonne, un presidio `dbops` (Q32) |
| Q17 | U29: i permessi di colonna con la veste NULL | ✅ **Deciso da Tid il 2026-11-19:** **(b) il livello più restrittivo** fra le vesti; per la cascata dei preset il passo del ruolo si salta (Q28) |
| Q18 | U30: la composizione del preset alla cancellazione della colonna | ✅ **Deciso da Tid il 2026-11-19: (b) bloccato** (NO ACTION), coerente con Q8; controllo preventivo che conta anche i preset, messaggio e commenti veri. La raccomandazione iniziale era (a) CASCADE |
| Q19 | U31: le cinque tabelle di catalogo delle dashboard in sola lettura per l'app | ✅ **Deciso da Tid il 2026-11-19: sì** |
| Q20 | U32: «la home non è mai vuota» | ~~Un presidio `dbops`, non un trigger~~ (2026-11-19). ✅ **Superata da Q31 (2026-11-20): un constraint trigger differito**, come U18 |
| Q21 | U33: area e azione del widget | ✅ **Deciso da Tid il 2026-11-19:** se c'è l'azione, l'area è nulla oppure quella dell'azione |
| Q22 | U36: le preferenze senza audit | ✅ **Deciso da Tid il 2026-11-19: voluto.** Il COMMENT lo dice; `data_update` la scrive il DB, non il BE |
| Q23 | U39: «lista accesa per codice» per chi vuole «niente» | ✅ **Deciso da Tid il 2026-11-19:** **il BE chiama il BB** e intercetta il codice, nessun BB nuovo |
| Q24 | L'ordine dei giri (§2) | ✅ **Deciso da Tid il 2026-11-19: come in §2.** **Q24-bis:** il preset di ruolo che prevale sull'emittente resta (§3.7). Il giro 1 diviso in 1a e 1b (Q36) |
| Q25 | Una guida delle dashboard: oggi non c'è (§9) | ✅ **Deciso da Tid il 2026-11-19: (a), scritta a fine giro 5.** **Una guida `configurazione-dashboard`** sua, che rimanda alla guida delle liste per il meccanismo comune |
| Q26 | `dashboard_preset.is_default = false`: uno stato senza lettori | ✅ **Deciso da Tid il 2026-11-20: `is_default` si ritira, su liste e dashboard.** Un preset per posto, vale se acceso; la bozza si prepara spenta. Il gemello delle liste è uguale (trovato il 2026-11-19). I preset alternativi, se verranno, nascono nel brief delle viste nominate. Nel giro si riallinea la guida `configurazione-liste` (§2.3 e il passo 5 di §10), che oggi descrive `is_default`; lo stesso changeSet toglie `is_default` dalle colonne del software di `ui.lista_preset` nel registro del seed (riga 5 di `dbops.automazione_seed_primo_impianto`), o la tabella diventa `NON_CLASSIFICATA`. I due indici `uq_*_default` li sostituisce l'UNIQUE parziale `WHERE attivo` (Q30) |

### 7.1 Le decisioni dell'analisi critica (2026-11-20)

Aperte dall'analisi critica prima del via al giro 1, e **decise da Tid il 2026-11-20, tutte come raccomandate**. Ognuna
completa o sostituisce una decisione già presa: la decisione nuova sta in §7 e nella scheda del difetto, e la scelta
superata è barrata, non resta come alternativa. Q37-Q39 vengono dopo: le ha aperte il piano del giro 1b (§3.1-ter,
2026-11-20), e Tid le ha decise lo stesso giorno, come raccomandate.

| # | Domanda | Riapre o completa | Opzioni | Decisione |
| --- | --- | --- | --- | --- |
| Q27 | Le tabelle di catalogo di `ui` nel meccanismo del [brief del seed](../work-done/brief-db-seed-primo-impianto-non-si-riscrive.md): sono mirror `runOnChange` che l'app scrive dalle pagine admin, e il migrate riscrive le modifiche dell'app (`ricerca_min_caratteri`, preset, colonne, composizione) | Q14; i giri che toccano i CSV di `ui` (Q7, Q9, Q20, Q26) | (a) Le tabelle si dichiarano nel censimento del brief del seed, ognuna con la sua specie, e i giri di `ui` che toccano i CSV partono dopo; (b) il censimento si fa qui, nel giro 4, e il brief del seed lo riceve | ✅ **Deciso da Tid il 2026-11-20.** **(a)**: il meccanismo ha una sede sola. Le cinque tabelle delle dashboard, in sola lettura per l'app (Q19), escono dal censimento |
| Q28 | Un significato solo per la veste NULL: oggi la cascata dei preset unisce le identità (U4, parità fra due PORTALE), i permessi di colonna prendono il livello più restrittivo (Q17) | U4 (lo spareggio sull'id, superato), Q17 | (a) Con la veste NULL il passo del ruolo si salta, e la cascata parte dall'azienda; i permessi restano al più restrittivo; (b) un vincolo impedisce due profili applicabili di pari priorità per lo stesso utente; (c) lo spareggio su un attributo del modello (il tipo del profilo) | ✅ **Deciso da Tid il 2026-11-20.** **(a)**: «il ripiego non allarga mai» vale per preset e permessi, e la parità non può più nascere |
| Q29 | La forma delle date per chiave dal lato della preferenza: lo snapshot (scritto dal DB, Q1) e l'ignorato sono una colonna ciascuno; le chiavi della dashboard non sono elencate | Q1, Q3, Q4; BE7 | (a) Snapshot e ignorato diventano un JSONB `{chiave: data}` ciascuno, chiavi validate dal guard di forma (Q6); (b) una colonna per chiave e per dato | ✅ **Deciso da Tid il 2026-11-20.** **(a)**: le chiavi sono le stesse della `configurazione`, una chiave nuova non chiede DDL. Le chiavi della dashboard (`widget`, `dimensione_max`) si dichiarano nella decisione |
| Q30 | Che cosa garantisce «un preset per posto» quando `is_default` si ritira: gli indici `uq_*_default` sono `WHERE is_default = true` | Q26; §3.7 | (a) UNIQUE parziale `WHERE attivo` sulle stesse chiavi; lo scambio con la bozza si fa spegnendo il vecchio prima di accendere la bozza (un indice parziale non si differisce); (b) UNIQUE pieno, e la bozza vive altrove | ✅ **Deciso da Tid il 2026-11-20.** **(a)**, con l'ordine dello scambio scritto nella guida e nel messaggio dell'UNIQUE |
| Q31 | Lo stesso strumento per «il catalogo ha sempre un default» (U18, constraint trigger differito) e «la home non è mai vuota» (U32, presidio `dbops`) | Q20 (il motivo) | (a) Constraint trigger differito per tutti e due; (b) presidio `dbops` per tutti e due; (c) strumenti diversi, con la ragione sul modello scritta | ✅ **Deciso da Tid il 2026-11-20.** **(a)**: il differito risolve i passaggi intermedi, e dopo Q19 tutti e due i cataloghi li scrive solo l'owner |
| Q32 | Una vista che perde colonne (DDL sulla vista), il caso di U27 che Q16 non copre | Q16 | (a) Un presidio `dbops` che confronta le colonne di ogni lista con la sua relazione; (b) limite accettato, dichiarato nella guida, e resta il pgTAP sul seed | ✅ **Deciso da Tid il 2026-11-20.** **(a)**: copre le liste create dall'app, che il pgTAP sul seed non vede |
| Q33 | La sede di «la data del contenuto si sposta solo se il contenuto cambia», oggi violata dal DELETE + INSERT identico del BE (BE3) | BE3 | (a) Nel DB: ~~il trigger delle righe del preset passa per istruzione, con le transition table, e confronta l'insieme vecchio col nuovo~~ (il mezzo non regge: Q37); (b) il BE fa il diff | ✅ **Deciso da Tid il 2026-11-20.** **(a)**: la regola vale per ogni scrittore; BE3 si ritira. Il mezzo è quello di Q37 |
| Q34 | Chi traduce in codice il campo sorgente che il FE usa come `col` (Q7) | Q7; BE20 | (a) Il guard di forma rifiuta un `col` che non è un codice della lista, e il BE traduce; (b) il guard traduce, riscrivendo il valore | ✅ **Deciso da Tid il 2026-11-20.** **(a)**: un guard non riscrive in silenzio ciò che riceve |
| Q35 | I residui senza decisione: BE9 (chi applica oggi l'ordinamento risolto); U38 (la variabile utente non numerica); U22 (le preferenze della lista spenta, e il messaggio alla riaccensione rifiutata da Q16) | Q13, Q16; BE9, U38 | Una risposta per voce | ✅ **Deciso da Tid il 2026-11-20.** BE9: lo verifica la sessione BE prima del giro 2 e la voce diventa una richiesta chiusa; U38: un codice d'errore dedicato, non il 22P02; U22: le preferenze restano e si sospendono con la lista, la riaccensione rifiutata nomina le colonne orfane |
| Q36 | La dimensione del giro 1: U1-U9, Q26, il cambio di modello di Q4, quattro ricadute BE | Q24 | (a) Giro 1a (z90, snapshot, `preset_base`, Q28, `is_default` e Q30) e giro 1b (date per chiave, Q29, esito «base cambiata»); (b) un giro solo | ✅ **Deciso da Tid il 2026-11-20.** **(a)**: due apply più piccoli, e 1b parte con la forma di Q29 già decisa |
| Q37 | La sede di «la data si sposta solo se la composizione cambia»: la forma di Q33 (trigger per istruzione con le transition table) non vede il DELETE + INSERT come un'operazione sola, e un constraint trigger differito esiste solo per riga (provato il 2026-11-20, §3.1-ter) | **Riapre Q33** (2026-11-20): ne tiene la sede (il DB) e cambia il mezzo | (a) Un'impronta della composizione sul preset (`composizione_impronta`, dal BB `ui.fn_preset_impronta`) e un constraint trigger differito per riga: a fine transazione la data si sposta solo se l'impronta è cambiata; (b) il diff lo fa il BE (l'opzione (b) di Q33, BE3 torna aperta); (c) il BE scrive con un `MERGE` che tocca solo le righe diverse: è (b) con un altro strumento | ✅ **Deciso da Tid il 2026-11-20, come raccomandata:** **(a)**: la regola vale per ogni scrittore, come voleva Q33, e toglie anche la personalizzazione finta del seed. Costo: una colonna di stato derivato e un trigger che scatta al commit |
| Q38 | L'ignorato del banner, ora che lo snapshot lo scrive il DB: il flag dipende solo dal più recente fra snapshot e ignorato, e «Ignora» può essere un riallineamento (§3.1-ter) | **Riapre Q29** (2026-11-20) per la sola parte dell'ignorato; Q1 e Q3 restano | (a) `preset_aggiornato_ignored_at` si ritira dalle due preferenze; «Ignora» è una scrittura che nomina `preset_base_id`, e il trigger riallinea lo snapshot; le righe di oggi convertono lo snapshot a `max(snapshot, ignorato)`; (b) come Q29: anche l'ignorato diventa `jsonb` per chiave, e lo scrive il BE | ✅ **Deciso da Tid il 2026-11-20, come raccomandata:** **(a)**: una colonna in meno, nessun JSONB scritto dall'app da validare (la validazione di Q29 aspetterebbe il guard di forma del giro 2), e BE7 si riduce a una scrittura che il BE già sa fare |
| Q39 | La forma della data per chiave dal lato del preset (Q4 la vuole per chiave, Q29 dà la forma solo per la preferenza) | **Completa Q4** | (a) `contenuto_aggiornato_il` resta col suo nome e diventa `jsonb` `{chiave: data}`, con le chiavi della `configurazione`; (b) una colonna per chiave (`colonne_aggiornate_il`, `ordinamento_aggiornato_il`, …) | ✅ **Deciso da Tid il 2026-11-20, come raccomandata:** **(a)**: le chiavi sono quelle della preferenza e dello snapshot, così il confronto è chiave contro chiave; una funzione sola regge le due tabelle; la riga 5 del registro del seed non cambia. Il nome dice ancora «una data»: lo dichiara il COMMENT |
| Q40 | Il campo sorgente che il FE manda come `col`, quando due colonne della stessa lista hanno lo stesso `campo_sorgente`: il modello lo ammette, e la traduzione del BE (Q34) non sa quale colonna sia (§3.2-bis) | **Completa Q34** | (a) Un UNIQUE parziale `(lista_id, campo_sorgente)` sulle colonne con il campo valorizzato: il campo dice sempre una colonna, e la traduzione è una funzione; (b) il FE manda il codice (lo ha, dalle colonne risolte) e la traduzione del BE si ritira: Q34 resta per il guard, cambia chi scrive; (c) la traduzione rifiuta il campo ambiguo | ⏳ **Aperta.** Raccomandata **(b)** se la verifica di BE9 dice che l'ordinamento passa dal FE al BE per codice senza costi; altrimenti **(a)**. (c) lascia un caso del modello senza risposta |
| Q41 | La sede dei legami di U14 sulle composizioni: `lista_preset_colonna` e `dashboard_preset_widget` non portano la lista né la dashboard, e una FK composita le chiede | U14, Q8 | (a) Una colonna `lista_id` (`dashboard_id`) sulla composizione, scritta dal DB dal preset, e le FK composite verso il preset, la colonna e il pool: il legame vale per costruzione da tutti e due i lati (anche un cambio di `lista_id` della colonna); (b) un guard sulla composizione e un lucchetto su `lista_colonna.lista_id`: nessuna colonna in più, ma ogni lato ha il suo trigger | ⏳ **Aperta.** Raccomandata **(a)**: un vincolo non ha un lato dimenticato; il costo è una colonna derivata per tabella, che il BE non scrive |
| Q42 | Il codice di una voce della preferenza (o di `col`) al guard di forma: una colonna della lista in qualsiasi stato, o solo accesa; per la dashboard un widget del pool, o un widget qualsiasi | Q6, Q34 | (a) Della lista in qualsiasi stato, e del pool: una colonna spenta si sospende e torna (Q13), e la preferenza che la nomina resta valida; il resolver già la salta; (b) solo accesa: una preferenza scritta prima che la colonna si spenga viene rifiutata alla prima riscrittura | ⏳ **Aperta.** Raccomandata **(a)** |

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
