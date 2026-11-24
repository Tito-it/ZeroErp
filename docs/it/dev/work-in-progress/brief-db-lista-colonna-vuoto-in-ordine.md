# Brief DB — Dove va il vuoto quando una lista ordina: si dichiara in `ui.lista_colonna`

## ⏭️ Chi riparte — aggiornato al 2026-11-24 (analisi critica della sessione DB)

**Riparte: la sessione DB, col giro di §7.7** (D-1 … D-4 decise da Tid il 2026-11-24, §7.6); i numeri dei changeSet li
dà Tid, perché un'altra sessione DB è attiva.
Poi il team BE/FE con le ricadute di §5, che **aspettano l'apply**: fino ad allora il BE resta com'è, con i `COALESCE`
scritti a mano nelle whitelist. Decisioni di Tid prese il 2026-11-24 (§2). La domanda di §6 ha la risposta della
sessione DB in §7.2.

| # | Chi | Che cosa | Dove | Aspetta |
|---|---|---|---|---|
| 0 | Sessione DB | ✅ Analisi critica (2026-11-24): fatti verificati, risposta a §6, forma, vincolo, sede di lettura, un buco in §5 | §7 | — |
| 0b | Tid | ✅ Le decisioni D-1 … D-4 (2026-11-24) | §7.6 | — |
| 1 | Sessione DB | La colonna nuova, il seed, le correzioni di testo, COMMENT, pgTAP, guide e `manual/` | §7.7 | il range dei numeri da Tid |
| 2 | Tid | Apply | — | 1 |
| 3 | Team BE/FE | Le ricadute: `sql_order_direction`, lettura dal catalogo, ritiro dei `COALESCE`, presidio, e il drawer (§7.5) | §5, §7.5 | 2 |

Decisioni aperte di Tid: nessuna; resta da dare il range dei due changeSet. Da committare: questo brief (§7).

**Brief vicini verificati** (2026-11-24): `brief-db-revisione-ui` tocca lo schema `ui` (documentazione, difetti, metadati) ed è alla chiusura; non tratta l'ordinamento delle liste né `ui.lista_colonna` come sede di una regola di ordinamento: non basta, e non va fuso. Nessun altro brief aperto su ordinamento, `NULLS` o `COALESCE` di whitelist.
**Guide verificate** (`guide_coinvolte.py --oggetti ui.lista_colonna`): [configurazione-liste.md](../../guide/configurazione-liste.md) — coerente (non descrive dove va il vuoto quando una lista ordina); dopo l'apply è **guida indietro** e si aggiorna (§4, punto 6).
Allargate dalla sessione DB il 2026-11-24 a tutti gli oggetti del brief: l'esito per guida è in §7.8.

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

### 7.7 Il giro della sessione DB, dopo le decisioni

1. `00_schema/ui`: la colonna, il `COMMENT` (che cosa vuol dire, che vale per l'ordinamento e non per i filtri), il `CHECK`.
2. `80_data`: la colonna nel CSV di `ui.lista_colonna` (su tutte le righe) e nell'elenco del caricatore
   `20260806-15-riancora-mirror-ui-lista-colonna` (`runOnChange: true`, lo stesso percorso di `origine_campo`); `true` sulle
   righe di §3.1 (e sulla 304, se D-2 dice sì); l'etichetta estesa della 304 corretta.
3. `00_schema/pratiche`: il `COMMENT` di `pratiche.pratiche.data_scadenza` e di `pratiche.flussi.data_scadenza`
   («NULL = nessuna scadenza»).
4. pgTAP in `db/pgtap/ui/`: il default, il `CHECK`, le righe dichiarate cercate per lista e codice (non per id), il
   presidio di D-2.
5. **La sede di lettura per il BE (§4.5)**: la tabella, dalla lettura che il BE fa già del catalogo
   (`list_colonne_by_codice`). Non `ui.fn_resolve_lista_config`: quella risolve come si presenta la lista a un utente
   (preferenza, preset, permessi, visibilità), e l'ordinamento ha bisogno del catalogo della lista. Metterci il flag
   mescolerebbe le due cose, e la funzione gira a ogni apertura.
6. ✅ Le guide e la pagina `manual/` (§7.8), scritte il 2026-11-24: `configurazione-liste` §2.2, §5.2 e l'intestazione
   delle colonne; `gestione-pratiche`, la tabella delle colonne; `manual/lista_colonna`, la sezione «Dove va il vuoto
   quando la lista ordina», il codice del vincolo e il test. Valgono dall'apply.

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
