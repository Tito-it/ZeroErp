# Brief DB — Il riepilogo permessi diventa la lista operatori, con i permessi aperti

> **Chi scrive:** sessione BE/FE (`dev/backend-tid`), 2026-10-06. **A chi:** team DB
> (`dev/db-tid`); poi BE/FE (§5), che **attende** la consegna DB.
> **Decisioni:** di Tid, 2026-10-06 (§2).
> **Stato:** ✅ **DB applicato il 2026-10-06, pgTAP verdi** (§6): `20261006-01`, `-02`,
> due righe di CSV e un pgTAP nuovo. ✅ **BE/FE fatto il 2026-10-06** (§7, con le
> correzioni di §6.4), **non committato**. ⏳ Resta il collaudo a video, dopo il migrate
> che accende la colonna *Override* (§7). 🔵 **Nuova richiesta al team DB in §8**: ritirare
> la colonna «Azioni» della lista 28, rimasta senza kebab.

## 1. Perché

La vista *Amministrazione software → Riepilogo permessi* è una matrice operatori × aree:
una colonna per area funzionale, generata a runtime. Con 14 aree non entra più nella
pagina e va scrollata in orizzontale. È anche fuori standard: una `DataTable` registrata
come eccezione, senza paginazione, kebab, esportazione né personalizzazione delle colonne.

Lato backend il motivo è lo stesso: la query costruisce con un f-string una subquery
`fn_resolve_livello_area(au.id, '<schema_db>')` **per ogni area**, su **tutti** gli
operatori in una volta.

Si passa alla forma standard:

* **una riga per operatore**: le colonne della lista Operatori, più una colonna
  **Override** col numero di override dell'operatore;
* sotto ogni riga, un'**espansione sempre aperta** con le aree come chip compatte:
  `Anagrafiche · Tutto · 3 ⚠`, cioè il livello effettivo, il numero di override
  nell'area e il triangolo se il tetto d'area ne ferma qualcuno. È la stessa lettura
  dell'elenco delle aree nel pannello permessi, e i due devono dire la stessa cosa;
* il **kebab** di riga: *Permessi*, che apre il drawer dei permessi, e *Modifica operatore*.

## 2. Le decisioni (Tid, 2026-10-06)

| # | Domanda | Decisione |
| --- | --- | --- |
| D-1 | Lista nuova, o la lista Operatori? | **Il catalogo `anagrafiche.operatori`** (lista 28), con la stessa sorgente dati. Il riepilogo diventa «la lista operatori con i permessi aperti». Una seconda lista sugli stessi operatori sarebbe una copia destinata a divergere. |
| D-2 | Il numero conta tutti gli override o solo quelli in vigore? | **Quelli scritti**, a prescindere da `valido_dal`/`valido_al`. Come il badge del pannello. |
| D-3 | Il triangolo del tetto nelle chip? | **Sì.** |
| D-4 | Sede unica a DB per il conteggio degli override (§3.1), letta da lista, espansione e pannello? | **Sì**: building block unico (regola del 2). |

## 3. Richiesta

### 3.1 Una sede per «quali override ha un operatore, area per area»

Il numero serve in **tre** posti: la colonna della lista (il totale), le chip
dell'espansione (per area) e il badge del pannello (per area, oggi calcolato a video).
Sono tre letture della stessa regola. Per questo propongo una **sede unica a DB** e
non tre conteggi.

> ✅ Building block per **regola del 2**, confermato da Tid il 2026-10-06 (D-4). La
> forma qui sotto è una proposta, e la scelta finale spetta al team DB.

Forma proposta: una vista (o funzione) che dà **una riga per override scritto**, con la
sua area:

| colonna | da dove |
| --- | --- |
| `auth_user_id` | la tabella di override |
| `area_id` | `user_override_aree.area_id`; per un'azione `azioni_processo.area_id`; per un oggetto `area_model_overrides.area_id` (la FK composita garantisce che l'oggetto sia a catalogo) |
| `tipo` | `AREA` / `AZIONE` / `OGGETTO` |

**Perimetro del conteggio**: deve coincidere con ciò che il pannello mostra, altrimenti
lista e pannello danno due numeri diversi per lo stesso operatore.

* Aree **attive**.
* Azioni **attive**: il pannello mostra solo quelle (`listAzioniProcesso` filtra
  `ap.attivo`).
* Oggetti: tutti quelli a catalogo, **riservati compresi**. Il pannello mostra anche i
  riservati che hanno già un override, così restano visibili e si possono togliere.

📌 *Fatto da verificare, non motivo:* un override su un'azione **non attiva** oggi
resta scritto ma il pannello non lo mostra. Se il team DB ritiene che vada contato,
lo dichiari: allora il pannello si allinea e lo mostra, non il contrario.

> ✅ **Risposta del team DB (§6.2): il caso non esiste sul modello**, e nemmeno quello
> dell'oggetto riservato con override. Il conteggio non filtra niente.

### 3.2 Il riepilogo per area, per un insieme di operatori

```text
script.fn_get_permessi_riepilogo_aree(p_auth_user_ids integer[])
RETURNS TABLE (auth_user_id integer, area_id integer,
               livello config.livello_accesso,   -- effettivo dell'area
               override_count integer,           -- da §3.1, per (utente, area)
               voci_limitate integer)            -- azioni + oggetti fermati dal tetto
```

* **Una riga per (operatore, area attiva)**, anche senza override (`override_count = 0`).
* Il **livello** è quello effettivo dell'area, cioè la catena di `fn_resolve_livello_area`.
* Le **voci limitate** si contano da `fn_get_permessi_effettivi_azioni` (`limitata_da_area`,
  solo azioni attive) e `fn_get_permessi_effettivi_oggetti` (`limitato_da_area`). Sono le
  sedi uniche del tetto, e qui **non si ricalcola** niente.
* **Super admin** e **veste spenta** rispondono come rispondono le funzioni del tetto.
  Il riepilogo non aggiunge rami suoi: il bypass e il fail-closed stanno dove stanno.
* Riceve un **array di id**: il backend chiede solo le righe della **pagina** (25-50
  operatori), non tutti come oggi.
* `STABLE`. Il contesto GUC è quello delle funzioni del tetto, chiamate oggi dal
  pannello per un operatore diverso da chi guarda: va verificato che valga anche qui.

### 3.3 La colonna del catalogo

In `ui/lista_colonna.csv`, lista **28** (`anagrafiche.operatori`):

| campo | valore |
| --- | --- |
| `codice` / `campo_sorgente` | `override_count` |
| `etichetta` | `Override` |
| `etichetta_estesa` | `Override dei permessi scritti per l'operatore (aree, azioni e oggetti)` |
| `tipo_colonna` / `tipo_dato` / `formato` | `informazione` / `numeric` / `number` |
| `allineamento` | `right` |
| `ordinabile` / `filtrabile` / `esportabile` / `ricercabile_full` | `t` / `f` / `t` / `f` |
| `etichetta_i18n_key` | `amministrazione.col_override` (la chiave la aggiunge il FE) |
| `ordine_default` | dopo `unita_organizzativa_nome` (30), prima di `emittenti_descrizione` (40) |

Modello: la colonna `operatori_count` della lista reparti (id 969). Se esistono preset
della lista 28, la colonna va nei preset di default: la decisione è del team DB, che
conosce la forma di casa.

## 4. Test (pgTAP)

* §3.1: un operatore con un override per tipo, più un'azione **non attiva** con override
  e un oggetto **riservato** con override. I conteggi devono rispettare il perimetro di §3.1.
* §3.2:
  * una riga per area attiva anche a zero override;
  * il `livello` coincide con `fn_resolve_livello_area` per ogni (utente, area);
  * `voci_limitate` coincide con il conteggio fatto direttamente sulle due funzioni del
    tetto (area `BLOCCATO` + override azione abilitata ⇒ 1);
  * un super admin e una veste spenta rispondono come le funzioni del tetto;
  * un array vuoto dà zero righe.

## 5. Dopo la consegna: BE/FE (dev/backend-tid)

Si fa solo **dopo** l'applicazione a DB.

* **BE, lista operatori:**
  * la `SELECT` di `list_operatori` proietta `override_count` (totale da §3.1);
  * la colonna entra nella whitelist di ordinamento.
* **BE, riepilogo:** l'endpoint `permessi-riepilogo` legge
  `fn_get_permessi_riepilogo_aree(ids)` per gli id richiesti, cioè le righe della pagina.
  La query con un f-string per area si **toglie**.
* **FE, `PermessiRiepilogoView`:**
  * `ListaConfigurabile codice="anagrafiche.operatori"` con lo store della lista operatori;
  * slot `row-expansion` con le chip, espansione pilotata e **tutta aperta** a ogni
    caricamento («Comprimi tutte» resta l'azione di testata);
  * kebab `#actions` con *Permessi* e *Modifica operatore*;
  * la `DataTable` esce dal registro delle eccezioni (`datatable.baseline.json`).
* **I filtri del riepilogo** (emittente, reparto, super admin) devono esistere nella
  lista operatori. Quelli che mancano entrano nella sua whitelist. Va controllato il
  filtro emittente: oggi legge `config.user_emittenti_fiscali`, mentre lo scope dichiarativo è
  `fn_get_user_emittenti_scope`.
* **Pannello:** il badge per area legge lo stesso numero (§3.1) invece di ricontarlo a
  video (D-4).
* **i18n:** `amministrazione.col_override` in it/en.
* **Test:**
  * BE: proiezione e ordinamento di `override_count`, riepilogo per id;
  * FE: espansione aperta al caricamento, chip con numero e triangolo, kebab.

## 6. Consegna DB (2026-10-06) — ✅ applicata, pgTAP verdi

> **Chi scrive:** sessione DB (`dev/db-tid`), 2026-10-06.
> ✅ **Applicata da Tid il 2026-10-06, pgTAP verdi** (`script/test-permessi-riepilogo-aree-v1`
> e i presidi trasversali): la corsa come applicazione copre ciò che la prova pre-apply
> da owner non poteva coprire (§6.3). Il lato BE/FE (§5 + §6.4) è sbloccato.

### 6.1 Cosa c'è

| Pezzo | File | Cosa fa |
| --- | --- | --- |
| §3.1 | `20_code/script/20261006-01-create-vw-override-operatore-area-mctit.yaml` | `script.vw_override_operatore_area`: una riga per override **scritto** — `auth_user_id`, `area_id`, `tipo` (`AREA`/`AZIONE`/`OGGETTO`), `override_id`. `security_invoker`, `SELECT` all'app. È la sede unica del conteggio (D-4) |
| §3.2 | `20_code/script/20261006-02-create-fn-get-permessi-riepilogo-aree-mctit.yaml` | `script.fn_get_permessi_riepilogo_aree(p_auth_user_ids integer[])` con la firma del §3.2. plpgsql, `STABLE`, INVOKER, `EXECUTE` all'app |
| §3.3 | `80_data/sql/ui/lista_colonna.csv`, riga **1110** | `override_count` sulla lista 28, come chiesto, con `ordine_default` **35**, `larghezza_default` 110 e `priorita` 70 (quelle di `operatori_count`, 969). ⚠️ Nasce **`attivo = f`** (§6.4) |
| §3.3 | `80_data/sql/ui/lista_preset_colonna.csv`, riga `28,1110,35,t,f` | la colonna entra nel preset di default `operatori_default` (28), visibile. Così non accende il banner «colonne nuove» quando il BE la attiva |
| §4 | `db/pgtap/script/test-permessi-riepilogo-aree-v1.sql` | 16 test (§6.3) |
| doc | `docs/it/dbzero/script/manual/vw_override_operatore_area.md`, `…/fn_get_permessi_riepilogo_aree.md` | pagine manuali |

Il CSV non vuole changeSet nuovi: lo rileggono i mirror `runOnChange` già esistenti
(`20260507-07` e `20260507-09`).

### 6.2 Il perimetro del conteggio: il modello lo chiude già, quindi niente filtri

Il §3.1 chiedeva di contare aree attive, azioni attive e oggetti a catalogo riservati
compresi, e il 📌 chiedeva se un override su un'azione non attiva andasse contato.
**Quei casi sul modello non esistono**, e lo dicono i vincoli, non i dati:

* **override d'area** → l'area resta attiva: `aree_funzionali` ha il blocco di
  disattivazione sui figli `user_override_aree`, che non hanno `attivo` (basta che la
  riga esista), e l'override nasce solo su un'area attiva;
* **override d'azione** → l'azione resta attiva (stesso blocco sui figli
  `user_override_azioni`; l'override nasce solo su un'azione attiva), e un'azione attiva
  tiene attiva la sua area;
* **override d'oggetto** → l'oggetto è a catalogo e **non riservato**: la FK composita
  `fk_user_override_oggetti_catalogo` porta `riservato` generato a `false`. Un oggetto
  con un override non può diventare riservato né uscire dal catalogo, e un override su
  un oggetto riservato è rifiutato. Quindi «il pannello mostra anche i riservati che
  hanno già un override» descrive un caso che il database non lascia nascere.

⇒ La vista **non filtra**: ogni override scritto è uno che il pannello mostra. Un filtro
su `attivo` o `riservato` sarebbe un ramo morto che ripete, in un secondo posto, regole
che il catalogo tiene già.

Stessa ragione per le **voci limitate** del §3.2: il brief chiedeva «solo azioni
attive», ma un'azione spenta non può essere `limitata_da_area`. Per esserlo serve un
override o una riga di profilo sull'azione, e anche `profili_accesso_azioni` non ha
`attivo`: qualunque sua riga blocca la disattivazione. Il super admin, che non passa da
lì, non è mai limitato. Il filtro non c'è.

⭐ Il §4 chiedeva di **contare** un override su un'azione non attiva e uno su un oggetto
riservato. Il pgTAP prova invece che il database **rifiuta di costruirli** (test 6-8):
è quella la garanzia che rende giusta la vista senza filtri, e se un giorno cadesse il
test diventa rosso.

### 6.3 Le altre scelte, e la prova

* **Super admin, veste spenta, contesto**: nessun ramo proprio. `livello` e
  `voci_limitate` vengono dalle tre funzioni lette; `override_count` resta il numero
  scritto anche per la veste spenta (D-2). Il gate di contesto delle funzioni del tetto
  guarda la sessione di **chi legge** (`app.ruolo_applicativo`), non l'operatore letto:
  è lo stesso contesto in cui il pannello le chiama oggi. Le tabelle lette direttamente
  (`config.aree_funzionali` e le tre di override, via vista) non hanno RLS.
* **Parametro**: duplicati e `NULL` dentro l'array si ignorano; array vuoto **o `NULL`**
  → zero righe. Un id che non è un operatore riceve le sue righe come le darebbero le
  funzioni del tetto (`BLOCCATO`, 0, 0).
* **Ordine**: operatore, poi area per `ordinamento` e `codice`, cioè quello del pannello.
* **Costo** (fatto datato, 2026-10-06, dbdev, da owner): 16 operatori × 14 aree
  attive, `fn_resolve_livello_area` ~40 ms in tutto, le due funzioni del tetto ~30 e
  ~20 ms. La pagina da 25-50 operatori non è un problema.

**Prova pre-apply** (2026-10-06, dbdev, da **owner**, una transazione con `ROLLBACK`
che contiene l'SQL **estratto** dai due YAML e il corpo del pgTAP):

* pgTAP **16/16**. Al primo giro tre rossi del test, non del codice (i booleani di
  `concat_ws` escono `t/f`; il rifiuto della FK porta il nome del vincolo, non lo
  SQLSTATE): attese corrette;
* **mutazioni**: togliendo gli oggetti dalle voci limitate vanno rossi 12 e 13;
  facendo contare alla vista i soli override in vigore vanno rossi 4, 5 e 12;
* `plpgsql_check_function` sulla funzione nuova: nessun rilievo;
* dopo la prova, vista e funzione **non** esistono su dbdev.

⚠️ Cosa la prova **non** copre: la corsa come applicazione con la RLS sulle tabelle
lette dalle funzioni del tetto (`identita_digitali`) e i presidi trasversali
(`dbops/test-riferimenti-morti-v1`, che compila ogni plpgsql). Li dà la corsa di Tid.

### 6.4 Per Tid, e poi per BE/FE

~~**Tid:** apply e corsa pgTAP~~ — ✅ fatti il 2026-10-06.

**Correzioni al §5 (BE/FE):**

* ⚠️ **La colonna nasce spenta** (`attivo = f`, riga 1110). La lista 28 non ha
  `vista_sql`, e il cancello `test_lista_proiezione_campo_sorgente` vuole che ogni
  `campo_sorgente` attivo sia proiettato dalla `SELECT` del repository: accesa ora,
  farebbe rosso quel test finché il BE non proietta. Il BE la accende (`attivo = t` nel
  CSV) **nello stesso commit** in cui `list_operatori` proietta `override_count` e lo
  mette nella whitelist di ordinamento (`ordinabile = t`).
* Il totale della lista si legge dalla vista, per esempio
  `(SELECT count(*) FROM script.vw_override_operatore_area v WHERE v.auth_user_id = au.id)`:
  le tre tabelle di override hanno un UNIQUE che comincia da `auth_user_id`.
* Il badge per area del pannello legge la stessa vista (o la funzione del riepilogo per
  un solo id), e i due ricalcoli di oggi — quello a video del pannello e la query con
  l'f-string del riepilogo — si **ritirano nello stesso giro** (regola del 2).
* Il pannello e le chip **non** devono filtrare gli override su azioni spente o oggetti
  riservati: per il §6.2 non esistono, e un filtro lì sarebbe un secondo posto della
  regola.
* La chiave `amministrazione.col_override` non c'è ancora in `it.json`/`en.json`
  (controllato il 2026-10-06): la aggiunge il FE. Con la colonna spenta
  `check_i18n_keys.py` non la chiede ancora.

## 7. Giro BE/FE (2026-10-06) — ✅ fatto, da collaudare a video

> **Chi scrive:** sessione BE/FE (`dev/backend-tid`), 2026-10-06. Non committato.

⭐ **Una scelta di forma presa durante il giro (Tid):** il riepilogo non è una pagina
sua con lo stesso catalogo, ma un **interruttore «Mostra permessi»** nella lista
Operatori (*Accessi → Operatori*). Due pagine sullo stesso store si sarebbero passate
filtri e pagina, e una seconda pagina con uno store suo avrebbe chiesto un componente
lista estratto e una factory. La voce di menu *Riepilogo permessi*
(`/amm-software/permessi`) resta come **redirect** con l'interruttore acceso
(`?permessi=1`), così menu e preferiti salvati continuano a funzionare.

| Pezzo | Dove | Cosa |
| --- | --- | --- |
| Colonna *Override* | `amm_software_repository.list_operatori` | `override_count` contato su `script.vw_override_operatore_area` (§6.4), in whitelist d'ordinamento; `OperatoreRow.override_count`. Riga **1110** del CSV accesa (`attivo = t`) nello stesso giro |
| Riepilogo per area | `get_permessi_riepilogo` + `PermessiRiepilogoView` (BE) | `GET permessi-riepilogo/?auth_user_ids=1,2,3` → `{results: [...]}` da `fn_get_permessi_riepilogo_aree`, con `area_codice`/`area_descrizione`. Gli id che non sono operatori si scartano prima della funzione; al massimo `MAX_LIMIT` id; un id non valido, o nessun id, è un 400 (`E_AMM_VALIDAZIONE`); il pezzo lo legge `optional_int` (cifre ASCII, corretto nello stesso giro), più il tetto di un `integer` PG. **Ritirata** la query con un f-string per area, e i vecchi filtri dell'endpoint |
| Lista operatori | `OperatoriListView.vue` | interruttore *Mostra permessi* (fuori dai filtri: cambia cosa si vede, non quali righe); espansione pilotata, tutta aperta a ogni caricamento con l'interruttore acceso; chip per area con livello, numero di override e triangolo del tetto; il riepilogo si chiede per le righe aperte della pagina in una chiamata e si scarta a ogni ricarica della lista (dopo un Salva nel drawer la ricarica già `useTabFreshness`); una lettura fallita lo dice sulla riga. Il `?permessi=1` vive in `QUERY_MOSTRA_PERMESSI*` (`amministrazione/constants`), letto da router e vista |
| Pannello | `OperatorePermessiTab.vue`, store `riepilogoAree` | il badge dell'area legge il numero dalla funzione (D-4); un'area con modifiche non salvate lo conta a video, come anteprima (la stessa regola del tetto). Ricaricato a ogni Salva |
| Pagina tolta | `PermessiRiepilogoView.vue` (FE) | cancellata; uscita dal registro `datatable.baseline.json` (28 grezze) |
| CSS | `main.css` | `.app-permessi-tetto-icona` globale: ora la usano pannello e lista |
| i18n | it/en | nuove `col_override`, `mostra_permessi`, `mostra_permessi_hint`; tolte le 7 chiavi della pagina ritirata (`permessi_col_*`, `permessi_filter_*`, `permessi_stato_super_admin`/`_operatore`), cercate anche in `db/` e `backend/` |

**Test:**

* BE: `test_permessi_riepilogo.py` (8: id, 400, tetto, forma della query, colonna e
  whitelist); adattati `test_operatori_senza_utenti_tecnici` e
  `test_operatore_altre_vesti_db`: al riepilogo si chiedono **apposta** gli id non
  operatori, e deve scartarli lui. Suite `amm_software` verde; test su DB reale
  (`ZEROERP_TEST_DB_E2E=1`) del dominio e del catalogo liste verdi (44).
* FE: `OperatoriListView.spec.js` (5: deep link, chip, interruttore, cache scartata
  alla ricarica — provato anche a rovescio —, lettura fallita e nuovo tentativo); `OperatorePermessiTab.spec.js`
  test 9 (DB contro anteprima). Suite 700 verde, lint, guard e build puliti.

**Verifica sul DB di sviluppo** (2026-10-06, sola lettura): `pochi` 23 override in
lista, uguale alla somma delle sue aree (Anagrafiche 3, come nel pannello), e `fara`
5 = 4 + 1.

⚠️ **Prima del collaudo:** la riga 1110 del CSV la rilegge il mirror `runOnChange` al
prossimo migrate. Finché non gira, su `dbdev` la colonna *Override* resta spenta,
mentre interruttore e chip funzionano già. Il backend di sviluppo è stato ricaricato
(`kill -HUP`).

### 7.1 Ritocchi dopo la prima prova a video (Tid, 2026-10-06)

| Cosa | Perché |
| --- | --- |
| **Tolta la voce di menu** *Riepilogo permessi* | portava ad *Accessi → Operatori*, e il menu evidenziava «Accessi»: fuorviante |
| **Tolti il redirect** `/amm-software/permessi` **e il link** `?permessi=1` | senza la voce non li usava più nessuno (un segnalibro vecchio finisce sulla pagina di errore) |
| **Tolto il kebab** *Gestisci permessi* **e il drawer** `OperatorePermessiDrawer` | apriva lo stesso pannello della scheda *Permessi* del drawer operatore, che si apre già cliccando la riga: due strade per la stessa cosa |
| **Le chip vanno a capo** (`contain: inline-size`) | la tabella delle liste è larga quanto il contenuto, e il blocco delle chip contava come una riga sola: allargava la tabella e accendeva lo scroll orizzontale |

Tolte anche l'etichetta di menu, la costante dell'icona e le chiavi
`gestisci_permessi` / `permessi_operatore_title`, senza più usi (cercate anche in `db/` e
`backend/`).

## 8. Richiesta al team DB: ritirare la colonna «Azioni» della lista 28

Senza kebab, la colonna `azioni` della lista `anagrafiche.operatori` (`ui/lista_colonna.csv`,
riga **345**, `tipo_colonna = azione`) non viene più disegnata: `ListaConfigurabile` la rende
solo se la pagina passa lo slot `#actions`. Ma la riga di catalogo resta, e in *Personalizza
colonne* compare come una colonna da accendere che non fa niente.

* `lista_colonna.csv` riga 345 → `attivo = f` (o la forma di ritiro di casa);
* `lista_preset_colonna.csv` → la riga `28,345,90,t,f` del preset di default.

Nessuna ricaduta BE/FE: il frontend non la chiede più. Se un giorno la lista avrà di nuovo
azioni di riga (es. *Disabilita*, *Reinvia invito*), la colonna si riaccende.

