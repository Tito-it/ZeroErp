# Richieste aperte dal backend — l'elenco unico per il team DB

> ## ✅ CHIUSO — 2026-08-31: l'ordine di lavoro è esaurito
>
> **Tutte e cinque le voci sono fatte e APPLICATE.** La 1 era già in git quando
> l'elenco è stato ri-verificato; le altre quattro sono 12 changeSet
> (`20260831-24..33` più `-36`), 4 file pgTAP nuovi e 2 classificazioni
> nell'inventario della pulizia. Il dettaglio sta nel §«Cosa è stato costruito».
>
> ⭐ **Ogni presidio è stato provato per MUTAZIONE**, non solo visto verde — e
> ognuna fa cadere **il caso suo e solo quello**. `pgtap-baseline.sh vendite
> config`: 285 file, nessuna regressione.
>
> ⛔ **Il file resta aperto in una cosa sola, e non è lavoro DB**: le richieste
> nel **verso opposto** del §omonimo — `F0` sono undici codici (dodici col
> `E_FATTURA_RIGA_CAPOFILA_INCOERENTE` nato qui), l'ordinamento delle righe di
> fattura per `codice` articolo invece che per UUID, e le tre chiavi in
> `_CREATE_KEYS_TESTATA`. Vivono nel piano di
> [Fase 3](brief-be-fe-iva-fase-3-consumatori-risolutore.md),
> che è il documento da guardare adesso.
>
> ⚠️ **Se arrivano richieste nuove dal backend, NON si riapre questo file**: è
> chiuso perché il suo elenco è esaurito, e un ordine di lavoro che si riapre
> smette di dire cosa è finito. Se ne fa uno nuovo, con la stessa forma.

> **Destinatario:** team DB (`dev/db-tid`). ⭐ **È un ORDINE DI LAVORO, non un
> brief di analisi**: qui c'è *cosa fare*, in ordine, con lo stato verificato.
> Il *perché* sta nei brief linkati e **non viene ricopiato**.
>
> **Origine.** Richiesta di Tid del 2026-08-31: *«possiamo mettere tutto in un
> unico brief per non disperdere il lavoro?»*. Le richieste erano quattro,
> nate in momenti diversi, e chi apriva un file solo non vedeva le altre.
>
> ⛔ **Perché l'elenco NON sostituisce i brief**, ed è la stessa scelta del
> §8-nonies del brief madre IVA: *«là c'è il ragionamento, qui c'è solo
> l'elenco con il rimando — duplicare la motivazione la farebbe divergere»*.
> Le voci qui sono corte perché la richiesta è corta; dove il ragionamento
> serve davvero (voci 4 e 5) si clicca.
>
> **Stato.** 2026-08-31, verificato sul repo a `e22a25ba7` — non ricordato.
> Ogni riga «Verificato» qui sotto è il risultato di un controllo fatto
> quel giorno, non una previsione.
>
> ⭐ **Ri-verificato il 2026-08-31 (3) su `46fbf56ab`**, prima di scrivere una
> riga di codice — ed è servito: la voce 1 **era già stata fatta** e il
> documento non lo sapeva. Le quattro decisioni del §«Le decisioni» sono state
> prese da Tid in quello scambio.
>
> 🔨 **Costruito il 2026-08-31 (4)**: voci 2, 3, 4 e 5 — l'elenco dei changeSet è
> nel §«Cosa è stato costruito». ⚠️ **Costruito non vuol dire applicato**: cosa
> sia passato si chiede a `databasechangelog`, non a questo file.

---

## L'ordine, e perché è questo

```text
1. seed del codice errore        ✅ FATTO         in git dal 31/08 — e i codici sono TRE
2. fn_create_contratto           3 stringhe       fermo dal 29/08
4. vendite.fatture_atti          tabella + FK     ⭐ sblocca I4  (+ due satelliti vecchi)
5. fatture_righe: capofila       colonna + FK     ⭐ sblocca I4
3. DEFAULT_IVA                   rename+registry  ⛔ prima si disinnesca parameters.csv
```

⛔ **La 3 è scesa in fondo, e non è una preferenza**: costava «minuti» finché
nessuno aveva guardato il file che va toccato. `parameters.csv` è una **mina
dormiente** già esplosa il 2026-08-25, e la voce 3 non si può fare senza
disinnescarla prima — il dettaglio, con la decisione presa, sta nella voce.

⭐ **La 2 costa ancora minuti** ed è quella da fare per prima se si fa una cosa
sola. La **4** e la **5** sono un cantiere piccolo, e vanno **insieme**: `I4` ha
bisogno di entrambe, e `I6` — l'ultima voce del cantiere IVA — viene dopo `I4`.

⚠️ **La quinta è nata il 2026-08-31 controllando, e non era nell'elenco**: la
decisione `N3` sceglieva le due righe legate padre/figlia da settembre, ma
nessuno aveva verificato che `fatture_righe` **non ha** una colonna per
reggerle. Era un lavoro dichiarato bloccato su un prerequisito che non era mai
stato chiesto.

---

## 🔨 Cosa è stato costruito — 2026-08-31 (4)

> ⚠️ **Istantanea del lavoro, non dello stato del database.** Cosa sia
> **applicato** si chiede a `databasechangelog`, non a questa tabella.

| # | changeSet | Cosa |
| --- | --- | --- |
| **2** | `20260831-24` | i tre codici dell'atto in `v_testata_allowed` di `fn_create_contratto` |
| **4** | `20260831-25` | `vendite.fatture_atti` — tabella, `UNIQUE (fattura, contratto)` e `UNIQUE (id, fattura_id)` per la FK composita |
| **4** | `20260831-26` | `fatture_righe.fattura_atto_id` + **FK composita** `(fattura_atto_id, fattura_id)` |
| **4** | `20260831-27` | `fatture_indirizzi` ← `storicizza`; `fatture_riepiloghi_iva` ← `tx_id` + `storicizza` |
| **4** | `20260831-28` | montaggio di `trgfn_fattura_satellite_guard_congelamento` su `fatture_atti` |
| **4** | `20260831-29` | seed `fk_index_policy` (2 sì, 1 no motivato) |
| **5** | `20260831-30` | `fatture_righe.riga_capofila_id` + FK composita + `CHECK` non-se-stessa |
| **5** | `20260831-31` | `trgfn_fatture_righe_guard_riga_capofila` — «niente catene», **due rami** |
| **5** | `20260831-32` | `vw_fattura_righe_esposte` conosce la riga spezzata (`PARTE_PLAFOND`) |
| **5** | `20260831-33` | seed `fk_index_policy` per il legame capofila |
| **5** | — | `E_FATTURA_RIGA_CAPOFILA_INCOERENTE` (`TECNICO`, msg **1033**), append ai due CSV |
| **3** | `20260831-36` | `fn_check_parameter_fk_surrogate`: il vuoto vale come assenza |
| **3** | — | riga 5 in `parameter_fk_surrogate.csv`; `DEFAULT_IVA_ID`→`DEFAULT_IVA`, valore `22` |

**pgTAP**: `test-fn-create-contratto-v1` (casi 13-15, aggiunti al file
esistente), `test-fatture-atti-v1` (11), `test-fatture-righe-capofila-v1` (10),
`test-parameter-fk-surrogate-vuoto-v1` (8+fixture), più le due classificazioni in
`test-cleanup-fattura-copertura-figlie-v1`, che è **diventato rosso due volte e
ha fatto il nome** — di `vendite.fatture_atti` al primo livello e di
`fk_fatture_righe_riga_capofila` al secondo. È il lavoro per cui esiste.

⭐ **Ogni presidio è stato provato per MUTAZIONE**, non solo visto verde: FK
semplice al posto della composita (cade il caso della fattura altrui), guard
senza il ramo all'indietro (cade quel caso e solo quello), trigger di
congelamento non montato, whitelist vecchia, funzione della check vecchia.

⚠️ **Un difetto trovato dalla mutazione e corretto**: nel test degli atti il caso
«sotto la soglia si scrive» riusava la stessa coppia del caso precedente, quindi
dipendeva dal **fallimento** di quello — togliendo il trigger davano rosso in
due, e il secondo indicava il posto sbagliato.

### ⚠️ Due cose da sapere prima di applicare

* ⛔ **`20260831-31` aveva una preCondition sbagliata e ha fatto FALLIRE il
  migrate** (`Expected '1' got '0'`): controllava che il codice errore fosse a
  catalogo, ma `20_code` gira **prima** di `80_data`, quindi quel seed non c'è
  ancora. Corretta — la preCondition resta sulla sola colonna, e che il codice
  esista lo verifica il pgTAP, che gira dopo tutto il migrate. È la regola già
  scritta in `feedback_liquibase_phase_ordering_preconditions`, ricaduta;
* ⚠️ **fra il commit e il migrate `test-cleanup-fattura-copertura-figlie-v1` è
  ROSSO** su due asserzioni («voce dell'inventario sparita dal catalogo»): le
  classificazioni precedono le tabelle. Rientra da sé con l'apply — non è una
  regressione da inseguire.

---

## Le decisioni — quattro, prese da Tid il 2026-08-31

> Non si ri-discutono a valle. Ognuna sta anche nella sua voce, con il perché:
> qui c'è l'elenco per chi deve sapere **cosa è già chiuso** senza rileggere tutto.

| | La domanda | La risposta |
| --- | --- | --- |
| **A** | `parameters.csv` non è riscrivibile: come si disinnesca? | ⭐ **La stringa vuota vale come «nessun default»** — si insegna a `script.fn_check_parameter_fk_surrogate` che su un parametro `''` è l'assenza. Voce 3 |
| **B** | Le due parti di una riga spezzata, come si vedono legate? | **Due righe sorelle**: `tipo_riga` nuovo, entrambe a `livello 0`, stesso `ordinamento` della capofila. ⛔ **Non** la forma del kit. Voce 5 |
| **C** | `fatture_atti`: `tx_id` e `storicizza`? | **`tx_id` sì**; **`storicizza` presente ma `DEFAULT false`**. E si chiude lo stesso buco su `fatture_indirizzi` e `fatture_riepiloghi_iva`. Voce 4 |
| **D** | «Stessa fattura»: guard o vincolo? | ⭐ **Vincolo** (FK composita). Il guard resta solo per «niente catene», che un vincolo non sa esprimere. Voce 5 |

---

## 1. ~~⛔ Il seed di `E_DOCUMENTO_DATA_ANTERIORE_ULTIMO_NUMERO`~~ ✅ FATTO

> ✅ **CHIUSA il 2026-08-31**, verificato su `46fbf56ab`:
> [codici_errore.csv:822](../../../../db/changelog/migrations_v2/80_data/sql/config/codici_errore.csv) e
> [messaggi_errore.csv:819](../../../../db/changelog/migrations_v2/80_data/sql/config/messaggi_errore.csv)
> (id messaggio **1030**), committati, working tree pulito.
>
> ⛔ **E il messaggio da dare al backend NON è «il quinto è arrivato».** Nello
> stesso giro sono entrati **altri due** codici che questo elenco non nominava,
> dai changeSet `20260831-18` e `-23`:
>
> | Codice | Classe | id msg | Origine |
> | --- | --- | --- | --- |
> | `E_DOCUMENTO_DATA_ANTERIORE_ULTIMO_NUMERO` | `DATO_ERRATO` | 1030 | registri, C2-6/7 |
> | `E_FAMIGLIA_DOCUMENTO_RIFERIMENTO_INESISTENTE` | `TECNICO` | 1031 | registri, C2-18 |
> | `E_EMITTENTE_CODICE_FORMA_NON_VALIDA` | `DATO_ERRATO` | 1032 | registri, §5.4 |
>
> ⇒ **Il cancello `F0` ora ne trova UNDICI, non nove**, e la corsa unica di
> `genera_error_policies` va fatta su quel numero. ⚠️ Se il BE rigenera
> contando nove, il `--check` — che confronta **carattere per carattere** —
> torna rosso in CI il giorno dopo, su una PR che non c'entra. Il prossimo
> id messaggio libero è **1033**.
>
> ⭐ **E la lezione della voce regge, marcata e non cancellata**: il seed è
> arrivato il giorno dopo il codice, per la **seconda** volta nello stesso
> cantiere. Il modo di non ripeterlo è la voce `C1-4` del piano dei registri —
> *«solo append al CSV»*, nello stesso commit del codice che lo solleva.

**Il testo originale, per la storia:**

**Non c'è un brief: è una riga.** Due, per la precisione — una in
`codici_errore.csv` e una in `messaggi_errore.csv`.

**Verificato il 2026-08-31**: il codice **non esiste in nessun punto di git** —
né nei due CSV, né in un changeSet, né in un brief. Esiste **solo sul database
di sviluppo**. Viene dal cantiere
[registri di numerazione](brief-db-registri-di-numerazione-emittente-e-trasloco.md).

**Cosa blocca.** Il backend non può rigenerare `error_policies_generated.py`.
`manage.py genera_error_policies --check` gira in CI e confronta il file
**carattere per carattere** col catalogo: in CI il database si ricostruisce da
zero, quindi quel codice non c'è e il file rigenerato risulterebbe divergente —
rosso su una PR che coi registri non c'entra niente.

⇒ Finché manca, **nove** codici restano senza policy: i quattro dell'IVA, i tre
dell'annullo forzatura, quello del registro emittente, e questo. Un codice senza
policy che il DB solleva arriva all'operatore come **400 «errore di
validazione»** invece che sulla sua classe — su un `TECNICO` significa dire «hai
sbagliato tu» per un guasto.

⚠️ **E va detto perché è la seconda volta.** Il 2026-08-30 era successo identico
con `E_FATTURA_REGISTRO_EMITTENTE_INCOERENTE`, dello **stesso** cantiere:
applicato sul DB di sviluppo, seminato il giorno dopo. Non è un rimprovero — è
che finché il seed arriva in ritardo il cancello dei codici resta rosso e nessun
altro lavoro può rigenerare quel file. ⭐ Il modo di non ripeterlo è quello che
il piano dei registri già scrive alla voce **C1-4**: *«solo append al CSV»*,
nello stesso commit del codice che lo solleva.

---

## 2. `fn_create_contratto` non whitelista i tre riferimenti dell'atto

📌 **Brief:** [brief-db-fn-create-contratto-codici-atto.md](brief-db-fn-create-contratto-codici-atto.md)
(scritto il 2026-08-29).

**La richiesta, per intero:** estendere `v_testata_allowed` di
`vendite.fn_create_contratto` con `'codice_cig'`, `'codice_cup'`,
`'codice_commessa'`. Nient'altro: le tre colonne esistono già coi loro
`COMMENT`.

**Verificato il 2026-08-31**: la whitelist non li contiene ancora.

**Cosa blocca.** La slice `S3-b`: in **PATCH** il backend li scrive già, in
**CREATE** no — e la funzione non solleva, **scarta**. Il contratto nasce,
l'operatore non vede errori, e il CIG non va da nessuna parte.

⚠️ Le tre avvertenze (changeSet nuovo, corpo dalla doc auto-gen e non dallo
YAML, `COMMENT` aggiornato) sono nel brief. ⭐ E il motivo per cui non è una
comodità: **è lo stesso difetto già costato un giro su questa stessa funzione**
il 2026-07-27 con `fatturazione_immediata`, documentato nel commento che gli sta
accanto.

---

## 3. `DEFAULT_IVA_ID` è l'ultimo parametro che stocca un id

📌 **Brief:** [brief-db-default-iva-chiave-naturale.md](brief-db-default-iva-chiave-naturale.md).

**La richiesta, per intero:**

1. rinominare il parametro `DEFAULT_IVA_ID` → `DEFAULT_IVA`;
2. cambiarne il valore da `16` al `codice_interno` corrispondente, e riscrivere
   la descrizione (che oggi cita `config.iva.id=16`);
3. una riga in `config.parameter_fk_surrogate`: `code_pattern` EXACT su
   `DEFAULT_IVA`, target `config.iva.codice_interno`.

**Verificato il 2026-08-31**: il seed dice ancora `DEFAULT_IVA_ID,16`.

⭐ **La condizione che lo bloccava è caduta**: `linee-guida-sql §6b` nomina
proprio questo parametro come tech debt e descrive quattro passi; i primi due
(`codice_interno` su `config.iva` + lock automatico) li ha fatti `D28`
(`20260829-43`). Restano il terzo e il quarto, che sono seed.

⚠️ **Il lettore BE si adegua nello stesso giro, non prima** — è uno solo, il
form-defaults dell'articolo. Se il seed cambia da solo, quel lettore cerca un
parametro che non c'è più e prende il ripiego.

### ⛔ Il prerequisito che nessuno aveva chiesto: `parameters.csv` non è riscrivibile

> **Trovato il 2026-08-31 (3)**, verificando la voce prima di scriverla. È il
> motivo per cui questa voce **è scesa in fondo all'ordine**: la riga
> *«costa minuti»* era vera solo finché nessuno aveva guardato il file.

La richiesta è editare una riga di
[parameters.csv](../../../../db/changelog/migrations_v2/80_data/sql/config/parameters.csv).
⛔ **Quel file non si può toccare**, e la storia è già scritta nell'intestazione
di `20260826-03`, dove è esplosa il 2026-08-25:

* il mirror `20250715-01-upsert_parameters` è `runOnChange: true`: **qualunque**
  modifica al CSV ne cambia il checksum e lo **sveglia**;
* svegliato, rilegge tutto il file — riga 11 compresa: `12,DEFAULT_UTILITY,`
  con `default_value` **stringa vuota**;
* `config.trgfn_parameters_fk_surrogate_dispatch` esce presto **solo su `NULL`**;
  su `''` chiama la check, che cerca `''` in `config.utilities.codice_interno`
  e non lo trova → `E_PARAMETER_DEFAULT_VALUE_INVALID` → **migrate fermo**.

⛔ **E la via d'uscita ovvia è chiusa**: mettere il token `NULL` nella cella non
si può, perché `config.parameters.default_value` è **`NOT NULL`** (verificato
sulla doc auto-generata). Quella riga oggi non può contenere **né `''` né
`NULL`**: è irriscrivibile in entrambi i versi.

⚠️ **E non si aggira con un CSV dedicato ri-ancorato**, che sarebbe il pattern
di casa: lascerebbe in `parameters.csv` una riga `DEFAULT_IVA_ID,16` **stantia**
davanti a un mirror `runOnChange` **dormiente**. Il primo che tocca quel file
per un altro motivo riporta indietro il parametro, in silenzio — è la trappola
armata che il progetto ha già catalogato, costruita di proposito.

#### ✅ Decisione `A` (Tid, 2026-08-31): la stringa vuota **è** l'assenza

Si insegna a `script.fn_check_parameter_fk_surrogate` che su un parametro il
valore vuoto vale come «nessun default», esattamente come il `NULL` — cioè si
allarga il ramo di uscita in testa da `p_value IS NULL` a *«nullo o vuoto»*.

⭐ **E l'argomento è sul modello, non sul far passare il migrate**: la colonna è
`NOT NULL`, quindi su `config.parameters` la stringa vuota **è l'unica forma che
"nessun valore" può assumere**. Il ramo `NULL` della check, per quella tabella,
è codice irraggiungibile: serve solo agli override, dove la colonna è un'altra.
La funzione oggi dichiara una regola che sulla sua tabella principale non può
mai applicarsi — e la riga `DEFAULT_UTILITY` è il controesempio che lo dimostra.

⛔ **Le due alternative sono state scartate, e vanno sapute:** dare a
`DEFAULT_UTILITY` un `codice_interno` vero **cambia il comportamento** delle
maschere che oggi non propongono nulla; `enabled = false` sulla riga di registry
**toglie il presidio** proprio mentre se ne sta aggiungendo un altro.

#### L'ordine dei passi, che da qui in poi è obbligato

1. **`20_code`** — `script.fn_check_parameter_fk_surrogate`: il vuoto passa come
   il nullo. ⚠️ Serve un pgTAP che provi **entrambi**: `''` ammesso, un codice
   inesistente ancora **rifiutato**. Senza il secondo si sta allargando un
   cancello senza verificare che regga ancora;
2. **`80_data`** — la riga di registry: `code_pattern` EXACT `DEFAULT_IVA`,
   target `config.iva.codice_interno`;
3. **`80_data`** — `parameters.csv`: `DEFAULT_IVA_ID` → `DEFAULT_IVA`, valore
   `16` → **`22`** (il `codice_interno` della riga `id = 16`, verificato sul
   seed di `config.iva`), descrizione riscritta senza `config.iva.id=16`.
   ⚠️ L'`id` della riga resta **11**: il mirror è un `loadUpdateData` con
   `primaryKey: id`, quindi è un `UPDATE` e non nasce nessun orfano.

⚠️ **Il passo 1 viene PRIMA del 3 per forza**: il passo 3 sveglia il mirror, e
il mirror rilegge la riga `DEFAULT_UTILITY`. Se la check non è ancora stata
allargata, il migrate si ferma lì — cioè il difetto che questa sezione esiste
per evitare, riprodotto.

⚠️ **Una trappola sul valore, per chi scriverà il lettore BE.** Il nuovo valore
è **`22`**, che è un numero. Un lettore rimasto indietro che facesse `int(...)`
non fallirebbe: otterrebbe l'**id 22**, che oggi in `config.iva` non esiste — ma
che il modello **ammette** eccome, e il giorno che esistesse sarebbe un'aliquota
sbagliata applicata in silenzio. È la ragione per cui il gemello negativo del
brief — `DEFAULT_IVA_ID` cercato per nome nudo in `backend/` e nei seed, zero
occorrenze — **non è una formalità**: è l'unica prova che nessun lettore vecchio
è sopravvissuto.

---

## 4. ⭐ `vendite.fatture_atti` — il satellite dei riferimenti dell'atto

📌 **Brief:** [brief-db-fatture-atti-riferimenti-contratto.md](brief-db-fatture-atti-riferimenti-contratto.md).
⚠️ **Questa è l'unica voce in cui il ragionamento serve davvero**: la forma è
stata scelta dopo aver verificato come la FatturaPA modella il blocco.

**La richiesta, in sintesi** (dettaglio, vincoli e presidi nel brief):

* tabella `vendite.fatture_atti` — una riga per `(fattura, contratto)`, con lo
  **snapshot** di numero, data e i tre codici;
* `vendite.fatture_righe.fattura_atto_id`, **nullable**, FK verso quella;
* montare `trgfn_fattura_satellite_guard_congelamento` (⭐ è già parametrica da
  `D34`: basta `TG_ARGV = ('fattura_id')`, **nessun codice errore nuovo**);
* classificare la tabella in `test-cleanup-fattura-copertura-figlie-v1.sql`,
  che diventerà rosso e ne farà il nome — ⚠️ e la sua intestazione dice che la
  categoria si **decide**, non si aggiunge per far tornare il verde.

**Verificato il 2026-08-31**: la tabella non esiste.

**Cosa blocca.** `I4` — la riga di fattura che ri-risolve l'IVA e porta i
riferimenti dell'atto — e a cascata `I6`, che è l'ultima voce del cantiere IVA.
⚠️ Da sola non basta: serve anche la **5**.

⛔ **Non è «una colonna», ed è il motivo per cui c'è un brief**: una riga
FatturaPA porta **un** blocco `DatiContratto` per atto, con
`RiferimentoNumeroLinea` a puntare le sue righe. Una fattura può mescolare
contratti diversi, quindi né la testata né una colonna di riga reggono il caso.

✅ **La metà BE è FATTA** (2026-08-31, prima della tabella e apposta):
`contratto_id` è entrato nella chiave di aggregazione delle righe di fattura —
senza, il satellite sarebbe una sede che non si può riempire, perché una riga
aggregata apparterrebbe a due atti. Finché la tabella non c'è l'atto della riga
vive nello `meta` (`group_key.contratto_id`), quindi al momento del popolamento
**il dato per riempirla esiste già**.

### ✅ Decisione `C` (Tid, 2026-08-31) — `tx_id` sì, `storicizza` presente e spento

⛔ **Il brief figlio dice «audit + `tx_id` + `storicizza`: convenzione di
progetto». Quella convenzione uniforme NON esiste** — verificato sulla doc
auto-generata dei cinque parenti stretti:

| Tabella | `tx_id` | `storicizza` |
| --- | --- | --- |
| `fatture` (testata) | sì | **acceso** |
| `fatture_scadenze` | sì | **acceso** |
| `fatture_righe` | sì | **spento** (`DEFAULT false`) |
| `fatture_indirizzi` | sì | *la colonna non c'è* |
| `fatture_riepiloghi_iva` | **no** | *la colonna non c'è* |

Cinque tabelle della stessa famiglia, **quattro comportamenti diversi**: non è
una convenzione, è una scelta caso per caso, e va fatta guardando cosa la
tabella *è*.

**`tx_id`: sì.** Quattro su cinque ce l'hanno, e l'unica che non ce l'ha è la più
vecchia e la più sguarnita del gruppo — quella che non ha nemmeno il guard di
congelamento montato. Non è il modello da seguire, è il buco da chiudere. E qui
il timbro serve davvero: le righe di `fatture_atti` nascono **nella stessa
transazione** delle righe di fattura, ed è esattamente il legame che il `tx_id`
esiste per registrare.

**`storicizza`: colonna presente, `NOT NULL DEFAULT false`** — come
`fatture_righe`. ⭐ **Il criterio è il ciclo di vita**, e spiega da solo la
tabella qui sopra: `fatture` e `fatture_scadenze` sono cose che **vivono** (una
testata cambia stato, un piano rate si rinegozia) e sapere com'erano prima è
informazione vera; `fatture_righe`, `fatture_indirizzi` e
`fatture_riepiloghi_iva` sono cose che si **rifanno** — buttate e ricalcolate a
ogni rigenerazione del lotto finché la fattura è in bozza, intoccabili dopo il
congelamento. Tenerne la storia significa riempire una gemella con dieci
versioni identiche di un calcolo intermedio: rumore che nasconde il segnale.
`fatture_atti` sta senza dubbi nel secondo gruppo — è letteralmente la faccia
«atto» della stessa scrittura delle righe.

⇒ Con il flag spento non serve la riga in `config.storico_set_storicizza`.

### ✅ E si chiudono i due buchi vecchi (Tid, 2026-08-31)

Dato che si apre la famiglia, si allineano anche le due tabelle rimaste
indietro — **non è scope creep, è togliere il precedente sbagliato** che il
prossimo lettore userebbe come modello:

* `vendite.fatture_indirizzi` ← `storicizza` (`NOT NULL DEFAULT false`);
* `vendite.fatture_riepiloghi_iva` ← **`tx_id` e `storicizza`** (stesso default).

⭐ **Verificato che è sicuro**: tutti gli scrittori di quelle due tabelle usano
`INSERT` con l'**elenco delle colonne esplicito**
([fn_snapshot_indirizzi_fattura](/dbzero/vendite/funzioni/fn_snapshot_indirizzi_fattura),
[fn_ricalcola_riepilogo_iva_fattura](/dbzero/vendite/funzioni/fn_ricalcola_riepilogo_iva_fattura)),
e nessuna vista o funzione fa `SELECT *` su di esse. La modifica è puramente
additiva.

⚠️ **Conseguenza messa in conto**: la sola presenza della colonna `storicizza`
fa nascere **due gemelle vuote** in `storico` — l'automazione le provisiona
dalla colonna, non dal valore del flag. Si vede da `storico.fatture_righe`, che
esiste benché lì il flag sia spento. È il prezzo di lasciare la porta aperta.

📌 **Resta fuori, ed è una voce a sé**: `fatture_riepiloghi_iva` è l'unico
satellite di fattura su cui il **guard di congelamento non è montato**. Il
`COMMENT` della funzione parametrica lo nomina già come caso futuro
(*«e (quando servirà) fatture_riepiloghi_iva»*). Non si fa in questo giro
perché tocca il ricalcolo del riepilogo, che ha una sua soglia da verificare
prima — ma va deciso, non dimenticato.

### ✅ L'ordine delle `ON DELETE` — risolto, e non era una domanda aperta

Il brief figlio dichiara di non pronunciarsi. La risposta c'è ed è verificabile:

* `fatture_atti` → `vendite.fatture`: **`ON DELETE CASCADE`** (categoria
  `CASCADE_DB`, il blocco è uno snapshot di *quella* fattura e muore con lei);
* `fatture_righe.fattura_atto_id` → `fatture_atti`: **`NO ACTION`** (il default).

⭐ **Non esplode, e il motivo è nel momento in cui la `NO ACTION` si verifica**:
è controllata **a fine istruzione**, quando entrambe le cascate della `DELETE`
sulla testata sono già passate — quindi non c'è nessun istante in cui una riga
viva punta a un atto già morto. E sul percorso della pulizia il caso non si pone
nemmeno: [fn_cleanup_fatture_by_ids](/dbzero/vendite/funzioni/fn_cleanup_fatture_by_ids)
cancella `fatture_righe` **prima** di `fatture`.

⚠️ **Va provato con un pgTAP, non dedotto**: cancellare una fattura che ha
insieme righe **e** atti, e vederla passare. È l'unica prova che quel
ragionamento sull'ordine è giusto.

---

## 5. ⭐ `vendite.fatture_righe` — la riga capofila, per la riga che si spezza

📌 **Il ragionamento è già scritto**, e non si ricopia: decisione `N3` del
[piano BE/FE di Fase 3](../work-done/brief-be-fe-iva-fase-3-consumatori-risolutore.md#n3), §3.

**Il fatto.** In fattura il risolutore riceve l'imponibile **vero**, quindi può
tornare **due** parti: la quota che il plafond del titolo copre e il resto. Una
riga FatturaPA porta **una** `AliquotaIVA` e **una** `Natura` ⇒ due trattamenti
sullo stesso imponibile sono due `DettaglioLinee`, **per obbligo di formato**.
La spezzatura non si può evitare: si può solo decidere chi la regge.

**La scelta già fatta (`N3`, opzione `a'`)**: le due parti sono **due
`fatture_righe` in relazione padre/figlia**, e `attivita_fatturabili.
fattura_riga_id` continua a puntare la **capofila**. Dall'attività si raggiunge
la capofila, dalla capofila le sue parti. ⭐ Nessuna modifica a
`attivita_fatturabili`, nessuna unique violata, e `fatturato` —
`GENERATED ALWAYS AS (fattura_riga_id IS NOT NULL)` — resta `true` da sé.

**⛔ E la colonna che regge quel legame NON ESISTE.** Verificato il 2026-08-31
sulla doc auto-generata di `vendite.fatture_righe`: ci sono `kit_key`,
`kit_articolo_padre_id`, `kit_descrizione_padre` — e basta.

⚠️ **Riusare le colonne del kit sarebbe la scorciatoia sbagliata**, ed è il
motivo per cui questa voce esiste invece di non esistere: `kit_key` dice *«queste
righe vengono dallo stesso kit venduto»*. Una riga spezzata dal plafond non viene
da nessun kit, e marcarla così farebbe leggere al prossimo — e a
`vw_fattura_righe_esposte`, che le aggrega — un fatto che non è vero.

**La richiesta.**

1. `vendite.fatture_righe.riga_capofila_id`, **nullable**, FK verso
   `vendite.fatture_righe(id)`. `NULL` sulla capofila (che è essa stessa la
   prima parte), valorizzata sulle parti successive;
2. un guard che tenga **due** invarianti — e sono i due che, se violati,
   non darebbero nessun sintomo:
   * ⛔ **niente catene**: una riga con `riga_capofila_id` deve puntare a una
     riga che ce l'ha `NULL`. Senza, «capofila → parti» smette di essere una
     lettura a un salto e chi somma prende metà valore;
   * ⛔ **stessa fattura**: la capofila deve stare sulla `fattura_id` della
     parte. Una parte che punta a un altro documento è un totale che non torna
     su due fatture insieme.
3. ~~`vw_fattura_righe_esposte` deve conoscere la relazione nuova — ⭐ ma conosce
   già quella del kit, quindi la forma non si inventa.~~
   ⛔ **La seconda metà di questa riga è SBAGLIATA**, e la decisione `B` qui
   sotto la sostituisce: la forma del kit **aggrega**, e aggregare qui
   cancellerebbe la ragione per cui la riga si spezza. La vista deve conoscere
   la relazione — quello sì — ma con una forma **opposta** a quella del kit.

**Cosa blocca.** `I4`, esattamente come la voce 4 — e per la stessa slice.
⛔ Senza, la riga **non si può spezzare**, quindi il risolutore in fattura non si
può chiamare con l'imponibile vero, quindi il plafond non si consuma: il registro
costruito in Fase 2 resta una promessa.

**Presidio atteso.** ⭐ Quello che discrimina non è «la INSERT riesce» — riesce
comunque: è **una parte che punta a una parte** (la catena) e **una parte che
punta a una riga di un'altra fattura**, entrambe **rifiutate**. E il gemello
positivo: due parti sulla stessa capofila della stessa fattura, **ammesse**.
Senza il terzo, un guard che rifiuta sempre passerebbe i primi due.

⚠️ **Una nota sul momento, che è del BE ma va saputa anche qui**: la spezzatura
deve avvenire mentre la fattura è ancora `EMESSA`.
`trgfn_fattura_satellite_guard_congelamento` legge lo stato **vivo** al momento
della scrittura — in una transazione che porta prima a `DEFINITIVA` e poi scrive
le righe, il guard vede `congela_fiscale = t` e rifiuta.

### ✅ Decisione `B` (Tid, 2026-08-31) — due righe sorelle, non un padre e un figlio

**La domanda**: le due parti *devono* restare due righe esposte, ognuna col suo
imponibile — lo impone la FatturaPA, e su questo non c'è scelta. Ma a video
l'operatore vedrà due righe con lo stesso articolo, la stessa descrizione, lo
stesso prezzo e **quantità non tonde** («6,3492» e «4,2328» invece di «10»). Se
sono scollegate, chi legge pensa a un errore di caricamento. Come si mostrano
legate?

**La risposta: `tipo_riga` nuovo, entrambe a `livello 0`, stesso `ordinamento`.**
Le due parti restano righe **pari e adiacenti**; la seconda porta un
`tipo_riga` suo (per esempio `PARTE_PLAFOND`); `ordinamento` è quello della
capofila su entrambe, così restano attaccate anche se in tabella hanno `riga_nr`
diversi.

⛔ **Scartata la forma «la parte rientra sotto la capofila» (`livello 1`), e non
è una preferenza estetica.** Nella vista `livello 1` significa oggi una cosa
precisa: *riga descrittiva, senza importo*. I componenti di kit escono infatti
con `imponibile` a `NULL`, perché il loro valore è già dentro il totale del
padre — e chi li sommasse raddoppierebbe il documento. La parte staccata dal
plafond è l'opposto: ha un importo **suo e vero**, che nel totale ci deve stare.
⚠️ Il codice che fa *«salta il livello 1, è solo descrizione»* **esiste, perché
è la regola della vista**: su una fattura spezzata perderebbe la seconda parte
**senza nessun errore**, con un totale semplicemente più basso.

⭐ La strada scelta non riusa nessun significato esistente: aggiunge
un'etichetta nuova per un caso nuovo, e lascia `livello` a dire quello che ha
sempre detto.

📌 In entrambi i casi il generatore XML non cambia: emette due `DettaglioLinee`
comunque. Qui si decide solo **cosa vedono gli occhi** in PDF e portale.

### ✅ Decisione `D` (Tid, 2026-08-31) — «stessa fattura» è un vincolo, non un guard

Delle due invarianti del punto 2, **una sola resta al trigger**.

**«Stessa fattura» → FK composita.** Invece di puntare *«a una riga»*, la parte
punta *«a una riga **e** alla sua fattura»*:

```text
FK (riga_capofila_id, fattura_id) -> vendite.fatture_righe (id, fattura_id)
```

⭐ **Non è una verifica che qualcuno esegue: è una condizione che il database
non lascia violare** — da uno script, da una migrazione, da un errore in un
servizio. È l'invariante da cui dipendono i totali di **due** documenti insieme:
merita una garanzia, non una sorveglianza che qualcuno può spegnere.

⭐ **E un dettaglio casca a fagiolo**: con il comportamento standard di
PostgreSQL (`MATCH SIMPLE`), quando `riga_capofila_id` è `NULL` il vincolo
**non si applica affatto**. Su tutte le righe normali e su tutte le capofila non
costa niente e non serve nessuna eccezione scritta.

⚠️ **Il prezzo, ed è l'unico: un indice.** Per essere bersaglio di una FK la
coppia `(id, fattura_id)` va dichiarata `UNIQUE`. Lo è già di suo — `id` è la
chiave primaria — ma PostgreSQL pretende l'indice fisico. Quindi nasce un indice
che, dal punto di vista di *«impedisce doppioni?»*, è **ridondante**, e
comparirà in `dbops.vw_duplicate_indexes`. **Va scritto nel changeSet**, o il
prossimo lo legge come una svista e prova a cancellarlo. ⭐ La rete c'è
comunque: la seconda guardia di `apply_fk_index_policy()` **rifiuta il `DROP`**
di un indice che sostiene un vincolo, con un warning invece di rompere qualcosa
in silenzio.

**«Niente catene» → resta il trigger.** Per verificarla bisogna **guardare la
riga puntata** e vedere se lei a sua volta punta a qualcuno: nessun vincolo di
PostgreSQL sa fare questa domanda. ⛔ Esiste un modo per renderla strutturale
anche lei, ma costa una colonna artificiale il cui unico scopo è ingannare il
meccanismo dei vincoli: il prossimo lettore non capirebbe cosa sta guardando.
**Scartato.**

### ⚠️ Il codice errore del guard — va coniato, e il brief non lo diceva

Il guard anti-catena **solleva**, quindi gli serve un codice registrato a
catalogo. ⛔ `E_PARAMETRO_INVALIDO` **non è una sede**: è un debito dichiarato
(`D11` di `brief-db-be-classe-codici-errore`), non un posto dove mettere roba
nuova.

**Classe `TECNICO`**, e la ragione è il criterio di casa — *si guarda chi può
rimediare*: quel legame non lo digita nessuno in un form, lo scrive
l'orchestrazione del backend che spezza la riga. ⇒ Su un `TECNICO` la chiave
`campo` **esce** dal contesto: non c'è nessun campo da accendere.

Prossimo id messaggio libero: **1033**.

### Il montaggio del trigger, e perché il nome conta

Il guard va montato come `trg_fatture_righe_a10_guard_riga_capofila_ins_upd`.
⚠️ **Il nome non è cosmetico**: i `BEFORE … FOR EACH ROW` di PostgreSQL scattano
in **ordine alfabetico**, e su questa tabella c'è già
`trg_fatture_righe_a10_guard_congelamento_ins_upd_dlt`. Con `guard_riga_…` il
nuovo scatta **dopo** — così su una fattura congelata a parlare è il messaggio
giusto («è congelata»), non quello sulla capofila.

---

## ✅ Cosa NON è più da fare

⭐ **L'annullo di una forzatura è APPLICATO** (merge `#1438`, 2026-08-31):
`anagrafiche.soggetti_titoli_iva_movimenti.annulla_movimento_id` c'è, con
`CHECK`, FK, unique e guard trigger. Il brief
[brief-db-titoli-iva-movimenti-annullo.md](brief-db-titoli-iva-movimenti-annullo.md)
è chiuso, e sblocca `T3-b` del [piano BE/FE dei titoli](brief-be-fe-titoli-iva-soggetto.md).

---

## 📌 Le richieste nel verso opposto — DB → backend

Questo elenco raccoglie ciò che il **backend chiede al DB**. Ciò che il DB
chiede al backend non si ricopia qui: sta nel piano di Fase 3
([brief-be-fe-iva-fase-3-consumatori-risolutore.md](brief-be-fe-iva-fase-3-consumatori-risolutore.md)),
e al 2026-08-31 sono tre:

* ⛔ **`F0` sono UNDICI codici, non cinque né nove** — vedi la voce 1 qui sopra;
* **l'ordinamento delle righe di fattura per `codice` articolo** (decisione di
  Tid, 2026-08-31): oggi la chiave di ordinamento è l'**UUID** dell'articolo, che
  è deterministico e illeggibile;
* **le tre chiavi in `_CREATE_KEYS_TESTATA`** quando la voce 2 sarà applicata.

---

## Diario

| Data | Cosa |
| --- | --- |
| 2026-08-31 (4) | 🔨 **Costruite le voci 2, 3, 4 e 5** — 12 changeSet (`20260831-24..33` + `-36`), 4 file pgTAP e 2 classificazioni nell'inventario della pulizia. ⭐ Ogni presidio provato per **mutazione**, non solo visto verde: FK semplice al posto della composita, guard senza il ramo all'indietro, trigger di congelamento non montato, whitelist vecchia, check vecchia — ognuna fa cadere **il caso suo e solo quello**. ⛔ Due ricadute su regole gia' scritte: una preCondition di `20_code` su un seed di `80_data` ha fatto **fallire il migrate**, e un `csv.writer` ha ri-quotato 11 righe di `parameters.csv` che non c'entravano (ripristinato, sostituita la sola riga 11). ⚠️ Un difetto del test trovato **dalla mutazione**: un caso riusava la coppia del precedente e dipendeva dal suo fallimento |
| 2026-08-31 (3) | ⭐ **Ri-verificate tutte e cinque le voci su `46fbf56ab` prima di scrivere codice**, e la verifica ha spostato l'ordine di lavoro: la **voce 1 era già fatta** (e i codici seminati sono **tre**, non uno — `F0` ne conta undici); la **voce 3 è scesa in fondo** perché `parameters.csv` non è riscrivibile e il disinnesco è un passo che nessuno aveva chiesto; ⛔ della **voce 5** una riga era **sbagliata** — «la forma del kit non si inventa»: la forma del kit *aggrega*, e qui aggregare cancella la ragione della spezzatura. Prese le quattro decisioni `A`–`D`. ⛔ **Nessun file scritto lato DB**: il lavoro riprende da qui |
| 2026-08-31 (2) | ⭐ **Aggiunta la voce 5** — la colonna capofila su `fatture_righe`. Trovata rispondendo alla domanda «c'è qualcosa di Fase 3 che non aspetta il DB?»: `N3` sceglieva le due righe legate da giorni, ma nessuno aveva verificato che la sede del legame non esiste. ⛔ Il lavoro risultava bloccato su un prerequisito **mai chiesto**. Nello stesso giro la metà BE della voce 4 (`contratto_id` nella chiave di aggregazione) è passata da «da fare» a **fatta** |
| 2026-08-31 | Elenco nato dalla richiesta di Tid, dopo che le richieste al DB erano diventate quattro e nate in momenti diversi — la stessa dispersione che il §8-nonies del brief madre aveva già risolto con un elenco unico. ⭐ Scritto verificando **tutte e quattro sul repo**, non ricordandole: una era già stata applicata (l'annullo) e una era cambiata sotto (il seed del codice errore, arrivato per un codice e mancante per un altro dello stesso cantiere) |
