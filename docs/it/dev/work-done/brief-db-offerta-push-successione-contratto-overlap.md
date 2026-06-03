# Brief DB — Successione contratti: meccanismo generico su overlap

> **Stato**: ✅ **COMPLETO end-to-end** (DB + BE + FE), 2026-05-31. DB su
> `dev/db-tid` (migration `20260531-01..04`, pgTAP 18 verdi); BE+FE cablati
> (push a 3 param + endpoint `contratto-sovrapposto/` + dialog di successione,
> 53/53 test service verdi, vite build verde). Documentazione API aggiornata
> (`api_offerte.md` + catalogo BB backend). Vedi checklist §8.
>
> **Unico residuo aperto**: i percorsi di creazione contratto **diversi dal
> push offerta** (creazione manuale, futuri push) non agganciano ancora il
> meccanismo di successione — debito tracciato in §6, fuori scope per
> decisione di Tid.
>
> **Owner concettuale**: Tid (Michele Carlo Titini)
>
> **Tipo**: nuovo meccanismo di **dominio contratti** (successione su
> sovrapposizione temporale), riusabile da ogni percorso di creazione
> contratto. Il push offerta→contratto è il **primo consumatore**, non il
> proprietario della logica.
>
> **Revisione 2026-05-31**: brief riscritto attorno al **piano esecutivo
> spuntabile** (§8) dopo verifica del brief contro il codice reale. Le verifiche
> hanno confermato l'impianto ma corretto tre punti (vedi §0):
>
> 1. gli id dei codici errore (il brief precedente puntava a 463/464 già
>    occupati → ora **465/466**);
> 2. il "punto di rischio principale" (lock post-attivazione) è un **non
>    problema**: il trigger non scatta sull'UPDATE di `valido_al`;
> 3. aggiunta la gestione della **concorrenza** (advisory lock + exception
>    backstop), assente nella stesura precedente e invece presente nel pattern
>    di riferimento.
>
> **Revisione 2026-05-30b** (storica): riscritto attorno al meccanismo generico
> (decisione Tid: la nota di simmetria §6 della stesura precedente è
> confermata). La logica di successione **non** vive dentro
> `fn_push_offerta_a_contratto`: è estratta in funzioni di dominio contratti
> che il push (e i futuri percorsi) invocano. Memoria
> `feedback_simmetria_modello_no_meta_scope`: abbracciare la simmetria piena
> subito, non incassarla in un solo percorso e rifattorizzare dopo.
>
> **Dipendenze a valle (BE + FE)**: bloccate finché questo brief non è
> applicato. Per decisione di Tid (2026-05-30) si procede **brief DB ora,
> BE+FE tutto insieme a DB pronto** (memoria
> `feedback_be_fe_attende_prerequisiti_db`).

---

## 0. Verifiche fatte il 2026-05-31 (codice reale vs brief)

Confronto del brief con lo stato corrente di `dev/db-tid`. **Conferme** e
**correzioni** che hanno plasmato il piano §8.

### Conferme (il brief regge)

- EXCLUDE `ex_contratti_no_overlap` su `(billing_account_id, istanza_utility_id,
  utility_id, ambito, validita)` con `WHERE (NOT is_abortito_snapshot)` —
  `00_schema/vendite/20260521-03-alter-contratti-validita-attiva-temporal-unique-mctit.yaml`.
- `validita` è `GENERATED ALWAYS AS daterange(COALESCE(valido_dal,
  '-infinity'), COALESCE(valido_al, 'infinity'), '[]') STORED NOT NULL` —
  `00_schema/vendite/20260514-10-alter-contratti-validita-stored-temporal-unique-mctit.yaml`.
- `chk_contratti_validita`: `valido_al IS NULL OR valido_al >= valido_dal` —
  `00_schema/vendite/20260119-03-rename-contratti-valid-dal-al-mctit.yaml`.
- Il push **non** valorizza `ambito` (→ default `'COMMODITY'`) e prende le date
  da `v_offerta.validita_dal` / `validita_al`; firma attuale `(p_offerta_id,
  p_pratica_id)` —
  `20_code/vendite/20260526-26-update-fn-push-offerta-a-contratto-add-componenti-mctit.yaml`.
- `is_abortito_snapshot` mantenuto da trigger e usato dall'EXCLUDE parziale —
  `00_schema/vendite/20260521-01-alter-contratti-add-is-abortito-snapshot-mctit.yaml`.

### Correzioni (cosa cambia rispetto alla stesura precedente)

1. **Id codici errore**: il CSV ha già id fino a **464** (463 =
   `E_CONTRATTO_EMITTENTE_NON_RISOLTO`, 464 = `E_CONTRATTO_EMITTENTE_BA_INCOERENTE`,
   lavoro emittente del 2026-05-29). I nuovi codici vanno a **465 / 466**, non
   463/464. *(Verificato 2026-05-31: nessun doppione id nel CSV; un codice = un
   id, mappatura 460→464 pulita.)*
2. **Lock post-attivazione NON è un rischio**: `trg_contratti_a10_lock_post_attivazione_upd`
   è `BEFORE UPDATE OF listino_id, listino_versione_id,
   tipo_variazione_globale, valore_variazione_globale` — scatta **solo** sui 4
   campi di pricing. Il suo stesso commento dice: *"Il trigger non scatta per
   update di altri campi (meta, note, valido_al)"*
   (`20_code/vendite/20260515-14-create-trg-contratti-lock-post-attivazione-mctit.yaml`).
   Accorciare `valido_al` su un contratto ATTIVO è quindi già un path libero. Il
   relativo test resta come **regressione banale**, non come "punto di rischio".
3. **Concorrenza (nuovo)**: lo split detect→insert introduce una gara
   check-then-act (TOCTOU). Il pattern di riferimento
   `catalogo.fn_duplica_componente_versione` la risolve con
   `pg_advisory_xact_lock` + `EXCEPTION WHEN exclusion_violation`. Il brief
   precedente ereditava il pattern ma ne ometteva questa parte: ora è esplicita
   (§3.4).
4. **Guard data esplicita necessaria** (conferma motivata): il riferimento BoM
   delega l'errore data a un trigger parlante; sui contratti esiste **solo** il
   CHECK `chk_contratti_validita` (errore generico). Quindi la guard esplicita
   `E_CONTRATTO_SUCCESSIONE_DATA_INVALIDA` **prima** del CHECK è indispensabile,
   non ridondante.
5. **Naming**: `fn_cedi_contratto_per_successione` →
   **`fn_chiudi_contratto_per_successione`** (il verbo descrive l'operazione:
   accorciamento di `valido_al`).

### Pre-verifiche — esito (2026-05-31)

- ✅ **Job `chiusura_scadenze_daily`** (Tid, 2026-05-31): cessa effettivamente
  un contratto ATTIVO con `valido_al` passato. L'assunzione "niente cambio di
  stato, ci pensa il job" (§3.2.2) è confermata.
- ✅ **Doppioni id CSV**: nessuno. Mappatura 460→464 pulita, un codice = un id.

---

## 1. Problema

Ogni creazione di un contratto fa un `INSERT`/`UPDATE` su `vendite.contratti`.
Quando per la stessa quintupla `(billing_account_id, istanza_utility_id,
utility_id, ambito, validita)` esiste già un contratto attivo (non abortito) la
cui finestra temporale si sovrappone, scatta il constraint di esclusione:

```text
ex_contratti_no_overlap
  EXCLUDE USING gist (billing_account_id, istanza_utility_id, utility_id,
                      ambito, validita)
  WHERE (NOT is_abortito_snapshot)
```

Oggi questo si manifesta nel **push offerta→contratto**
(`vendite.fn_push_offerta_a_contratto`), che fa INSERT diretto: l'errore grezzo
Postgres trapela al client avvolto in `E_VENDITE_VALIDATION` ("Errore push
offerta a contratto." + DETAIL della GiST). Esempio reale (2026-05-30):

```text
le chiavi in conflitto violano il vincolo di esclusione "ex_contratti_no_overlap"
DETAIL: La chiave (..., validita)=(173, 197, 5, COMMODITY, [2026-05-26,infinity])
è in conflitto con la chiave esistente (..., validita)=(173, 197, 5, COMMODITY, [2026-05-20,infinity]).
```

Lo stesso conflitto può emergere da **qualunque** altro percorso di creazione
contratto (creazione manuale via `ContrattiService`, futuri push da altre
sorgenti). Difetti:

1. **Errore non parlante**: il vincolo GiST trapela al client invece di un
   codice semantico con il contratto in conflitto.
2. **Nessun flusso di successione**: l'operatore non ha modo di dire
   "chiudi il vecchio contratto e apri il nuovo".
3. **Rischio di duplicazione logica**: risolverlo nel solo push lascia gli
   altri percorsi scoperti, e quando li toccheremo riscriveremo la stessa cosa.

## 2. Decisione di modello (Tid, 2026-05-30)

- La **successione** (chiudere il contratto esistente e aprire il nuovo) è
  un'operazione **legittima ma esplicita**: mai automatica. Nessun percorso, di
  default, chiude un contratto preesistente.
- Sul conflitto, il sistema deve **mostrare il contratto esistente** e chiedere
  conferma; solo dopo conferma esplicita si procede con la chiusura del
  vecchio e l'apertura del nuovo.
- Il contratto in conflitto è **preesistente legittimo** (non residuo di test):
  la successione ne **accorcia** la validità, non lo annulla.
- **Data di chiusura del vecchio**: `valido_al = <valido_dal del nuovo
  contratto> − 1 giorno` (continuità senza buchi né sovrapposizioni; la
  daterange `validita` del vecchio si restringe e l'EXCLUDE passa).
- **La logica è di dominio contratti, non del push**: estratta in funzioni
  riusabili (§3.2) che il push invoca (§3.4). I futuri percorsi di creazione
  contratto adotteranno le stesse funzioni.

> **Precedente identico già a modello** (memoria
> `feedback_simmetria_modello_no_meta_scope`):
> `catalogo.fn_duplica_componente_versione` gestisce esattamente questo schema
> sul BoM — l'EXCLUDE `ex_articoli_componenti_no_overlap` impedisce
> sovrapposizioni temporali e la fn "apre la nuova versione al giorno
> successivo alla chiusura della sorgente" (codice errore
> `E_BOM_VERSIONE_OVERLAP`, id 400). Stessa logica "chiudi sorgente − 1 giorno
> / apri nuovo": riusarla come riferimento implementativo — **inclusi**
> `pg_advisory_xact_lock` ed `EXCEPTION WHEN exclusion_violation` (§3.4).

## 3. Modifiche DB richieste

### 3.1 Nuovi codici errore

Aggiungere a `config.messaggi_errore` (CSV seed
`db/changelog/migrations_v2/80_data/sql/config/messaggi_errore.csv`, colonne
`codice,lingua,messaggio,id,causa,soluzione`; **ultimo id presente = 464**,
prossimi liberi **465/466**):

| Codice                                  | id  | Messaggio (it_IT)                                                                                                                               |
| --------------------------------------- | --- | ----------------------------------------------------------------------------------------------------------------------------------------------- |
| `E_CONTRATTO_OVERLAP_ESISTENTE`         | 465 | "Esiste già un contratto attivo per questo cliente/utility nel periodo indicato (contratto %s). Per procedere chiudere il contratto esistente." |
| `E_CONTRATTO_SUCCESSIONE_DATA_INVALIDA` | 466 | "Successione non possibile: il contratto esistente (%s) inizia dopo la data di decorrenza del nuovo. Verificare le date di validità."           |

> Nomi **neutri rispetto al percorso**: `E_CONTRATTO_OVERLAP_ESISTENTE` (non
> `E_CONTRATTO_PUSH_*`) perché lo solleva il meccanismo generico, non il push.
> `%s` = numero del contratto in conflitto. Compilare anche
> `causa`/`soluzione` come per gli altri codici.

### 3.2 Funzioni generiche di dominio contratti (il cuore del brief)

Due funzioni nello schema `vendite`, indipendenti dall'offerta, che incapsulano
**rilevamento** e **successione**. Vivono nel dominio contratti
(`20_code/vendite/`), non nel file dell'offerta.

#### 3.2.1 Rilevamento — `fn_contratto_sovrapposto`

```sql
vendite.fn_contratto_sovrapposto(
    p_billing_account_id bigint,
    p_istanza_utility_id bigint,
    p_utility_id         integer,
    p_ambito             varchar,
    p_valido_dal         date,
    p_valido_al          date
) RETURNS bigint
```

- Ritorna l'`id` dell'**unico** contratto non abortito la cui finestra si
  sovrappone (`NOT is_abortito_snapshot` AND stessi BA/istanza/utility/ambito
  AND `validita && <finestra candidata>`), oppure `NULL` se nessuno.
- **Costruisce la daterange internamente** con la **stessa formula della
  colonna GENERATED**: `daterange(COALESCE(p_valido_dal,'-infinity'),
  COALESCE(p_valido_al,'infinity'), '[]')`. Così detection e constraint non
  possono divergere quando `valido_al` è NULL (correzione §0/#5 stesura).
- L'EXCLUDE garantisce **al più uno**: la fn può fare `SELECT ... LIMIT 1`.
- Funzione di sola lettura (`STABLE`). Riusabile anche dal BE in pre-check
  read-only per il preview FE (vedi §5) senza tentare l'INSERT.

#### 3.2.2 Successione — `fn_chiudi_contratto_per_successione`

```sql
vendite.fn_chiudi_contratto_per_successione(
    p_contratto_esistente_id bigint,
    p_nuovo_valido_dal       date
) RETURNS date          -- valido_al impostato sul contratto chiuso
```

- Guard data: se `contratto_esistente.valido_dal > (p_nuovo_valido_dal − 1)` la
  chiusura produrrebbe un intervallo invalido (`valido_al < valido_dal`, viola
  `chk_contratti_validita`). In tal caso `RAISE`
  `E_CONTRATTO_SUCCESSIONE_DATA_INVALIDA` via `script.fn_log_and_raise_error`
  (con `numero` del contratto nel detail) — **prima** di lasciar esplodere il
  CHECK. La guard esplicita è **necessaria**: sui contratti non c'è un trigger
  parlante sulle date, solo il CHECK (correzione §0/#4).
- Altrimenti: `UPDATE vendite.contratti SET valido_al = (p_nuovo_valido_dal − 1)
  WHERE id = p_contratto_esistente_id`. Restringe la `validita` generata e
  libera la finestra. Ritorna la nuova `valido_al`.
- **Niente cambio di stato**: la chiusura è un accorciamento di `valido_al`. La
  cessazione di *stato* (ATTIVO→CESSATO) la fa poi il job notturno
  `chiusura_scadenze_daily` (modello data-driven già esistente). **Assunzione
  da verificare** (§8, Step 0): che il job intercetti davvero un ATTIVO con
  `valido_al` passato.

> **Lock post-attivazione — NON è un rischio (correzione §0/#2)**:
> `trg_contratti_a10_lock_post_attivazione_upd` è `BEFORE UPDATE OF` solo dei 4
> campi di pricing (`listino_id`, `listino_versione_id`,
> `tipo_variazione_globale`, `valore_variazione_globale`). **Non** scatta
> sull'UPDATE di `valido_al`. L'accorciamento è quindi già consentito; resta un
> semplice test di regressione (§4), non un punto critico.

> **`validita` GENERATED ALWAYS STORED**: l'UPDATE di `valido_al` aggiorna la
> daterange in modo sincrono nella stessa transazione, quindi l'EXCLUDE è già
> soddisfatto all'INSERT/UPDATE successivo del nuovo contratto. Nessun bisogno
> di toccare `validita` direttamente.

### 3.3 Cambio firma `fn_push_offerta_a_contratto` (DROP + CREATE)

Il push diventa **consumatore** del meccanismo §3.2. Firma attuale
`(p_offerta_id bigint, p_pratica_id bigint)` → aggiunto un terzo parametro:

```sql
vendite.fn_push_offerta_a_contratto(
    p_offerta_id                 bigint,
    p_pratica_id                 bigint,
    p_chiudi_contratto_esistente boolean DEFAULT false
) RETURNS bigint
```

> **ATTENZIONE overload ambiguo** (memoria `feedback_overload_ambiguo_default`):
> NON usare `CREATE OR REPLACE` aggiungendo il 3° parametro con DEFAULT —
> lascerebbe due overload `(bigint,bigint)` e `(bigint,bigint,boolean DEFAULT)`
> e una chiamata a 2 argomenti diventerebbe ambigua. **DROP della versione a 2
> parametri + CREATE della nuova a 3.** Progetto non in produzione (memoria
> `project_no_produzione_solo_sviluppo`): breaking change ammesso. Il BE passerà
> sempre i 3 argomenti.

### 3.4 Logica del push (con gestione concorrenza)

Subito dopo le guard esistenti (stato ACCETTATA + idempotenza `offerta_id`) e
**prima** dell'`INSERT INTO vendite.contratti`:

1. **Advisory lock** sulla quintupla (serializza push concorrenti sullo stesso
   combo; non blocca l'intera tabella; rilascio a fine transazione):

   ```sql
   PERFORM pg_advisory_xact_lock(
       hashtext('vendite.contratti.overlap:'
                || billing_account_id || ':' || istanza_utility_id
                || ':' || utility_id || ':' || ambito)
   );
   ```

2. Determinare la finestra/quintupla che il nuovo contratto assumerà:
   - `valido_dal = v_offerta.validita_dal`, `valido_al = v_offerta.validita_al`.
   - `ambito`: l'INSERT del push **non** valorizza la colonna, quindi il nuovo
     contratto assume il default `'COMMODITY'`. Usare `'COMMODITY'` nel
     rilevamento. *(Invariante da documentare: se un giorno il push valorizzasse
     `ambito`, la detection va allineata.)*
3. `v_overlap_id := vendite.fn_contratto_sovrapposto(BA, istanza, utility,
   'COMMODITY', v_offerta.validita_dal, v_offerta.validita_al)`.
4. Casi:
   - **A — `v_overlap_id IS NULL`**: comportamento odierno (INSERT + copia
     eccezioni/componenti/utility + collegamento pratica). Nessun cambiamento.
   - **B — overlap e `p_chiudi_contratto_esistente = false`**: `RAISE`
     `E_CONTRATTO_OVERLAP_ESISTENTE` (numero del contratto in conflitto come
     `%s`, e id/numero/validità nel detail/context per il FE). **Nessun INSERT.**
   - **C — overlap e `p_chiudi_contratto_esistente = true`**: chiamare
     `vendite.fn_chiudi_contratto_per_successione(v_overlap_id,
     v_offerta.validita_dal)` (guard data + UPDATE), poi procedere con l'INSERT.
5. **Exception backstop** sull'INSERT del nuovo contratto: avvolgerlo in
   `BEGIN ... EXCEPTION WHEN exclusion_violation THEN ...` che ritraduce
   l'errore grezzo GiST in `E_CONTRATTO_OVERLAP_ESISTENTE` parlante. Rete di
   sicurezza se la gara sfugge al lock o un percorso futuro inserisce senza
   lock.

> Tutta la logica di "quale finestra, c'è overlap?, chiudi" sta nelle funzioni
> §3.2. Il push aggiunge solo il **routing** (param `p_chiudi` → caso B o C), la
> traduzione offerta→parametri, il **lock** e il **backstop**. Un futuro
> `ContrattiService.crea_contratto` che voglia la successione invocherà le
> stesse due funzioni con lo stesso schema lock+routing+backstop.

## 4. Test pgTAP richiesti

**Sul meccanismo generico** (nuovo file
`db/pgtap/vendite/contratti/test_fn_successione_contratti.sql`):

- `fn_contratto_sovrapposto` con overlap reale → ritorna l'id corretto.
- `fn_contratto_sovrapposto` senza overlap → `NULL`.
- `fn_contratto_sovrapposto` ignora contratti abortiti (`is_abortito_snapshot`)
  → `NULL` anche se le date coincidono.
- `fn_contratto_sovrapposto` con `valido_al` NULL (contratto perpetuo) →
  overlap rilevato correttamente (verifica COALESCE→infinity §3.2.1).
- `fn_chiudi_contratto_per_successione` con date valide → `valido_al` del vecchio
  = `p_nuovo_valido_dal − 1`, daterange ristretta.
- `fn_chiudi_contratto_per_successione` con `valido_dal` vecchio >
  `p_nuovo_valido_dal − 1` → `E_CONTRATTO_SUCCESSIONE_DATA_INVALIDA`, nessuna
  modifica.
- **Regressione** `fn_chiudi_contratto_per_successione` su contratto **ATTIVO** →
  l'accorciamento di `valido_al` passa (conferma che il lock post-attivazione
  non interferisce — §0/#2).

**Sul push** (estendere
`db/pgtap/vendite/offerte_commerciali/test_fn_push_offerta_a_contratto.sql` o
file dedicato `test_fn_push_offerta_successione.sql`):

- push con overlap e `p_chiudi=false` → `E_CONTRATTO_OVERLAP_ESISTENTE`,
  nessun contratto creato, vecchio invariato.
- push con overlap e `p_chiudi=true` → vecchio chiuso a `validita_dal − 1`,
  nuovo contratto DRAFT creato, EXCLUDE rispettato.
- push senza overlap → comportamento odierno invariato (regressione: i test
  push esistenti restano verdi con la firma a 3 argomenti).
- **Backstop**: simulare il path che porta all'`exclusion_violation` e
  verificare che venga ritradotto in `E_CONTRATTO_OVERLAP_ESISTENTE` e non
  trapeli l'errore grezzo (§3.4 punto 5).

## 5. Lavoro a valle (BE + FE) — ✅ COMPLETATO 2026-05-31

Cablato dopo la consegna DB. 53/53 test service verdi, vite build verde,
eslint pulito.

**Backend** (`apps/vendite`) — ✅ fatto:

- [x] `OfferteRepository.push_a_contratto(offerta_id, pratica_id, chiudi_esistente=False)`
  → passa il 3° argomento alla fn.
- [x] `OfferteRepository.get_contratto_sovrapposto(offerta_id)` — pre-check
  overlap read-only via `fn_contratto_sovrapposto` (id+numero+validità del
  contratto in conflitto) per il preview FE, senza tentare l'INSERT.
  **Nota di scope**: collocato in `OfferteRepository` (non in
  `ContrattiRepository`) perché oggi l'unico consumer è l'offerta; quando la
  creazione manuale contratto adotterà la successione (§6) il wrapper va
  promosso a `ContrattiRepository` o helper condiviso.
- [x] `OfferteService.push_a_contratto(..., chiudi_esistente=False)` +
  `get_contratto_sovrapposto(offerta_id)`. Il `_db_errors` esistente estrae i
  codici `E_*` dal MESSAGE → `E_CONTRATTO_OVERLAP_ESISTENTE` propagato parlante.
- [x] View `ApiOffertaPushContratto` accetta `chiudi_esistente`; nuova view
  `ApiOffertaContrattoSovrapposto` (`GET /<id>/contratto-sovrapposto/`).
- [x] Test: 4 nuovi casi (flag inoltrato, codice overlap propagato, preview
  404 + ok).

**Frontend** (`vendite/offerte`) — ✅ fatto:

- [x] `OffertaPushDialog.vue`: pulsante = **conferma standard** (`common.confirm`).
- [x] **Nuovo `OffertaSuccessioneDialog.vue`**: mostra il contratto in conflitto
  (numero, validità, link al `ContrattoDrawer`) + data di chiusura calcolata
  (`decorrenza − 1`), conferma esplicita.
- [x] `OffertaDrawer.runPush()`: routing a due passi sui codici parlanti —
  `E_OFFERTA_CONTRATTO_GIA_GENERATO` → dialog idempotenza,
  `E_CONTRATTO_OVERLAP_ESISTENTE` → carica il contratto sovrapposto e apre il
  dialog di successione; su conferma re-invoca il push con
  `chiudi_esistente=true` riusando la pratica scelta.
- [x] API client (`pushOffertaAContratto` + `getContrattoSovrapposto`), store
  (`pushAContratto({chiudiEsistente})` + `loadContrattoSovrapposto`), i18n
  it/en (chiavi `successione_*`).

> Poiché il meccanismo DB è generico, il dialog di successione FE è un buon
> candidato a **building block riusabile** (memoria
> `feedback_regola_del_2_estrai_bb`) quando la creazione manuale contratto
> adotterà lo stesso flusso. Per ora implementato nel solo push (1ª
> occorrenza); alla seconda si estrae. Da dichiarare a Tid prima di astrarre.

## 6. Percorsi non ancora coperti (debito tracciato)

Il meccanismo §3.2 è generico, ma in questo brief **solo il push** lo invoca.
Restano da agganciare, in brief successivi:

- **Creazione manuale contratto** (`ContrattiService` / INSERT diretto): oggi
  fallisce con l'errore GiST grezzo come faceva il push. Quando lo si tocca,
  adotta `fn_contratto_sovrapposto` + `fn_chiudi_contratto_per_successione` con
  lo stesso schema lock+routing+backstop.
- **Futuri push da altre sorgenti** verso contratto: stesso aggancio.

Questi non sono nello scope ora (decisione Tid: risolvere il caso push), ma il
meccanismo è progettato perché aggiungerli sia un semplice aggancio, non una
riscrittura.

## 7. Note operative team DB

- Workflow autorizzativo: applicare solo su conferma esplicita di Tid, branch
  `dev/db-tid` (memoria `feedback_db_actions_passaggio_team`).
- Naming Liquibase / trigger / audit come da `AGENTS.md` e linee-guida.
  Numerazione `YYYYMMDD-NN`: sequenza **globale per data** tra tutte le cartelle.
- Collocazione: `fn_contratto_sovrapposto` +
  `fn_chiudi_contratto_per_successione` in `20_code/vendite/` (dominio
  contratti); modifica push nel file della fn offerta. Documentare in
  `docs/it/dbzero/vendite/funzioni/` le due nuove fn e aggiornare il manuale
  `fn_push_offerta_a_contratto.md` (nuovo parametro + i due nuovi codici errore).
- Già confermato (non aperto): generazione `validita` GENERATED da
  `valido_dal`/`valido_al`, default `ambito='COMMODITY'`, `valido_al` inclusivo
  con cessazione via job.

---

## 8. Piano esecutivo (checklist)

> Spuntare man mano. Ordine consigliato: Step 0 (verifiche) → 1 → 2 → 3 → 4 → 5.
> Nessuna migration parte senza "procedi" esplicito di Tid.

### Step 0 — Pre-verifiche ✅ (completato 2026-05-31)

- [x] Job `chiusura_scadenze_daily` cessa un contratto ATTIVO con `valido_al`
      passato — confermato da Tid.
- [x] Nessun doppione id in `messaggi_errore.csv` — mappatura 460→464 pulita.

### Step 1 — Codici errore (seed CSV `80_data`) ✅ (2026-05-31)

- [x] `E_CONTRATTO_OVERLAP_ESISTENTE` (id **465**) — riga aggiunta a
      `80_data/sql/config/messaggi_errore.csv` con `messaggio`/`causa`/`soluzione`.
- [x] `E_CONTRATTO_SUCCESSIONE_DATA_INVALIDA` (id **466**) — idem.
- [x] Changelog upsert: `80_data/changelog/20260531-01-upsert-messaggi-errore-contratti-successione-mctit.yaml`
      (`loadUpdateData`, primaryKey `id`).

### Step 2 — Funzioni di dominio (`20_code/vendite/`) ✅ (2026-05-31)

- [x] `fn_contratto_sovrapposto(...)` `STABLE`: daterange con COALESCE→±infinity
      bound `'[]'` (identica alla GENERATED), `SELECT ... LIMIT 1`, ritorna id o
      NULL. File `20260531-02-create-fn-contratto-sovrapposto-mctit.yaml`.
      Nota: primi due parametri dichiarati `bigint` (non `%TYPE`=integer di
      contratti) per accettare via widening sia i chiamanti contratti (integer)
      sia offerte_commerciali (bigint).
- [x] `fn_chiudi_contratto_per_successione(...)`: guard data esplicita →
      `E_CONTRATTO_SUCCESSIONE_DATA_INVALIDA`; UPDATE `valido_al = nuovo_dal-1`;
      nessun cambio stato; ritorna la nuova `valido_al`. File
      `20260531-03-create-fn-chiudi-contratto-per-successione-mctit.yaml`.
- [x] Doc funzioni: pagine `funzioni/fn_contratto_sovrapposto.md` e
      `funzioni/fn_chiudi_contratto_per_successione.md` **auto-generate dal DB**
      (gen_db_docs.py, 2026-05-31) + **manuali narrativi** scritti a mano in
      `manual/fn_contratto_sovrapposto.md` e
      `manual/fn_chiudi_contratto_per_successione.md`. NB: le pagine `funzioni/`
      sono state generate prima dei manuali → una rigenerazione le aggancia
      (l'include scatta quando esiste il `manual/<nome>.md`).

### Step 3 — Push `fn_push_offerta_a_contratto` (DROP + CREATE a 3 parametri) ✅ (2026-05-31)

File `20260531-04-update-fn-push-offerta-a-contratto-successione-mctit.yaml`.

- [x] DROP della versione a 2 parametri + CREATE a 3 (no `CREATE OR REPLACE`).
- [x] `pg_advisory_xact_lock` sulla quintupla, dopo le guard, prima della
      detection.
- [x] Routing casi A / B / C (§3.4).
- [x] `EXCEPTION WHEN exclusion_violation` sull'INSERT in contratti → ritraduce
      in `E_CONTRATTO_OVERLAP_ESISTENTE` (backstop, con re-detection del numero).
- [x] Manuale narrativo `dbzero/vendite/manual/fn_push_offerta_a_contratto.md`
      aggiornato (rev4): 3° parametro, sezione "Successione su overlap"
      (lock/routing/backstop), nuovo codice `E_CONTRATTO_OVERLAP_ESISTENTE`,
      esempi e diagramma trigger. La pagina `funzioni/` auto-gen riflette la
      nuova firma a 3 parametri.

### Step 4 — Test pgTAP ✅ (2026-05-31)

- [x] `db/pgtap/vendite/contratti/test_fn_successione_contratti.sql` (12 test):
      detection (overlap / no / abortito / valido_al NULL), successione (date
      valide / data invalida) + regressione su ATTIVO.
- [x] `db/pgtap/vendite/offerte_commerciali/test_fn_push_offerta_successione.sql`
      (6 test): overlap+false → throws; nessun contratto creato; overlap+true →
      vecchio accorciato + nuovo DRAFT; no-overlap con chiamata a 2 argomenti.
- [x] Regressione firma a 3 argomenti: il test push esistente
      (`test_fn_push_offerta_a_contratto.sql`) invoca a 2 argomenti, coperto dal
      default `p_chiudi_contratto_esistente`.

### Step 5 — Chiusura DB

- [x] Liquibase: numerazione globale per data (`20260531-01..04`),
      `logicalFilePath`, un changeSet per file; collocazione corretta
      (`20_code/vendite/`, seed in `80_data`). YAML/CSV validati.
- [x] Autogen changelog: **non rigenerato a mano** — la CI esegue
      `gen_master_autogen.py` (i file `20_code` vengono inclusi; `80_data` via
      `includeAll`).
- [x] Liquibase `update` applicato su `dev/db-tid` (fix precondition cross-fase
      del file 03: rimossa la `changeSetExecuted` verso il seed `80_data`).
- [x] pgTAP verdi (18 test: 12 successione + 6 push).
- [x] Rigenerare le pagine `funzioni/` delle 2 nuove fn per agganciare i manuali
      narrativi (gen_db_docs.py): `fn_contratto_sovrapposto.md` +
      `fn_chiudi_contratto_per_successione.md` presenti in `funzioni/` e `manual/`.

### Step 6 — BE + FE + documentazione applicativa ✅ (2026-05-31)

- [x] BE: repository + service + view + route (§5). 53/53 test service verdi.
- [x] FE: `OffertaSuccessioneDialog` + routing `runPush` + API/store/i18n (§5).
      Vite build verde, eslint pulito.
- [x] Doc API: `docs/it/backend/vendite/manual/api_offerte.md` (endpoint push a
      3 param + `contratto-sovrapposto/` + 2 codici errore + dipendenze DB) e
      `docs/it/dev/backend/catalogo-building-block-backend.md` (sezione
      "Successione contratti su overlap" con le 4 voci BB).
- [X] Commit + push (in attesa di OK Tid).
