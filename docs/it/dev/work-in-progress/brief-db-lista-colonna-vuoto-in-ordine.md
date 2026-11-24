# Brief DB — Dove va il vuoto quando una lista ordina: si dichiara in `ui.lista_colonna`

## ⏭️ Chi riparte — aggiornato al 2026-11-24 (giro BE/FE fatto; D-5 decisa, tocca alla sessione DB, §8.3)

**Riparte: la sessione DB, col passo 5 (§8.3): Tid ha detto sì a D-5 il 2026-11-24.** Il giro BE/FE di §5 e §5.1 è fatto (§8, 2026-11-24):
il BE legge la dichiarazione dal catalogo e la applica nel BB dell'ordinamento, i `COALESCE` delle whitelist sono
ritirati, le colonne che la whitelist dimenticava (lotti, flussi e pratiche: tre, non quattro, §8.2) ordinano il
vuoto come il massimo. Resta fuori una colonna che §3.4
dava per assente dal catalogo e che invece c'è: `giorni_alla_scadenza` (righe 1157 e 1164). Il BE la tiene col suo
`COALESCE` finché il seed non la dichiara.

| # | Chi | Che cosa | Dove | Aspetta |
|---|---|---|---|---|
| 0 | Sessione DB | ✅ Analisi critica (2026-11-24): fatti verificati, risposta a §6, forma, vincolo, sede di lettura, un buco in §5 | §7 | — |
| 0b | Tid | ✅ Le decisioni D-1 … D-4 (2026-11-24) | §7.6 | — |
| 1 | Sessione DB | ✅ La colonna nuova, il seed, il registro del primo impianto, COMMENT, pgTAP, guide e `manual/`; provato sullo scratch (2026-11-24) | §7.7 | — |
| 2 | Tid | ✅ Apply, `ci_apply`, pgTAP `test-lista-colonna-vuoto-ordinato-come-massimo-v1` come app: verde (2026-11-24) | §7.7 | — |
| 3 | Team BE/FE | ✅ Le ricadute di §5 e §5.1: lettura dal catalogo, `sql_order_direction`, ritiro dei `COALESCE`, presidi, vincolo nella mappa, D-4 (2026-11-24) | §8 | — |
| 4 | Tid | ✅ D-5: `giorni_alla_scadenza` (righe 1157 e 1164) si dichiara «vuoto come il massimo» — **sì** (2026-11-24) | §8.3 | — |
| 5 | Sessione DB | `t` sulle righe 1157 e 1164 del CSV di `ui.lista_colonna`, il pgTAP del giro allineato; poi l'apply di Tid | §8.3 | — |
| 6 | Team BE/FE | Ritira `_SQL_GIORNI_SENZA_SCADENZA` e la voce di `_DEBITO_SENTINELLA` (il presidio diventa rosso da solo all'apply del passo 5) | §8.3 | 5 |

Decisioni aperte di Tid: nessuna (D-5 decisa il 2026-11-24, §8.3). Da committare: il giro DB di §7.7 (se non già fatto) e il giro BE/FE di §8.1.
Il brief si archivia quando il passo 6 è chiuso.

**Brief vicini verificati** (2026-11-24): `brief-db-revisione-ui` tocca lo schema `ui` (documentazione, difetti, metadati) ed è alla chiusura; non tratta l'ordinamento delle liste né `ui.lista_colonna` come sede di una regola di ordinamento: non basta, e non va fuso. Nessun altro brief aperto su ordinamento, `NULLS` o `COALESCE` di whitelist.
**Guide verificate** (`guide_coinvolte.py --oggetti ui.lista_colonna`): [configurazione-liste.md](../../guide/configurazione-liste.md) — coerente (non descrive dove va il vuoto quando una lista ordina); dopo l'apply è **guida indietro** e si aggiorna (§4, punto 6).
Allargate dalla sessione DB il 2026-11-24 a tutti gli oggetti del brief: l'esito per guida è in §7.8; quelle del giro BE
in §8.5.

---

## 1. Il problema

Quando una lista ordina per una colonna che ha righe vuote, qualcuno deve decidere dove vanno i vuoti. Oggi lo decidono
due regole, entrambe nel BE:

- **la regola generale**: il vuoto vale come il **minimo** (`sql_order_direction`: `ASC NULLS FIRST` /
  `DESC NULLS LAST`, decisione di Tid del 2026-07-19). È il caso del «non ancora»: il numero di una bozza, una data di
  evasione che non è ancora arrivata;
- **l'eccezione**: su una fine validità il vuoto vuol dire «non scade mai», quindi vale come il **massimo**. È scritta a
  mano dentro le whitelist di ordinamento, come `COALESCE(col, 'infinity'::date)` (decisione di Tid del 2026-08-01).

L'eccezione è un **fatto della colonna** (cosa vuol dire il vuoto lì), ma sta nel codice delle query. Si vede dove
diverge (§3.1): quattro colonne in cui il vuoto vuol dire «non scade» non hanno il `COALESCE` nella whitelist, quindi i
loro vuoti vanno ordinati come il minimo, cioè al contrario di quello che vogliono dire.

## 2. Le decisioni di Tid (2026-11-24)

1. **Il default resta il minimo.** Il vuoto è «non ancora» quasi sempre.
2. **L'eccezione «vuoto = massimo» si dichiara nel catalogo, in `ui.lista_colonna`**, al posto dei `COALESCE` scritti a
   mano nel BE. Il BE la legge e la applica da sé.
3. Fuori da questo brief, stesso giorno: la regola «le date partono decrescenti» è ritirata, nel FE e nel BE
   (`colonne_desc` / `e_chiave_data`). Non tocca il DB, ma spiega perché qui si parla solo di **dove va il vuoto** e non
   del verso di partenza.

## 3. Le colonne da dichiarare (censimento del 2026-11-24)

Il censimento serve a trovare le divergenze, non a decidere la regola: la regola è quella di §2 e vale per ogni colonna
in cui il vuoto vuol dire «non finisce». Per ogni colonna si è verificato sul DB (2026-11-24) che la colonna di origine
può essere vuota, e il significato del vuoto dal COMMENT della colonna, dall'etichetta del catalogo o dal modello.

### 3.1 Il seed: `true` su queste 13 righe di `ui.lista_colonna`

| `lista_colonna.id` | Lista | `campo_sorgente` | Colonna di origine | Il vuoto vuol dire | Oggi nel BE |
|---|---|---|---|---|---|
| 45 | `vendite.contratti` | `valido_al` | `vendite.contratti.valido_al` | contratto senza scadenza | `COALESCE` ✅ |
| 67 | `vendite.preventivi` | `validita_al` | `vendite.preventivi.validita_al` | «NULL non scade mai» (`script.fn_check_preventivo_accettabile`) | `COALESCE` ✅ |
| 87 | `vendite.offerte` | `validita_al` | `vendite.offerte_commerciali.validita_al` | come il preventivo | `COALESCE` ✅ |
| 1154 | `vendite.listini_versioni` | `valido_al` | `vendite.listini_versioni.valido_al` | versione aperta (etichetta) | ❌ **divergenza** |
| 1053 | `catalogo.articolo_componenti` | `valido_al` | `catalogo.articoli_componenti.valido_al` | componente senza fine | `COALESCE` ✅ |
| 297 | `catalogo.conversioni_uom` | `valido_al` | `catalogo.unita_misura_conversioni.valido_al` | senza scadenza (etichetta) | `COALESCE` ✅ |
| 376 | `anagrafiche.categorie_clienti_listini` | `valido_al` | `anagrafiche.categorie_clienti_listini.valido_al` | senza scadenza (etichetta) | `COALESCE` ✅ |
| 343 | `anagrafiche.operatori` | `valido_al` | `anagrafiche.risorse_umane.valido_al` | identità senza scadenza (etichetta) | `COALESCE` ✅ |
| 246 | `config.tipi_ruolo_tipi_indirizzo` | `valido_al` | `config.tipi_ruolo_tipi_indirizzo.valido_al` | regola senza fine | `COALESCE` ✅ |
| 974 | `documenti.template_versioni` | `valido_al` | `documenti.template_documenti_versioni.valido_al` | senza scadenza (etichetta) | `COALESCE` ✅ |
| 924 | `magazzino.lotti` | `data_scadenza` | `magazzino.lotti.data_scadenza` | «NULL = non scade» (COMMENT) | ❌ **divergenza** |
| 957 | `pratiche.flussi` | `data_scadenza` | `pratiche.flussi.data_scadenza` | nessuna scadenza (etichetta) | ❌ **divergenza** |
| 255 | `pratiche.pratiche` | `data_scadenza` | `pratiche.pratiche.data_scadenza` | nessuna scadenza prevista | ❌ **divergenza** |

⚠️ La sessione DB verifica la colonna di origine nella vista della lista, se la vista la riprende da un'altra tabella:
qui è indicata la tabella che la scrive.

### 3.2 Correzioni di testo che il censimento ha trovato

- **`pratiche.pratiche.data_scadenza` e `pratiche.flussi.data_scadenza`**: il COMMENT dice solo «Scadenza prevista»
  e non dice cosa vuol dire il vuoto. Va scritto («NULL = nessuna scadenza»), come in `magazzino.lotti`.
- **`vendite.promo_articoli` (riga 304)**: l'etichetta estesa dice «vuoto significa senza scadenza», ma
  `vendite.promo_articoli.valido_al` è **NOT NULL**. L'etichetta va corretta, e la riga **non** si dichiara.

### 3.3 Esclusi, e perché

- **Le scadenze delle rate** (`pagamenti.rate` 754, `pagamenti.rate_fuori_capienza` 597, `pagamenti.distinta_righe`
  775): vengono da `vendite.fatture_scadenze.data_scadenza`, che è NOT NULL. Il vuoto non c'è.
- **Le inizio validità** (`*_dal`): il vuoto vuol dire «da sempre», cioè il minimo, che è già il default. Due whitelist
  del BE hanno `COALESCE(col, '-infinity'::date)` e danno lo stesso ordine del default: il BE li toglie, senza
  dichiarazione.

### 3.4 Fuori dal seed: il BE ordina, ma il catalogo non ha la colonna

> ⚠️ Corretto dal giro BE (§8.2, 2026-11-24): `giorni_alla_scadenza` **è** una colonna del catalogo. Vedi §8.3.

- **Gli asset documentali** (`documenti.template_asset`): la whitelist del BE ordina per `valido_al` con il `COALESCE`
  (`ASSET_ORDER_COLUMNS` in `documenti_repository.py`), ma la lista di catalogo non ha la colonna, quindi il FE non la
  può chiedere. Il team BE la toglie dalla whitelist. Se Tid vuole la colonna a video, la sessione DB la aggiunge al
  catalogo con la dichiarazione a `true` (`documenti.template_asset.valido_al`: «NULL = senza fine», dal COMMENT).
- **I giorni rimanenti dei listini** (`giorni_rimanenti`, il vuoto è «non in scadenza», oggi `2147483647` in
  `listini_repository.py`): non sono una colonna del catalogo. Il team BE ne fa il censimento con le ricadute di §5.

## 4. La richiesta alla sessione DB

1. **Una colonna nuova in `ui.lista_colonna`** che dice dove va il vuoto quando la lista ordina per quella colonna.
   Proposta: `vuoto_ordinato_come_massimo boolean NOT NULL DEFAULT false` (`false` = il default, il minimo). La forma
   (boolean o vocabolario) e il nome li decide la sessione DB secondo le linee guida. Il default deve essere il minimo:
   le colonne che non dicono niente restano come oggi.
2. **Il seed**: `true` sulle 13 righe di §3.1; le correzioni di testo di §3.2.
3. **Il COMMENT** della colonna: cosa vuol dire, e che vale per l'ordinamento della lista, non per i filtri.
4. **Il pgTAP**: il default, il vincolo se ce n'è uno (per esempio: la dichiarazione ha senso solo su una colonna
   ordinabile), e le righe del seed.
5. **Dove il BE la legge**: la superficie di lettura che il BE usa per il catalogo delle colonne
   (`UiRepository.list_colonne_by_codice`, o `ui.fn_resolve_lista_config` se la sessione DB preferisce esporla da lì).
   Il brief dice quale, così il BE la legge da un posto solo.
6. Aggiornare la guida [configurazione-liste.md](../../guide/configurazione-liste.md) e la pagina `manual/` della
   tabella, se c'è.

## 5. Le ricadute sul BE (team BE/FE, dopo l'apply)

Le fa il team BE/FE, su `dev/backend-tid`, dopo l'apply. La sessione DB non tocca `backend/`.

1. `sql_order_direction` impara il caso «vuoto = massimo»: `ASC NULLS LAST` / `DESC NULLS FIRST`. Così vale per ogni
   tipo, senza `COALESCE` e senza un valore «infinito» per tipo.
2. `sql_order_clause` riceve dal catalogo, per la lista che ordina, l'insieme delle colonne dichiarate. Le view
   dichiarano già il loro `lista_codice`: la lettura passa di lì.
3. Si tolgono i `COALESCE(…, 'infinity')` e `COALESCE(…, '-infinity')` dalle whitelist e il valore
   `_SQL_GIORNI_SENZA_SCADENZA`, con i test che li asseriscono. Restano solo dove non sono ordinamento di lista (per
   esempio il filtro «non scaduto» in `pagamenti_repository.py`, che è un `WHERE`).
4. Un presidio: una colonna dichiarata nel catalogo e ordinata dal BE senza la dichiarazione è rossa.

⚠️ Una lista che il BE ordina **senza** catalogo (nessuna riga in `ui.lista_definizione`) non può leggere la
dichiarazione. Il team BE ne fa il censimento quando scrive il punto 2, e porta a Tid i casi che restano.

### 5.1 Dalla sessione DB, dopo le decisioni (2026-11-24)

1. **Dove si legge**: `ui.lista_colonna.vuoto_ordinato_come_massimo`, dalla lettura del catalogo che il BE fa già
   (`UiRepository.list_colonne_by_codice`). Non da `ui.fn_resolve_lista_config` (§7.7).
2. **Il vincolo nuovo** `chk_ui_lista_colonna_vuoto_massimo_con_campo` arriva come violazione di vincolo, come gli altri
   `CHECK` di `ui.lista_colonna` che il BE traduce per nome: va nella sua mappa. Dal drawer non lo si raggiunge (la
   colonna non c'è, D-1), ma una colonna dell'installazione creata con il flag e senza campo sì.
3. **D-4 no**: la lista degli asset documentali non riceve la colonna `valido_al`; `valido_al` esce da
   `ASSET_ORDER_COLUMNS` (§3.4).
4. **D-1, il drawer non cambia**: la colonna non entra nel drawer «Catalogo colonne». Su una colonna nata dal seed
   l'installazione non la può cambiare (`E_SEED_COLONNA_DEL_SOFTWARE`): un payload del BE che la scrivesse su una
   riga di seed sarebbe rifiutato.

## 6. Domanda aperta per la sessione DB

> ⚠️ Risposta della sessione DB in §7.2 (2026-11-24): la sede resta `ui.lista_colonna`, con un presidio su `valido_al`.

Va bene che la dichiarazione stia sulla **colonna della lista** (`ui.lista_colonna`) e non sulla **colonna della
tabella** (un COMMENT o un metadato sullo schema di dominio)? Il significato del vuoto è del dato, e la stessa colonna
compare in più liste: con la dichiarazione per lista, due liste dello stesso dato potrebbero dichiarare due cose
diverse. Tid ha scelto `ui.lista_colonna`. Se la sessione DB vede un motivo di modello per l'altra sede, lo porta a Tid
prima di scrivere.

## 7. Analisi critica della sessione DB (2026-11-24)

### 7.1 Che cosa regge, verificato

- **Le 13 righe di §3.1** esistono nel seed (`80_data/sql/ui/lista_colonna.csv`), con il `campo_sorgente` indicato,
  `ordinabile = t` e `attivo = t`. Le colonne di origine sono nullable sulla doc auto-generata; `vendite.promo_articoli.valido_al`
  è `NOT NULL`, come dice §3.2.
- **Le cinque liste con una vista** (contratti, preventivi, offerte, componenti, conversioni) espongono la colonna così
  com'è, senza `COALESCE`: il vuoto arriva alla lista.
- **Le altre otto liste non hanno `vista_sql`**: le righe le compone il repository del BE, e la colonna di origine la
  dichiara il BE. La sessione DB non la può verificare (non legge `backend/`): per quelle righe vale il censimento
  del BE.
- **Il censimento è chiuso** sul nome: fra le colonne di data del catalogo che finiscono in `_al`, `scadenza` o `fine`,
  fuori dal seed restano le tre rate (`NOT NULL` all'origine, escluse a ragione), la 304 (§3.2) e la 1099
  `periodo_al`, che non è ordinabile.
- **Il modello**: completa due decisioni, non ne revoca. Il default «vuoto come il minimo» è del 2026-07-19 (nato sui
  `numero` NULL delle bozze DDT, oggi `sql_order_direction`: lo racconta
  `work-done/2026/brief-db-liste-drawer-lotto.md`); l'eccezione «vuoto come il massimo» era del 2026-08-01, scritta come
  `COALESCE` nelle whitelist. Il brief sposta l'eccezione dal codice al catalogo.
- **`validita_al` dei preventivi «dice due cose»** (registro dei residui): l'altra cosa è il ripiego della competenza nel
  push e nella dashboard, non la lista. Sulla lista vale la scadenza («Data fine validità»): il residuo non interferisce.

### 7.2 La risposta a §6: la sede resta `ui.lista_colonna`

Il motivo è nel modello, non nei numeri: una lista **può** non avere una vista (`vista_sql` è facoltativa, e la guida
delle liste lo prevede), e allora la colonna che il BE ordina è una proiezione del repository. Dalla lista alla colonna
di una tabella non c'è un legame scritto, nemmeno per le colonne calcolate di una vista. Una dichiarazione sulla tabella
il BE non la saprebbe trovare, e il DB non saprebbe controllarla.

Il rischio di §6 (due liste dello stesso dato che dicono cose diverse) ha però una risposta strutturale per la colonna
più frequente: **`valido_al` ha già un significato in tutto il database**. Le linee guida SQL (§7b) dicono
«`valido_al` NULL = aperto», e la colonna `validita` lo scrive come `COALESCE(valido_al, 'infinity')`. Un presidio
pgTAP può quindi chiedere che ogni colonna accesa di catalogo con `campo_sorgente = 'valido_al'` sia dichiarata. È la
convenzione che diventa controllo, non una misura. Le altre (`validita_al`, `data_scadenza`) non hanno una convenzione
comune e restano dichiarate una per una. Vedi D-2.

### 7.3 La forma: un booleano basta

Il vuoto in un ordinamento ha due posti possibili, il minimo e il massimo: non c'è un terzo significato da prevedere, e
un vocabolario per due valori sarebbe un booleano travestito. Il nome `vuoto_ordinato_come_massimo` dice l'effetto e
non il significato («senza fine»), ed è giusto così: la colonna governa l'ordinamento, non i filtri (§4.3). Proposta
accettata, `boolean NOT NULL DEFAULT false`.

### 7.4 Il vincolo: dal campo sorgente, non da `ordinabile`

§4.4 suggerisce «la dichiarazione ha senso solo su una colonna ordinabile». Non lo legherei a `ordinabile`: il flag
dice che cosa vuol dire il vuoto del dato, `ordinabile` dice che cosa la lista permette. Chi spegne l'ordinamento di
una colonna non cambia il significato del suo vuoto, e con un `CHECK` su `ordinabile` dovrebbe spegnere anche la
dichiarazione, che tornerebbe da riscrivere alla riaccensione. Il vincolo che regge è un altro: **una colonna senza
campo sorgente** (un'azione, una cella composta) **non ha un vuoto da ordinare**. Proposta:
`CHECK (NOT vuoto_ordinato_come_massimo OR campo_sorgente IS NOT NULL)`. Vedi D-3.

### 7.5 Un buco in §5: il drawer del catalogo colonne

La guida delle liste (§5.2, «Catalogo colonne») ha un drawer che crea e modifica le colonne, con i flag di
comportamento. §5 non dice se il flag nuovo ci entra. C'è un precedente: la **priorità di ritiro** non è nel drawer,
«si regola nel seed del catalogo». Il flag nuovo è della stessa specie, un fatto del software e non una preferenza di
configurazione: proposta, **solo dal seed**, e la guida lo dice come per la priorità. Una colonna su `valido_al`
creata dal drawer nascerebbe `false`: la vede il presidio di §7.2, che legge la tabella e non il CSV. Vedi D-1.

### 7.6 Le decisioni di Tid

| # | Domanda | Proposta della sessione DB | Decisione di Tid (2026-11-24) |
|---|---|---|---|
| D-1 | Il flag entra nel drawer «Catalogo colonne», o si scrive solo dal seed? | **Solo dal seed**, come la priorità (§7.5) | ✅ **solo dal seed** |
| D-2 | Il presidio su `valido_al` (§7.2) | **Sì**: ogni colonna accesa con `campo_sorgente = 'valido_al'` è dichiarata. Allora anche la 304 va a `true`: su una colonna `NOT NULL` il flag non cambia niente, e il presidio non ha eccezioni da tenere. In alternativa, la 304 resta `false` come eccezione dichiarata nel test | ✅ **sì**, la 304 a `true` |
| D-3 | Il vincolo (§7.4) | `CHECK` sul campo sorgente, non su `ordinabile` | ✅ **sì** |
| D-4 | §3.4: la colonna `valido_al` della lista degli asset documentali | Di Tid. Se sì, nasce già dichiarata, e la guida `documenti-e-stampe` entra fra le verificate | ✅ **no**: la colonna non entra nel catalogo, il team BE toglie `valido_al` da `ASSET_ORDER_COLUMNS` (§3.4) |

### 7.7 Il giro della sessione DB — scritto il 2026-11-24

- [x] `00_schema/ui/20261123-65-alter-ui-lista-colonna-vuoto-ordinato-come-massimo`: la colonna (`boolean NOT NULL
  DEFAULT false`), il `COMMENT` (che cosa vuol dire, che vale per l'ordinamento e non per i filtri, la convenzione di
  `valido_al`), `chk_ui_lista_colonna_vuoto_massimo_con_campo` col suo `COMMENT`.
- [x] `00_schema/pratiche/20261123-66-comment-pratiche-flussi-data-scadenza-nessuna-scadenza`: i due `COMMENT`
  («NULL = nessuna scadenza»).
- [x] `80_data`, il CSV di `ui.lista_colonna`: la colonna in coda su tutte le righe (26 campi, nessun `\r`), `t` sulle
  tredici righe di §3.1 e sulla 304 (D-2), l'etichetta estesa della 304 senza «vuoto significa senza scadenza».
- [x] `80_data`, **i due caricatori** dello stesso CSV, `20260507-07` e `20260806-15` (tutti e due `runOnChange` con
  l'elenco delle colonne): la voce `vuoto_ordinato_come_massimo` (`BOOLEAN`). È lo stesso percorso di `origine_campo`
  (§11.2 delle linee guida SQL). ⚠️ Il brief nominava solo il secondo.
- [x] `80_data`, **il registro del primo impianto** (`automazione_seed_primo_impianto.csv`, riga 4): la colonna fra
  quelle del software (D-1), col motivo. ⚠️ Non era nel brief, ed era obbligato: `ui.lista_colonna` è iscritta nella
  forma per colonna, dove ogni colonna sta in uno dei due elenchi; una colonna non classificata ferma il giro del
  trigger su quella tabella (pagina `manual/` del registro).
- [x] pgTAP `db/pgtap/ui/test-lista-colonna-vuoto-ordinato-come-massimo-v1.sql` (plan 11): il default, il vincolo, la
  dichiarazione indipendente da `ordinabile`, le quattordici righe per lista e codice, la convenzione di `valido_al`
  (D-2), la colonna del software nel registro e il rifiuto dell'app (D-1), i due `COMMENT`.
- [x] **La sede di lettura per il BE (§4.5)**: la tabella, dalla lettura che il BE fa già del catalogo
  (`list_colonne_by_codice`). Non `ui.fn_resolve_lista_config`: quella risolve come si presenta la lista a un utente
  (preferenza, preset, permessi, visibilità), e l'ordinamento ha bisogno del catalogo della lista. Metterci il flag
  mescolerebbe le due cose, e la funzione gira a ogni apertura. Nessun oggetto nuovo.
- [x] Le guide e la pagina `manual/` (§7.8): `configurazione-liste` §2.2, §5.2 e l'intestazione delle colonne;
  `gestione-pratiche`, la tabella delle colonne; `manual/lista_colonna`, la sezione «Dove va il vuoto quando la lista
  ordina», il vincolo e il test. Valgono dall'apply.
- [x] L'apply su dbdev (Tid, 2026-11-24): migrate, poi `ci_apply` (rimonta il trigger del seed col registro nuovo),
  poi il pgTAP **come app**: verde, caso 9 compreso. La doc auto-generata di `ui.lista_colonna` è rigenerata (la
  colonna, il vincolo, il trigger del seed con l'elenco nuovo).

**La prova sullo scratch (2026-11-24, `prova_changeset.py`, transazione in `ROLLBACK`, come owner).** I due changeSet:
preCondition vere, estratto eseguito per intero, catalogo identico dopo. Il pgTAP: 7/11 coi soli changeSet (i casi
6-9 vogliono il seed, che lo script non carica); 10/11 col seed simulato da un estratto di prova nello scratchpad (gli
stessi valori del CSV e del registro come `UPDATE`, più il runner del seed su `ui`). Il caso 9 resta rosso **da owner
per costruzione**: la sessione del proprietario è il migratore, cioè il software, che la colonna la scrive. Come app è
il caso da guardare. `test-seed-primo-impianto-ui-installazione-v1` uguale prima e dopo (13/19 da owner, i 6 rossi
sono di perimetro e preesistenti), quindi nessuna divergenza nuova del registro. Il caricatore vero non è provato:
il CSV è controllato campo per campo (1165 righe, 26 campi, 14 `t`, nessuna dichiarata senza campo, nessuna `valido_al`
accesa fuori).

**Pre-commit sui file del giro:** verde, tranne `check-i18n-keys`, che segnala
`anagrafiche.soggetti.cambio_natura_blocco.verso_nessuna`: è del giro delle anagrafiche dell'altra sessione
(`fn_check_cambio_natura_soggetto`), non di questo.

### 7.8 Guide e note di dominio (`guide_coinvolte.py --oggetti`, 2026-11-24)

Oggetti: `ui.lista_colonna`, `ui.fn_resolve_lista_config`, `pratiche.pratiche`, `pratiche.flussi`, `vendite.promo_articoli`,
`magazzino.lotti`, `documenti.template_asset`.

| Guida | Esito |
|---|---|
| `configurazione-liste` | coerente; **guida indietro** dopo l'apply: i flag di comportamento (§2.2) e il drawer (§5.2, come la priorità se D-1 dice «solo seed») |
| `gestione-pratiche` | coerente; **guida indietro** dopo il COMMENT: la tabella delle colonne dice solo «Scadenza prevista» |
| `gestione-listini` | coerente: la promo scade a `valido_al`; era l'etichetta della 304 a dire «vuoto» |
| `documenti-e-stampe` | coerente; entra in gioco solo se D-4 dice sì |
| `gestione-pratiche-configurazione`, `audit-e-tracciabilita`, `uso-di-obsoleto`, `risorse-umane-e-accessi` | nominano le tabelle delle pratiche per altro: non toccate |
| pagina `manual/` di `ui.lista_colonna` | **indietro** dopo l'apply: «Che cosa si può fare con la colonna» e l'elenco dei test |

Nessuna nota di dominio. **`magazzino.lotti` non lo cita nessuna guida**: è un concetto del dominio, quindi manca una
guida del magazzino o il «Vedi anche» di una guida esistente è incompleto. Lo decide Tid, fuori da questo brief.

## 8. Il giro del team BE/FE (2026-11-24)

### 8.1 Che cosa fa il BE

- **La lettura** (§4.5, §5.2): `fetch_colonne_vuoto_massimo(lista_codice)` in `apps/core/db/lista_catalogo_repository.py`
  legge i `campo_sorgente` delle colonne con `vuoto_ordinato_come_massimo`, senza filtro su `attivo` né su `ordinabile`
  (il flag dice che cosa vuol dire il vuoto del dato, §7.4). ⚠️ Non da `UiRepository.list_colonne_by_codice`, come §5.1.1
  indicava: la legge la base view, e `core` non importa `ui` (la stessa ragione delle altre letture del catalogo di quel
  modulo). La sede del dato resta una, la tabella.
- **Il percorso**: la base view di ogni porta, se ha `lista_codice`, registra nella richiesta la **lettura** (pigra, una
  per richiesta: `applica_vuoti_come_massimo`, come la misura di partenza). `sql_order_direction_lista`, la sede unica della
  direzione (la usa `sql_order_clause`), la consulta quando risolve una colonna, per la chiave chiesta o per quella che il
  `default` della lista nomina. Sulla colonna dichiarata `sql_order_direction(vuoto_massimo=True)` scrive `ASC NULLS LAST` /
  `DESC NULLS FIRST` (§5.1). Nessun repository cambia firma. ⛔ Ma la dichiarazione la riceve solo chi compone la direzione
  con `sql_order_direction_lista` (o `sql_order_clause`): cinque `ORDER BY` composti a mano chiamavano
  `sql_order_direction` diretto (eccedenze di pagamenti, code dei resi, giornale delle entità, fondi da decidere,
  audit di amm-software) e una colonna dichiarata domani su quelle liste sarebbe rimasta al minimo, senza errore.
  Portati sul BB dalla `/verifica` del 2026-11-24, con il presidio «nessuna chiamata diretta fuori dal BB». ⭐ Dalla `/verifica` del 2026-11-24 (Tid) la lettura sta
  **fuori** dal gate dell'utente autenticato: è un fatto del catalogo, e la riceve anche la lista letta da un anonimo
  dello shop. Ordinamento e misura di partenza restano dentro, perché dipendono da chi legge. Presidio:
  `test_anche_l_anonimo_riceve_la_dichiarazione` in `core/tests/api/test_vuoto_come_massimo.py`, provato a rovescio.
  Pagine `manual/` allineate lo stesso giorno: le liste che hanno cambiato ordine (lotti, pratiche, flussi; la promo no, `valido_al` è `NOT NULL`),
  i `COALESCE` citati come regola (tipi ruolo-tipi indirizzo, titoli IVA, operatori, conversioni UoM), `valido_al`
  tolto dagli asset.
- **Il ritiro** (§5.3): via i `COALESCE(…, 'infinity')` da contratti, preventivi, offerte, versioni di listino, componenti
  della distinta, conversioni UoM, categorie clienti-listini, operatori, tipi ruolo-tipi indirizzo, versioni dei template;
  via i due `'-infinity'` (preventivi `validita_dal`, tipi ruolo-tipi indirizzo `valido_dal`), che davano già il default.
  Restano dove non sono ordinamento di lista: il `WHERE` «non scaduto» di `pagamenti_repository.py` e il `daterange` di
  `listini_repository.py`. `titoli_iva_repository` passa da `COALESCE(valido_al,'infinity') DESC` a
  `valido_al DESC NULLS FIRST` nel suo `default_clause`: stesso ordine, senza valore «infinito». ⚠️ (Corretto dalla
  `/verifica` del 2026-11-24.) La lista di catalogo c'è, `anagrafiche.soggetto_titoli_iva` (62), ma `valido_al` non è
  una sua colonna: il catalogo non la può dichiarare, e la regola scritta nel default è legittima. Il presidio a regex
  cerca solo i `COALESCE` e non vede un `NULLS FIRST` scritto a mano: questo è l'unico, dichiarato qui.
- **D-4**: `valido_al` esce da `ASSET_ORDER_COLUMNS`.
- **Il vincolo nuovo** (§5.1.2): `chk_ui_lista_colonna_vuoto_massimo_con_campo` nella mappa `_CHECK_CONSTRAINTS` di
  `ListaColonnaAdminService`, sul campo `campo_sorgente`.
- **Il drawer** (§5.1.4, D-1): invariato.
- **I presidi** (§5.4): `core/tests/test_vuoto_come_massimo_seed.py` (senza DB): ogni lista che nel seed dichiara una
  colonna accesa e ordinabile è servita da una view con quel `lista_codice`, altrimenti la dichiarazione non arriva al BB;
  nessuna whitelist scrive `COALESCE(col, <sentinella>)`, con il registro di debito `_DEBITO_SENTINELLA` che deve calare.
  `core/tests/api/test_vuoto_come_massimo.py` (BB e base view, senza DB), `core/tests/db/test_vuoto_come_massimo_db.py`
  (catalogo → BB → righe costruite con `VALUES`, ordinate da PostgreSQL). I test che asserivano il `COALESCE` sono
  adeguati; `test_listini_in_scadenza_db` legge la dichiarazione dal catalogo vero.
- **Documentazione**: catalogo BB (partenza della lista, `sql_order_direction`, `sql_order_direction_lista`) con l'indice
  rigenerato; api.md, «Dove va il vuoto: lo dichiara il catalogo».

Prova (2026-11-24): i test del giro verdi, catena compresa sul DB di sviluppo (`ZEROERP_TEST_DB_E2E=1`); mypy a cricchetto
verde. La suite intera ha rossi che non sono di questo giro: i repository che chiedono `auth_user_id` e
`test_scope_senza_utente.py` sono del giro non committato di `brief-db-porte-aperte-dalla-sola-guc`; le due prove delle
policy d'errore (`E_DATI_SOCIETARI_*`) seguono il DB, avanti rispetto a git.

### 8.2 Correzioni al censimento di §3

- **1154 `vendite.listini_versioni`** non era divergente: la whitelist del BE aveva il `COALESCE`. Le divergenti vere erano
  tre (lotti, flussi, pratiche). Il seed resta giusto.
- **§3.4, `giorni_alla_scadenza`**: è una colonna del catalogo, sulla lista 27 (`vendite.listini`, riga 1164) e sulla 112
  (`vendite.listini_versioni`, riga 1157), `ordinabile = t`, oggi `vuoto_ordinato_come_massimo = f`.
- **§5, le liste ordinate senza catalogo** (il ⚠️): fuori da una view con `lista_codice` ordinano i tool dell'assistente
  (`ai_assistant/tools`). Fatto datato del 2026-11-24: ordinano per `data`, `valido_dal`, `codice`, `data_insert`, nessuna
  colonna dichiarata. Per regola, fuori da una lista vale il minimo: un tool che domani ordinasse per una fine validità
  non riceve la dichiarazione. Nessun caso da portare a Tid.

### 8.3 D-5: `giorni_alla_scadenza`

Il vuoto della colonna vuol dire «non in scadenza» (la versione ha un successore, o scade oltre il preavviso): nel BE è
già la scadenza **più lontana** (`COALESCE(giorni_rimanenti, 2147483647)`, `_SQL_GIORNI_SENZA_SCADENZA`, in tutte e due
le whitelist), cioè l'eccezione «vuoto come il massimo» scritta fuori dal catalogo, quella che §2.2 sposta nel catalogo.
Togliere il `COALESCE` senza la dichiarazione rovescerebbe l'ordine: il BE lo tiene, registrato come debito.

**Decisione di Tid (2026-11-24): sì**, `t` sulle righe 1157 e 1164. Non è «senza fine» alla lettera, ma per
l'ordinamento è lo stesso fatto: il vuoto sta oltre ogni valore.

**Richiesta alla sessione DB**: nel CSV di `ui.lista_colonna`, `vuoto_ordinato_come_massimo = t` sulle righe 1157
(`vendite.listini_versioni`) e 1164 (`vendite.listini`); il pgTAP `test-lista-colonna-vuoto-ordinato-come-massimo-v1`
conta le righe dichiarate per lista e codice, e va allineato (da quattordici a sedici). Fino all'apply il BE resta com'è
oggi, con la sentinella: chi cambia per primo è il DB.

Dopo l'apply il presidio `test_il_debito_della_sentinella_si_chiude_con_la_dichiarazione` diventa rosso: il team BE toglie
`_SQL_GIORNI_SENZA_SCADENZA`, i suoi test (`test_listini_in_scadenza_db`, `test_chi_non_scade_va_in_fondo_crescendo`
leggerà la dichiarazione come le versioni) e la voce del registro.

### 8.4 Garanzie ritirate

Nessuna: la whitelist dava la stessa proprietà («la fine vuota è la più lontana») che ora dà il catalogo, alle stesse
liste, per le richieste che passano da una view con `lista_codice`. Fuori da quelle (§8.2) il `COALESCE` valeva anche
per una chiamata interna; i lettori censiti non ordinano per una colonna dichiarata.

### 8.5 Guide (`guide_coinvolte.py`, 2026-11-24)

| Guida | Esito |
|---|---|
| `configurazione-liste` (§2.2, §5.2, intestazione delle colonne) | coerente: descrive già il comportamento che il BE ora ha |
| le altre restituite sui file di `core` (`automazione-db`, `risorse-umane-e-accessi`, `fatturazione`…) | nominano oggetti di quei file per altro: non toccate |

