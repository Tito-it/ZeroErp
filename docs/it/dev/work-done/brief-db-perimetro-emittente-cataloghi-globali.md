# Brief DB — I cataloghi globali che il seed non dichiara: `perimetro_emittente = false` manca a cinque liste

> Chi scrive: backend (`dev/backend-tid`), 2026-09-15.
> Origine: collaudo in-app di «Esegui ora» ([piano-be-fe-avvio-manuale-di-un-processo.md](piano-be-fe-avvio-manuale-di-un-processo.md)
> §4.4.2). Aprendo *Processi automatici* con **«Tutti gli emittenti»** nella
> combo, la lista è sbarrata dal cancello di perimetro («Scegli un emittente
> per continuare») — su un registro che un emittente non ce l'ha.
>
> **In una riga:** sei liste in più dichiarate `perimetro_emittente = false`
> nel seed. Nessuna funzione nuova. Più **cinque domande** su liste che una
> dimensione emittente ce l'hanno (§5) — ✅ **tutte decise da Tid il
> 2026-09-18**, in §5-bis, con il lavoro che ne discende (§7).
> ⛔ **E una decisione di metodo, sempre del 18-09 (§3-bis):** il valore NON
> sta più nel CSV laterale `lista_definizione_perimetro_emittente.csv` — quel
> tipo di seed è **deprecato**, «il rischio è troppo, si rischia
> disallineamento con i csv» — ma nella **colonna** di `lista_definizione.csv`,
> come `multi_emittente`. Il CSV laterale e il suo changeSet `20260902-02`
> sono **ritirati**.
>
> **Stato:** ✅ **CHIUSO e archiviato in `work-done/` il 2026-09-19.**
> Tre giri, tutti consegnati: **giro 1-2 (DB)** il 18-09 — sette globali a
> `perimetro_emittente = f` nella **colonna** di `lista_definizione.csv`,
> `operatori` e `lista_preset` certificate `multi_emittente`, colonne 872/873
> a catalogo, laterale ritirato, `20260918-28`, i sei laterali di
> `famiglie_documento` rientrati nel CSV unico (`b655ea6d4`, PR #1612);
> **giro 3 (BE/FE)** il 19-09 — `list_logs` proietta
> `emittente_ragione_sociale`, 872 accesa, «Riferimento» dei preset ristretta
> al profilo, i18n, presidio BE-1 nei due versi (`ecbff9efa`, PR #1616/#1617);
> **l'ultima riga DB** il 19-09 — `config.email_log` `multi_emittente = t` +
> elenco del test 5, provata con l'SQL reso da Liquibase dei due mirror e la
> mutazione «flag prima della colonna» (§8). **Applicato su dbdev e pgTAP
> verdi** (Tid, 19-09): i due `ui/` e `vendite/test-viste-dash-emittente-v1`.
> Il commit dell'ultima riga è di Tid.
>
> ⭐ **Cosa ne resta, da leggere altrove:** (1) la regola **«una tabella, un
> CSV»** è nel meccanismo condiviso — linee-guida-sql §11.2 e AGENTS.md §«I
> dati di `80_data` si cambiano dal CSV» — non qui; (2) l'ordine
> **colonna → flag** per certificare una lista `multi_emittente` è ora scritto
> nel test 5 del pgTAP, dove chi accende il flag deve venire a dichiararlo.
>
> 🔵 **Eredità, una riga BE non bloccante:** la ragione di `config.email_log`
> in `_ESENZIONI` (`test_perimetro_emittente_copertura.py`) dice ancora
> *«diario tecnico di sistema»* mentre il seed la certifica `multi_emittente`;
> va riscritta sullo stampo di `operatori`/`lista_preset` (§8, riquadro).
> Coerenza del registro, non un rosso: nessun cantiere da aprire, si fa al
> prossimo passaggio su quel file.

---

## 1. Il fatto, misurato il 2026-09-15 (dbdev, `fn_resolve_lista_config` via API)

Con un token **senza** `emittente_attivo_id` (la combo su «Tutti gli
emittenti»), super admin:

| Lista | `perimetro_emittente` | `multi_emittente` | `richiede_scelta_emittente` |
| --- | --- | --- | --- |
| `amm.processi` | true (default) | false | **true — sbarrata** |
| `anagrafiche.operatori` | true (default) | false | **true — sbarrata** |
| `anagrafiche.emittenti_fiscali` | true (default) | false | **true — sbarrata** |
| `ui.lista_definizione` | true (default) | false | **true — sbarrata** |
| `storico.audit_log` | true (default) | false | **true — sbarrata** |
| `vendite.famiglie_documento` | **false** (seed) | false | false — si entra |

Il super admin deve scegliere un emittente per vedere **l'elenco degli
emittenti**. La misura serve a trovare l'errore, non a disegnare: la regola è
già scritta, e sta nel commento della colonna stessa.

⚠️ Riletto il 2026-09-18 su dbdev: identico. Il brief era fermo dal 15-09,
zero passi lato DB (CSV a una riga, `databasechangelog` ai soli tre changeSet
del 02-09).

## 2. La regola c'è già: è il commento di `ui.lista_definizione.perimetro_emittente`

`00_schema/ui/20260902-01`, testuale: *«su un catalogo GLOBALE — le famiglie
di documento, **le liste tecniche di ui**, **i vocabolari di config** — non
c'è nessun emittente da dire, quindi il suo `false` è letteralmente vero e
l'effetto è sbagliato: la schermata chiede di scegliere un emittente prima di
entrare, e sbarra la strada proprio a chi ha lo scope più largo»*.

Il commento nomina **tre** famiglie; il seed (`20260902-02`,
`lista_definizione_perimetro_emittente.csv`) ne dichiara **una**: la riga
`vendite.famiglie_documento,false`. Le liste tecniche di `ui` e il registro dei
processi sono rimaste al default `true`, che è il verso prudente per una lista
**nuova** — non per una la cui natura è già stata scritta.

Il backend lo sa da mesi, ma nella sede sbagliata per questo effetto:
`apps/core/tests/test_perimetro_emittente_copertura.py::_ESENZIONI` motiva
l'assenza del cancello **sull'endpoint** (`AdminAPIView`) e per `amm.processi`
scrive *«registro di catalogo, senza perimetro emittente»*, per tre `ui.*`
*«nessun `emittente_fiscale_id` in tabella»*. Ma il cancello **del pannello**
lo calcola `richiede_scelta_emittente(...)` dai flag del seed
(`perimetro_emittente.py`, ramo 2: «la lista non ha un perimetro → non c'è
niente da scegliere»), e il seed dice il contrario del registro. Due sedi che
dicono due cose: la differenza si vede solo su «Tutti gli emittenti».

### 2.1 I due flag, in una frase ciascuno — perché il nome inganna

Sono flag della **lista**, non di chi la guarda e non di ciò che contiene:

* `perimetro_emittente = false` — *«nessuna riga di questa lista appartiene
  a un'azienda»*: catalogo del software. Si entra senza scegliere niente;
* `multi_emittente = true` — *«questa lista può mostrare righe di aziende
  DIVERSE insieme, perché ogni riga dichiara la sua»*. Il super admin su
  «Tutti» le vede tutte, con l'azienda accanto.

⚠️ `multi_emittente` **non** dice che l'operatore è multi-emittente: un
operatore ha **un** emittente, e l'unico attore multi-emittente è il super
admin (decisione Tid 2026-08-17, `fn_check_user_emittente_scope` passo 3).
Il 18-09 la domanda su `anagrafiche.operatori` è stata capita male proprio per
questo nome, e la §5 di questo brief parlava di *«scope n:m»* — corretto.

## 3. Cosa si chiede — sei liste in più a `false`

Nella colonna `perimetro_emittente` di `80_data/sql/ui/lista_definizione.csv`
(dal 18-09, §3-bis; fino ad allora nel CSV laterale), accanto a
`vendite.famiglie_documento`:

| `codice` | `perimetro_emittente` | Perché (verificato sul dbdev il 15-09: nessuna colonna `emittente_fiscale_id`) |
| --- | --- | --- |
| `amm.processi` | false | `dbops.processi` è catalogo del software: le righe valgono identiche su ogni installazione. Le identità un emittente ce l'hanno, ma stanno nel **dettaglio**, non nella lista |
| `ui.lista_definizione` | false | catalogo delle liste |
| `ui.lista_colonna` | false | catalogo delle colonne |
| `ui.lista_colonna_permesso` | false | grant per colonna/profilo |
| `storico.audit_log` | false | diario delle modifiche ai dati: le colonne a catalogo sono `timestamp, tabella, tipo_operazione, user_modifica, dettaglio` — nessuna dimensione emittente sulla riga |
| `anagrafiche.emittenti_fiscali` | false | ✅ **D-1, Tid 18-09**: l'elenco degli emittenti è un registro globale. La riga non *appartiene* a un'azienda, la riga **è** l'azienda — non c'è niente da scegliere prima di entrare |

Tutte e sei hanno `multi_emittente = false`, quindi il CHECK
`chk_ui_lista_definizione_perimetro_coerente` (`perimetro OR NOT multi`) è
soddisfatto. ⚠️ Non si tocca `multi_emittente` su queste: dichiararle `true`
vanterebbe una capacità che non hanno, e
`dbops.vw_liste_multi_emittente_non_certificate` le intercetterebbe — è la
strada breve che il commento della colonna ha già rifiutato.

### 3-bis. Dove si dichiara — una tabella, un CSV (Tid, 2026-09-18)

Il 02-09 il flag era nato in un **CSV laterale** chiavato su `codice`
(`lista_definizione_perimetro_emittente.csv`, changeSet `20260902-02`), «per
non toccare il mirror mergiato» — lo stesso pattern di `colonna_serie`
(`20260901-12`) e `anno_nel_numero` (`20260908-16`) su `famiglie_documento`.
La prima stesura di questo giro (18-09 sera) ci aveva aggiunto le sei righe.

⛔ **Tid l'ha fermata: quel tipo di seed è deprecato.** Due CSV sulla stessa
tabella sono due sorgenti di verità sulla stessa riga: chi aggiunge una lista
in `lista_definizione.csv` non vede il laterale, chi legge il laterale non vede
la lista, e nessun presidio li confronta — divergono in silenzio. Il
precedente giusto era già in casa: `multi_emittente` il 18-08 è entrata come
**colonna** di `lista_definizione.csv` + riga nell'elenco `columns` del mirror
`20260507-06`, ritoccato dopo il merge (`runOnChange` + `ANY`: il checksum
non è un vincolo).

Quindi, il 18-09:

* `lista_definizione.csv`: colonna `perimetro_emittente` in coda (`t` su
  tutte, `f` sulle sette), dichiarata nel mirror `20260507-06`;
* `20260902-02` e il CSV laterale: **cancellati** (precedente:
  `20251001-05` + CSV, 15-09). La riga in `databasechangelog` resta orfana, e Liquibase non
  se ne cura; su un DB da zero non gira mai;
* il COMMENT vivo della colonna diceva *«il valore si dichiara nel seed
  (20260902-02)»* → riferimento morto nella sede più letta →
  **`00_schema/ui/20260918-28`**, solo `COMMENT`, testo **vivo** con una frase
  sostituita (`20260902-01` è mergiato e non si tocca);
* ✅ **e `famiglie_documento`, stesso giorno («chiudiamo anche quello»,
  Tid)**: i laterali erano **cinque**, non due — `formato`
  (prefisso/lunghezza, `20260902-53-01`, in mezzo a `20260831-53`),
  `colonna_serie` (`20260901-12`), `regole_fiscali` (`20260902-05`),
  `anno_nel_numero` (`20260908-16`) e la **riga** `DISTINTA`
  (`20260915-33`). Tutti rientrati in `famiglie_documento.csv` (18 colonne,
  6 righe) + mirror `20260830-14`, e cancellati (9 file; il changeSet in
  mezzo a `20260831-53` sostituito da un commento datato che spiega ancora
  la terza preCondition del changeSet dopo). ⭐ Il mirror ora si chiava su
  **`codice_interno`** e l'`id` esce dal CSV: DISTINTA è nata senza id e su
  dev è **812** (6 da zero) — un CSV che pretendesse `6` la duplicherebbe;
  nessun seed, pgTAP o backend nomina un id letterale (verificato). Il
  `setval` resta, innocuo. Ordine su un DB da zero verificato: `20260831-03`
  (conta per nome le quattro non fiscali) e il terzo changeSet di
  `20260831-53` (vuole il prefisso) girano **dopo** `20260830-14`, che ora
  porta già tutto. Prova in `ROLLBACK`: upsert **completo** delle sei righe
  sul vivo → sei UPDATE, zero INSERT, **zero differenze** su tutte le
  colonne (id compreso), guard `_a10_` passati sul no-op, NULL dove devono
  (serie di COMMESSA/RESO/DISTINTA, prefisso FATTURA, BA DISTINTA); ramo
  INSERT su un clone `LIKE … INCLUDING ALL`: sei righe, id 1..6, DISTINTA =
  6, valori identici. Nessun dato cambia ⇒ nessun pgTAP da toccare (le
  asserzioni sui valori restano vere). Una riga di fatto corretta in
  `20260915-34`; i riferimenti in `00_schema`/`20_code` (`runOnChange:
  false`) restano come storia.
  🔴 **Apply del 18-09 sera, rosso al primo colpo — e la prova era verde.**
  `trg_famiglie_documento_a10_guard_struttura_upd` su COMMESSA: *«le colonne
  che dicono dove vive il documento non si modificano, ci sono già 2
  registri»*. Il mirror aveva `nullValue: ""` (mai esercitato: il vecchio CSV
  non aveva celle vuote) e alla prima cella vuota Liquibase ha scritto `''`,
  non NULL; il guard fa `IS DISTINCT FROM` su `colonna_serie`. La mia prova
  non l'ha visto perché le `UPDATE` le avevo **scritte io**, con NULL: per un
  `loadUpdateData` l'«SQL estratto» è il render del comando di anteprima
  offline di Liquibase, non una riscrittura. Rimedio: `nullValue: "NULL"` +
  token letterale `NULL` nel CSV (la convenzione di `lista_definizione.csv` e
  dei laterali ritirati); riprovato con l'SQL **reso da Liquibase** in
  transazione ritirata: sei UPDATE, zero differenze, NULL veri (3 serie, 1
  prefisso, 1 BA), nessuna stringa vuota. La transazione del changeSet era
  tornata indietro: valori vivi intatti.
  ✅ La parte `ui` (`20260918-28`, `20260507-06`, `20260806-15`) è **entrata**
  in quell'apply: 872/873 spente, sette globali, `operatori` multi.

⭐ La preCondition di `20260902-02` («la riga delle famiglie esiste, altrimenti
INSERT monco») sparisce con lui, e non serve più: il valore viaggia nella
riga della lista, che il mirror **crea** con tutte le colonne.

## 4. Cosa NON si chiede

* Nessuna modifica a `fn_resolve_lista_config`: legge già la colonna e la
  porta nell'envelope (`perimetro_emittente`, `COALESCE(…, true)`).
* Nessun cambio al default `true` della colonna: una lista nuova nasce **con**
  perimetro e la globalità si dichiara — è giusto così, ed è il motivo per cui
  la richiesta è un seed e non un DDL.
* Nessuna riga per le liste di **dominio** (`vendite.*`, `catalogo.*`,
  `pratiche.*`): lì il perimetro esiste e il cancello è voluto.

## 5. Le domande al DB — le liste amministrative che una dimensione emittente ce l'hanno

Erano sbarrate allo stesso modo, ma per loro `perimetro_emittente = false`
sarebbe **falso**, quindi non stavano in §3. Poste a Tid una alla volta il
2026-09-18; la risposta è in §5-bis.

| Lista | Il fatto (verificato su dbdev e nel FE il 18-09) | Decisione |
| --- | --- | --- |
| `anagrafiche.emittenti_fiscali` | **è** l'elenco degli emittenti. Nessuna RLS, nessuna colonna `emittent*` a catalogo (codice, ragione sociale, P.IVA, stato, valuta, regime) | ✅ D-1 → `perimetro = false`, riga in §3 |
| `anagrafiche.emittente_billing_account` | mappa BA → emittente. Montata **solo** dentro il drawer di un emittente (`EmittenteFiscaleBillingAccountTab.vue`, `:emittente-esplicito="emittenteId"`): il ramo 1 di `richiede_scelta_emittente` la scioglie sempre, **non è sbarrata** | ✅ D-2 → **invariata** |
| `anagrafiche.operatori` | ogni operatore ha **un** emittente; la lista ne mescola di aziende diverse e ha **già** la colonna attiva `emittenti_descrizione` («Emittente fiscale»), che il presidio riconosce (`^emittent`) | ✅ D-3 → `multi_emittente = true` |
| `config.email_log` | ha `emittente_fiscale_id` (RLS `rls_email_log_ambito`: whitelist per azienda, o `SISTEMA`); **nessuna** colonna emittente a catalogo (inviato il, destinatario, oggetto, template, account, errore, stato) | ✅ D-4 → colonna «Emittente» + `multi_emittente = true` |
| `ui.lista_preset` | ha `emittente_fiscale_id` nullable + `ambito`; la colonna «Riferimento» mostra l'azienda per riga ma è **calcolata dal BE** (`campo_sorgente` vuoto) → invisibile a `vw_liste_multi_emittente_non_certificate` | ✅ D-5 → colonna `emittente_*` riconosciuta + `multi_emittente = true` |

## 5-bis. Decisioni di Tid — 2026-09-18

Poste in forma semplice, una alla volta, sempre con «lasciare com'è» fra le
opzioni. Nessuna delle cinque è rimasta com'era per pigrizia: D-2 lo è perché
il cancello **non scatta** già oggi.

* **D-1 — `anagrafiche.emittenti_fiscali` → `perimetro_emittente = false`.**
  Il registro degli emittenti si apre senza sceglierne uno. Alternativa
  scartata: certificarla `multi_emittente` avrebbe voluto una colonna
  `emittent*` che non esiste — e sarebbe stata la stessa informazione della
  ragione sociale, ripetuta per far contento un presidio.
* **D-2 — `anagrafiche.emittente_billing_account` → invariata.** Il perimetro
  esiste davvero (ogni riga è il BA di un'azienda) e il drawer lo fissa già:
  una riga `false` sarebbe falsa e non cambierebbe niente a video.
* **D-3 — `anagrafiche.operatori` → `multi_emittente = true`.** È il caso
  «so dire da quale azienda arriva ogni riga», e la colonna c'è già: il flag
  basta. L'operatore **resta** mono-emittente (§2.1).
* **D-4 — `config.email_log` → colonna «Emittente» a catalogo, poi
  `multi_emittente = true`.** Il super admin su «Tutti» vede le email di tutte
  le aziende con l'azienda accanto; le righe `SISTEMA` con la cella vuota.
* **D-5 — `ui.lista_preset` → colonna emittente riconosciuta, poi
  `multi_emittente = true`.** L'informazione c'è già («Riferimento»): serve
  una colonna con `campo_sorgente` che il presidio veda. Se affianca o
  sostituisce «Riferimento» lo decide il BE, che quella colonna la calcola.

## 6. Come si verifica che è arrivato

Le sei righe di §1 rilette con lo stesso token senza emittente: le sei di
§3 devono rispondere `richiede_scelta_emittente = false`, e
`anagrafiche.operatori` (D-3) anche — per il ramo 3, non per il 2. Lato BE,
dopo l'apply, un presidio piccolo e senza DB in
`test_perimetro_emittente_copertura`: ogni voce di `_ESENZIONI` la cui ragione
dichiara «senza perimetro» / «nessun `emittente_fiscale_id`» / «catalogo
globale» deve avere `perimetro_emittente = f` nella **colonna** di
`80_data/sql/ui/lista_definizione.csv` (dal 18-09, §3-bis: non più una riga
nel CSV laterale) — così registro e seed non possono più dire due cose. Lo
scrive il backend a seed applicato: dettaglio in §8.

## 7. Il lavoro che discende dalle decisioni — in ordine

Tre giri, perché D-4 e D-5 hanno un vincolo d'ordine che gli altri non hanno.

> ✅ **Giro 1 e giro 2 SCRITTI il 2026-09-18 sera** (`dev/db-tid`, non
> ancora applicati né committati — apply, pgTAP e commit sono di Tid):
>
> * `80_data/sql/ui/lista_definizione.csv`: **colonna nuova
>   `perimetro_emittente`** (`f` sulle sette di §3, `t` altrove) + colonna
>   nell'elenco del mirror `20260507-06`; `multi_emittente = t` su
>   `anagrafiche.operatori` (id 28) — D-3. ⚠️ Seconda stesura: la prima
>   appendeva sei righe al CSV laterale, ritirato in §3-bis;
> * **cancellati** `80_data/changelog/20260902-02-…-perimetro-emittente-mctit.yaml`
>   e `80_data/sql/ui/lista_definizione_perimetro_emittente.csv`;
> * **nuovo** `00_schema/ui/20260918-28-comment-ui-lista-definizione-perimetro-emittente-seed-nel-csv`:
>   solo `COMMENT`, dal testo vivo (`col_description`), una frase sostituita;
> * `80_data/sql/ui/lista_colonna.csv`: **id 872** (lista 31, `email_log`) e
>   **id 873** (lista 58, `lista_preset`), `codice = emittente_fiscale`,
>   `campo_sorgente = emittente_ragione_sociale`, **`attivo = f`** — D-4/D-5,
>   sullo stampo delle sei colonne certificate di `vendite`.
>   ⚠️ Erano nate come 787/788: mentre il giro era in corso, «Aggiornato csv
>   lista» (`4a245db9e`, liste `magazzino.*` 75-77) ha portato il CSV a 871.
>   Tid ha fermato il giro, i CSV sono stati riportati indietro e riscritti
>   dopo il merge — è il caso della memoria *«il numero libero scade
>   subito»*, visto in diretta;
> * **pgTAP** (i tre che pinnano la vista di certificazione erano da rileggere,
>   due da toccare): `ui/test-lista-definizione-perimetro-emittente-v1` — il
>   test 6 pinnava «nessun'altra globale oltre le famiglie» (rosso sulla
>   prima riga giusta: *test che pinna il sintomo*) → riscritto come
>   **elenco dichiarato** delle sette, sullo stampo del gemello; **nuovo test
>   8**, derivato: nessuna lista globale espone una colonna attiva
>   `^emittent` (le due dichiarazioni si escludono — è la trappola di
>   `email_log`/`lista_preset` resa test). `plan(7) → plan(8)`.
>   `ui/test-lista-definizione-multi-emittente-v1` test 5: `anagrafiche.
>   operatori` aggiunta all'elenco, con la riga datata. `vendite/test-viste-
>   dash-emittente-v1` test 10 lavora su id fissi: non lo vede, invariato;
> * **prova in transazione ritirata** (SQL **estratto** da `20260918-28` +
>   seed generato *dai CSV*, non riscritto + corpo dei pgTAP): COMMENT
>   riscritto, sette globali, otto multi, vista a zero, envelope giusti;
>   perimetro **7/8 verdi** — il 4 rosso solo per veste
>   (`titodb` non è membro di `zeroerp_app`: risponde il CHECK 23514 e non il
>   guard P0001, come il test stesso avverte); multi non leggibile da owner
>   (i test 3/4 scrivono invece di essere respinti e inquinano 5/6/8) →
>   provato **isolato**: test 5 = elenco atteso, vista di certificazione a 0,
>   envelope `operatori.multi_emittente = true`, `amm.processi` ed
>   `emittenti_fiscali` `perimetro = false`, 872/873 passano il trigger di
>   `campo_sorgente` e sono spente, nessuna riga viola `perimetro OR NOT
>   multi`. ⚠️ Il verde vero lo dà la corsa come app, che lancia Tid.
>
> * ✅ **D-5 chiusa lato DB nello stesso giro** (18-09 sera): `_PRESET_SELECT_SQL`
>   (`ui_admin_repository.py`, riga 15) **proiettava già**
>   `emittente_ragione_sociale` per la colonna calcolata «Riferimento» → la
>   873 nasce **attiva**, `ui.lista_preset` è `multi_emittente = t` e sta
>   nell'elenco del test 5. Presidi BE sulle colonne attive verificati
>   (`ordinabile = f`, non azione, non sensibile, formato vuoto, proiezione
>   via `list_preset_by_lista`); prova in `ROLLBACK`: vista di certificazione
>   a 0, nove multi, envelope `true`. Al BE resta solo la chiave i18n (§8).
> * regola scritta nel meccanismo condiviso: linee-guida-sql **§11.2**
>   (riga «aggiungere una colonna» + paragrafo «una tabella, UN CSV»; la
>   vecchia via «CSV dedicato se il file è una mina» **non è più una via**)
>   e AGENTS.md §«I dati di 80_data si cambiano dal CSV».
>
> ✅ **Giro 3 chiuso il 2026-09-19** — la parte BE con `ecbff9efa`
> (PR #1616/#1617, già su `dev/db-tid`), la riga DB nel riquadro di §8.
> 🔵 **Resta a Tid**: apply (porta insieme i due mirror `ui`: `20260507-06`
> con la 31 multi, `20260806-15` con la 872 accesa e la 663 su
> `profilo_accesso_codice` — su dbdev entrambi sono fermi al `RERAN` del
> 18/19-09 notte, **prima** del commit BE) + pgTAP (i due `ui/` sul perimetro
> e sul multi, `vendite/test-viste-dash-emittente-v1`) + commit → `work-done/`.

**Giro 1 — solo seed, un CSV e mezzo (DB).** Chiude §1 e D-1, D-3:

1. `lista_definizione.csv` (mirror `20260507-06`, `runOnChange` + `ANY`:
   riallinea da solo): colonna `perimetro_emittente`, `f` sulle sei di §3
   (§3-bis: non più il CSV laterale);
2. stesso file: `multi_emittente = t` sulla
   riga `id = 28` (`anagrafiche.operatori`). ⚠️ Solo questa, non `email_log` né
   `lista_preset`: il flag va **dopo** la colonna attiva, o
   `vw_liste_multi_emittente_non_certificate` esce da zero e i tre pgTAP che
   la vogliono vuota (`ui/test-lista-definizione-multi-emittente-v1`,
   `ui/test-lista-definizione-perimetro-emittente-v1`,
   `vendite/test-viste-dash-emittente-v1`) diventano rossi.

**Giro 2 — la colonna a catalogo (DB), con `attivo = false`.** Per
`config.email_log` (lista 31) e `ui.lista_preset` (lista 58) una riga in
`lista_colonna.csv` sullo stampo delle sei già certificate di `vendite`
(`codice = emittente_fiscale`, `campo_sorgente = emittente_ragione_sociale`,
gruppo «Emittente»), **spenta** finché il repository BE non emette il campo
(memoria: una colonna con `campo_sorgente` che il SELECT non produce rompe la
lista). La chiave i18n dell'etichetta va coniata (`config.email_log.col_emittente`,
`ui.lista_preset.col_emittente`).

**Giro 3 — BE, poi il flag (DB).** Riguarda ormai la sola `config.email_log`
(D-4): la 873 dei preset è attiva e certificata dal giro 2 (sopra). Il
backend espone `emittente_ragione_sociale` nella SELECT della lista del log
email (`apps/core/db/email_repository.py`, ~riga 648) e conia le chiavi i18n;
attiva la 872 (`attivo = t` nel CSV, **nello stesso commit** della
proiezione — il cancello `test_lista_proiezione_campo_sorgente` guarda le
colonne attive); a quel punto `multi_emittente = t` sulla riga `id = 31` di
`lista_definizione.csv` **e `config.email_log` si aggiunge all'elenco del
test 5** di `test-lista-definizione-multi-emittente-v1` (è il biglietto).
Elenco completo e file esatti in §8.

⚠️ Sui pgTAP: nessuna firma cambia e nessun contratto di vista; i presidi da
rileggere sono i tre sulla vista di certificazione (devono restare a zero in
ogni giro) e `test_perimetro_emittente_copertura` lato BE.

## 8. Richieste al BE — in un posto solo (18-09 sera)

Tutto ciò che il DB ha consegnato è nel riquadro di §7. Al backend resta
questo, in ordine di dipendenza. ⚠️ Nessuna di queste voci è bloccante per
l'apply DB: le colonne che non hanno ancora la proiezione sono **spente**.

> ✅ **BE/FE chiuse il 2026-09-19** (`dev/backend-tid`), con le due decisioni
> di Tid su BE-6 e BE-7 prese lo stesso giorno accettando la raccomandazione
> del backend:
>
> * **BE-6 → «Riferimento» ristretta al solo profilo.** Con la 873 attiva
>   l'emittente compariva due volte (codice nella 663 calcolata, ragione
>   sociale nella 873); toglierla avrebbe perso il profilo, che la 873 non
>   copre. La 663 è ora una colonna **vera**: `codice = profilo_accesso`,
>   `campo_sorgente = profilo_accesso_codice` (già in `_PRESET_SELECT_SQL`),
>   etichetta «Profilo di accesso», chiave `ui.admin.preset_profilo_accesso`
>   (esisteva); la cella calcolata `#cell-preset_riferimento` di
>   `ListaPresetPanel.vue` e la chiave `ui.admin.preset_riferimento` sono
>   **ritirate**. `esportabile = t` come la 873 (era `f` perché calcolata).
>   ⚠️ Chi aveva `preset_riferimento` nella preferenza personale della lista
>   58 perde quella colonna in silenzio: non c'è produzione, e la lista è
>   dell'amministrazione;
> * **BE-7 → si lascia `ordinabile = f`** su 872/873: spente di proposito dal
>   DB, nessuno l'ha chiesto, ed è una modifica in due file quando servirà.
>
> Il resto, voce per voce: BE-1 → test 5 di
> `test_perimetro_emittente_copertura` (**nei due versi**: ragione «globale»
> senza `f` a seed = lista sbarrata; `f` a seed senza ragione = globalità che
> il registro non conosce); BE-2 → ragioni riscritte, con D-1/D-3/D-5 in
> commento; BE-3 → `list_logs` proietta `emittente_fiscale_id` +
> `emittente_ragione_sociale` (catena `ef → soggetti_ruoli → soggetti`, NULL
> su `SISTEMA`); BE-4 → 872 `attivo = t` nello stesso giro; BE-5 → entrambe
> le chiavi (`ui.admin.preset_emittente` era già entrata il 18-09 con
> `8e6422e32`); BE-8 → nota chiusa nel piano. Verificato: guard i18n pulito,
> `test_lista_proiezione_campo_sorgente` (E2E sul DB vero, catalogo dal CSV)
> verde con 872 attiva e 663 su `profilo_accesso_codice`, 304 test di
> `ui`/`amm_software` verdi. ⚠️ Il pgTAP non è lanciabile dal server BE
> (nessuna credenziale): la lista 31 non è globale, il test 8 non la guarda.
>
> ✅ **L'ultima riga DB è scritta il 2026-09-19** (`dev/db-tid`, non
> applicata né committata):
>
> * `lista_definizione.csv`, riga `id = 31`: `multi_emittente = t` — la 872
>   è attiva nel CSV dal commit BE, quindi il flag arriva **dopo** la colonna,
>   come voleva l'ordine di §7;
> * `ui/test-lista-definizione-multi-emittente-v1` test 5: `config.email_log`
>   nell'elenco, con la riga datata (D-4) e l'avvertenza sull'ordine;
>   intestazione del test aggiornata. `plan(9)` invariato: cambia l'elenco,
>   non il numero di asserzioni. Gli altri due presidi sulla vista
>   (`perimetro` test 7/8, `dash` test 10/11) non nominano la lista e
>   restano com'erano;
> * **prova in transazione ritirata**, con l'SQL **reso da Liquibase**
>   (`updateSQL` offline) di **entrambi** i mirror `ui` — non del solo
>   `lista_definizione`, perché la certificazione dipende dalla 872 che a DB
>   vivo è ancora spenta: `EXCEPT` prima/dopo = una differenza su
>   `lista_definizione` (la 31, `f → t`) e due su `lista_colonna` (663 e 872,
>   entrambe del commit BE), zero INSERT; elenco del test 5 identico
>   all'atteso (dieci liste); vista di certificazione a **zero**; test 8 del
>   perimetro a `{}`; le sette globali intatte; nessuna riga viola `perimetro
>   OR NOT multi`; envelope di `fn_resolve_lista_config('config.email_log')`
>   → `multi_emittente = true`. ⭐ **Mutazione**: con il solo mirror di
>   `lista_definizione` (il flag prima della colonna, cioè lo stato del DB
>   vivo se si applicasse a metà) la vista esce da zero con `31 |
>   config.email_log` — il presidio vede l'ordine sbagliato. ⚠️ Il verde
>   vero lo dà la corsa come app, che lancia Tid.
>
> ⚠️ **Una riga BE, non bloccante** (stessa regola di BE-2: il registro dice
> ciò che il seed dice): in `_ESENZIONI` la ragione di `config.email_log` è
> ancora *«diario tecnico di sistema»*, mentre da oggi il seed la certifica
> `multi_emittente` — sullo stampo di `operatori`/`lista_preset`:
> *`multi_emittente` certificata (colonna 872 `emittente_fiscale`)*. Il test
> BE-1 non la vede (guarda solo le globali): è coerenza del registro, non un
> rosso.
>
> ✅ **Applicato e pgTAP verdi il 2026-09-19** (Tid); archiviato in `work-done/` lo stesso giorno.

| # | Cosa | Dove | Note |
| --- | --- | --- | --- |
| BE-1 | **Presidio §6**: ogni voce di `_ESENZIONI` motivata «senza perimetro» / «nessun `emittente_fiscale_id`» / «catalogo globale» ha `perimetro_emittente = f` in `lista_definizione.csv` (colonna 10, letta col modulo `csv`, senza DB) | `apps/core/tests/test_perimetro_emittente_copertura.py` | Le sette globali: `amm.processi`, `anagrafiche.emittenti_fiscali`, `storico.audit_log`, `ui.lista_definizione`, `ui.lista_colonna`, `ui.lista_colonna_permesso`, `vendite.famiglie_documento` |
| BE-2 | **Ragioni di `_ESENZIONI` da riscrivere** perché ora il seed le dice: `anagrafiche.emittenti_fiscali` → *catalogo globale (`perimetro_emittente = false`)*, come `famiglie_documento`; `amm.processi` e `storico.audit_log` → aggiungere *(`perimetro_emittente = false`)*; `anagrafiche.operatori` → *`multi_emittente` certificata: colonna «Emittente fiscale» per riga*; `ui.lista_preset` → *`multi_emittente` certificata (colonna 873 `emittente_fiscale`)*, non più «P-2c via Riferimento» | stesso file | ⛔ Non è cosmesi: il registro deve dire la stessa cosa del seed, ed è ciò che BE-1 presidia |
| BE-3 | **D-4, `config.email_log`**: proiettare `emittente_ragione_sociale` nella SELECT della lista (LEFT JOIN `anagrafiche.emittenti_fiscali ef ON ef.id = el.emittente_fiscale_id` → `soggetti_ruoli` → `soggetti.ragione_sociale_completa`, stessa forma di `_PRESET_SELECT_SQL`; NULL sulle righe `SISTEMA`) | `apps/core/db/email_repository.py` ~648 | `campo_sorgente` della 872 è `emittente_ragione_sociale`: il nome è fissato dal seed |
| BE-4 | **Accendere la 872** nello stesso commit di BE-3: `attivo = t` sulla riga `872` di `80_data/sql/ui/lista_colonna.csv` | `lista_colonna.csv` | I commit BE toccano già questo CSV (`f915a32a5`); il mirror `20260806-15` è `runOnChange`. ⛔ Non prima di BE-3: `test_lista_proiezione_campo_sorgente` diventa rosso |
| BE-5 | **Chiavi i18n** (`it.json`, `en.json`): `amministrazione.email_emittente` = «Emittente», `ui.admin.preset_emittente` = «Emittente» | `frontend/src/locales/` | Senza chiave `etichettaColonna` ricade sull'etichetta del seed («Emittente»): non rompe, ma la regola è `$t()` |
| BE-6 | **«Riferimento» dei preset** (colonna 663, calcolata dal BE): ora c'è la 873 riconosciuta accanto. Decidere se «Riferimento» resta (mostra anche il profilo) o si restringe al profilo | `ui_admin_repository.py` + seed 663 | Scelta BE; il DB non ha una preferenza. ✅ **Tid, 19-09: ristretta al solo profilo** — colonna vera su `profilo_accesso_codice` (riquadro sopra) |
| BE-7 | **Ordinamento per emittente**, se lo si vuole: `ordinabile = t` su 872/873 **+** il campo nella whitelist di ordinamento del repository — *una modifica, due file* | seed + repository | Oggi `ordinabile = f` su entrambe, di proposito. ✅ **Tid, 19-09: resta `f`** |
| BE-8 | Chiudere la nota d'origine: *«Nel frattempo si entra scegliendo un emittente nella combo»* | `work-done/piano-be-fe-avvio-manuale-di-un-processo.md` §4.4.2 | Il caso è risolto dal seed |

**Poi torna al DB** (una riga, un pgTAP): a BE-3/BE-4 fatti, `multi_emittente = t`
sulla riga `id = 31` di `lista_definizione.csv` e `config.email_log` nell'elenco
del test 5 di `ui/test-lista-definizione-multi-emittente-v1`. ✅ **Fatto il
2026-09-19** (riquadro sopra). Con l'apply e i pgTAP di Tid il brief va in
`work-done/`.
