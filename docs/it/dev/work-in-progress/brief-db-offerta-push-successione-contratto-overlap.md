# Brief DB — Successione contratti: meccanismo generico su overlap

> **Stato**: APERTO — in attesa di applicazione team DB su `dev/db-tid`.
> Nessuna migration parte senza conferma esplicita di Tid.
>
> **Owner concettuale**: Tid (Michele Carlo Titini)
>
> **Tipo**: nuovo meccanismo di **dominio contratti** (successione su
> sovrapposizione temporale), riusabile da ogni percorso di creazione
> contratto. Il push offerta→contratto è il **primo consumatore**, non il
> proprietario della logica.
>
> **Revisione 2026-05-30b**: riscritto attorno al meccanismo generico
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
  riusabili (§3.2) che il push invoca (§3.3). I futuri percorsi di creazione
  contratto adotteranno le stesse funzioni.

> **Precedente identico già a modello** (memoria
> `feedback_simmetria_modello_no_meta_scope`):
> `vendite.fn_duplica_componente_versione` gestisce esattamente questo schema
> sul BoM — l'EXCLUDE `ex_articoli_componenti_no_overlap` impedisce
> sovrapposizioni temporali e la fn "apre la nuova versione al giorno
> successivo alla chiusura della sorgente" (codice errore
> `E_BOM_VERSIONE_OVERLAP`, id 400). Stessa logica "chiudi sorgente − 1 giorno
> / apri nuovo": riusarla come riferimento implementativo.

## 3. Modifiche DB richieste

### 3.1 Nuovi codici errore

Aggiungere a `config.messaggi_errore` (CSV seed
`db/changelog/migrations_v2/80_data/sql/config/messaggi_errore.csv`, colonne
`codice,lingua,messaggio,id,causa,soluzione`; ultimo id offerta = 462, prossimi
liberi 463/464):

| Codice                                  | id  | Messaggio (it_IT)                                                                                                                               |
| --------------------------------------- | --- | ----------------------------------------------------------------------------------------------------------------------------------------------- |
| `E_CONTRATTO_OVERLAP_ESISTENTE`         | 463 | "Esiste già un contratto attivo per questo cliente/utility nel periodo indicato (contratto %s). Per procedere chiudere il contratto esistente." |
| `E_CONTRATTO_SUCCESSIONE_DATA_INVALIDA` | 464 | "Successione non possibile: il contratto esistente (%s) inizia dopo la data di decorrenza del nuovo. Verificare le date di validità."           |

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
    p_validita           daterange
) RETURNS bigint
```

- Ritorna l'`id` dell'**unico** contratto non abortito la cui finestra si
  sovrappone alla quintupla data (`NOT is_abortito_snapshot` AND stessi
  BA/istanza/utility/ambito AND `validita && p_validita`), oppure `NULL` se
  nessuno.
- L'EXCLUDE garantisce **al più uno**: la fn può fare `SELECT ... LIMIT 1`.
- Funzione di sola lettura (`STABLE`). Riusabile anche dal BE in pre-check
  read-only per il preview FE (vedi §5) senza tentare l'INSERT.

#### 3.2.2 Successione — `fn_cedi_contratto_per_successione`

```sql
vendite.fn_cedi_contratto_per_successione(
    p_contratto_esistente_id bigint,
    p_nuovo_valido_dal       date
) RETURNS date          -- valido_al impostato sul contratto chiuso
```

- Guard data: se `contratto_esistente.valido_dal > (p_nuovo_valido_dal − 1)` la
  chiusura produrrebbe un intervallo invalido (`valido_al < valido_dal`, viola
  `chk_contratti_validita`). In tal caso `RAISE`
  `E_CONTRATTO_SUCCESSIONE_DATA_INVALIDA` via `script.fn_log_and_raise_error`
  (con `numero` del contratto nel detail) — **prima** di lasciar esplodere il
  CHECK.
- Altrimenti: `UPDATE vendite.contratti SET valido_al = (p_nuovo_valido_dal − 1)
  WHERE id = p_contratto_esistente_id`. Restringe la `validita` generata e
  libera la finestra. Ritorna la nuova `valido_al`.
- **Niente cambio di stato**: la chiusura è un accorciamento di `valido_al`. La
  cessazione di *stato* (ATTIVO→CESSATO) la fa poi il job notturno
  `chiusura_scadenze_daily` (modello data-driven già esistente, manuale
  contratti §"Workflow stato e cessazione automatica").

> **Lock post-attivazione**: un contratto ATTIVO è guardato da
> `trg_contratti_a10_lock_post_attivazione_upd`
> (`trgfn_contratti_lock_post_attivazione`), ma il manuale dichiara che
> accorciare `valido_al` è il path utente consentito. Verificare che l'UPDATE
> dentro la fn rispetti quel guard; se il guard distingue PATCH applicativo da
> UPDATE in funzione, allinearlo. Questo è il punto di rischio principale del
> brief: va testato (§4).

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

**Logica del push** — subito dopo le guard esistenti (stato ACCETTATA +
idempotenza `offerta_id`) e **prima** dell'`INSERT INTO vendite.contratti`:

1. Determinare la finestra/quintupla che il nuovo contratto assumerà:
   - `valido_dal = v_offerta.validita_dal`, `valido_al = v_offerta.validita_al`,
     quindi `p_validita = daterange(valido_dal, valido_al, '[]')` coerente con
     la generazione di `contratti.validita`.
   - `ambito`: l'INSERT del push **non** valorizza la colonna, quindi il nuovo
     contratto assume il default `'COMMODITY'` (confermato: `ambito varchar
     DEFAULT 'COMMODITY'`). Usare `'COMMODITY'` nel rilevamento.
2. `v_overlap_id := vendite.fn_contratto_sovrapposto(BA, istanza, utility,
   'COMMODITY', p_validita)`.
3. Casi:
   - **A — `v_overlap_id IS NULL`**: comportamento odierno (INSERT + copia
     eccezioni/componenti/utility + collegamento pratica). Nessun cambiamento.
   - **B — overlap e `p_chiudi_contratto_esistente = false`**: `RAISE`
     `E_CONTRATTO_OVERLAP_ESISTENTE` (numero del contratto in conflitto come
     `%s`, e id/numero/validità nel detail/context per il FE). **Nessun INSERT.**
   - **C — overlap e `p_chiudi_contratto_esistente = true`**: chiamare
     `vendite.fn_cedi_contratto_per_successione(v_overlap_id,
     v_offerta.validita_dal)` (che applica la guard data + l'UPDATE), poi
     procedere con l'INSERT del nuovo contratto come oggi.

> Tutta la logica di "quale finestra, c'è overlap?, chiudi" sta nelle funzioni
> §3.2. Il push aggiunge solo il **routing** (param `p_chiudi` → caso B o C) e
> la traduzione offerta→parametri. Un futuro `ContrattiService.crea_contratto`
> che voglia la successione invocherà le stesse due funzioni con lo stesso
> routing.

## 4. Test pgTAP richiesti

**Sul meccanismo generico** (nuovo file
`db/pgtap/vendite/contratti/test_fn_successione_contratti.sql`):

- `fn_contratto_sovrapposto` con overlap reale → ritorna l'id corretto.
- `fn_contratto_sovrapposto` senza overlap → `NULL`.
- `fn_contratto_sovrapposto` ignora contratti abortiti (`is_abortito_snapshot`)
  → `NULL` anche se le date coincidono.
- `fn_cedi_contratto_per_successione` con date valide → `valido_al` del vecchio
  = `p_nuovo_valido_dal − 1`, daterange ristretta.
- `fn_cedi_contratto_per_successione` con `valido_dal` vecchio >
  `p_nuovo_valido_dal − 1` → `E_CONTRATTO_SUCCESSIONE_DATA_INVALIDA`, nessuna
  modifica.
- `fn_cedi_contratto_per_successione` su contratto **ATTIVO** → l'accorciamento
  passa il guard `lock_post_attivazione` (test del punto di rischio §3.2.2).

**Sul push** (estendere
`db/pgtap/vendite/offerte_commerciali/test_fn_push_offerta_a_contratto.sql` o
file dedicato `test_fn_push_offerta_successione.sql`):

- push con overlap e `p_chiudi=false` → `E_CONTRATTO_OVERLAP_ESISTENTE`,
  nessun contratto creato, vecchio invariato.
- push con overlap e `p_chiudi=true` → vecchio chiuso a `validita_dal − 1`,
  nuovo contratto DRAFT creato, EXCLUDE rispettato.
- push senza overlap → comportamento odierno invariato (regressione: i test
  push esistenti restano verdi con la firma a 3 argomenti).

## 5. Lavoro a valle (BE + FE) — fuori da questo brief, da fare a DB pronto

Annotato per completezza; **non** si implementa finché il DB non chiude.

**Backend** (`apps/vendite`):

- `OfferteRepository.push_a_contratto(offerta_id, pratica_id, chiudi_esistente=False)`
  → passa il 3° argomento alla fn.
- Pre-check overlap per il preview FE: esporre `fn_contratto_sovrapposto` (read
  only) via un metodo repo riusabile — collocarlo in
  `ContrattiRepository`/helper condiviso (è dominio contratti, non offerta),
  così anche la futura creazione manuale lo riusa. Ritorna id+numero+validità
  del contratto in conflitto.
- `OfferteService.push_a_contratto(..., chiudi_esistente=False)`: il
  `_db_errors` esistente già estrae i codici `E_*` dal MESSAGE; mappare
  `E_CONTRATTO_OVERLAP_ESISTENTE` propagando nel detail i dati del contratto in
  conflitto.

**Frontend** (`vendite/offerte`):

- `OffertaPushDialog.vue`: il pulsante azione diventa il **bottone standard di
  conferma** (richiesta esplicita Tid — oggi è l'azione `@save` di `AppDialog`
  con label `vendite.offerte.push_conferma`; allineare alla conferma standard).
- Flusso a due passi: sul codice `E_CONTRATTO_OVERLAP_ESISTENTE` mostrare il
  contratto esistente (numero, validità, link al `ContrattoDrawer`) e chiedere
  conferma "chiudi il contratto esistente (valido fino al GG-MM-AAAA) e genera
  il nuovo?" → su conferma, re-invocare il push con `chiudi_esistente: true`.
- API client + store: aggiungere il parametro `chiudiEsistente` a
  `pushContratto`.

> Poiché il meccanismo DB è generico, il dialog di successione FE è un buon
> candidato a **building block riusabile** (memoria
> `feedback_regola_del_2_estrai_bb`) quando la creazione manuale contratto
> adotterà lo stesso flusso. Per ora si implementa nel solo push; alla seconda
> occorrenza si estrae. Da dichiarare a Tid prima di astrarre.

## 6. Percorsi non ancora coperti (debito tracciato)

Il meccanismo §3.2 è generico, ma in questo brief **solo il push** lo invoca.
Restano da agganciare, in brief successivi:

- **Creazione manuale contratto** (`ContrattiService` / INSERT diretto): oggi
  fallisce con l'errore GiST grezzo come faceva il push. Quando lo si tocca,
  adotta `fn_contratto_sovrapposto` + `fn_cedi_contratto_per_successione` con lo
  stesso routing `chiudi_esistente`.
- **Futuri push da altre sorgenti** verso contratto: stesso aggancio.

Questi non sono nello scope ora (decisione Tid: risolvere il caso push), ma il
meccanismo è progettato perché aggiungerli sia un semplice aggancio, non una
riscrittura.

## 7. Note operative team DB

- Workflow autorizzativo: applicare solo su conferma esplicita di Tid, branch
  `dev/db-tid` (memoria `feedback_db_actions_passaggio_team`).
- Naming Liquibase / trigger / audit come da `AGENTS.md` e linee-guida.
- Collocazione: `fn_contratto_sovrapposto` + `fn_cedi_contratto_per_successione`
  in `20_code/vendite/` (dominio contratti); modifica push nel file della fn
  offerta. Documentare in `docs/it/dbzero/vendite/funzioni/` le due nuove fn e
  aggiornare il manuale `fn_push_offerta_a_contratto.md` (nuovo parametro + i
  due nuovi codici errore).
- Punto di rischio da verificare e testare (§4): interazione dell'UPDATE di
  `valido_al` dentro `fn_cedi_contratto_per_successione` con
  `trg_contratti_a10_lock_post_attivazione_upd` su contratto ATTIVO.
- Già confermato (non aperto): generazione `validita` GENERATED da
  `valido_dal`/`valido_al`, default `ambito='COMMODITY'`, `valido_al` inclusivo
  con cessazione via job.
