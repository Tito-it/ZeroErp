# Brief DB — L'ereditato dei permessi coincide col resolver (pgTAP) · e la veste che non si filtra

> **Chi scrive:** backend (`dev/backend-tid`), 2026-09-25. **A chi:** Tid
> (decisioni, §4), poi team DB (`dev/db-tid`) e backend per la ricaduta.
> **Origine:** [piano-be-fe-ui-permessi-operatore.md](piano-be-fe-ui-permessi-operatore.md),
> stato in testa: *«la versione durevole è un pgTAP, ed è da chiedere al team
> DB»*. Analisi madre:
> [analisi-ui-permessi-operatore.md](analisi-ui-permessi-operatore.md) §7.7.
> **Stato:** ✅ **D-1 e D-2 decise da Tid il 2026-09-25** (§4): come proposto.
> ✅ **D-3 decisa da Tid lo stesso giorno** (§3-bis): il reparto vince sul
> profilo di veste.
> ✅ **DB scritto il 2026-09-25** (§7): sette changeSet `20260925-80` → `-86`
> e il pgTAP `test-fn-get-permessi-ereditati-v1.sql` (27 test), provati in
> transazione annullata sullo scratch. ✅ **Applicati** (i sette changeSet
> sono in `databasechangelog`).
> ✅ **Ricaduta BE fatta il 2026-09-25** (§5): repository e resolver leggono
> le due funzioni del §7.1, nessuna copia dello spareggio resta nel backend.
> FE invariato (contratto JSON identico).
> 📁 **Spostato in `work-done/` il 2026-09-25**, su richiesta di Tid, a lavoro
> DB e BE chiuso. Il collaudo a video ha un copione suo, in
> `work-in-progress/`:
> [collaudo-in-app-permessi-ereditati-veste-operatore.md](collaudo-in-app-permessi-ereditati-veste-operatore.md).
> **Da leggere per primo:** §7 (consegna DB), poi §5.1 (consegna BE).
>
> **In una riga:** il pannello permessi mostra per ogni area e azione il valore
> **ereditato** dal profilo, con una query del backend che ripete lo spareggio
> dei resolver. Serve un presidio a DB che provi che le due letture coincidono.
> ⚠️ Mentre scrivevo il brief è emerso un **difetto di modello**: i resolver da
> operatore contano anche i profili delle **altre vesti** dell'utente (§3).

---

## 1. Cosa c'è oggi

`GET /amm-software/operatori/<id>/permessi-ereditati/` →
`AmmSoftwareRepository.get_permessi_ereditati`
([amm_software_repository.py:982](../../../backend/apps/amm_software/db/amm_software_repository.py#L982)):

```sql
SELECT DISTINCT ON (paa.area_id) paa.area_id, paa.livello, pa.descrizione, pa.tipo
  FROM script.fn_get_profili_accesso_applicabili(%s) h
  JOIN config.profili_accesso_aree paa ON paa.profilo_accesso_id = h.profilo_accesso_id
  ...
 ORDER BY paa.area_id, h.priorita
```

(e la gemella su `config.profili_accesso_azioni`).

La **fonte** dei profili è la stessa dei resolver
(`fn_get_profili_accesso_applicabili`). Ma lo **spareggio** (`DISTINCT ON … ORDER
BY priorita`) è una seconda scrittura del passo 4 di `fn_resolve_livello_area` e
di `fn_check_azione_processo` (`ORDER BY h.priorita LIMIT 1`, per area/azione).

Oggi lo presidia solo un test Django che legge l'**SQL generato** e controlla
che usi la funzione e ordini per `h.priorita`. Il confronto col resolver è stato
fatto **a mano** il 2026-09-05. In questo repo nessun test Django tocca un DB
reale, quindi il confronto vero può stare solo in pgTAP.

---

## 2. La richiesta: portare l'ereditato a DB e provarlo contro i resolver

> ⚠️ **Consegnato in una forma diversa** (§7): due funzioni invece di una
> con `tipo_voce`, e i resolver le **chiamano** invece di esserne
> confrontati. Il §2 resta com'era come richiesta.

Un pgTAP non può leggere una query che vive in un file Python. Se la si copiasse
nel test, le copie diventerebbero **tre**. La forma che toglie la copia invece
di presidiarla (*si sposta la sede, non si copia*):

1. **Funzione nuova** `script.fn_get_permessi_ereditati(p_auth_user_id integer)`
   (nome a scelta del team DB). Restituisce le righe di aree e azioni con
   `tipo_voce` (`AREA` | `AZIONE`), `voce_id`, `livello` (aree), `abilitata`
   (azioni), `profilo_id`, `profilo_nome`, `profilo_tipo`. Lo spareggio lo
   scrive **una volta**, con lo stesso criterio del passo 4 dei resolver.
2. **pgTAP** `db/pgtap/script/test-fn-get-permessi-ereditati.sql`, casi al §2.1.
3. **Ricaduta BE** (la facciamo noi): `get_permessi_ereditati` chiama la
   funzione e perde le due query. Il contratto JSON dell'endpoint non cambia.

### 2.1 I casi del pgTAP

L'uguaglianza vale **per costruzione** solo dove il resolver arriva al passo 4:
utente con identità `OPERATORE` attiva, non super admin, senza override su
quella voce. I casi:

| # | Fixture | Atteso |
| --- | --- | --- |
| 1 | Operatore con solo un profilo `REPARTO` | Per **ogni** area del catalogo: `fn_resolve_livello_area` = livello ereditato, oppure `BLOCCATO` dove l'ereditato manca |
| 2 | Idem per le azioni | `fn_check_azione_processo` = `abilitata` ereditata, oppure negata dove manca |
| 3 | Operatore con `AD_HOC` **e** `REPARTO` sulla stessa area, livelli diversi | Vince l'`AD_HOC` in **entrambe** le letture, e `profilo_tipo = 'AD_HOC'` |
| 4 | Area coperta da un profilo di priorità più bassa e non da quello più alta | Entrambe le letture scendono al profilo più basso, perché lo spareggio è **per voce** e non per utente |
| 5 | Operatore **multi-veste**: `OPERATORE` + `SHOP_CUSTOMER`, con un profilo `PORTALE` e uno `REPARTO` sulla stessa area, livelli diversi (vedi §3) | Per D-1: in **entrambe** le letture conta **solo** il profilo `REPARTO`; il profilo della veste cliente non compare nell'ereditato. Oggi è il caso che fallisce |
| 6 | Utente senza profili | Ereditato vuoto; resolver `BLOCCATO` / negata ovunque |

⚠️ Il caso 1 va fatto **su tutto il catalogo** (`config.aree_funzionali` e
`config.azioni_processo` attivi), non su due voci scelte: il presidio deve
accorgersi di un'area nuova (dal 05-09 sono arrivate `ai_assistant` e un'azione
di `magazzino`).

---

## 3. 🔴 Trovato strada facendo: i profili delle altre vesti entrano nei permessi da operatore

I quattro resolver da operatore — `fn_resolve_livello_area`,
`fn_check_azione_processo`, `fn_get_user_permissions_map`,
`fn_get_user_actions_map` — chiamano

```sql
script.fn_get_profili_accesso_applicabili(p_auth_user_id)   -- ruolo = DEFAULT NULL
```

cioè **senza filtro di veste**. Il passo 0 della catena verifica che il
contesto sia `OPERATORE`, ma poi i profili si raccolgono da **tutte** le
identità dell'utente. Un operatore che ha anche un'identità da cliente
shop o portale si porta nei permessi da operatore il profilo `PORTALE` di
quell'altra veste.

E `PORTALE` e `REPARTO` hanno la **stessa priorità (2)**. Sulla stessa area lo
spareggio `ORDER BY h.priorita LIMIT 1` sceglie **a caso** fra i due.

> 📌 *Fatto datato (2026-09-25, dev), non motivo:* l'utente `auth_user_id = 6`
> ha le vesti `OPERATORE` e `SHOP_CUSTOMER`. Nel contesto operatore gli
> arrivano *«Profilo reparto Marketing»* (`REPARTO`, `TUTTO`) **e** *«Profilo
> standard cliente shop»* (`PORTALE`, `LETTURA`), **entrambi su `vendite` e
> `pagamenti`**, a priorità 2. Su `vendite` oggi lo copre un override. Su
> `pagamenti` `fn_resolve_livello_area(6, 'pagamenti')` dà **`LETTURA`**: vince
> il profilo da **cliente shop**, e il reparto che dà `TUTTO` perde. Quale dei
> due vinca non è determinato: lo decide il piano di esecuzione. Con
> `fn_get_profili_accesso_applicabili(6, 'OPERATORE')` resta il solo profilo di
> reparto.

⛔ Non è un'ambiguità dei dati di dev: è la catena che non filtra la veste. Il
`DEFAULT NULL` è una scelta **dichiarata** del 2026-04-20
([sviluppo-multi-face-auth.md](sviluppo-multi-face-auth.md),
«semantica legacy, nessun filtro veste»). Era pensata per i due chiamanti BE di
allora, non per i resolver. Il gate di `fn_is_super_admin` invece è stato reso
*operatore-only* proprio per evitare lo stesso sconfinamento su un utente
multi-veste: la simmetria manca solo qui.

---

## 3-bis. 🔴 Trovato dal team DB: la parità resta anche sotto la sola veste OPERATORE

D-1 toglie la parità fra **vesti diverse**. Sotto la sola veste `OPERATORE`
il modello ne ammette però ancora una. Il guard di coerenza dei binding
accetta un profilo `PORTALE` legato alla veste `OPERATORE` (un profilo base
per tutti gli operatori), e il `REPARTO` arriva dall'unità organizzativa.
Erano tutti e due a priorità 2, quindi `LIMIT 1` sceglieva a caso.

Gli indici unici dicono che è **l'unica** parità possibile sotto una veste:
un binding per identità, uno per veste, uno per UO, una UO per risorsa
umana, una identità attiva per veste. Lo stesso spareggio casuale c'era nei
preset di liste e dashboard (`ORDER BY priorita LIMIT 1`).

✅ **D-3 (Tid, 2026-09-25): vince il reparto.** L'helper dà AD_HOC 1,
REPARTO 2, PORTALE 3. È la regola della guida dei permessi, §3: il più
specifico vince, e l'unità organizzativa è più specifica della veste. Le
altre due strade scartate: «a parità il più restrittivo» (come
`ui.fn_lista_colonne_livello`) avrebbe fatto del profilo di veste un tetto
sul reparto, e lasciato indeterminati i preset; «vietare PORTALE sulla veste
OPERATORE» avrebbe tolto il profilo base per tutti gli operatori.

📌 *Fatto datato, non motivo (prova del 2026-09-25):* con la priorità vecchia
il test 22 del pgTAP (reparto contro PORTALE di veste) è uscito **verde per
caso**, perché il piano ha pescato il reparto. Lo spareggio casuale non si
vede da un esito: lo prende il test 25, che asserisce le priorità.

---

## 4. Decisioni per Tid

| | Domanda | Proposta |
| --- | --- | --- |
| **D-1** | I resolver da operatore devono contare **solo** i profili della veste `OPERATORE`? | ✅ **DECISA (Tid, 2026-09-25): sì, come proposto.** I quattro resolver passano `'OPERATORE'` a `fn_get_profili_accesso_applicabili`, e così la funzione del §2. È un **cambio di semantica** (un operatore multi-veste perde i livelli del profilo cliente), quindi è una decisione tua e non del team |
| **D-2** | L'ereditato si sposta a DB (funzione del §2), o resta nel BE col solo pgTAP che copia la query? | ✅ **DECISA (Tid, 2026-09-25): a DB, come proposto.** Il pgTAP prova la funzione vera e il BE perde la sua copia dello spareggio. Con la query nel test le copie diventano tre |
| **D-3** | Sotto la veste OPERATORE, PORTALE di veste e REPARTO sono a pari priorità: chi vince? (§3-bis) | ✅ **DECISA (Tid, 2026-09-25): il reparto.** PORTALE passa a priorità 3 nell'helper; vale per tutti i chiamanti |

⚠️ **D-1 e il pgTAP vanno insieme.** Se si corregge il resolver e non
l'ereditato (o viceversa), il pannello mostra un valore diverso da quello
applicato, cioè proprio il difetto che il presidio deve vedere. Per questo il
caso 5 del §2.1 fissa il comportamento deciso con D-1.

---

## 5. Ricaduta BE (la facciamo noi, dopo il DB)

> ✅ **Fatta il 2026-09-25**, dopo l'apply di `-80` → `-86`.

- ✅ `AmmSoftwareRepository.get_permessi_ereditati` → chiamata alle due
  funzioni del §7.1, col solo `JOIN` di catalogo per le etichette; le due
  query spariscono. Il commento sulla parità a priorità uguale **tolto**:
  con D-3 la parità non esiste più. Chiavi dell'endpoint invariate
  (`profilo_nome` = `profilo_descrizione`).
- ✅ Il test Django sull'SQL generato si riduce a *«chiama la funzione, e non
  riscrive lo spareggio»* (niente `DISTINCT ON`, niente `priorita`, niente
  `fn_get_profili_accesso_applicabili`); il confronto vero è il pgTAP.
- ✅ Con D-1: `PermissionResolver.has_profilo_applicabile_per_area` legge
  `fn_get_permessi_ereditati_aree` invece dell'helper a 1 argomento (tutte le
  vesti). I due chiamanti — il messaggio di diniego (già gated su
  `OPERATORE`) e `permessi-effettivi` sul `target_user` — sono di contesto
  operatore, e ora «l'area ha un profilo» dice la stessa cosa del passo 4 del
  resolver. Un utente **senza** veste operatore riceve `has_profilo_reparto =
  false`, coerente col nome del campo (nessun consumatore FE).
- ✅ Binding provato con chiamata **reale** sul DB di sviluppo, in
  transazione annullata. 📌 *Fatto datato:* utente 6, `pagamenti` = `TUTTO`
  dal profilo `REPARTO` (prima `LETTURA` dal profilo cliente shop, §3).
- ℹ️ Non toccato: `ui_repository.fetch_preset_base_snapshot` usa l'helper con
  la veste della GUC e `ORDER BY priorita`, quindi segue già D-3 senza
  modifiche. La sua replica della cascata dei preset è un debito già
  dichiarato nel codice, fuori da questo brief.

### 5.1 Consegna BE (2026-09-25)

| File | Cosa |
| --- | --- |
| `backend/apps/amm_software/db/amm_software_repository.py` | `get_permessi_ereditati` legge `fn_get_permessi_ereditati_aree` / `_azioni` + `JOIN` di catalogo; commento riscritto (sede a DB, niente parità) |
| `backend/apps/core/services/permissions_resolver.py` | `has_profilo_applicabile_per_area`: `EXISTS` su `fn_get_permessi_ereditati_aree` (veste OPERATORE), docstring allineata a D-1 |
| `backend/apps/amm_software/tests/api/test_permessi_ereditati.py` | Test 5 riscritto: `test_query_non_riscrive_lo_spareggio` al posto di `test_query_sceglie_per_priorita`; test 4 sulle due funzioni nuove |
| `backend/apps/core/tests/services/test_permissions_resolver.py` | `test_has_profilo_true`: la query usa `fn_get_permessi_ereditati_aree` e **non** l'helper a 1 argomento |
| `backend/apps/amm_software/api/views.py` | Docstring di `PermessiEreditatiView`: priorità AD_HOC 1, REPARTO 2, PORTALE 3; sede a DB |
| `frontend/src/amministrazione/api/amministrazione.js` | Solo il commento sulle priorità. Nessun cambio funzionale FE |

**Prove:** 81 test Django verdi sui moduli toccati (`test_permessi_ereditati`,
`test_permissions_resolver`, `test_permissions`, `test_permessi_effettivi_api`,
`test_permissions_decisione_skip_area`); binding provato con chiamata reale
sul DB di sviluppo (vedi sopra).

**Resta:**

- ⏳ il collaudo a video di questo cambio, nel suo copione:
  [collaudo-in-app-permessi-ereditati-veste-operatore.md](collaudo-in-app-permessi-ereditati-veste-operatore.md)
  (comincia col `kill -HUP` sul master gunicorn, senza il quale in app non
  cambia niente). Resta aperto anche il collaudo del pannello
  ([collaudo-in-app-ui-permessi-operatore.md](collaudo-in-app-ui-permessi-operatore.md));
- ⏳ il commit, su richiesta di Tid.

---

## 6. Fuori da questo brief

- ⛔ Il **tetto d'area** (analisi §3): difetto aperto a sé, in
  `.codex/PROJECT_CONTEXT.md` § «Aperto».
  ✅ *Nota del 2026-10-31: chiuso il 2026-10-04 da [brief-db-permessi-tetto-area.md](brief-db-permessi-tetto-area.md) — un permesso specifico ora può solo restringere quello della sua area. La frase qui sotto è la storia di quando era aperto.*
- La **provenienza completa** restituita dai resolver (analisi §5).

---

## 7. Consegna DB (2026-09-25)

### 7.1 Cosa c'è, e perché in questa forma

| changeSet | Cosa |
| --- | --- |
| `20260925-80` | `script.fn_get_profili_accesso_applicabili`: PORTALE a **priorità 3** (D-3). Firma ancorata, identità invariata |
| `20260925-81` | ⭐ **nuova** `script.fn_get_permessi_ereditati_aree(p_auth_user_id)` |
| `20260925-82` | ⭐ **nuova** `script.fn_get_permessi_ereditati_azioni(p_auth_user_id)` |
| `20260925-83` | `fn_resolve_livello_area`: il passo 4 legge `…_aree` |
| `20260925-84` | `fn_check_azione_processo`: il passo 4 legge `…_azioni` |
| `20260925-85` | `fn_get_user_permissions_map`: via le CTE `livelli_user`/`best_per_area`, `LEFT JOIN` su `…_aree` |
| `20260925-86` | `fn_get_user_actions_map`: via le CTE `abilitazioni_user`/`best_per_azione`, `LEFT JOIN` su `…_azioni` |

**Due scelte che si discostano dal §2, con la ragione:**

1. **I resolver CHIAMANO il building block, non ne vengono confrontati.** Lo
   spareggio era scritto in **cinque** posti, non due: i due resolver
   puntuali (`LIMIT 1`), le due mappe (`DISTINCT ON`) e la query del
   backend. Un pgTAP che confronta la funzione nuova coi resolver avrebbe
   provato che *oggi* coincidono. Così la regola è scritta una volta, e il
   test 4 prova che nessun resolver la riscrive (linee-guida-sql §12.5.2).
   D-1 vive nello stesso posto: il `'OPERATORE'` sta nel building block.
2. **Due funzioni invece di una con `tipo_voce`.** Con una sola, ogni riga
   avrebbe avuto `livello` o `abilitata` a `NULL`, e ogni resolver avrebbe
   filtrato metà del risultato. Due forme pulite, stesse colonne di
   provenienza.

**Il contratto** (per il BE, §5):

```text
fn_get_permessi_ereditati_aree(p_auth_user_id integer)
  → area_id, livello, profilo_accesso_id, profilo_tipo, profilo_descrizione
fn_get_permessi_ereditati_azioni(p_auth_user_id integer)
  → azione_id, abilitata, profilo_accesso_id, profilo_tipo, profilo_descrizione
```

- **Una riga per voce coperta** da almeno un profilo; voce assente = nessun
  profilo = `BLOCCATO` / negata. È la semantica di oggi dell'endpoint.
- **Niente override, niente super admin**: è ciò che l'operatore avrebbe dal
  solo profilo.
- **Non dipende dalla veste di chi legge** (test 27): l'amministratore che
  apre il pannello interroga l'operatore scelto. Il gate di veste resta nei
  resolver.
- Le etichette di catalogo (`area_codice`, `area_descrizione`,
  `permission_codename`, `azione_descrizione`) le prende il BE con un `JOIN`
  su `config.aree_funzionali` / `config.azioni_processo`: sono presentazione,
  non logica. `profilo_nome` di oggi = `profilo_descrizione`.
- `LANGUAGE sql` `BEGIN ATOMIC`, `STABLE`, `INVOKER`: il planner le inlina
  nei resolver, e le dipendenze stanno in `pg_depend`.

### 7.2 Il pgTAP — `db/pgtap/script/test-fn-get-permessi-ereditati-v1.sql`

27 test, tutti su fixture **costruite**: tre operatori
(`fn_pgtap_crea_operatore_umano`), due UO, cinque profili, e i binding di
veste scritti in upsert. I casi del §2.1 ci sono tutti:

| §2.1 | Test |
| --- | --- |
| 1-2, su **tutto** il catalogo | 9, 10, 14, 26: per ogni area e azione **attiva**, resolver **e** mappa = ereditato, o default dove manca |
| 3 AD_HOC contro REPARTO | 11, 12 |
| 4 spareggio per voce | 13 |
| 5 multi-veste (D-1) | 17 (il caso esiste davvero), 18-21 |
| 6 senza profili | 15, 16 |

In più: la sede unica (4), la **premessa** dello spareggio determinato, cioè
i cinque indici unici con le loro colonne (5), D-3 (22-25) e l'indipendenza
dalla veste di sessione (27).

Adeguati nello stesso giro, perché fissavano la priorità 2 del PORTALE:
`script/test-fn-get-profili-accesso-applicabili.sql` (test 3, ora 3) e i
commenti di `ui/test-fn-lista-colonne-ricerca-full-v1.sql` (l'esito non
cambia: vince comunque l'AD_HOC).

### 7.3 Le prove fatte, e cosa resta a Tid

Tutto **prima dell'apply**, sullo scratch `zeroerp_ci` come `zeroerp`
(owner), con l'SQL **estratto** dai sette YAML in `BEGIN … ROLLBACK`:

- firme **identiche** al vivo e **una sola funzione per nome**
  (`pg_get_function_identity_arguments`, e il `DEFAULT NULL` dell'helper resta);
- guardrail statici verdi (letterali SQL, preCondition/seed, preambolo pgTAP);
- `plpgsql_check` sui quattro resolver: zero errori (restano i due avvisi di
  prima, il `PERFORM` del guard sul parametro delle mappe);
- pgTAP nuovo **27/27**. ⭐ **Vede il difetto**: con i resolver vecchi dà 4
  rossi (4, 18, 20, 26), senza il `-80` dà rosso il 25;
- stessi esiti con e senza l'SQL estratto per `test-fn-get-profili-accesso-applicabili-overload`,
  `test-permessi-funzioni-risoluzione`, `test-fn-resolve-regression-operatore`,
  `test-fn-guard-azione-v1`, e i quattro `ui/` che usano l'helper. L'unico
  cambio atteso: `test-fn-get-profili-accesso-applicabili` test 3, rosso sul
  DB non migrato e verde col `-80`.

⚠️ **Da owner la RLS non c'è**, ma le tabelle del giro non la hanno
(profili, binding, identità, risorse umane): la corsa come app non dovrebbe
dire cose diverse.

✅ **A Tid — fatto il 2026-09-25:** apply di `-80` → `-86` (verificato dal
backend: le sette righe sono in `databasechangelog`, le due funzioni nuove
esistono) e corsa dei pgTAP (commit `f7d1a47b0`, *«Eseguiti test pgtap»*).
L'elenco da far girare era: il pgTAP nuovo, i nove sopra e i due presidi
trasversali (`dbops/test-riferimenti-morti-v1`,
`script/test-rubinetto-primo-motivo-v1`: nessuna funzione nuova chiama
l'helper del primo motivo).

📌 Numerazione: scritti come `-90…-96` e riportati a `-80…-86` su richiesta di
Tid prima di qualunque apply (nessuna riga in `databasechangelog`).

### 7.4 Documentazione aggiornata

- `docs/it/dbzero/script/manual/fn_get_profili_accesso_applicabili.md`:
  priorità, stato dei chiamanti, sede dello spareggio.
- `docs/it/guide/architettura-permessi-e-autorizzazioni.md`: l'ordine delle
  tre sorgenti (il reparto prima della veste), la veste OPERATORE per i
  permessi da operatore, la sede della regola.
