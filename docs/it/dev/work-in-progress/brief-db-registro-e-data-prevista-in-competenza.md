# Brief DB — il registro e la data che il documento prenderà, in lista

> **Destinatario:** team DB (`dev/db-tid`). BE e FE **attendono** i prerequisiti
> ([[feedback_be_fe_attende_prerequisiti_db]]).
>
> **Origine.** Tid, 2026-08-26, dopo un caso reale: *«sulle liste competenza
> fattura non si può aggiungere se front/back, in pratica il tipo di registro?»*
> La domanda nasce da mezz'ora persa a capire perché un documento appena
> generato portasse la data del 31 luglio.
>
> **Correlati:** [brief-db-numerazione-data-documento-e-sequenza.md](brief-db-numerazione-data-documento-e-sequenza.md)
> (il cantiere che ha reso la data una decisione del registro) ·
> [analisi-numerazione-fattura-data-e-sequenza.md](analisi-numerazione-fattura-data-e-sequenza.md)
>
> **Vicino ma senza intersezioni:**
> [brief-db-lavoro-che-non-torna-indietro.md](brief-db-lavoro-che-non-torna-indietro.md)
> (attività orfane e «Riporta da emettere»). Verificato il 2026-08-26: **non tocca
> nessuna funzione né vista di questo cantiere**. Condivide però la classe di
> difetto — *lavoro che esce dal giro senza un errore* — e una trappola
> identica: la vista della dashboard è fail-closed senza contesto operatore
> (loro §7.3, qui R-11 e T8).
>
> ⛔ **Intrecciato, non solo correlato:**
> [brief-db-limite-emissione-e-data-verificata.md](../work-done/brief-db-limite-emissione-e-data-verificata.md).
> Quel cantiere fa `DROP + CREATE` della stessa `fn_calcola_data_documento` che
> queste viste chiamano, aggiungendo `p_serie` — e lo fa **contando su DB-1 di
> qui**, che è ciò che dà la serie alle viste. ✅ **Consegna unica**, con l'ordine
> fissato in §12 D-8.
>
> ✅ **Decisioni prese** (Tid, 2026-08-26): D-2 «più registri» con data vuota,
> D-3 nessuna colonna sulla lista per commessa. D-1 verificata sul codice.
>
> ✅ **Stato: LATO DB CHIUSO — applicato il 2026-08-26.** Sei changeSet
> (`20260826-14` … `-19`), due righe di catalogo, un pgTAP 12/12 verde, doc
> concettuale delle due funzioni nuove. Migrazione applicata da Tid: **nessuna
> regressione, suite verde**. Restano solo le consegne BE/FE (§11.8).
>
> ⛔ ~~Stato: pronto per il team DB. Nessun file scritto.~~
>
> ⭐ **Revisione critica e piano: §10, §11, §12** (2026-08-26). La revisione
> aggiunge una consegna portante (**DB-0**, §11.1) senza la quale DB-1 non è
> scrivibile senza duplicare la regola, e corregge la firma di DB-1. Le sezioni
> 1-9 restano **come consegnate**: dove la revisione le supera, il punto è
> marcato sul posto e la spiegazione sta in §10.
>
> ❓ **Sei domande nuove** (D-4…D-9, §12). ✅ **Decise da Tid il 2026-08-26**:
> **D-4** — la frase «più registri» la mette BE/FE, il DB dice solo *quanti* sono;
> **D-9** — la previsione resta **vuota** dove il documento esiste già; **D-5** —
> il filtro per sezionale **si fa** (e con esso `registri_ids` sulla vista), **D-5b**
> per sezionale e non per politica della data.
> **D-7** — larghezze **libere**, come le altre undici; **D-8** — **consegna
> unica** insieme al cantiere gemello del limite di emissione, che riscrive la
> stessa `fn_calcola_data_documento`; **D-6** — **chiusa senza debito**:
> l'omogeneità dell'emittente nell'albero dei BA è imposta da un guard.
>
> ⭐ **Nessuna domanda aperta.** ✅ **D-10** (2026-08-26): il guard di
> `fn_get_registro_id` passa a un codice **TECNICO** — ⚠️ **status 400 → 500**,
> nota per il BE in §12.
> ⛔ Resta la dipendenza d'ordine con il gemello
> (§12 D-8): le viste non possono precedere il suo `DROP + CREATE`.

---

## 1. Il caso che lo motiva

Il 2026-08-25 Tid fattura un gruppo dalla Dashboard Competenza di **luglio**.
Nasce il lotto `LTF-0007307` con dentro un documento datato **31/07/2026**, e
lui se lo aspettava datato agosto — il giorno in cui stava lavorando.

Non è un difetto: il gruppo finiva sul registro **Back-office**, politica
`FINE_MESE_COMPETENZA`, quindi una competenza luglio produce un documento
datato l'ultimo giorno di luglio. È il comportamento voluto dal cantiere della
numerazione. **Ma non era scritto da nessuna parte prima di premere.**

⭐ La schermata da cui si decide di fatturare non dice né su quale **sezionale**
finirà il documento, né **che data** porterà. Sono le due informazioni che
governano tutto ciò che viene dopo — la sequenza dei numeri, la scheda
«recuperi del mese», il termine di trasmissione — e si scoprono a cose fatte.

---

## 2. Cosa si aggiunge: due colonne, e perché due

| colonna | cosa dice | perché |
| --- | --- | --- |
| `registro_codice` | `Front-office` / `Back-office` / … | è il **perché**: la politica della data vive sul registro |
| `data_documento_prevista` | `2026-07-31` | è il **cosa**: la data che il documento prenderà |

⭐ **Da sola la prima non basta**, ed è il motivo per cui sono due: «Back-office»
obbliga chi legge a tradurre registro → politica → data. La seconda risponde
alla domanda vera. La prima resta perché quando la data sorprende, il registro
è la spiegazione.

⚠️ **`data_documento_prevista` è una PREVISIONE, e il nome deve dirlo.** La
calcola `vendite.fn_calcola_data_documento(registro, competenza, NULL)`: è la
data che nascerà **se nessuno ne dichiara un'altra**. Un lotto creato con una
data dichiarata la scavalca — e va bene così, purché la colonna non prometta
una certezza.

**Su quale lista: la 42**, `vendite.dash_competenza_gruppi` — la lista da cui si
fattura. È lì che la domanda si pone, ed è lì che la risposta serve.

⚠️ **Non sulla 43** (`dash_competenza_commesse`), e non è una dimenticanza:
quella lista è aggregata **per commessa** (`n_attivita`, `valore_tot`,
`valore_fatturato_tot`), e una commessa attraversa per definizione più gruppi —
quindi potenzialmente più registri e più date. Metterci una colonna «registro»
vorrebbe dire mostrare «più registri» quasi sempre, cioè una colonna che non
informa. ✅ **D-3 DECISA** (Tid, 2026-08-26): **no**, la colonna non va sulla
lista per commessa. La lista errori (41) non c'entra.

---

## 3. ⛔ IL PUNTO DEL CANTIERE: la regola va LETTA, non riscritta

Il registro lo decide oggi `vendite.fn_build_fattura_key`, con questa catena:

```sql
-- da vendite.attivita_fatturabili a  JOIN anagrafiche.billing_account ba
v_ba_id         := a.billing_account_id
v_ba_fattura_id := COALESCE(ba.parent_account_id, a.billing_account_id)
v_utility_id    := ba.utility_id                      -- ⚠️ dalla BA DELLA RIGA
v_emittente_id  := anagrafiche.fn_get_emittente_fiscale_id(v_ba_fattura_id)
                                                      -- ⚠️ dalla BA DI FATTURAZIONE
(registro, serie) := vendite.fn_get_registro_id(tipo_doc, natura, utility, emittente)
```

⚠️ **Due ancoraggi diversi nella stessa chiave**: l'utility viene dalla BA della
riga, l'emittente dalla BA **di fatturazione** (il parent, quando c'è). Chi
ricopia la catena a occhio li scambia, e il difetto è silenzioso: la lista
mostrerebbe un registro e la fattura ne prenderebbe un altro.

⛔ **Ricopiare quella catena dentro le viste sarebbe una SECONDA implementazione
della stessa regola.** Non è un'ipotesi: è la classe di difetto che questo mese
ha già prodotto due incidenti — il messaggio del dialog che annunciava il
pavimento di un altro sezionale, e la colonna `riaperto` che leggeva l'indice
sbagliato. Una previsione che mente è peggio di una previsione assente.

### 3.1 ⭐ La forma giusta: estrarre, e chiamare in due

Nuova funzione che incapsula la catena **per intero**, dagli ingressi grezzi:

```sql
vendite.fn_resolve_registro_documento(
    p_billing_account_id  bigint,
    p_tipo_doc_fiscale_id bigint,
    p_natura_doc_id       bigint
) RETURNS TABLE(registro_id bigint, serie varchar,
                politica_data_documento varchar)
```

e **due chiamanti**:

* `fn_build_fattura_key` — che smette di risolvere in proprio e chiama questa
  (rifattorizzazione **a comportamento invariato**);
* le due viste della dashboard.

⭐ È la disciplina di [[feedback_estrarre_non_condividere_stato]] applicata a una
regola invece che a un oggetto: **si condivide la funzione, non una copia della
sua logica**. Ed è ciò che rende la colonna una lettura e non una profezia.

⚠️ **La rifattorizzazione va provata sul risultato, non sulla lettura del
codice**: per ogni fattura esistente il registro risolto dalla funzione nuova
deve coincidere con `fatture.registro_id` già scritto. È un confronto secco su
dati veri, e senza quello la «rifattorizzazione a comportamento invariato» è
una promessa.

---

## 4. ⛔ Il ponte NON c'è dove serve: misurato

L'idea più naturale — leggere gli ingressi da `attivita_fatturabili`, come fa
`fn_build_fattura_key` — **non funziona proprio sulla popolazione che conta**.
Misurato il 2026-08-26:

| stadio | con riga in `attivita_fatturabili` | SENZA |
| --- | ---: | ---: |
| **DA_EMETTERE** | 2 | **46** |
| EMESSA_NON_FATTURATA | 5 | 0 |
| FATTURATA | 43 | 0 |

⭐ **46 su 48.** La riga in `attivita_fatturabili` nasce all'**emit**: prima di
fatturare non esiste. E «prima di fatturare» è esattamente il momento in cui la
colonna serve — è il senso della richiesta.

> ⚠️ **Nota di metodo (2026-08-26).** La conclusione è giusta e la tabella qui
> sopra **non serve a sostenerla**: la riga in `attivita_fatturabili` la crea
> `fn_emit_attivita_fatturabili_da_commessa`, cioè **l'emit** — quindi prima di
> fatturare non esiste **per costruzione**, su qualunque database. I conteggi
> illustrano, non dimostrano; su un'installazione nuova sarebbero `0` e `0` e
> l'argomento resterebbe identico. Vedi `.codex/AGENTS.md` § «Le misure sul DB
> non progettano».

⚠️ Le 2 con la riga sono l'eccezione che spiega la regola: vengono da un lotto
**annullato**, e la riga è sopravvissuta al reset (è il «vaso» che il ri-emit
riempie di nuovo).

⛔ Conseguenza: la funzione di §3.1 deve accettare gli ingressi **grezzi**
(`billing_account_id`, `tipo_doc_fiscale_id`, `natura_doc_id`) e non un
`attivita_fatturabile_id`. Solo così serve entrambi i lati: chi ha già la riga
e chi non ce l'ha ancora.

### 4.1 ~~❓ La domanda aperta che ne discende (D-1)~~ ✅ CHIUSA

> ✅ **CHIUSA il 2026-08-26 (§10, R-12.1): sì, sono sempre la stessa.**
> `vendite.fn_emit_attivita_fatturabili_da_commessa` è l'**unica** funzione che
> scrive righe in `vendite.attivita_fatturabili` — verificato su `pg_proc`, e
> nessun `INSERT` diretto nel backend Python — e scrive
> `billing_account_id = v_commessa.billing_account_id` **sia sull'INSERT sia
> sull'UPDATE**. La vista può fermarsi alla commessa.
> ⚠️ Il dubbio qui sotto resta a testo perché è **il modo giusto di porre la
> domanda**; è la conclusione («non l'ho verificato») a essere superata.

`vendite.commesse_attivita` **non ha** `billing_account_id`: la BA sta sulla
**commessa** (`vw_dash_competenza_attivita.billing_account_id = co.billing_account_id`).
`attivita_fatturabili` invece ce l'ha **per riga**.

**Sono sempre la stessa?** Se l'emit copia la BA della commessa su ogni riga,
sì e la vista può usare quella della commessa. Se esiste un percorso che la
cambia per riga (destinatario diverso, split), allora **no**, e la previsione
sarebbe sbagliata proprio nei casi non banali.

⚠️ Non l'ho verificato e non lo do per buono: è la prima cosa da guardare, e la
risposta decide se la vista può fermarsi alla commessa o deve arrivare alla
riga.

---

## 5. ⚠️ Un gruppo può toccare PIÙ registri

La chiave del gruppo (`fn_build_gruppo_fatturabile_key`) è
`(sorgente_tipo, sorgente_uid, commessa)`: **non contiene tipo documento né
natura**. Un gruppo con righe di tipo diverso si separa in terne diverse e
finisce su registri diversi — è un fatto già noto e dichiarato («un gruppo con
righe di tipo doc fiscale diverso finisce in terne diverse»).

Quindi sulla lista **gruppi** le due colonne sono «uno oppure N»:

* un solo registro → il codice e la data;
* più registri → una dicitura esplicita (`più registri`), **mai il primo che
  capita**. ⛔ Un `min()` o un `LIMIT 1` qui sarebbe la stessa bugia del dialog:
  un valore plausibile che descrive solo una parte di ciò che sta per succedere.

Sulla lista **attività** (drill-down) il registro è invece sempre uno solo.

> ⚠️ **Corretto il 2026-08-26 (§10, R-12.3): quella lista non esiste.** A
> catalogo la 43 è `vendite.dash_competenza_commesse`, aggregata **per
> commessa**; una lista a grana *attività* non c'è. La frase resta vera come
> fatto sul **dato** (sotto la commessa, la singola attività ha un registro
> solo), ed è falsa come riferimento a una lista. Nessuna conseguenza sulle
> consegne: D-3 aveva già escluso la 43.

✅ **D-2 DECISA** (Tid, 2026-08-26): quando i registri sono più d'uno, il
registro mostra **«più registri»** e la data prevista resta **vuota**. Una data
sola su un gruppo che ne produrrà due è di nuovo una mezza verità.

---

## 6. Le consegne

> ⚠️ **Elenco rivisto il 2026-08-26.** La forma eseguibile, in ordine di
> dipendenza e con i nomi dei file, è in **§11.1**: quella tabella è la sede
> operativa, questa resta come consegna d'origine. Le differenze, tutte
> motivate in §10: **DB-0** è nuova e viene prima di tutto (R-2); la firma di
> DB-1 cambia (R-3, R-4); DB-5 è la sola lista 42 (R-12.2); DB-6 passa da 3 a 8
> asserzioni (R-5, R-1, R-8, R-11).

| | Cosa |
| --- | --- |
| **DB-0** | ⭐ **Aggiunta dalla revisione (§10, R-2).** `vendite.fn_lookup_registro_id` — il lookup del registro **senza** il raise, STABLE. Senza, DB-1 può solo ricopiare la gerarchia a quattro livelli (= la seconda implementazione che il §3 vieta) o ingoiare l'eccezione |
| **DB-1** | ~~`vendite.fn_resolve_registro_documento(ba, tipo_doc, natura)` → `(registro_id, serie, politica_data_documento)`~~ ⚠️ **firma rivista** (§11.2): il parametro è il BA **della riga** e il ritorno porta anche `ba_fatturazione_id`, `utility_id` ed `emittente_soggetto_ruolo_id` — altrimenti i due ancoraggi restano scritti in due posti (R-3) |
| **DB-2** | `fn_build_fattura_key` chiama DB-1 invece di risolvere in proprio. ⚠️ Comportamento invariato, **provato sul risultato**: per ogni fattura esistente il registro risolto deve coincidere con `fatture.registro_id` — ⛔ ma quel confronto **non può** provare i due ancoraggi, che si distinguono solo dove `parent_account_id` e' valorizzato (R-5): serve il caso costruito, T2 in §11.7 |
| **DB-3** | `vw_dash_competenza_attivita`: due colonne nuove via DB-1 (+ `fn_calcola_data_documento`). ⚠️ Sono quattro (§11.4), e la ragione non è una lista: è che la vista **gruppi** ci si appoggia (R-12.4) |
| **DB-4** | `vw_dash_competenza_gruppi`: le stesse due, con la regola «uno oppure N» del §5 — ⚠️ più `registri_n`, o il terzo stato è indistinguibile (R-8, R-9) |
| **DB-5** | ~~Seed `ui.lista_colonna` per le liste **42** e **43**~~ → **solo la 42** (vedi §7): D-3 aveva già escluso la 43, questa riga la contraddiceva (R-12.2) |
| **DB-6** | pgTAP: DB-1 risolve come la catena vecchia su casi reali; un gruppo multi-registro non mostra un registro solo; la data prevista di un registro `FINE_MESE_COMPETENZA` è l'ultimo giorno della competenza, di uno `OGGI` è la data operativa — ⚠️ **più cinque** (§11.7) |

---

## 7. Il seed delle colonne (DB-5)

Lista **42** (`vendite.dash_competenza_gruppi`) — ordini liberi dopo `valore` (60)
e `data_attivita_max` (70), priorità libere sotto 60. Verificato sul CSV: gli
ordini 75/78 e le priorità 45/50 non collidono con le undici colonne già a
catalogo.

| campo | `registro` | `data_documento_prevista` |
| --- | --- | --- |
| `campo_sorgente` | `registro_codice` | `data_documento_prevista` |
| `tipo_dato` / `formato` | `string` / — | `date` / `date_short` |
| `ordine_default` | 75 | 78 |
| `priorita` | 45 | 50 |
| `larghezza` / `allineamento` | 140 / left | 120 / center |
| `filtrabile` / `ordinabile` | `t` / `t` | `f` / `t` |
| `etichetta_i18n_key` | `vendite.dashboard_competenza.col_registro` | `vendite.dashboard_competenza.col_data_prevista` |

⚠️ Il namespace i18n è **`vendite.dashboard_competenza`** (`dashboard_`, non
`dash_`): è quello delle undici colonne già a catalogo — `col_commessa`,
`col_cliente`, `col_valore`… Sbagliarlo non dà un errore, dà una **colonna
senza intestazione**, e il guard i18n lo vede solo perché controlla proprio
questo.

⚠️ `filtrabile = t` sul registro **sì**, ed è il caso opposto a
`lotti.data_documento`: qui la colonna è valorizzata su **tutte** le righe, e
«mostrami solo ciò che finisce sul Back-office» è una domanda che si fa.
Sulla data prevista `f`: è derivata, e un filtro su un valore calcolato promette
una precisione che non ha.

⛔ **Due prerequisiti, o il seed sanguina** — entrambi già pagati questo mese:

1. `ordinabile = t` vuole la voce nella **whitelist di ordinamento** del
   repository (`DASH_COMPETENZA_GRUPPI_SORT_COLUMNS`), o la freccia risponde
   400. Presidiato da `test_liste_configurabili_seed`;
2. `etichetta_i18n_key` vuole la chiave in `it.json` **e** `en.json`, o
   `check_i18n_keys.py` fallisce in CI.

Sono lavoro BE/FE: vanno fatti **prima** del seed, o insieme.

> ✅ **Verificato il 2026-08-26 (§10, R-13)**: ordini e priorità sono davvero
> liberi, e i prossimi `id` del CSV sono **553 e 554**.
> ⚠️ Ma la tabella qui sopra copre **8 campi su 24**: mancano fra gli altri
> `tipo_colonna` (senza, la colonna non viene costruita) e `sensibile` (⛔ un
> **cancello**, non un'etichetta). Le due righe CSV per esteso sono in **§11.6**.
> ❓ E il `filtrabile = t` motivato qui sopra descrive un filtro che su questa
> lista **non esiste** — vedi **D-5**, da chiudere prima di scrivere la riga.

---

## 8. Cosa parte dopo

| | Consegna |
| --- | --- |
| BE-1 | Proiezione delle due colonne nella lista gruppi (`vendite_repository`, la `SELECT` su `vw_dash_competenza_gruppi`) |
| BE-2 | Voci in `DASH_COMPETENZA_GRUPPI_SORT_COLUMNS` (nome verificato nel repository) |
| BE-3 | Chiavi `vendite.dashboard_competenza.col_registro` / `col_data_prevista` (it **e** en) |
| FE-1 | ~~Nulla di strutturale: le liste sono `<ListaConfigurabile>` e prendono le colonne dal catalogo. Da guardare solo la resa di «più registri»~~ |

> ⚠️ **Rivisto il 2026-08-26 (§10, R-9) — versione operativa in §11.8.** Le
> colonne sono **tre** (con `registri_n`), e **FE-1 è strutturale**: «più
> registri» è una frase italiana e nel database non ci va, quindi il valore
> resta NULL e l'etichetta la mette uno slot `#cell-registro`. Il meccanismo
> esiste (`ListaConfigurabile` espone `cell-{codice}`), ma è codice da scrivere
> — e l'export non passa dallo slot (**D-4**).

---

## 9. Cosa NON è in questo cantiere

* **La politica della data** in sé: se un arretrato di luglio lavorato oggi
  debba portare la data di luglio o quella di oggi è una decisione **aperta** di
  Tid, e da lì dipende un'eventuale terza politica sul registro. Questo cantiere
  rende visibile ciò che succede, non cambia ciò che succede.
* **La scheda «recuperi del mese»**, che con `FINE_MESE_COMPETENZA` è vuota per
  costruzione (il suo criterio è la data del documento, che ha smesso di dire
  «quando l'ho fatto»). Cantiere suo, e la decisione è la stessa del punto
  sopra.
* Il **filtro per registro** sulla lista lotti: qui si parla delle liste di
  competenza.
* ⛔ **L'invariante dell'emittente sulla commessa** — scoperto qui il 2026-08-26
  chiudendo D-6, ma è un difetto suo e ha un brief suo:
  [brief-db-emittente-commessa-invariante.md](brief-db-emittente-commessa-invariante.md).
  ⚠️ **Tocca però lo scope di queste viste**: `vw_dash_competenza_attivita` filtra
  su `co.emittente_soggetto_ruolo_id`, quindi una commessa con quel valore a NULL
  non compare in nessuna delle liste di cui parla questo brief — colonna nuova
  compresa.

---

## 10. Revisione critica del piano (2026-08-26, team DB)

> ⛔ **Ogni argomento qui sotto poggia sulla STRUTTURA, mai sulla popolazione.**
> Nullabilità, `CHECK`, chiavi, RLS, GRANT, volatilità e corpo delle funzioni sono
> il **contratto** — sono il progetto, e si leggono sulla doc auto-gen (che
> riflette l'oggetto vivo) o sui file del repo, mai dagli YAML, che sono quasi
> sempre stantii.
> Quante righe esistano oggi in uno stato è la fotografia di una macchina e **non
> decide niente**: la domanda è *«il modello lo ammette?»*, non *«oggi
> succede?»*. Regola in `.codex/AGENTS.md` § «Regola zero — le misure non disegnano il progetto».
>
> ⚠️ **Prima stesura corretta il 2026-08-26**: tre conclusioni di questa sezione
> (R-1, R-5, R-7) erano appoggiate a tre conteggi. Le conclusioni erano giuste —
> ed è ciò che rende il difetto difficile da vedere: la misura non sbagliava la
> risposta, **occupava il posto dell'argomento**. Riscritte sul modello, dicono
> la stessa cosa e valgono anche su un database vuoto.

### R-1 ⛔ Le funzioni della catena SOLLEVANO, e una lista non può morire su una previsione

| funzione | volatilità (`pg_proc`) | solleva |
| --- | --- | --- |
| `vendite.fn_get_registro_id` | **VOLATILE** | `E_PARAMETRO_INVALIDO` (tipo doc nullo o ≤ 0), `E_CONFIG_MANCANTE` (natura non risolta, registro non risolto) |
| `anagrafiche.fn_get_emittente_fiscale_id` | **VOLATILE** | `E_EMITTENTE_DEFAULT_MISSING` |
| `vendite.fn_calcola_data_documento` | STABLE | `E_VENDITE_CHIAMATA_NON_VALIDA` (registro nullo o ≤ 0), `E_CONFIG_MANCANTE` |

⛔ **Oggi nessuna vista del database chiama queste funzioni**: verificato su tutte
le viste auto-generate. Questo cantiere sarebbe il primo, e il ramo è
raggiungibile: `chk_commesse_attivita_tipo_doc_emittibile` impone
`tipo_doc_fiscale_id` **solo** su una riga APPROVATA + NON_EMESSA. Su una riga
`DA_APPROVARE` la colonna **può essere NULL**, e la Dashboard Competenza quelle
righe le mostra (è uno dei quattro stadi della vista). Con un NULL lì,
`fn_get_registro_id` solleva e **l'intera lista risponde 500** — non «la colonna
resta vuota»: tutta la lista. E ogni tentativo lascia una riga in `error_log`,
che il log scrive per canale autonomo e sopravvive al rollback.

⚠️ **La domanda non è se oggi esista una riga così.** Il `CHECK` quel NULL lo
**ammette**, e uno stato che il modello prevede è un caso da gestire, non da
contare: `DA_APPROVARE` è uno dei quattro stadi che la vista **calcola**, quindi
è un percorso di progetto. Una previsione che può spegnere la lista da cui si
fattura è un difetto adesso, con o senza righe che lo esercitano.

⚠️ **Il precedente che sembra autorizzare non autorizza.**
`fn_build_gruppo_fatturabile_key` è già chiamata per riga dentro
`vw_dash_competenza_attivita` e ha guard che sollevano — ma i suoi guard
presidiano invarianti che un CHECK rende impossibili
(`chk_commesse_attivita_sorgente_pair`). Qui il CHECK fa l'opposto: **permette**
il caso che farebbe sollevare.

### R-2 ⭐ La forma giusta esiste già nel progetto, sull'emittente

| ruolo | funzione | forma |
| --- | --- | --- |
| **lettore puro** | `script.fn_get_ba_emittente_sr_id` | `LANGUAGE sql`, **STABLE PARALLEL SAFE**, torna `NULL` |
| **involucro che ferma** | `anagrafiche.fn_get_emittente_fiscale_id` | VOLATILE, trasforma il `NULL` in errore di dominio |

La regola «mapping specifico, poi `is_default`» è scritta **una volta sola**, nel
lettore; il `COMMENT` dell'involucro lo dichiara esplicitamente. È il modello: la
vista consuma il lettore, lo scrittore consuma l'involucro.

⛔ **Sul registro quell'equivalente non c'è**: `fn_get_registro_id` è lookup **e**
raise nello stesso corpo. Finché resta così, DB-1 ha due strade e sono entrambe
sbagliate — ricopiare il `SELECT` con la gerarchia a quattro livelli (cioè la
seconda implementazione che il §3 vieta) oppure ingoiare l'eccezione con un
`EXCEPTION WHEN OTHERS`, che intanto ha già scritto in `error_log` e nasconde
anche i guasti veri.

→ **Serve una consegna in più, DB-0**: spaccare `fn_get_registro_id` in
`fn_lookup_registro_id` (STABLE, 0 righe invece di sollevare) + involucro. Costo
reale, verificato sul codice: **un solo chiamante** (`fn_build_fattura_key`),
firma e `RETURNS TABLE` invariati.

### R-3 La DB-1 proposta non toglie la duplicazione che dichiara di togliere

Con la firma del §3.1 — `(ba, tipo_doc, natura) → (registro_id, serie, politica)`
— `fn_build_fattura_key` deve **comunque** calcolarsi in proprio
`COALESCE(ba.parent_account_id, …)`, `ba.utility_id` e l'emittente: gli servono
per la chiave (BA di fatturazione, emittente, utility) e per il lookup del
reseller. I **due ancoraggi** resterebbero scritti in due posti — cioè
esattamente il difetto silenzioso descritto al §3, spostato di un metro.

→ DB-1 deve restituire **anche gli anelli intermedi**: `ba_fatturazione_id`,
`utility_id`, `emittente_soggetto_ruolo_id`. Solo allora
`fn_build_fattura_key` non risolve più niente da sé.

### R-4 ⚠️ Il nome del parametro mente, ed è il punto esatto in cui si sbaglia

`p_billing_account_id` dev'essere il **BA della riga**, non quello di
fatturazione: è da lì che esce la `utility_id`. Chi legge la firma passerà il
`ba_fatturazione_id` — che la vista gruppi **già espone** — e otterrà una
previsione plausibile e sbagliata proprio sui BA con padre, cioè nei casi non
banali.

→ chiamarlo `p_billing_account_id_riga`, e scriverlo nel `COMMENT`.

### R-5 ⚠️ La prova «sul risultato» di DB-2 non può provare i due ancoraggi

Il §3 chiede di provare la rifattorizzazione confrontando, per ogni fattura
esistente, il registro risolto con `fatture.registro_id` già scritto. ⛔ **Quel
confronto non può dimostrare la cosa che deve dimostrare**, e non per un difetto
del metodo: per come è fatto il modello.

I due ancoraggi si distinguono **solo** dove `anagrafiche.billing_account.parent_account_id`
è valorizzato — altrove `COALESCE(parent_account_id, id)` restituisce l'id
stesso e le due catene collassano in una. Ma quella colonna è **nullable**: un
confronto su una popolazione esistente esercita i rami che quella popolazione
**per caso** contiene, e su un ramo opzionale non offre nessuna garanzia.

⚠️ **Su quale asse si distinguono, corretto il 2026-08-26** (▶ R-6, ritirata).
Non sull'**emittente**: quello è protetto da un invariante imposto — padre e
figlio non possono averne due diversi. Si distinguono sulla **utility**, che
`fn_build_fattura_key` prende dalla riga mentre l'emittente lo prende dal padre,
e che **nessun guard** vincola fra padre e figlio. È l'altro dei due assi con cui
`fn_get_registro_id` sceglie il sezionale, quindi la differenza è viva.

→ Il confronto **resta**, ma declassato a quello che è: una **rete anti-regressione
grossolana**, non una prova. La prova è un pgTAP che **costruisce** il caso — BA
figlio con `parent_account_id`, padre mappato a un emittente diverso, asserzione
che il registro esce quello del **padre** e la utility quella del **figlio**.
⭐ È la regola generale, non un'eccezione di questo cantiere: *un ramo che si
distingue solo quando una colonna opzionale è valorizzata si prova costruendo
quel caso.* Senza, «comportamento invariato» resta la promessa che il §3 stesso
rifiuta.

### R-6 ⛔ ~~La vista NON deve usare l'emittente che ha già in mano~~ — RITIRATA

> ⛔ **Ritirata il 2026-08-26 su richiamo di Tid** — *«questo avevamo controllato
> che era impossibile: ogni BA figlio si collega solo al BA padre generato per
> quell'emittente»*. Verificato, ed è vero: **l'invariante è IMPOSTA, non solo
> rispettata da chi scrive**. Lasciata a testo perché la parte che regge —
> l'altro ancoraggio — è ciò che tiene in piedi R-5.

**Dove è imposta**, e vale la pena saperlo perché è un presidio ben fatto:

* `anagrafiche.fn_guard_albero_ba_emittente(ba_id)` verifica l'omogeneità
  dell'emittente **verso il padre e verso tutti i figli** — il secondo verso è
  quello che di solito si dimentica;
* è agganciata da **due** trigger `z95`, uno su `billing_account` e uno su
  `emittenti_fiscali_billing_account`: si presidia sia chi sposta il BA sotto un
  altro padre, sia chi cambia il mapping dell'emittente;
* è `SECURITY DEFINER` **apposta**, perché `billing_account` ha la RLS e da
  `SECURITY INVOKER` un padre di un altro emittente sarebbe invisibile — il
  guard direbbe «a posto» proprio nel caso da bloccare;
* il confronto (`fn_check_ba_coppia_emittente_omogenea`) usa **lo stesso
  risolutore** che usa `fn_build_fattura_key`, è fail-closed sul NULL, e il
  `COMMENT` chiude la porta a ripensamenti: *«nessuna eccezione per il pregresso
  e nessuna GUC di override: un invariante con l'interruttore non è un
  invariante»*.

⇒ Padre e figlio **non possono** risolvere due emittenti diversi. La colonna
«Emittente» già a video e il sezionale previsto non possono contraddirsi, e
**D-6 si chiude senza debito** (§12).

⭐ **Ma dei due ancoraggi ne resta uno in piedi, ed è quello che conta davvero.**
`fn_build_fattura_key` prende l'emittente dal padre e la **utility dalla riga**.
Sull'emittente l'invariante rende il punto innocuo; sulla **utility no**:
`billing_account.utility_id` è `NOT NULL` e **nessun guard la vincola fra padre e
figlio** — l'albero è presidiato su emittente e gestore globale, non su utility.
E la utility è **l'altro dei due assi** su cui `fn_get_registro_id` sceglie il
sezionale.

→ DB-1 continua a **ricalcolare** la catena invece di leggere colonne già in
vista, e T2 (§11.7) resta necessario — ma va costruito facendo variare la
**utility** fra padre e figlio, non l'emittente, che non può variare. ▶ R-5.

⛔ ~~Residuo minore~~ — **NON è minore, ed è un cantiere suo**:
[brief-db-emittente-commessa-invariante.md](brief-db-emittente-commessa-invariante.md).
Approfondito su richiamo di Tid il 2026-08-26: `vendite.commesse.emittente_soggetto_ruolo_id`
non è un attributo, è la **chiave di perimetro** della commessa — ci si appoggiano
la RLS della tabella, il filtro di scope delle viste di questo cruscotto e il
giornale degli eventi. Ed è **nullable**: con un NULL la commessa diventa
invisibile all'operatore in `SELECT`, `UPDATE` **e** `DELETE`, cioè lavoro che non
viene mai fatturato e di cui nessuno si accorge. ⚠️ Il ramo peggiore non richiede
nessun override: la colonna è una **fotografia** scattata alla nascita, e
riassegnare un BA a un altro emittente — operazione che nessun trigger blocca —
la rende stantìa mentre `fn_build_fattura_key` all'emissione ricalcola.

### R-7 Il caso «più registri» è ammesso per costruzione, non è un'eccezione

Tre fatti di struttura, e la conclusione segue da sola:

1. la chiave del gruppo — `fn_build_gruppo_fatturabile_key(sorgente_tipo, sorgente_uid, commessa)`
   — **non contiene** né tipo documento né natura (lo dice già il §5);
2. `tipo_doc_fiscale_id` e `natura_doc_id` sono colonne **di riga** su
   `commesse_attivita`, non della commessa;
3. `tipi_doc_fiscale_registri` mappa la coppia `(tipo_doc, natura)` sul registro,
   e registri diversi possono avere **politiche di data diverse**
   (`politica_data_documento` è per registro).

→ Un gruppo con righe di tipo o natura diversa **finisce su registri diversi, e
può portare due date diverse**. Non è un caso limite da tollerare: è ciò che il
modello ammette.

⭐ Ed è il ramo **normale** della porta manuale: i gruppi `MAN:` sono la sede di
oneri e rettifiche — sourceless per progetto — dove il tipo documento lo sceglie
l'operatore riga per riga. Un onere `FRONTOFFICE` e una rettifica accanto sono
due nature, due registri, due politiche.

⭐ Buona notizia per l'implementazione: nel `GROUP BY` della CTE `aggregato` c'è
già `a.billing_account_id`, e la `gruppo_key` porta la commessa — quindi **dentro
un gruppo il BA è costante per costruzione**. Le uniche variabili sono
`tipo_doc_fiscale_id` e `natura_doc_id`: «uno oppure N» si riduce a contare i
registri distinti, senza ricalcolare niente.

### R-8 ⚠️ «Uno oppure N» ha un terzo stato, e `count(DISTINCT)` lo nasconde

`count(DISTINCT registro_id)` **ignora i NULL**: un gruppo con una riga risolta e
una non risolvibile risponderebbe «1» e mostrerebbe **un registro solo** — la
stessa mezza verità del `LIMIT 1` che il §5 vieta, presa dall'altra parte.

→ il contatore dev'essere `count(DISTINCT COALESCE(registro_id, -1))`, e
`registri_n` deve **uscire dalla vista**: senza, il frontend non ha modo di
distinguere «vuoto perché sono due» da «vuoto perché non lo so».

### R-9 «più registri» è una frase italiana, e nel database non ci va

La lista è `<ListaConfigurabile>`, che prende i **valori** dalle colonne e i
**testi** da `$t()`; il prodotto ha `it.json` **e** `en.json`, e
`check_i18n_keys.py` presidia proprio quello. Una vista che restituisce la
stringa `più registri` scrive italiano dentro il database.

⭐ Il precedente giusto è **nella stessa vista**: `tipo_gruppo` restituisce
`COALESCE(s.codice_interno, 'ONERI_COMMESSA')` — un **codice**, non una frase;
l'etichetta la mette il frontend.

→ DB: `registro_codice` valorizzato **solo** quando la risposta è una (NULL negli
altri due casi) + `registri_n`. FE: `registri_n > 1` → chiave i18n nuova;
altrimenti il codice, o «—».

⚠️ Ne discende che **FE-1 non è «nulla di strutturale»**: serve uno slot
`#cell-registro`. Il meccanismo esiste (`ListaConfigurabile` espone
`cell-{codice}`, `CellaConfigurabile` lo invoca), ma è codice da scrivere.
✅ **D-4 decisa** (Tid, 2026-08-26): la frase la mette BE/FE. ⭐ E l'export di
queste liste è **server-side** e condivide la proiezione della lista — quindi
componendo la frase nel **BE** compare anche nel file, senza colonne in più.

### R-10 Costo: due funzioni per riga sulla vista che ne alimenta altre quattro

`vw_dash_competenza_attivita` è la base di `vw_dash_competenza_gruppi`,
`vw_dash_competenza_mensile`, `vw_dash_competenza_gruppi_riepilogo` e
`vw_lotti_gruppi_serviti`, oltre a `fn_check_commessa_annullabile`,
`fn_annulla_commessa_attivita` e `fn_get_commessa_stato`. Due chiamate per riga
tassano **tutti**, anche chi le colonne nuove non le guarda.

Attenuanti **strutturali**: le tre tabelle lette dalla catena
(`registri_fatturazione`, `tipi_doc_fiscale_registri`,
`emittenti_fiscali_billing_account`) **non hanno RLS** e `zeroerp_app` ha
`SELECT` su tutte e tre — quindi `security_invoker=on` regge senza
`SECURITY DEFINER`. E sono tabelle di **configurazione**: la loro cardinalità è
di dominio (i sezionali di un'azienda, la matrice tipo×natura), non cresce con
i documenti.

→ Requisito, non consiglio: `fn_lookup_registro_id` e
`fn_resolve_registro_documento` **dichiarate STABLE**. Se restano VOLATILE il
planner non può nemmeno potarle dalle viste che non usano le colonne. Precedente
già battuto: `fn_calcola_data_documento` è STABLE e chiama
`fn_log_and_raise_error`.

### R-11 ⚠️ `billing_account` ha la RLS, e le altre no: la previsione può sbagliare in silenzio

`anagrafiche.billing_account` ha la **RLS attiva**, con le sue policy — a
differenza delle tre tabelle di configurazione di R-10. La vista è
`security_invoker=on`, quindi la catena la legge l'operatore. Se la
riga del BA (o del padre) non è visibile, `parent_account_id` e `utility_id`
tornano NULL: la risoluzione **non fallisce**, ripiega sul livello meno specifico
della gerarchia a quattro e restituisce un registro **plausibile e sbagliato**.

La vista gruppi ha già preso una decisione su questo caso — `ba_codice_fatturazione`
NULL quando il padre è fuori scope, e il gruppo resta comunque in lista — ma lì
l'effetto è una **colonna vuota**; qui è un **valore falso**. Da coprire con un
pgTAP di scope, non da assumere. ⚠️ E il cancello di quel test è
`app.ruolo_applicativo`: svuotare `app.current_user_id` **non è** fail-closed.

### R-12 Contraddizioni interne del brief, da sanare

1. **D-1 dice due cose opposte nello stesso file**: l'intestazione e il §10
   la danno «verificata sul codice», il §4.1 dice «non l'ho verificato e non lo
   do per buono».
   ✅ **La risposta è sì**, e la citazione è questa:
   `vendite.fn_emit_attivita_fatturabili_da_commessa` è l'**unica** funzione che
   scrive righe in `vendite.attivita_fatturabili` (verificato su `pg_proc`;
   nessun `INSERT` nel backend Python) e scrive
   `billing_account_id = v_commessa.billing_account_id` **sia sull'INSERT sia
   sull'UPDATE**. La BA per riga è la BA della commessa: la vista può fermarsi
   alla commessa. Il §4.1 va marcato risolto con questa riga, non lasciato
   aperto.
2. **DB-5 dice «liste 42 e 43»**, ma D-3 (§2) ha deciso **no** sulla 43. → DB-5
   è la sola **42**.
3. **Il §5 parla di «lista attività (drill-down)»**, ma a catalogo la 43 è
   `vendite.dash_competenza_commesse`, aggregata **per commessa** (verificato in
   `80_data/sql/ui/lista_definizione.csv`): una lista a grana **attività** non
   esiste. La frase è vera come fatto sul dato, falsa come riferimento a una
   lista.
4. **DB-3** aggiunge le colonne a `vw_dash_competenza_attivita`: è giusto, ma la
   motivazione non è «una lista le mostra» — è che la vista **gruppi** ci si
   appoggia. Va scritto, o al primo giro qualcuno seeda anche quelle.

### R-13 Il seed del §7 è verificato, ma incompleto

✅ Verificato riga per riga sul CSV: sulla lista 42 gli `ordine_default` sono
10…100 + 999 e le `priorita` 100/70/90/85/60/95/65/100/40/35/30 → **75/78 e
45/50 sono liberi**. I prossimi `id` liberi sono **553 e 554** (l'ultimo del CSV
è 552).

⚠️ Mancano però **dieci dei ventiquattro campi** del CSV, e tre contano:

* `tipo_colonna` → `informazione` (senza, la colonna non viene costruita);
* `sensibile` → `f`. ⛔ `sensibile = t` è un **cancello**, non un'etichetta:
  senza grant la colonna diventa invisibile a tutti;
* `larghezza_default`: tutte e undici le colonne della 42 la lasciano **vuota**,
  il §7 propone 140/120. Non è un errore, ma è una deroga → **D-7**.

---

## 11. Piano di sviluppo

> ⛔ **Prima di tutto, l'ordine con il cantiere gemello** (✅ D-8, §12): L4/L5
> vanno **dopo** il `DROP + CREATE` di `fn_calcola_data_documento` del brief
> [limite-emissione-e-data-verificata](../work-done/brief-db-limite-emissione-e-data-verificata.md),
> o quel `DROP` fallisce sulla dipendenza della vista. Consegna unica.
>
> ⚠️ **Numerazione: i numeri `01…06` qui sotto sono BRUCIATI.** Il cantiere
> «limite emissione» ha occupato `20260826-01 … -13` (verificato sul repo). La
> serie di questo cantiere parte da **`20260826-14`**, e va **riverificata prima
> di scrivere**: la sequenza è globale per data, e al 2026-08-26 se la dividono
> **tre** cantieri — il terzo è
> [brief-db-lavoro-che-non-torna-indietro.md](brief-db-lavoro-che-non-torna-indietro.md),
> che numeri non ne ha ancora presi ma ne prenderà.
> Tutti i changeSet in stato finale con `runOnChange: false` e `validCheckSums`
> (**al plurale**).
> ⛔ Nei `COMMENT` si cita il **nome** del brief, mai il path
> `work-in-progress/`: il commento vive nel DB e a cantiere chiuso il documento
> si sposta. (Le due funzioni del cantiere numerazione lo fanno: non copiarle
> su questo punto.)

### 11.1 Le consegne, in ordine di dipendenza

| # | Consegna | File | Dipende da |
| --- | --- | --- | --- |
| ✅ **L0** | ⭐ **DB-0, nuova (R-2).** `vendite.fn_lookup_registro_id(tipo_doc, natura, utility, emittente)` → `TABLE(registro_id, serie)`. Stesso `SELECT` di oggi, stessa gerarchia a quattro livelli, stesso filtro **esatto** sulla natura. **STABLE**. Torna **0 righe** dove oggi si solleva. Nessun `fn_log_and_raise_error` | `20_code/vendite/20260826-14-create-fn-lookup-registro-id-mctit.yaml` ✍️ **scritto** | — |
| ✅ **L1** | `vendite.fn_get_registro_id` diventa l'**involucro**: chiama L0 e tiene i tre `fn_log_and_raise_error` (parametro, natura, registro non risolto). Firma e `RETURNS TABLE` **invariati** → `CREATE OR REPLACE` lecito. Un solo chiamante da non toccare | `20260826-15-update-fn-get-registro-id-involucro-mctit.yaml` ✍️ **scritto** | L0 |
| ✅ **L2** | **DB-1 corretta (R-3, R-4).** `vendite.fn_resolve_registro_documento(p_billing_account_id_riga, p_tipo_doc_fiscale_id, p_natura_doc_id)` → `TABLE(ba_fatturazione_id, utility_id, emittente_soggetto_ruolo_id, registro_id, serie, politica_data_documento)`. **STABLE**, restituisce **sempre una riga** (con NULL dove non risolve), nessun raise sui dati | `20260826-16-create-fn-resolve-registro-documento-mctit.yaml` ✍️ **scritto** | L0 |
| ✅ **L3** | **DB-2.** `fn_build_fattura_key` smette di risolvere in proprio: una `SELECT … FROM vendite.fn_resolve_registro_documento(…)` sostituisce il blocco BA/utility/emittente/registro | `20260826-17-update-fn-build-fattura-key-resolve-registro-mctit.yaml` ✍️ **scritto** | L2 |
| ✅ **L4** | **DB-3.** `vw_dash_competenza_attivita`: `registro_id`, `registro_codice`, `politica_data_documento`, `data_documento_prevista` | `20260826-18-update-vw-dash-competenza-attivita-registro-mctit.yaml` ✍️ **scritto** | L2 |
| ✅ **L5** | **DB-4.** `vw_dash_competenza_gruppi`: `registri_ids` (✅ D-5, è ciò su cui si filtra), `registri_n`, `registro_codice`, `data_documento_prevista` con la regola «uno oppure N» | `20260826-19-update-vw-dash-competenza-gruppi-registro-mctit.yaml` ✍️ **scritto** | L4 |
| ✅ **L6** | **DB-5 corretta.** Due righe in **append** a `80_data/sql/ui/lista_colonna.csv` (id 553/554, lista **42** soltanto) | *nessun changeSet nuovo*: il mirror ri-ancorato `20260806-15` è `runOnChange` e ri-legge il CSV — ✍️ **righe appese** | ⚠️ BE-2 + BE-3 in ritardo |
| ✅ **L7** | **DB-6 estesa.** pgTAP | `db/pgtap/vendite/test-registro-documento-previsto-v1.sql` ✍️ **scritto, 12/12 verde** | L2…L5 |

### 11.2 L2 — la firma per esteso, e i due ancoraggi

```sql
CREATE OR REPLACE FUNCTION vendite.fn_resolve_registro_documento(
    p_billing_account_id_riga vendite.attivita_fatturabili.billing_account_id%TYPE,
    p_tipo_doc_fiscale_id     config.tipi_doc_fiscale.id%TYPE,
    p_natura_doc_id           config.nature_doc_fiscale.id%TYPE DEFAULT NULL)
RETURNS TABLE(
    ba_fatturazione_id          anagrafiche.billing_account.id%TYPE,
    utility_id                  config.utilities.id%TYPE,
    emittente_soggetto_ruolo_id anagrafiche.soggetti_ruoli.id%TYPE,
    registro_id                 vendite.registri_fatturazione.id%TYPE,
    serie                       vendite.fatture.serie%TYPE,
    politica_data_documento     vendite.registri_fatturazione.politica_data_documento%TYPE)
LANGUAGE plpgsql STABLE
```

Corpo, in quattro righe di sostanza:

```
v_ba_fattura := COALESCE(ba.parent_account_id, p_billing_account_id_riga) -- dal PADRE
v_utility    := ba.utility_id                                             -- dalla RIGA
v_emittente  := script.fn_get_ba_emittente_sr_id(v_ba_fattura)            -- lettore PURO
(registro, serie) := vendite.fn_lookup_registro_id(tipo_doc, natura, v_utility, v_emittente)
politica     := (SELECT politica_data_documento FROM registri_fatturazione WHERE id = registro)
```

ℹ️ **Sull'emittente il padre non cambia la risposta** — `fn_guard_albero_ba_emittente`
impone che padre e figlio ne abbiano uno solo (R-6). Si risolve comunque dal BA
di fatturazione, per restare **identici** a `fn_build_fattura_key`: allineare le
due catene è il punto del cantiere, non ottimizzare una lettura.

⚠️ **`script.fn_get_ba_emittente_sr_id` e non `anagrafiche.fn_get_emittente_fiscale_id`**,
e le due **non** sono intercambiabili in generale: l'involucro conserva un
ripiego proprio sul default per il caso **senza** billing account, che la
delegata corto-circuita. Qui non c'è divergenza — `vendite.commesse.billing_account_id`
è `NOT NULL` e il guard di parametro rifiuta il nullo — ma va scritto, o al primo
riuso la funzione risponde diverso dallo scrittore.

⚠️ **Guard di parametro, uno solo**: `p_billing_account_id_riga` nullo o ≤ 0 →
errore **TECNICO** (nessuna interfaccia produce quel valore, lo produce solo un
chiamante rotto). ⛔ **Non riusare `E_PARAMETRO_INVALIDO`** — è un debito
dichiarato, non una sede: conio o riuso di un codice `TECNICO` già registrato
(es. `E_VENDITE_CHIAMATA_NON_VALIDA`, che è quello che usa
`fn_calcola_data_documento`). E nel `VARIADIC` va la frase che legge una
persona, non il nome del parametro.

⛔ **Tipo documento e natura nulli NON sollevano**: tornano una riga con
`registro_id` NULL. È tutta la differenza fra una colonna vuota e una lista che
non si apre (R-1).

### 11.3 L3 — cosa cambia in `fn_build_fattura_key`, e cosa NON cambia

Il blocco «recupera BA, tipo doc, natura, valuta, utility» resta **solo** per
`tipo_doc_fiscale_id`, `natura_doc_id` e `valuta_id` (che vengono dall'attività e
non c'entrano col registro). Il resto diventa:

```sql
SELECT r.ba_fatturazione_id, r.utility_id, r.emittente_soggetto_ruolo_id,
       r.registro_id, r.serie
  INTO v_ba_fattura_id, v_utility_id, v_emittente_id, v_registro_id, v_serie
  FROM vendite.fn_resolve_registro_documento(
           v_ba_id, v_tipo_doc_fiscale_id, v_natura_doc_id) r;
```

⚠️ **E poi i cancelli restano qui**, perché sul percorso di **scrittura** un
buco di configurazione deve fermare, non passare:

* `v_emittente_id IS NULL` → `anagrafiche.fn_get_emittente_fiscale_id(v_ba_fattura_id)`,
  che solleva `E_EMITTENTE_DEFAULT_MISSING` come oggi;
* `v_registro_id IS NULL` → `vendite.fn_get_registro_id(...)` (l'involucro L1),
  che solleva `E_CONFIG_MANCANTE` come oggi.

⭐ Chiamare l'involucro solo sul ramo nullo costa una seconda risoluzione **solo
quando si sta già andando in errore**, e lascia i messaggi identici a quelli di
oggi — cioè non rompe nessun `throws_like` esistente.

### 11.4 L4 — la vista attività

```sql
    reg.registro_id,
    r.codice                       AS registro_codice,
    reg.politica_data_documento,
    CASE WHEN reg.registro_id IS NOT NULL
         THEN vendite.fn_calcola_data_documento(
                  reg.registro_id, ca.competenza_mese, reg.serie, NULL)
    END                            AS data_documento_prevista
  ...
  LEFT JOIN LATERAL vendite.fn_resolve_registro_documento(
           co.billing_account_id, ca.tipo_doc_fiscale_id, ca.natura_doc_id) reg
       ON (af.fattura_riga_id IS NULL)   -- ✅ D-9: nessuna previsione dove il documento c'e' gia'
  LEFT JOIN vendite.registri_fatturazione r ON r.id = reg.registro_id
```

⛔ **`p_serie` è obbligatoria e senza `DEFAULT`** (✅ D-8): la firma di
`fn_calcola_data_documento` la aggiunge il cantiere gemello
[limite-emissione-e-data-verificata](../work-done/brief-db-limite-emissione-e-data-verificata.md),
proprio perché queste viste la serie ce l'hanno — gliela dà L2 in `reg.serie`.
✅ **L'ordine dei parametri NON è più un'incognita: il gemello ha applicato.**
Firma vigente, letta sulla doc auto-gen il 2026-08-26 —
`(p_registro_id, p_competenza_mese, p_serie, p_data_dichiarata DEFAULT NULL)`:
`p_serie` è il **terzo**, prima della data dichiarata. Lo sketch qui sopra è
allineato.

⭐ **E il `DROP` è già avvenuto** (`20260826-08-recreate-fn-calcola-data-documento-serie-e-clamp`),
quando nessuna vista dipendeva ancora dalla funzione: la finestra si è chiusa da
sola nell'ordine giusto. Da qui in avanti L4/L5 possono entrare **quando
vogliono** — ma se il gemello dovesse ricreare ancora quella funzione, la
dipendenza tornerebbe a valere e l'ordine di §12 D-8 con lei.

⚠️ Il `CASE` **non è difensivo, è obbligatorio**: `fn_calcola_data_documento`
solleva su `p_registro_id` nullo. Un `CASE` cortocircuita, un argomento no.

⚠️ `registro_codice` viene da `r.codice`, la colonna **mutabile**, e va bene:
è display, l'alias è fedele alla sorgente (linee-guida-sql §6c) e
`registri_fatturazione` non espone `codice_interno` — quindi **nessuna logica
può appoggiarcisi**, e non deve.

⛔ `WITH (security_invoker=on)` va **ri-specificato** nel `CREATE OR REPLACE
VIEW`: è una reloption invisibile nel corpo e un `REPLACE` che non la ripete la
**azzera**, senza errore. Vale per L4 **e** per L5.

### 11.5 L5 — la vista gruppi, «uno oppure N»

Nella CTE `aggregato`, senza toccare il `GROUP BY` (R-7: il BA è già costante):

```sql
array_agg(DISTINCT a.registro_id)                       AS registri_ids,
cardinality(array_agg(DISTINCT a.registro_id))::smallint AS registri_n,
CASE WHEN cardinality(array_agg(DISTINCT a.registro_id)) = 1
     THEN min(a.registro_codice) END                     AS registro_codice,
CASE WHEN cardinality(array_agg(DISTINCT a.registro_id)) = 1
     THEN min(a.data_documento_prevista) END             AS data_documento_prevista
```

⭐ **`registri_ids` è l'elemento portante, non un extra** (✅ D-5): è ciò su cui
il BE filtra — `%s = ANY(g.registri_ids)` — e un gruppo che tocca due sezionali
compare **sotto entrambi i filtri**, che è la verità. Filtrare su
`registro_codice` lo escluderebbe da tutti e due, perché lì è NULL per decisione
D-2.

⭐ E `registri_n` non è una seconda verità: è `cardinality()` **della stessa
espressione**, calcolata nella stessa vista. Non possono divergere.

⚠️ `array_agg` **include i NULL**, a differenza di `count(DISTINCT …)` che li
scarta silenziosamente. È proprio questo che chiude R-8: un gruppo con una riga
risolta e una non risolvibile produce `{5,NULL}`, cardinalità **2**, e legge
«più registri» invece di mostrare un sezionale solo. Il `COALESCE(-1)` della
prima stesura non serve più.

⚠️ `min()` su un insieme di **un** elemento non è un `LIMIT 1` travestito: è il
`CASE` a garantire che l'elemento sia uno. Senza il `CASE`, sarebbe esattamente
la bugia del §5.

⚠️ **Resta un'imprecisione dichiarata**: «uno più un ignoto» legge «più
registri», mentre la verità è diversa. Se un giorno servisse distinguerlo costa
una colonna — `bool_or(a.registro_id IS NULL) AS registro_ignoto` — ma non è
questo cantiere.

### 11.6 L6 — le due righe del CSV, per esteso

Colonne del CSV, nell'ordine: `id,lista_id,codice,etichetta,etichetta_estesa,campo_sorgente,tipo_colonna,tipo_dato,formato,larghezza_default,ordine_default,allineamento,gruppo,gruppo_ordine,filtrabile,ordinabile,esportabile,ricercabile_full,sensibile,attivo,data_insert,user_insert,etichetta_i18n_key,priorita`

```
553,42,registro,Registro,Sezionale su cui nascera il documento,registro_codice,informazione,string,,,75,left,,,t,t,t,f,f,t,2026-08-26 00:00:00,mctit,vendite.dashboard_competenza.col_registro,45
554,42,data_documento_prevista,Data prevista,Data che il documento prendera se nessuno ne dichiara un altra,data_documento_prevista,informazione,date,date_short,,78,center,,,f,t,t,f,f,t,2026-08-26 00:00:00,mctit,vendite.dashboard_competenza.col_data_prevista,50
```

Entrambe **24 campi**, verificato contro l'intestazione del CSV.

✅ **D-7 decisa** (Tid, 2026-08-26): `larghezza_default` **vuota** su entrambe,
come le undici colonne già a catalogo. Le larghezze 140/120 del §7 decadono.

⚠️ Gli `id` 553/554 sono i primi liberi **al momento in cui questo piano è
scritto**: il CSV è un file condiviso e cresce con ogni cantiere. Da riverificare
sull'ultima riga del file prima di appendere, non da copiare a scatola chiusa.

⚠️ `larghezza_default` lasciata **vuota** come le altre undici della 42 (D-7 se
si decide diversamente). ⚠️ Nessun apostrofo nelle etichette: il CSV non li
raddoppia e le altre righe della lista fanno lo stesso (`Ragione sociale dell
emittente fiscale`). ⚠️ `sensibile = f`, `attivo = t`, `tipo_colonna = informazione`.

⚠️ **La cella vuota qui NON è un NULL, ed è deliberato.** Su questa tabella una
cella vuota diventa stringa vuota sulle colonne di testo e `NULL` sulle
numeriche — verificato sul DB: delle undici righe della 42, `formato` e `gruppo`
sono `''` e `larghezza_default` è `NULL`. È il comportamento che il seed ha già,
nessuna di queste colonne ha un CHECK di non-vuoto, e le due righe nuove **si
allineano**. ⛔ Non introdurre qui il token letterale `NULL` con `nullValue`:
cambierebbe il valore di quelle colonne su una lista sola, e diventerebbe una
differenza che nessuno sa spiegare.

⛔ **Due prerequisiti, o il seed sanguina** (§7, confermati):
`ordinabile = t` su entrambe pretende le due voci in
`DASH_COMPETENZA_GRUPPI_SORT_COLUMNS` — chiavate sul **campo fisico**
(`registro_codice`, `data_documento_prevista`), non sul `codice` di catalogo — e
`etichetta_i18n_key` pretende le chiavi in `it.json` **e** `en.json`. Il presidio
`test_liste_configurabili_seed` lega catalogo e whitelist **nei due versi**: sono
un solo passo, non due.

### 11.7 L7 — i test pgTAP

Preambolo obbligatorio e presidiato: `BEGIN;`, riga di contesto operatore,
`SET CONSTRAINTS ALL IMMEDIATE`. ⚠️ Ogni `throws_ok` con lo **SQLSTATE**
(`P0001` per il dominio): senza, accetta anche il crash del guard.

| | Cosa verifica | Perché |
| --- | --- | --- |
| T1 | Per ogni fattura esistente, il registro risolto da L2 coincide con `fatture.registro_id` | rete anti-regressione di DB-2 — ⛔ **non una prova** (R-5) |
| T2 | ⭐ **Caso costruito**: BA figlio con `parent_account_id` e **utility diversa** da quella del padre → il registro segue la utility del **figlio**, mentre il BA in chiave è il **padre** | è **la** prova dei due ancoraggi (R-5). ⛔ Non costruirlo su emittenti diversi: quello è vietato da `fn_guard_albero_ba_emittente` e il test non partirebbe nemmeno (R-6) |
| T3 | L2 con `tipo_doc_fiscale_id` NULL → una riga con `registro_id` NULL, **nessuna eccezione** | R-1: è la differenza fra colonna vuota e lista morta |
| T4 | `fn_get_registro_id` (involucro) con tipo doc NULL continua a sollevare `P0001` | L1 non deve perdere il cancello dello scrittore |
| T5 | Gruppo `MAN:` con due tipi doc → `registri_n = 2`, `registro_codice` NULL, `data_documento_prevista` NULL | R-7: la chiave del gruppo non contiene tipo doc ne' natura, che sono colonne di riga — il caso va **costruito**, non cercato |
| T6 | Registro `FINE_MESE_COMPETENZA` → data = ultimo giorno della competenza; registro `OGGI` → `script.fn_data_operativa()` | DB-6 originale |
| T7 | Gruppo con una riga risolta + una non risolvibile → `registri_n = 2` | R-8: il `COALESCE(-1)` va **asserito**, non dedotto |
| T8 | ⚠️ Scope: un operatore che non vede il BA non vede un registro **sbagliato** | R-11. Il cancello è `app.ruolo_applicativo`, **non** `app.current_user_id` svuotato |
| T9 | Riga con `fattura_riga_id` valorizzato → le colonne nuove sono **NULL** | ✅ D-9. Ramo che sparisce in silenzio se qualcuno riporta il join a `ON true` |

⛔ **T1 è l'unico che interroga la popolazione, e per questo va scritto con una
dichiarazione dentro.** Su un database ricostruito da zero — cioè in CI — le
fatture sono zero e l'asserzione passa **a vuoto**: è la classica forma del
«verde per sottrazione», che passa smettendo di verificare. Due modi onesti di
scriverlo, e uno va scelto:

* un `skip()` esplicito quando il denominatore è zero, con il motivo scritto
  (pattern `CASE WHEN … THEN skip()` già in uso nel progetto), **e** l'asserzione
  vera affidata a T2;
* oppure T1 si toglie del tutto, e la copertura resta su T2…T8, che i loro
  soggetti **se li costruiscono**.

⭐ La seconda è la più coerente col resto del piano: i test che valgono qui sono
quelli che fabbricano il caso. T1 vale il suo posto solo finché è dichiarato per
quello che è.

⚠️ A valle: `scripts/pgtap-baseline.sh vendite`. Una nuova FK o un nuovo guard
generico possono far nascere trigger che scattano prima dei propri; e la suite ha
rossi preesistenti — un rosso non è automaticamente il proprio.

### 11.8 Cosa parte dopo (§8 aggiornato)

| | Consegna | Nota |
| --- | --- | --- |
| BE-1 | Proiezione nella lista gruppi: `registro_codice`, `data_documento_prevista`, `registri_n` (+ `registri_ids`, che serve al filtro) nel `SELECT` di `list_dash_competenza_gruppi` e in `DashCompetenzaGruppoRow` | ⛔ le chiavi delle due colonne a catalogo devono essere i loro `campo_sorgente`, o si spuntano e restano vuote. `registri_n`/`registri_ids` **non** vanno a catalogo: servono al render e al filtro |
| ⚠️ **BE-0** | ✅ **D-10**: `vendite.fn_get_registro_id` cambia il codice del guard di parametro — `E_PARAMETRO_INVALIDO` (DATO_ERRATO, **400**) → `E_VENDITE_CHIAMATA_NON_VALIDA` (TECNICO, **500**). ⭐ **Nessun lavoro da fare**, ma va saputo: se qualcosa si aspettava un 400 da lì, ora prende un 500 | ▼ §12 D-10 |
| BE-5 | ✅ **D-5**: filtro per sezionale in `_where_gruppi` — `%s = ANY(g.registri_ids)` — **più la facet** della tendina, che deve mostrare tutte le voci anche quando una è selezionata, **più** l'etichetta nel blocco «filtri applicati» dell'export | tre pezzi, non uno: la facet costruita male chiude la tendina dopo la prima scelta |
| BE-2 | `registro_codice` e `data_documento_prevista` in `DASH_COMPETENZA_GRUPPI_SORT_COLUMNS` | inscindibile da L6 |
| BE-3 | `col_registro`, `col_data_prevista` **e** la chiave di «più registri», in `it.json` **e** `en.json` | il namespace è `vendite.dashboard_competenza` |
| BE-4 | ✅ **D-4**: la frase «più registri» la compone il **BE**, nella riga accanto a `registro_codice` — così esce anche nell'**export**, che è server-side e passa dalla stessa `fetch` | senza, il file resta muto proprio sulle righe ambigue |
| FE-1 | ⚠️ **Rivista (R-9)**: slot `#cell-registro` su `<ListaConfigurabile>` — mostra ciò che il BE manda, e «—» dove non c'è nulla | non è più «nulla di strutturale» |

---

## 12. Domande aperte e decisioni da prendere

> D-1, D-2, D-3 sono chiuse (D-1 con la citazione di R-12.1). Quelle che seguono
> nascono dalla revisione e **non hanno una risposta ovvia**.

### ✅ D-4 DECISA — la frase la mette BE/FE, il DB dice solo quanti sono

> ✅ **Tid, 2026-08-26**: *«la mette il BE/FE»*. Il database **non produce la
> frase**: espone `registro_codice` (valorizzato solo quando la risposta è una) e
> `registri_n`. L'etichetta è di chi presenta.

⭐ **E l'export non è più un buco.** Nel presentare l'opzione avevo dato per
scontato che l'export fosse quello client-side di PrimeVue — dove lo slot di
cella non passa. **Non lo è**: le tre liste di questo cruscotto hanno un export
**server-side** (`GET …/dashboard-competenza/gruppi/export/`, che torna un
blob), e `build_dash_export_response` chiama **la stessa `fetch` del service**
che alimenta la lista. Quindi il file esce dalla **stessa proiezione** delle
righe a video.

→ Conseguenza pratica: **se la frase la compone il BE** (nella riga, accanto a
`registro_codice`), compare **sia a video sia nel file**, e non serve nessuna
colonna in più né nessun valore sentinella. Se invece la compone solo il FE, il
file resta muto sui gruppi multi-registro.

⚠️ **Un dettaglio resta al BE, e va deciso lì, non qui**: in che lingua. Le
intestazioni di colonna dell'export le prende già oggi dal catalogo
(`ListaExportService` + `ui.lista_colonna`), cioè scrive già italiano nel file —
quindi comporre lì la frase è coerente con quello che l'export fa adesso. Se
invece si vuole che segua la lingua della richiesta, è il BE a dover risolvere
la chiave i18n, e il FE si limita a mostrare ciò che riceve.

### ✅ D-10 DECISA — il guard di `fn_get_registro_id` diventa TECNICO ⚠️ **nota per il BE**

> ✅ **Tid, 2026-08-26**, dopo aver chiesto se fosse fattibile: *«procedi»*.

**Cosa cambia**, e riguarda solo chi consuma gli errori:

| | prima | dopo |
| --- | --- | --- |
| codice | `E_PARAMETRO_INVALIDO` | `E_VENDITE_CHIAMATA_NON_VALIDA` |
| classe / status | `DATO_ERRATO` → **400** | `TECNICO` → **500** |
| frase | *«Parametro non valido: p_tipo_doc_fiscale_id obbligatorio e > 0»* | *«Chiamata non valida a vendite.fn_get_registro_id: p_tipo_doc_fiscale_id (obbligatorio, maggiore di zero).»* |

⭐ **Al backend non serve fare niente.** `E_VENDITE_CHIAMATA_NON_VALIDA` è già
registrato su **tutti e tre** i lati — catalogo DB, `error_messages_fallback.py`
e `error_policies_generated.py` (classe `TECNICO`) — e **undici** funzioni di
vendite lo usano già, otto delle quali scritte lo stesso giorno dal cantiere del
limite di emissione. Nessun codice da coniare, nessuna riga da aggiungere ai
CSV, nessuna policy da rigenerare, nessun rilascio.

⚠️ **Ma va saputo**: se da qualche parte si contava su un **400** proveniente da
quel punto, ora arriva un **500**. È l'unica cosa che cambia per chi consuma.

**Perché è la verità**, e l'argomento è strutturale (non un conteggio):

* l'unico chiamante è `fn_build_fattura_key`, che il tipo documento lo legge da
  `attivita_fatturabili` — riga creata dall'emit a partire da un'attività
  **APPROVATA**, e `chk_commesse_attivita_tipo_doc_emittibile` garantisce che lì
  il tipo documento **ci sia**. Un NULL non è «l'operatore ha dimenticato un
  campo»: è un guasto a monte;
* ⛔ e la spia decisiva: nel contesto **non c'è la chiave `campo`**. Un
  `DATO_ERRATO` esiste per dire al frontend quale campo accendere — qui non c'è
  niente da accendere, quindi finora era **un 400 solo di nome**, che
  all'operatore non offriva nulla da correggere.

⭐ E nominare il parametro nella frase **smette di essere l'antipattern**: la
registrazione di quel codice lo autorizza esplicitamente, *«perché il suo lettore
è chi ha scritto la chiamata, non chi compila un form»*.

⚠️ **Precedente contrario, dichiarato**: in `error_policies_generated.py` è
registrato un caso in cui sei guard gemelli **restarono** su
`E_PARAMETRO_INVALIDO` con la motivazione opposta. Quel commento è **anteriore**
alla nascita di `E_VENDITE_CHIAMATA_NON_VALIDA` (2026-08-22), che esiste per
essere la casa di quei casi: precedente superato, non contraddizione.

ℹ️ **I due `E_CONFIG_MANCANTE` della stessa funzione restano intatti** — codice,
contesto, frase, area e nome. Cambiarli sarebbe rumore su punti di log che
nessuno ha chiesto di toccare.

### ✅ D-5 DECISA — il filtro si fa, ed è una consegna vera

> ✅ **Tid, 2026-08-26**: *«sì aggiungiamo il filtro, serve separare le due
> strade»*. Non è quindi un flag inerte allineato ai fratelli: è una **funzione
> nuova**, che va costruita.

⛔ **E il filtro NON può appoggiarsi alla colonna che stiamo aggiungendo.** Su un
gruppo che tocca due sezionali, `registro_codice` è **NULL** per decisione D-2 —
quindi un `WHERE registro_codice = …` lo escluderebbe da entrambi i filtri,
proprio il gruppo che ha più bisogno di essere visto. La domanda giusta non è
«qual è il registro di questo gruppo» ma **«questo gruppo tocca quel
registro?»**.

→ **Conseguenza sul DB (L5, §11.5)**: la vista gruppi espone
`registri_ids bigint[]` = `array_agg(DISTINCT a.registro_id)`, e il BE filtra con
`%s = ANY(g.registri_ids)`. Un gruppo multi-sezionale compare **sotto entrambi**,
che è la verità.

⭐ E `registri_n` non diventa una seconda verità: è `cardinality(registri_ids)`,
**la stessa espressione** con due nomi, calcolata nella stessa vista. ⚠️
`array_agg` **include i NULL** (a differenza di `count`), quindi il ramo «uno più
un ignoto» continua a contare 2 come voluto da R-8 — e il `COALESCE(-1)` del
§11.5 diventa superfluo.

⚠️ **Sul BE non è una riga**: serve anche la **facet** che alimenta la tendina,
con la regola già scritta per `tipo_gruppo` — *deve vedere tutte le voci anche
quando una è selezionata*, altrimenti scegliendo un sezionale gli altri
spariscono dalla tendina e non si può più cambiare idea. Più l'etichetta del
filtro nel blocco «filtri applicati» del file esportato (`_filtri_leggibili`).

✅ **D-5b DECISA** (Tid, 2026-08-26): si filtra **per sezionale**, non per
politica della data.

⚠️ **Il prezzo, dichiarato**: i sezionali non sono due. Ogni emittente fiscale ha
i suoi — un «Back-office» e un «Back-office-159» fanno la stessa cosa — quindi la
tendina **cresce con gli emittenti**, e «tutto ciò che sarà datato a fine mese»
si ottiene spuntandone più d'uno. È il costo della scelta, non un difetto.
⭐ Attenuante: la facet si costruisce sui `registri_ids` del **perimetro**, che la
vista filtra già per scope emittente — quindi l'operatore vede i sezionali che lo
riguardano, non tutti quelli esistenti.

ℹ️ L'alternativa scartata era filtrare su `politica_data_documento` (due voci
stabili per sempre, garantite da un `CHECK`). Resta scritta qui perché se un
giorno la tendina diventasse ingestibile, è lì che si torna.

### ~~D-5 — `filtrabile = t` sul registro: promessa o inerzia?~~ (superata)

Il §7 lo motiva con «"mostrami solo ciò che finisce sul Back-office" è una
domanda che si fa». ⚠️ Ma su questa lista quel filtro **non esiste**:
`_where_gruppi` ha filtri **nominali** (competenza, stadio, tipo gruppo, BA,
ricerca libera) e nessun filtro per colonna di catalogo — e infatti
`cliente_display`, `commessa_codice` e `id_fiscale` sono tutte `filtrabile = t`
senza che nessuno le filtri lato backend.

Quindi: o il flag è **inerte** (e allora `t` è coerente con i fratelli e non
promette niente a nessuno), oppure la domanda del §7 è una **consegna BE nuova**
— un filtro per registro, che non è nell'elenco §8. Da chiarire col backend
**prima** del seed, perché la riga del CSV la si scrive una volta.

### ✅ D-6 CHIUSA — non è un debito: l'invariante è imposta

> ✅ **Tid, 2026-08-26**: *«questo avevamo controllato che era impossibile: uno
> user è legato sempre a un emittente, ogni BA figlio si collega solo al BA padre
> generato per quell'emittente»*. **Verificato, ed è così** — e non per
> convenzione del codice che scrive, ma per **guard** (R-6): due trigger `z95`,
> `fn_guard_albero_ba_emittente` in entrambi i versi, `SECURITY DEFINER` contro
> la RLS, fail-closed sul NULL, nessuna GUC di override.

⇒ La colonna «Emittente» a video e il sezionale previsto **non possono**
contraddirsi. Niente debito da annotare, niente promemoria da aprire.

⭐ **Effetto sul piano, ed è la parte utile**: l'ancoraggio dell'emittente non è
un rischio, ma quello della **utility** sì — `billing_account.utility_id` non è
vincolata fra padre e figlio da nessun guard, ed è l'altro asse con cui si sceglie
il sezionale. **T2 è stato riscritto** su quell'asse (§11.7): costruirlo su
emittenti diversi non sarebbe nemmeno possibile.

### ~~D-6 — La colonna «Emittente» già a video descrive l'emittente della COMMESSA~~ (ritirata)

Conseguenza di R-6, fuori perimetro ma sulla **stessa riga** che stiamo
arricchendo: se un giorno esistessero BA con padre, l'operatore leggerebbe
«Emittente: Alpha» accanto a «Registro: sezionale di Beta» e avrebbe ragione a
non fidarsi di nessuna delle due. Si allinea la colonna esistente
(cantiere suo), o si dichiara il disallineamento e si va avanti?

### ✅ D-7 DECISA — larghezze libere, come le altre undici

> ✅ **Tid, 2026-08-26**: *«ok libere»*. Le due righe del §11.6 lasciano
> `larghezza_default` **vuota**, come tutte le colonne già a catalogo sulla 42.
> Le larghezze 140/120 proposte dal §7 **decadono**.

⭐ Nessuna modifica al §11.6: le due righe erano già scritte così. La decisione
toglie la deroga, non il testo.

### ~~D-7 — Le larghezze: 140/120 contro undici colonne che le lasciano vuote~~ (superata)

`useResponsiveColumns` fa il packing **a somma delle `larghezza_default`**:
introdurre due larghezze dove le altre undici sono vuote cambia il
comportamento del ritiro dinamico su tutta la lista, non solo sulle due nuove.
Da verificare col frontend prima del seed.

### ✅ D-8 DECISA — una consegna sola, appena chiude il cantiere gemello

> ✅ **Tid, 2026-08-26**: *«può essere una sola consegna appena loro terminano»*,
> con l'osservazione che
> [brief-db-limite-emissione-e-data-verificata.md](../work-done/brief-db-limite-emissione-e-data-verificata.md)
> tocca la stessa funzione. **Verificato: è così, e l'intreccio è più stretto di
> un'opinione.**

⛔ **Non è una preferenza di consegna: è un vincolo meccanico.** Il loro **DB-6**
fa `DROP + CREATE` di `vendite.fn_calcola_data_documento`, per aggiungere
`p_serie` **senza `DEFAULT`**. Le nostre due viste quella funzione la **chiamano**.
E PostgreSQL registra la dipendenza vista → funzione: provato in transazione il
2026-08-26,

```text
ERRORE: non è possibile eliminare funzione ... perché altri oggetti dipendono da esso
DETTAGLI: vista ... dipende da funzione ...
```

→ Se L4/L5 entrano **prima** del loro DB-6, il loro `DROP` **fallisce**. E il
rimedio sbagliato è a portata di mano: `CASCADE`, che porterebbe via le viste in
silenzio. ⛔ Vietato — è la trappola già scritta nelle regole del progetto («chi
RICREA deve avere numero più alto di chi DROPpa; mai `CASCADE`»).

⭐ **Ma la dipendenza è nei due sensi, ed è la ragione vera dell'unica consegna.**
Il loro brief **conta su DB-1**: dice, testualmente, che le viste «hanno già la
serie in mano, gliela dà `fn_resolve_registro_documento`». Cioè `p_serie` esiste
come parametro obbligatorio **perché** questo cantiere gliela sa dare. E la loro
**D-8** («la firma si disegna per entrambi i cantieri in una volta sola») è già
la decisione presa da Tid su quel punto.

**Ordine risultante, dentro un'unica consegna:**

| | Cosa | Perché lì |
| --- | --- | --- |
| 1 | **L0…L3** di questo brief | producono `serie`, che la firma nuova pretende. Nessuna vista li tocca, quindi non ostacolano nessun `DROP` |
| 2 | **DB-6 del cantiere gemello** — `DROP + CREATE` di `fn_calcola_data_documento` con `p_serie` | dev'essere fatto **mentre nessuna vista dipende dalla funzione** |
| 3 | **L4, L5** — le due viste | nascono già scritte sulla firma nuova: non c'è mai un momento in cui chiamano quella vecchia |
| 4 | **L6, L7** — seed e pgTAP | |

⚠️ **Numerazione**: la sequenza `20260826-NN` è **globale fra tutte le cartelle**
e i due cantieri se la dividono. I numeri `01…06` proposti al §11.1 sono
**provvisori**: vanno concordati con il gemello, e devono rispettare l'ordine
qui sopra.

⭐ **Effetto collaterale buono, e lo notano loro**: col limite di emissione, la
colonna `data_documento_prevista` smette di promettere il 31/07 su un lotto in
ritardo e mostra la data che il documento prenderà **davvero**. Cioè diventa vera
proprio nel caso che l'ha fatta nascere — il `LTF-0007307` del §1.

### ~~D-8 — Si spezza L3 dal resto?~~ (superata)

L3 (la rifattorizzazione di `fn_build_fattura_key`) è la parte con il rischio più
alto e il beneficio **meno visibile**: nessuna colonna nuova esce da lì.
La tentazione è consegnare L0-L2 + L4-L7 (la colonna, che è ciò che è stato
chiesto) e rimandare L3.

⛔ **Raccomandazione: non spezzare.** Per tutto il tempo che separa i due passi la
catena sarebbe scritta in **due** posti — cioè il difetto del §3, con
l'aggravante che il secondo posto è quello «giusto» e nessuno lo tocca più. Se
si spezza, L3 nello **stesso giro di PR**.

### ✅ D-9 DECISA — vuota dove il documento esiste già

> ✅ **Tid, 2026-08-26**: *«lasciare vuota»*. La colonna resta fedele al suo nome:
> «prevista» vuol dire *non è ancora successo*.

⚠️ **Il discriminante NON è lo stadio, è la riga di fattura.** Degli stadi che la
vista calcola, tre non hanno ancora nessun documento — `DA_APPROVARE`,
`DA_EMETTERE` e anche `EMESSA_NON_FATTURATA`, dove «emessa» vuol dire che
l'attività è passata in `attivita_fatturabili`, non che sia stata fatturata. Il
documento c'è solo quando c'è `af.fattura_riga_id`, che è **la stessa condizione**
con cui la vista distingue `FATTURATA` dagli altri.

→ Implementazione (§11.4): la risoluzione si aggancia con
`… ON (af.fattura_riga_id IS NULL)` invece di `ON true`. La regola sta **in un
punto solo**, il join, invece di essere ripetuta in un `CASE` su quattro colonne
— e dove il documento esiste la catena non si percorre affatto.

→ Test (§11.7, **T9**): su una riga con `fattura_riga_id` valorizzato le colonne
nuove sono NULL. ⚠️ Da asserire, non da dedurre: è un ramo che sparisce in
silenzio se qualcuno riporta il join a `ON true` per «semplificare».

⭐ **Conferma arrivata dall'esterno il 2026-08-26**, e vale la pena scriverla
perché è il motivo per cui la condizione è quella giusta.
[brief-db-lavoro-che-non-torna-indietro.md](brief-db-lavoro-che-non-torna-indietro.md)
documenta un difetto che produce **attività orfane**: la riga di fattura è stata
cancellata, l'attività resta marcata come fatturata e non torna in coda.
Quello stato cade nello stadio `EMESSA_NON_FATTURATA`, ma **un documento non ce
l'ha** — e infatti va ri-emesso.
⇒ Con la condizione su `af.fattura_riga_id` quelle righe **mostrano la
previsione**, che è esattamente l'informazione utile: dove finirà il lavoro
quando lo si rimetterà in coda. ⛔ Se avessimo agganciato la regola allo
**stadio** — «vuota da `EMESSA_NON_FATTURATA` in poi» — la colonna sarebbe muta
proprio sulle righe che quel brief chiama «spia di perdita».

#### ~~Le alternative, superate dalla decisione~~

La vista gruppi raggruppa **anche per `stadio`**: lo stesso gruppo compare su più
righe. Su una riga `FATTURATA` il documento esiste già, con il **suo** registro e
la **sua** data (`fatture.registro_id`, `fatture.data`, e la vista attività porta
già anno/serie/numero). Mostrarci accanto una *previsione* è la mezza verità che
questo cantiere combatte.

| | Opzione |
| --- | --- |
| a | Mostrarla comunque (è pur sempre «cosa succederebbe») |
| **b** ⭐ | Vuota sugli stadi in cui il documento **esiste già** — la colonna resta onesta al suo nome |
| c | Mostrare il registro **reale** quando c'è, la previsione altrimenti. ⛔ Ma allora la colonna non si chiama più `data_documento_prevista`, e il §2 ha già stabilito che il nome deve dire che è una previsione |

⭐ Scelta la **b**. La **c** non è morta come idea: se un giorno servisse vedere
su che sezionale un gruppo è finito davvero, è una colonna **sua**, con il suo
nome, non questa riusata.

---

## 13. Registro

### 2026-08-26 · Analisi e consegna

Richiesta di Tid dopo il caso `LTF-0007307`. Misurato sul DB vivo: il registro è
risolvibile dagli ingressi già disponibili, ma **il ponte `attivita_fatturabili`
non esiste su 46 righe DA_EMETTERE su 48** — quindi la funzione va scritta sugli
ingressi grezzi, e la catena va estratta invece che ricopiata. **Nessuna domanda resta aperta**: D-1 verificata sul codice che scrive la
colonna (§4.1), D-2 e D-3 decise da Tid lo stesso giorno.

⚠️ Due dettagli corretti prima di consegnare, entrambi del tipo che finisce
copiato in un seed e fallisce in CI: la lista 43 è aggregata **per commessa**
(non per attività) e il namespace i18n è `dashboard_competenza`, non
`dash_competenza`.

### 2026-08-26 · Revisione critica e piano di sviluppo (§10, §11, §12)

Rilettura del piano contro il codice vivo e contro il DB di sviluppo. Il disegno
regge — «estrarre invece di ricopiare» è la risposta giusta — ma **non è
scrivibile così com'è**, e il perché è una cosa sola: le funzioni della catena
**sollevano**, e una vista che le chiama non restituisce una colonna vuota,
**muore**. Nessuna vista del database le chiama oggi: questo cantiere sarebbe il
primo.

Da lì discende la consegna nuova (**DB-0**, il lookup senza raise) e la firma
corretta di DB-1: quella del §3.1 lascia `fn_build_fattura_key` a ricalcolarsi i
due ancoraggi in proprio, cioè non toglie la duplicazione che dichiara di
togliere.

Le altre tre conclusioni portanti si leggono tutte sul **contratto**, e non su
quante righe ci siano in questo momento:

* `billing_account.parent_account_id` è **nullable**, ed è l'unica colonna che
  separa i due ancoraggi → un confronto sui documenti **esistenti** non può
  provare DB-2: prova i rami che quella popolazione per caso contiene. La prova
  è un caso **costruito** (T2).
* La chiave del gruppo **non contiene** tipo documento né natura, che sono
  colonne **di riga** → un gruppo su più registri, con più politiche di data, è
  ammesso per costruzione. Non è un'eccezione: è il ramo normale della porta
  manuale, dove il tipo documento lo sceglie l'operatore riga per riga.
* Il `CHECK` sul tipo documento lo pretende **solo** su una riga approvata e non
  emessa → su uno stadio `DA_APPROVARE` il NULL è **ammesso**, e con quel NULL la
  lista risponde 500.

⚠️ **Nota di metodo, ed è una correzione a questa stessa revisione.** La prima
stesura appoggiava queste tre conclusioni a tre conteggi sul DB di sviluppo
(«42 su 42», «1 su 77», «zero righe»). Le conclusioni erano giuste — ed è
proprio questo che rende il difetto difficile da vedere: la misura non sbagliava
la risposta, **occupava il posto dell'argomento**, e una analisi così scade con
la macchina su cui è stata scritta. Riscritte sul modello. Richiamo di Tid, e la
regola ora vive nel repo: `.codex/AGENTS.md` § «Regola zero — le misure non disegnano il progetto»,
più il punto 5 della filosofia non negoziabile in `.codex/PROJECT_CONTEXT.md`.

Sanate anche quattro incoerenze interne, fra cui D-1 che il file dava per chiusa
in testa e per aperta al §4.1: **è chiusa**, ed è verificabile —
`fn_emit_attivita_fatturabili_da_commessa` è l'unica funzione che scrive
`attivita_fatturabili` e ci copia la BA della commessa.

Aperte sei domande nuove (**D-4…D-9**). Due bloccano il seed e nient'altro: se
`filtrabile` sia una promessa o un flag inerte su questa lista (**D-5**) e le
larghezze (**D-7**). ⛔ Nessun file scritto: il piano è pronto, l'esecuzione no.

### 2026-08-26 · Le decisioni (D-4…D-9) e una revisione ritirata

Sei domande, chiuse tutte in giornata con Tid. ⭐ **Nessuna domanda aperta.**

| | Decisione | Cosa cambia nel piano |
| --- | --- | --- |
| **D-4** | La frase «più registri» la mette **BE/FE**, il DB dice solo *quanti* | il DB non produce testo. ⭐ E l'export **non è un buco**: è server-side e passa dalla stessa proiezione della lista, quindi componendola nel BE compare anche nel file |
| **D-9** | La previsione resta **vuota** dove il documento esiste già | il join si aggancia `ON (af.fattura_riga_id IS NULL)`. ⚠️ Il discriminante è la riga di fattura, non lo stadio: `EMESSA_NON_FATTURATA` un documento non ce l'ha ancora |
| **D-5** | Il **filtro per sezionale si fa** | ⛔ e non può appoggiarsi a `registro_codice`, che su un gruppo multi-sezionale è NULL: nasce `registri_ids bigint[]`, e il gruppo compare **sotto entrambi** i filtri. `registri_n` diventa `cardinality()` della stessa espressione |
| **D-5b** | Per **sezionale**, non per politica della data | prezzo dichiarato: la tendina cresce con gli emittenti |
| **D-7** | Larghezze **libere** | il §7 (140/120) decade; le righe del §11.6 erano già così |
| **D-8** | **Consegna unica** col cantiere gemello | ▼ sotto |
| **D-6** | **Chiusa senza debito** | ▼ sotto |

⛔ **D-8 non è una preferenza, è un vincolo meccanico.**
[brief-db-limite-emissione-e-data-verificata.md](../work-done/brief-db-limite-emissione-e-data-verificata.md)
fa `DROP + CREATE` della stessa `fn_calcola_data_documento` che le nostre viste
chiamano, e PostgreSQL **rifiuta** di eliminare una funzione da cui dipende una
vista (provato in transazione). Se le viste entrassero prima, il loro `DROP`
fallirebbe — e il rimedio a portata di mano, `CASCADE`, porterebbe via le viste
in silenzio. ⭐ La dipendenza è **nei due sensi**: il loro `p_serie` obbligatorio
esiste perché `fn_resolve_registro_documento` di qui la sa dare. Ordine e
numerazione condivisa in §12 D-8.

⚠️ **R-6 ritirata su richiamo di Tid, ed è la correzione più importante della
giornata.** Avevo segnalato come rischio che l'emittente della commessa e quello
che sceglie il sezionale potessero divergere. Non possono: l'omogeneità
dell'emittente nell'albero dei billing account è **imposta** da
`fn_guard_albero_ba_emittente` — due trigger `z95`, verso il padre **e** verso i
figli, `SECURITY DEFINER` perché la RLS nasconderebbe proprio il caso da
bloccare, fail-closed sul NULL, e nessuna GUC di override.
⭐ **La correzione non svuota R-5, la mette a fuoco**: dei due ancoraggi resta in
piedi quello della **utility**, che nessun guard vincola fra padre e figlio ed è
l'altro asse con cui si sceglie il sezionale. **T2 riscritto** su quell'asse —
costruirlo su emittenti diversi non sarebbe nemmeno possibile.

### 2026-08-26 · L0 e L1 scritti e provati (nessuna migrazione)

⛔ **Nessun `update` eseguito.** I due file sono stati provati eseguendo l'SQL
**estratto dallo YAML** — non una copia riscritta, cosi' il `COMMENT ON` entra
nella prova — dentro un file con `BEGIN`/`ROLLBACK` **nel file stesso**.

| File | Cosa |
| --- | --- |
| `20260826-14-create-fn-lookup-registro-id` | il lookup: STABLE, `%TYPE` in firma, `RETURNS TABLE` e `DECLARE`, nessun raise, **sempre una riga** con la natura risolta in testa |
| `20260826-15-update-fn-get-registro-id-involucro` | l'involucro: firma, `RETURNS TABLE` e i **tre errori** invariati |

**Esito delle asserzioni** (nella stessa transazione, poi annullata):

| | Verifica | Esito |
| --- | --- | --- |
| A2 | tipo documento NULL sul lookup → **non solleva**, una riga | ✅ è il 500 sulla lista, chiuso |
| A4 / B1 | equivalenza vecchio ↔ nuovo su **tutta la matrice di configurazione** (8 combinazioni tipo × natura × emittente) | ✅ 0 registri divergenti, 0 serie divergenti |
| B2 | il guard di parametro solleva ancora `P0001`, **frase identica** | ✅ *«Parametro non valido: p_tipo_doc_fiscale_id obbligatorio e > 0»* |
| B3 | registro non risolvibile → solleva `P0001`, **frase identica** | ✅ *«Configurazione mancante: registro non risolto per tipo_doc 1 e natura 1»* |
| B4 | **lo stesso caso di B3 sul lookup** → NULL, nessuna eccezione | ✅ è la separazione, vista da entrambi i lati |
| B5 | `pg_get_function_identity_arguments` → **una sola** `fn_get_registro_id` | ✅ nessun overload nato per sbaglio |

⚠️ **Una premessa mia sbagliata, corretta**: avevo scritto un'asserzione «un
emittente inesistente ripiega sul livello 4 della gerarchia». Risponde **falso**,
e non è un difetto: in questa configurazione **nessun registro ha l'emittente a
NULL**, quindi il livello 4 non esiste — ed è una scelta presidiata da
`test-registri-per-emittente-v1` («nessun registro *di nessuno*», la condizione
che aveva fatto numerare due aziende sullo stesso registro).

ℹ️ **Numerazione reale: `-14` e `-15`**, non `-01`/`-02` come diceva il piano: il
cantiere «limite emissione» aveva già occupato `01…13`.

⭐ **Debito CHIUSO** in giornata, su decisione di Tid (✅ D-10, §12): il guard di
`fn_get_registro_id` passa da `E_PARAMETRO_INVALIDO` a
`E_VENDITE_CHIAMATA_NON_VALIDA`. ⚠️ Sposta lo **status da 400 a 500**, ed è la
sola cosa che cambia per chi consuma — al backend non serve fare niente, il
codice è già registrato su tutti e tre i lati. Riprovato dopo la modifica:

| | Verifica | Esito |
| --- | --- | --- |
| B2 | il guard solleva `P0001` con la frase nuova | ✅ *«Chiamata non valida a vendite.fn_get_registro_id: p_tipo_doc_fiscale_id (obbligatorio, maggiore di zero).»* |
| B6 | nel corpo non resta traccia del codice vecchio | ✅ `usa_codice_tecnico = t`, `usa_ancora_il_vecchio = f` |
| B7 | classe a catalogo | ✅ `TECNICO` |
| B1, B3, B4, B5 | equivalenza, secondo errore, lookup silenzioso, nessun overload | ✅ invariati |

### 2026-08-26 · L2 scritta e provata — ⭐ i due ancoraggi sono PROVATI

`20260826-16-create-fn-resolve-registro-documento`. Nessuna migrazione: prova
sull'SQL **estratto dallo YAML**, in transazione annullata.

⭐ **Il lookup ha guadagnato una colonna**: restituisce anche
`politica_data_documento`. Non è lavoro in più — il `JOIN` su
`registri_fatturazione` c'era già, quindi è **restituire ciò che si è già
letto** invece di far rifare al chiamante una `SELECT` per chiave sulla stessa
riga.

| | Verifica | Esito |
| --- | --- | --- |
| C1 | equivalenza con la catena di `fn_build_fattura_key` su **tutti** i billing account | ✅ 0 divergenze su BA di fatturazione, utility ed emittente |
| **C2** | ⭐ **il caso COSTRUITO**: figlio con `parent_account_id` e **utility diversa** dal padre | ✅ `ba_fatturazione` dal **PADRE**, `utility` dalla **RIGA** |
| C3 | tipo documento NULL | ✅ nessuna eccezione, registro NULL, **anelli intermedi comunque risolti** |
| C4 | billing account inesistente | ✅ tutto NULL — **nessun ripiego** sul registro «di nessuno» |
| C5 | guard di parametro | ✅ `P0001`, *«Chiamata non valida a vendite.fn_resolve_registro_documento: p_billing_account_id_riga (obbligatorio, maggiore di zero).»* |
| C6 | la politica esce insieme al registro | ✅ coerente con `registri_fatturazione` |

⭐ **C2 chiude R-5, ed è la consegna più importante di questo passo.** Il brief
diceva che la prova dei due ancoraggi doveva essere **costruita** e non cercata
nella popolazione — perché `parent_account_id` è nullable e un confronto sui
documenti esistenti esercita solo i rami che quella popolazione per caso
contiene. Il caso si costruisce davvero: un BA figlio con utility diversa passa
il guard dell'albero (l'emittente resta lo stesso, ed è quello che il guard
pretende). ⇒ **T2 di §11.7 è scrivibile**, e va scritto esattamente così.

⚠️ E conferma R-6 dal lato pratico: il caso si costruisce **sulla utility**, non
sull'emittente. Un figlio con emittente diverso il guard lo rifiuterebbe, e il
test non partirebbe nemmeno.

### 2026-08-26 · L3 scritta e provata — ⭐ la duplicazione è sparita

`20260826-17-update-fn-build-fattura-key-resolve-registro`. Nessuna migrazione.

Spariscono da `fn_build_fattura_key` **tre risoluzioni fatte a mano** — il
`COALESCE` sul `parent_account_id`, la lettura di `ba.utility_id` e
`fn_get_emittente_fiscale_id` — più la chiamata a `fn_get_registro_id`. Al loro
posto **una riga**: `fn_resolve_registro_documento(v_ba_id, tipo_doc, natura)`.

⭐ **Da qui la colonna «data prevista» smette di essere una profezia**: la lista e
il documento non coincidono più perché due implementazioni si comportano uguale,
ma perché è **la stessa funzione**.

**La prova di invarianza**, catturando la chiave **prima** della sostituzione e
riconfrontandola **dopo**, nella stessa transazione annullata:

| | Verifica | Esito |
| --- | --- | --- |
| D1 | tutte le attività, chiave completa vecchia ↔ nuova | ✅ **51 su 51, 0 divergenti** |
| D2 | confronto **elemento per elemento** degli undici | ✅ 0 righe: nessun elemento diverso |
| D3 | firma | ✅ una sola, invariata |

ℹ️ Nessuna attività andava già in errore prima, quindi il confronto è pieno e
nessuna riga è finita in `error_log`.

⚠️ **Due scelte scritte nel changelog perché non sembrino sviste:**

1. **il `JOIN` su `billing_account` RESTA**, ma non per leggere la utility — la
   dà il resolver. È il **guard** che produce `E_VALORE_MANCANTE` quando il
   billing account non esiste o non è visibile sotto RLS. Toglierlo sposterebbe
   quell'errore su un codice diverso e più avanti. Costa una seconda lettura per
   chiave, sul percorso di scrittura, una volta per attività: si paga;
2. **i due cancelli restano lì** perché il resolver non ferma — e non deve, è ciò
   che lo rende usabile da una vista. Emittente NULL richiama
   `fn_get_emittente_fiscale_id`, registro NULL richiama l'involucro: così i
   **messaggi restano identici** e la seconda risoluzione si paga **solo quando
   si sta già andando in errore**. ⚠️ E l'ordine è portante: prima l'emittente,
   o un billing account senza emittente mappato leggerebbe «registro non
   risolto» invece di «emittente di default mancante».

### 2026-08-26 · L4, L5 e L7 — le colonne ci sono, e il pgTAP è verde

Sei file scritti (`20260826-14` … `-19`) più il test. ⛔ **Nessuna migrazione**:
ogni prova è girata sull'SQL **estratto dagli YAML**, in transazione annullata.

#### L4 — `vw_dash_competenza_attivita`

| | Verifica | Esito |
| --- | --- | --- |
| E1 | `security_invoker=on` non azzerata dal `REPLACE` | ✅ |
| E3 | la vista si legge: 47 `DA_EMETTERE` e 5 `EMESSA_NON_FATTURATA` **con** sezionale e data, 44 `FATTURATA` **senza** | ✅ |
| E4 | D-9: 44 righe con documento, **0 violazioni** | ✅ |
| **E5** | ⭐ con una riga **senza tipo documento** la vista legge 96 righe invece di morire | ✅ **è il 500, chiuso** |
| E6 | il sezionale previsto coincide con quello della catena di scrittura | ✅ 0 divergenti |

⚠️ **Trappola incontrata**, e vale la pena averla scritta: la prima corsa dava
**0 righe** su tutto. Non era un difetto del mio codice — è il fail-closed della
vista senza contesto operatore (R-11, e la stessa trappola che il cantiere
«lavoro che non torna indietro» ha annotato al suo §7.3). Il contesto si mette
con `script.fn_pgtap_set_contesto_operatore()`.

#### L5 — `vw_dash_competenza_gruppi`

| | Verifica | Esito |
| --- | --- | --- |
| F0 | il presupposto di R-8: `array_agg(DISTINCT)` su `{1,NULL,1}` → `{1,NULL}`, cardinalità **2**, mentre `count(DISTINCT)` dice **1** | ✅ misurato, non assunto |
| F1, F2 | `security_invoker` preservata, quattro colonne in coda | ✅ |
| F5 | `registri_n` = `cardinality(registri_ids)` su tutti i gruppi | ✅ 0 divergenti |
| **F7** | ⭐ **caso costruito**: gruppo con due sezionali → `{3,4}`, `registri_n=2`, **codice e data vuoti**, e il gruppo compare **sotto entrambi** i filtri | ✅ D-2 e D-5 insieme |

⚠️ **F7 è costato tre tentativi, e i primi due erano il TEST a sbagliare** — vale
la pena scriverlo perché sono le stesse trappole in cui cadrà chi manutiene:

1. «due attività della stessa **commessa**» non è «stesso gruppo»: la chiave del
   gruppo contiene anche la **sorgente**;
2. cambiare il tipo documento non basta: con natura **NOTA_CREDITO** tutti i tipi
   convergono sullo stesso sezionale NC, quindi il candidato va cercato **a
   natura invariata** e verificando che porti davvero a un registro diverso.

⭐ Entrambe le lezioni sono finite dentro il pgTAP, che cerca un gruppo **dove il
caso sia costruibile** invece di prendere il primo.

#### L7 — `db/pgtap/vendite/test-registro-documento-previsto-v1.sql`

**12 asserzioni, 12 verdi, 0 rosse**, guardrail del preambolo superato. I due
casi che contano sono **costruiti**, non cercati: i due ancoraggi (test 4) e il
gruppo multi-sezionale (test 9-10).

⚠️ **T1 del piano è stato TOLTO, di proposito.** Era «per ogni fattura esistente
il registro coincide con `fatture.registro_id`»: su un database ricostruito da
zero — cioè in CI — quell'asserzione passa **a vuoto**, ed è la forma classica
del verde per sottrazione. La copertura sta sui test 3, 4 e 7, che i soggetti se
li fabbricano. La rete anti-regressione sulla popolazione è stata comunque
eseguita **una volta**, qui in analisi (D1: 51 chiavi su 51 identiche), che è il
posto giusto per una misura del genere.

#### ⛔ L6 (il seed) è FERMO, e non per una scelta mia

Servono **due cose dal backend**, e nessuna delle due è nel perimetro DB:

| | Cosa manca | Cosa succede senza |
| --- | --- | --- |
| BE-2 | le due voci in `DASH_COMPETENZA_GRUPPI_SORT_COLUMNS` | `test_liste_configurabili_seed` **rosso**: lega catalogo e whitelist nei due versi |
| BE-3 | le chiavi i18n in `it.json` **e** `en.json` | `check_i18n_keys.py` **rosso**: legge proprio `ui.lista_colonna.etichetta_i18n_key` |

⚠️ **Non c'è una scorciatoia**: mettere `ordinabile = f` eviterebbe il primo
guard ma non il secondo, perché la chiave i18n serve comunque. Le due righe CSV
sono pronte per esteso in §11.6.

### 2026-08-26 · L6 — le due righe di catalogo, appese

Scritte su decisione di Tid (*«scrivile, non c'è problema»*), accettando che due
guard restino rossi finché il backend non consegna. **Nessun changeSet nuovo**:
il mirror ri-ancorato `20260806-15` è `runOnChange` e carica tutte e 24 le
colonne — verificato — quindi le righe entrano al prossimo migrate.

`id` **553** e **554**, lista **42** soltanto. Provate inserendole davvero in
`ui.lista_colonna` dentro una transazione annullata, così CHECK, FK e trigger
sono stati esercitati:

| | Verifica | Esito |
| --- | --- | --- |
| | le due righe entrano nella tabella | ✅ nessun vincolo violato |
| | `sensibile = f`, `attivo = t`, `tipo_colonna = informazione` | ✅ (⛔ `sensibile = t` sarebbe stato un cancello, non un'etichetta) |
| | ordini `75`/`78` e priorità `45`/`50` | ✅ 13 colonne, 13 ordini distinti — nessuna collisione |
| ⭐ | **il `campo_sorgente` esiste davvero sulla vista** | ✅ `registro_codice` e `data_documento_prevista` ci sono entrambe |

⭐ L'ultima è la verifica che vale di più: è **esattamente** il modo in cui questa
classe di seed fallisce — una colonna a catalogo il cui campo a monte non
esiste si spunta e resta **vuota**, senza nessun errore. Qui il campo c'è.

⚠️ **Due guard resteranno rossi**, ed è noto e accettato:

| Guard | Perché | Chi lo chiude |
| --- | --- | --- |
| `test_liste_configurabili_seed` | le due colonne sono `ordinabile = t` e non sono nella whitelist del repository | **BE-2** |
| `check_i18n_keys.py` | legge `ui.lista_colonna.etichetta_i18n_key` e le due chiavi non sono in `it.json`/`en.json` | **BE-3** |

⛔ **Non c'era una scorciatoia**: mettere `ordinabile = f` avrebbe evitato il
primo ma non il secondo, perché la chiave i18n serve comunque.

---

## 2026-08-26 · ✅ CANTIERE DB CHIUSO — quadro completo

Migrazione applicata da Tid. **Nessuna regressione, test verdi, doc auto-generata
rigenerata.**

### Cosa è stato consegnato

| | Consegna | File | Stato |
| --- | --- | --- | --- |
| **L0** | `vendite.fn_lookup_registro_id` — la ricerca del sezionale **senza** il raise, `STABLE` | `20260826-14` | ✅ applicato |
| **L1** | `vendite.fn_get_registro_id` diventa l'**involucro** | `20260826-15` | ✅ applicato |
| **L2** | `vendite.fn_resolve_registro_documento` — la catena intera, i **due ancoraggi** compresi | `20260826-16` | ✅ applicato |
| **L3** | `fn_build_fattura_key` smette di risolvere in proprio | `20260826-17` | ✅ applicato |
| **L4** | `vw_dash_competenza_attivita` — 4 colonne | `20260826-18` | ✅ applicato |
| **L5** | `vw_dash_competenza_gruppi` — 4 colonne, «uno oppure N» | `20260826-19` | ✅ applicato |
| **L6** | catalogo: 2 righe, `id` 553-554, lista 42 | `ui/lista_colonna.csv` | ✅ caricate dal mirror |
| **L7** | pgTAP, 12 asserzioni | `test-registro-documento-previsto-v1.sql` | ✅ 12/12 verde |
| **DOC** | doc concettuale delle due funzioni nuove | `dbzero/vendite/manual/fn_lookup_registro_id.md`, `…/fn_resolve_registro_documento.md` | ✅ scritte, riferimenti verificati |

### Le prove che reggono il lavoro

Tutte girate sull'SQL **estratto dagli YAML** — non su una copia riscritta, così
il `COMMENT ON` entra nella prova — in transazione con `ROLLBACK` **nel file
eseguito**.

| | Cosa provava | Esito |
| --- | --- | --- |
| **A4 / B1** | equivalenza lookup ↔ involucro su tutta la matrice di configurazione | 8 combinazioni, **0 divergenze** |
| **B2, B3** | i messaggi d'errore dell'involucro | invariati, `P0001` |
| **B5** | nessun overload nato per sbaglio | una sola `fn_get_registro_id` |
| **C1** | equivalenza della catena su tutti i billing account | **0 divergenze** su BA, utility ed emittente |
| ⭐ **C2** | **i due ancoraggi, su caso COSTRUITO** | BA di fatturazione dal **padre**, utility dalla **riga** |
| **C4** | billing account irraggiungibile | tutto vuoto, **nessun ripiego** |
| ⭐ **D1/D2** | **invarianza della chiave fattura**, elemento per elemento | **51 su 51 identiche**, 0 elementi diversi |
| ⭐ **E5** | **il 500 sulla lista** | con una riga senza tipo documento la vista **legge**, non muore |
| **E4** | D-9 | 44 righe con documento, **0 previsioni mostrate** |
| **F0** | il presupposto di R-8, misurato | `array_agg` tiene i NULL, `count(DISTINCT)` no |
| ⭐ **F7** | **gruppo multi-sezionale, COSTRUITO** | `{3,4}`, codice e data vuoti, e compare sotto **entrambi** i filtri |

### Le decisioni prese durante il lavoro

| | |
| --- | --- |
| **D-4** | la frase «più registri» la mette BE/FE — il DB dice *quanti*. ⭐ L'export è server-side e condivide la proiezione: componendola nel BE compare anche nel file |
| **D-5 / D-5b** | il filtro per **sezionale** si fa — e da qui nasce `registri_ids`, perché un gruppo multi-sezionale deve comparire sotto **entrambi** i filtri |
| **D-6** | chiusa **senza debito**: l'omogeneità dell'emittente nell'albero dei BA è imposta da un guard |
| **D-7** | larghezze libere, come le altre undici |
| **D-8** | consegna unica col cantiere gemello del limite di emissione |
| **D-9** | previsione **vuota** dove il documento esiste già |
| **D-10** | il guard di `fn_get_registro_id` passa a un codice **TECNICO** — ⚠️ **status 400 → 500**, nota per il BE |

### Cosa il cantiere ha prodotto oltre a sé stesso

* ⭐ **Una regola nel repo**: `.codex/AGENTS.md` § «Regola zero — le misure non
  disegnano il progetto», con il discriminante **struttura contro popolazione**,
  la prova del nove e il corollario sui test. Più il punto 5 della filosofia non
  negoziabile in `PROJECT_CONTEXT.md`.
* ⭐ **Due cantieri nuovi**, nati da un difetto scoperto chiudendo D-6:
  [brief-db-emittente-commessa-invariante.md](brief-db-emittente-commessa-invariante.md)
  (la chiave di perimetro della commessa è nullable) e
  [brief-db-billing-account-cambio-emittente.md](brief-db-billing-account-cambio-emittente.md)
  (la domanda fiscale, separata apposta).

### ⚠️ Cosa resta aperto, e non è del DB

| | Consegna | Nota |
| --- | --- | --- |
| BE-0 | **prendere atto** del cambio 400 → 500 (D-10) | nessun lavoro: il codice è già registrato su tutti e tre i lati |
| BE-1 | proiezione delle colonne nella lista gruppi | ⛔ senza, le colonne si spuntano e restano **vuote** |
| BE-2 | whitelist di ordinamento | ⚠️ **`test_liste_configurabili_seed` è rosso finché non arriva** |
| BE-3 | chiavi i18n in `it.json` **e** `en.json`, «più registri» compresa | ⚠️ **`check_i18n_keys.py` è rosso finché non arrivano** |
| BE-4 | la frase «più registri» composta nel BE (D-4) | così esce anche nell'export |
| BE-5 | filtro per sezionale + **facet** + etichetta nei «filtri applicati» dell'export | tre pezzi, non uno |
| FE-1 | slot `#cell-registro` | mostra ciò che il BE manda, «—» dove non c'è nulla |

⚠️ **I due guard rossi sono noti e accettati** (decisione di Tid): non c'era
scorciatoia, perché `ordinabile = f` avrebbe evitato il primo ma non il secondo.
