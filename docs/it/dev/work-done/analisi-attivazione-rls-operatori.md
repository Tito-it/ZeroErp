# Attivazione RLS per lo scope Emittente Fiscale degli OPERATORI — analisi e brief al team DB

> **Ultima revisione:** 2026-06-01
> **Destinatari:** Tid (decisioni di dominio), team DB su `dev/db-tid` (esecuzione DDL/policy/ruoli), backend agent (write-side trigger + cablaggio scope)
> **Stato:** Analisi + brief. NESSUNA azione DB eseguita (regola `feedback_db_actions_passaggio_team`). ZeroErp NON in produzione: breaking change ammessi, niente gradient di staging.
> **Convenzione marcatura:** `[VERIFICATO]` = riscontrato sul codice/changeset attuale; `[DA VERIFICARE SU DB]` = richiede introspezione runtime non disponibile dal sandbox (psql non raggiungibile); `[DECISIONE TID]` = scelta di dominio aperta.
>
> **Documenti derivati** (estratti da questa analisi, 2026-06-01):
> - [analisi-attivazione-rls-db.md](analisi-attivazione-rls-db.md) — brief al team DB **+ log di implementazione** (DB-side completo, changeset `20260601-06..37`).
> - [analisi-attivazione-rls-operatori-be-fe.md](analisi-attivazione-rls-operatori-be-fe.md) — piano BE/FE dettagliato con prerequisiti DB.

---

## 1. Tesi e contesto

**Tesi: lo scope Emittente Fiscale (EF) degli OPERATORI interni può essere attivato in RLS PRIMA del portale.** `[VERIFICATO]`

La motivazione è che il *consumatore* della RLS-EF esiste già oggi: il backend interno autenticato come OPERATORE popola già i 5 GUC (`set_jwt_gucs` in `backend/apps/core/api/jwt_audit_authentication.py`), inclusi `app.ruolo_applicativo` e `app.current_identita_id`, che sono esattamente gli input richiesti dalla policy EF già scritta. Le policy `rls_fatture_ef_whitelist` (branch OPERATORE) e `rls_fatture_ba_ownership` (branch portale/shop) sono **PERMISSIVE indipendenti**, gated su `ruolo_applicativo`: attivare il branch OPERATORE NON richiede il portale. È solo il branch `BA_OWNERSHIP` (CLIENTE_PORTALE / SHOP_CUSTOMER) ad essere bloccato dall'assenza delle API portale.

Quindi l'asimmetria implicita nell'intuizione è corretta: ciò che è bloccato è il ramo portale, non il ramo operatore.

**Ma la tesi è fondata e INCOMPLETA.** L'attivazione semplice (`ENABLE` su una tabella) produrrebbe oggi enforcement falso o lockout, per tre ragioni verificate che diventano prerequisiti bloccanti (§3 e §6):

1. le viste di dominio NON sono `security_invoker` → la RLS sarebbe cosmetica (bypassata dalle viste definer);
2. i GUC sono **session-scoped** con `CONN_MAX_AGE=600` → rischio leak cross-request appena la RLS morde;
3. solo `vendite.fatture` ha il branch OPERATORE → ENABLE big-bang azzererebbe la vista operatore sulle altre tabelle.

Questo documento valida la tesi, censisce il primo lotto, e formalizza il brief al team DB con l'ordine dei prerequisiti.

---

## 2. Stato attuale: enforcement ibrido + buchi + RLS dormiente

### 2.1 Enforcement EF in LETTURA (applicativo, a macchia di leopardo) `[VERIFICATO]`

Single source of truth Python: `backend/apps/core/services/permissions_resolver.py`.

| Wrapper | Funzione DB | Convenzione | Guard OPERATORE/SUPER_ADMIN |
|---|---|---|---|
| `get_emittenti_ids` (L183) | `script.fn_get_emittenti_scope` (legacy) | PK | **NO guard** |
| `get_emittenti_sr_ids` (L202) | `fn_get_emittenti_scope_sr_ids` | SR | guard completi |
| `get_emittenti_pk_ids` (L233) | `fn_get_emittenti_scope_pk_ids` | PK | guard completi (incl. `fn_is_super_admin → RETURN NULL`) |

Semantica uniforme: `None` = nessuna restrizione (whitelist vuota = admin globale), `[]` = nessun accesso.

Punti che filtrano in lettura (estratto): liste preventivi (`preventivi_repository.py:110-116`), contratti (`contratti_repository.py:344-346`), lotti+lotto-fatture (`vendite_repository.py:31-43`), clienti/BA/soggetti (`anagrafiche/api/views_*`), ricerca universale (`core/api/search_view.py`), documenti (`documenti/services/_scope.py`). `EmittenteFiscaleScopeMixin` (`backend/apps/core/mixins.py:17`) è **definito ma non usato da nessuna view** (placeholder).

### 2.2 Enforcement EF in SCRITTURA (trigger, 2 sole tabelle) `[VERIFICATO]`

Grep `EXECUTE FUNCTION script.trgfn_guard_emittente_scope` →

| Trigger | Tabella | Mode | Colonna |
|---|---|---|---|
| `trg_fatture_a10_guard_emittente_scope_ins_upd` | `vendite.fatture` | `soggetto_ruolo` | `emittente_soggetto_ruolo_id` |
| `trg_vendite_movimenti_a10_guard_emittente_scope_ins_upd` | `pagamenti.vendite_movimenti` | `fattura` | `fattura_id` → fatture |

`script.trgfn_guard_emittente_scope` → `script.fn_check_user_emittente_scope(auth_user_id, emittente_fiscale_id)`: NULL user (batch) → true; SUPER_ADMIN → true; identità OPERATORE assente → false; whitelist vuota → true; altrimenti EXISTS. **Falso amico:** `trg_contratti_a10_guard_emittente_ba_ins_upd` verifica solo coerenza BA↔EF (`E_CONTRATTO_EMITTENTE_BA_INCOERENTE`), NON lo scope utente.

### 2.3 I BUCHI reali (motivazione della RLS) `[VERIFICATO]`

- **B1 — Offerte commerciali, lista SENZA filtro EF.** `offerte_repository.py:434 list_offerte` / `:474 count_offerte` / `:384 _build_offerte_filters` non accettano `auth_user_id` né predicato EF, benché `emittente_fiscale_id` sia NOT NULL. `offerte_service.py:351` non accetta nemmeno l'utente in firma → strutturalmente impossibile filtrare. `views_offerte.py:248` (GET lista) non passa lo scope. Un OPERATORE ristretto vede TUTTE le offerte. **Bug logico del modello** (asimmetria netta vs preventivi/contratti, stesso dominio, stessa colonna).
- **B2 — Detail-by-id senza scope (IDOR) su preventivi/contratti/offerte.** `get_contratto` (`contratti_repository.py:380`, `WHERE c.id=%s`), `get_preventivo` (`preventivi_repository.py:143`), `get_offerta` (`offerte_repository.py:509`): nessun predicato EF. Le liste filtrano, i getter di dettaglio no → un operatore fuori scope che conosce/indovina un ID legge testata+righe+capabilities.
- **B3 — Acquisti interamente scoperti in lettura.** `backend/apps/acquisti/db/` contiene solo `__init__.py`/`README.md`: nessun repository, nessun filtro. (Nota: il dominio acquisti non porta concetto EF — §4.)
- **B4 — fatture/scadenze: lettura solo lotto-scoped.** L'unica lettura filtrata è `list_lotto_fatture`. Nessuna lista fatture flat con filtro EF; il dettaglio fattura/scadenza non passa da un repo con predicato EF. Il guard DB esiste solo in WRITE.
- **B5 — fn legacy senza guard ancora in uso.** `get_emittenti_ids → fn_get_emittenti_scope` (legacy, senza guard) usata da documenti, ai_assistant, `parameter_repository.py:353`. Rischio: identità OPERATORE disattivata non fail-closed in questi path.

**Sintesi buchi:** lo scope è applicato in alcune liste, assente su offerte-lista, su tutti i dettagli by-id, su acquisti, su fatture in lettura diretta. Ogni nuovo endpoint deve ricordarsi di passare `auth_user_id` e scrivere il predicato — pattern fragile, già violato. La RLS rende l'enforcement uniforme e a prova di endpoint dimenticato (la policy agisce su OGNI SELECT, lista o by-id).

### 2.4 RLS dry-run dormiente `[VERIFICATO]`

Nessun `ENABLE ROW LEVEL SECURITY` / `FORCE ROW LEVEL SECURITY` in tutto `db/` (le occorrenze in `20260419-62` righe 19/85/87 sono `comment:`/`COMMENT ON POLICY`; in `test-rls-policies-structure.sql` L11 è un commento). Tutte le policy sono in `pg_policies` ma dormienti. Tutte sono **PERMISSIVE FOR SELECT** (nessuna `FOR ALL`/`FOR INSERT/UPDATE/DELETE`, nessun `WITH CHECK`).

---

## 3. Punti critici VERIFICATI (con esito)

| # | Punto critico | Esito | Dettaglio |
|---|---|---|---|
| C1 | **Whitelist VUOTA = globale** (rischio lockout?) | **OK, NESSUN LOCKOUT** `[VERIFICATO]` | `fn_scope_ef_whitelist` (`20260418-60-...yaml:36-78`): gate fail-closed sull'identità (L56-60) + ramo `NOT EXISTS` whitelist (L62-67) → con whitelist vuota ritorna `true` per qualsiasi EF. pgTAP test 5 lo esercita. Semantica: fail-closed sull'identità, fail-open sulla whitelist. |
| C2 | **`security_invoker` sulle viste** | **BLOCKER** `[VERIFICATO]` | Solo 2 changeset in tutto il repo usano `security_invoker=true` (`20260419-91`, `20260429-19`, entrambi la vista RUA). Le ~49 viste `vw_*` di dominio sono definer → eseguono col contesto RLS dell'owner (`postgres`, superuser BYPASSRLS) → RLS della tabella base **bypassata**. `reloptions`/owner reali `[DA VERIFICARE SU DB]`. |
| C3 | **GUC OPERATORE popolati** | **OK** `[VERIFICATO]` | `set_jwt_gucs` legge ruolo+SR da `identita_digitali` (CTE, attivo=true). `identita_digitali.soggetto_ruolo_id` NOT NULL. `fn_crea_operatore_v2 → fn_crea_risorsa_umana_v2` inserisce identità con `ruolo_applicativo='OPERATORE'` quando `p_auth_user_id IS NOT NULL`. Ogni operatore con login HA identità OPERATORE + SR. RU senza login non logga → irrilevante. |
| C4 | **`zeroerp_app` NOBYPASSRLS** | **OK (atteso)** `[conferma live pendente]` | App runtime gira come **`zeroerp_app`** confermato (`backend/.env` → `DB_USER`). `CREATE ROLE zeroerp_app LOGIN` senza `BYPASSRLS` (`20250311_01-...:36`) → **default NOBYPASSRLS** → RLS morde. Nessun `ALTER ROLE` che aggiunga BYPASSRLS in changelog. `[DA VERIFICARE SU DB]` solo l'attributo runtime effettivo (provisioning fuori Liquibase). |
| C5 | **GUC session-scoped vs `CONN_MAX_AGE`** | **BLOCKER (bug modello)** `[VERIFICATO]` | `set_jwt_gucs` usa `set_config(..., false)` → GUC di sessione (`jwt_audit_authentication.py:131-135`); `settings.py:216` ha `CONN_MAX_AGE=600`. Connessione persistente riusata senza ripassare dal middleware eredita i GUC del request precedente. Oggi colpisce solo l'audit; con RLS-EF attiva = leak di scope cross-request. |
| C6 | **`ENABLE` migrazione/batch** | **OK per migrazione** (rivisto) / batch a rischio | **CORRETTO 2026-06-01:** le migrazioni reali girano come **`titodb`** via `scripts/liquibase5.sh` (utente dedicato), NON `postgres`. Il `postgres` in `db/liquibase-mirror.properties` era un **ambiente di test obsoleto** (da ignorare). `titodb` superuser/BYPASSRLS `[DA VERIFICARE SU DB]` → migrazioni esenti. pgAgent batch gira **senza GUC** → vedi R4. Vedi §11.8. |
| C7 | **Branch SUPER_ADMIN nella policy EF** | **BUG MODELLO** `[VERIFICATO]` | `rls_fatture_ef_whitelist` USING = `ruolo_applicativo='OPERATORE' AND fn_scope_ef_whitelist(...)`: NESSUN branch SUPER_ADMIN. Il wrapper Python `fn_get_emittenti_scope_pk_ids` SÌ (`fn_is_super_admin → RETURN NULL`). Un SUPER_ADMIN (che ha comunque `ruolo_applicativo='OPERATORE'` nel GUC) con righe whitelist verrebbe ristretto in lettura RLS, asimmetrico rispetto a oggi. |

---

## 4. Censimento tabelle del primo lotto

Convenzione colonna EF (asimmetria di modello da segnalare, §6/R-modello):
- **SR** = `emittente_soggetto_ruolo_id` (soggetto_ruolo_id dell'EF) → compatibile con `fn_scope_ef_whitelist` esistente.
- **PK** = `emittente_fiscale_id` (PK reale di `anagrafiche.emittenti_fiscali`) → richiede una NUOVA `fn_scope_ef_whitelist_pk` (cfr `feedback_emittente_pk_vs_soggetto_ruolo`).

| Tabella | Colonna EF | Conv. | Policy EF dry-run | Letta da operatore | Primo lotto | Motivazione |
|---|---|---|---|---|---|---|
| `vendite.fatture` | `emittente_soggetto_ruolo_id` | SR | **SÌ** (`rls_fatture_ef_whitelist`) | sì (pipeline lotti/contabilità) | **ONDATA 1 — SÌ** | Unica con policy EF già scritta + guard scrittura attivo. Candidata ideale, zero fn nuove. |
| `vendite.fatture_scadenze` | `fattura_id` (indiretto) | — | no (solo BA via `fn_scope_ba_ownership_via_fattura`) | sì | **ONDATA 1 — SÌ** | Richiede nuova `fn_scope_ef_whitelist_via_fattura` speculare. Stesso dominio scadenzario. |
| `vendite.fatturazione_lotti` | `emittente_soggetto_ruolo_id` | SR | no | sì (pipeline) | **ONDATA 1 — SÌ** | Convenzione SR già compatibile, nessuna fn nuova. Stessa famiglia di join di fatture. |
| `vendite.preventivi` | `emittente_fiscale_id` (NOT NULL) | PK | no (read-side repo) | sì | **ONDATA 2 — SÌ** | Filtro applicativo già presente; richiede `fn_scope_ef_whitelist_pk`. RLS = defense-in-depth. |
| `vendite.contratti` | `emittente_fiscale_id` (NOT NULL) | PK | no (read-side repo) | sì | **ONDATA 2 — SÌ** | Ha guard BA (non scope). Richiede fn PK. Chiude IDOR B2. |
| `vendite.offerte_commerciali` | `emittente_fiscale_id` | PK | no (read-side repo) | sì | **ONDATA 2 — SÌ** | Chiude il BUCO B1 (lista non filtrata) e l'IDOR. Richiede fn PK. |
| `documenti.documenti_generati` | `emittente_fiscale_id` (NOT NULL) | PK | no (helper `_scope.py` maturo) | sì | **ONDATA 2 — SÌ** | NOT NULL = nessuna riga sfugge. RLS = defense-in-depth. Richiede fn PK. |
| `pratiche.pratiche` | `emittente_fiscale_id` | PK | no (read-side repo) | sì (coda 3 livelli) | **ONDATA 2 — valutare** `[DECISIONE TID]` | Da includere se pratiche sono nel perimetro operativo del lotto. Richiede fn PK + indice (§7). |
| `vendite.ordini` | `emittente_fiscale_id` (da AGGIUNGERE) | PK | no (solo cliente_ownership) | sì | **ONDATA 2 — SÌ** `[✅ DECISO]` | Decisione 2026-06-01: si denormalizza `emittente_fiscale_id` snapshot (come preventivi/contratti). Richiede nuova colonna + backfill + fn PK + trigger write + indice. Vedi §11.4. |
| `anagrafiche.billing_account` | NESSUNA — via efba | efba | no (solo `self_ownership` portale) | sì | **RIENTRA — famiglia efba** `[✅ DECISO §11.7]` | Scope via `emittenti_fiscali_billing_account` (specifico-o-default). Riusa `fn_check_ba_visible_for_emittenti` ∩ whitelist operatore. Famiglia di scope distinta (BA-visibility), allinea la RLS al filtro già attivo lato ricerca. |
| `acquisti.ordini` / `acquisti.ddt` | NESSUNA (fornitore) | — | no (solo fornitore_ownership) | sì | **FUTURO — fuori primo lotto** `[✅ DECISO §11.7]` | Rientrerà quando il dominio acquisti sarà sviluppato; oggi nessuna identità emittente (ciclo passivo). Non bloccante. |
| `documenti.template_documenti` / `template_asset` | `emittente_fiscale_id` | PK | no | sì (admin template) | **NO — lotto config** | Config, non documento transazionale. |
| `vendite.listini` | `emittente_soggetto_ruolo_id` (NOT NULL) | SR | no | sì | **NO — lotto config** | Pricing cross-EF per design. Unica famiglia config già compatibile con la fn SR esistente. |
| `vendite.commesse` | `emittente_soggetto_ruolo_id` | SR | no | da censire | **NO in prima battuta** | Verificare list-view operatore prima di includerla. |
| `vendite.fatture_arrotondamenti_scope` / `fatture_fondi_fattura_source` | `emittente_soggetto_ruolo_id` | SR | no | sì | **NO — config** | Config di fatturazione. Citate per completezza censimento SR. |

**Raccomandazione lotto in 3 ondate:**
- **ONDATA 1** (convenzione SR, zero/poche fn nuove): `vendite.fatture` (policy pronta) + `vendite.fatture_scadenze` (nuova fn via_fattura) + `vendite.fatturazione_lotti`.
- **ONDATA 2** (richiede `fn_scope_ef_whitelist_pk`): `vendite.preventivi`, `vendite.contratti`, `vendite.offerte_commerciali`, `documenti.documenti_generati`, `pratiche.pratiche` `[DECISIONE TID]`.
- **FUORI primo lotto:** config (listini, template, arrotondamenti/fondi) → lotto config dedicato; acquisti (no EF); `vendite.ordini` → bloccato da decisione di modello sulla colonna emittente.

---

## 5. Brief al team DB (`dev/db-tid`)

> Il backend agent NON esegue DDL/policy/ENABLE/ALTER ROLE. Questo è il brief da eseguire dal team DB, ordinato per dipendenza. ZeroErp non è in produzione: ammessi changeset distruttivi/breaking, ma con kill-switch pronto (§9).

### 5.1 Decisione write-side: SELECT in RLS + trigger (NON `FOR ALL`) `[VERIFICATO + raccomandazione]`

**Raccomandazione: mantenere RLS `FOR SELECT` ed estendere i trigger guard per la scrittura. NON estendere la policy a `FOR ALL`/`WITH CHECK`.** Motivi tecnici dirimenti:

1. **Doppia convenzione = doppia logica `WITH CHECK` duplicata** (SR vs PK) — viola la regola del 2; i trigger già lo fanno mode-driven.
2. **Il GUC d'identità non è garantito sui batch.** `trgfn_guard_emittente_scope` ha lo skip esplicito `IF v_auth_user_id IS NULL THEN RETURN NEW` per i job notturni. Una `FOR ALL WITH CHECK` con `app.current_identita_id=''` cadrebbe nel gate fail-closed della fn → **bloccherebbe i batch in scrittura**. Questo è il motivo dirimente.
3. **Errore strutturato** `E_SCOPE_EMITTENTE` (via `fn_log_and_raise_error`) vs il generico opaco `new row violates row-level security policy`.
4. **Defense-in-depth a strati distinti:** RLS `FOR SELECT` = confinamento in lettura; trigger `BEFORE INS/UPD` = confinamento in scrittura.

Conseguenza: estendere il trigger generico costa **una sola `CREATE TRIGGER`** per tabella. Serve però un nuovo ramo per la convenzione PK:

```sql
-- in script.trgfn_guard_emittente_scope: aggiungere il terzo mode
ELSIF v_mode = 'emittente_pk' THEN
    v_emittente_fiscale_id := v_col_value;   -- la colonna È già la PK, no risoluzione SR->PK
```

Poi attaccare il trigger a `contratti`, `offerte_commerciali`, `preventivi`, `documenti_generati`, `pratiche` con `('emittente_pk','emittente_fiscale_id')`; `fatture_scadenze` riusa `mode='fattura'`. **Senza questo, quelle tabelle restano scrivibili cross-EF dall'operatore anche dopo l'attivazione RLS in lettura — asimmetria lettura/scrittura prioritaria.**

### 5.2 Prerequisiti DB (ordine di dipendenza)

1. **[sblocca tutto] Verifica attributi ruolo.** Stato reale `rolbypassrls` per `zeroerp_app`, `zeroerp_admin`, `zeroerp_migration`. Atteso: app=NOBYPASSRLS, admin/migration=BYPASSRLS. Se `zeroerp_app` è BYPASSRLS → `ALTER ROLE zeroerp_app NOBYPASSRLS`. Formalizzare un ruolo migrazione esplicito (`zeroerp_migration BYPASSRLS`) anziché affidarsi a `postgres` nudo (no quick fix). [C4, R2]
2. **Ruoli di test pgTAP.** `zeroerp_rls_test` (NOBYPASSRLS) + `zeroerp_rls_test_bypass` (BYPASSRLS), con GRANT SELECT minimi sulle tabelle target. Prerequisito dei test funzionali (§8).
3. **Nuove fn scope.** `script.fn_scope_ef_whitelist_pk(identita_id, emittente_fiscale_id_pk)` (match diretto su `user_emittenti_fiscali.emittente_fiscale_id`) + `script.fn_scope_ef_whitelist_via_fattura(identita_id, fattura_id)` (risolve `fatture.emittente_soggetto_ruolo_id` e delega a `fn_scope_ef_whitelist`, speculare a `fn_scope_ba_ownership_via_fattura`).
4. **[bug modello C7] Branch SUPER_ADMIN** in `rls_fatture_ef_whitelist` e in tutte le nuove policy EF: `OR script.fn_is_super_admin(<auth_user dal GUC>)`, simmetrico a `fn_get_emittenti_scope_pk_ids`. Verificare che `fn_is_super_admin` accetti l'input GUC disponibile (`app.current_user_id`).
5. **Branch policy OPERATORE/EF** su `fatture_scadenze` (via_fattura), `preventivi`, `contratti`, `offerte_commerciali`, `documenti_generati`, `pratiche` (PK).
6. **`security_invoker=on`** su tutte le `vw_`/MATVIEW lette dagli operatori che insistono su tabelle del lotto (introspezione `reloptions`+owner+`pg_depend` prima). Le MATVIEW non supportano `security_invoker` → decisione esplicita (smaterializzare o filtrare a monte). [C2, R1-viste — BLOCCANTE]
7. **[congiunto BE, C5] GUC scope.** Risolvere il leak session-scoped: `[DECISIONE TID]` Opzione A (transaction-local `set_config(...,true)` dentro `ATOMIC_REQUESTS`) o Opzione B (reset esplicito dei 5 GUC a inizio request, fail-closed). BLOCCANTE.
8. **[batch] `dbops.fn_apply_chiusura_scadenze`.** Verificare se scrive su `fatture_scadenze`; se sì e si applica RLS, renderla `SECURITY DEFINER` owner-bypass (pattern già in repo, owner `postgres`). pgAgent NON è owner → non basta evitare FORCE.
9. **Decisione `vendite.ordini`** `[DECISIONE TID]`: denormalizzare `emittente_fiscale_id` snapshot o lasciare fuori scope.
10. **Changeset ENABLE per famiglia di join**, partendo da `vendite.fatture` (+ `fatture_scadenze` + `fatturazione_lotti` nello stesso changeset), ognuno con il changeset kill-switch gemello `DISABLE` (§9).

### 5.3 ENABLE vs FORCE `[VERIFICATO]`

- **`ENABLE ROW LEVEL SECURITY`** è sufficiente: l'owner (`postgres`) e i ruoli BYPASSRLS restano esenti (migrazioni/job owner non bloccati). Le policy sono `FOR SELECT` → INSERT/UPDATE/DELETE **non coperti**: con RLS attiva e nessuna policy di write, quei comandi vanno in **deny-all**. Vedi R5: per le tabelle scritte dall'operatore NON usare ENABLE senza prima decidere la copertura write (qui: il write resta governato dal trigger, ma deny-all RLS bloccherebbe comunque a monte se non si esclude la tabella o non si aggiunge policy di write).
- **`FORCE ROW LEVEL SECURITY`** applica RLS anche all'owner → complica migrazioni/job batch. **Tenere FUORI scope in questa fase.**

**Conseguenza operativa:** la via meno invasiva e coerente con l'architettura è RLS `FOR SELECT` su tabelle dove l'operatore legge, write governato dai trigger esistenti, **senza FORCE**. Per ogni tabella va verificato esplicitamente `[DECISIONE per tabella]` se l'operatore la scrive: in tal caso o si aggiunge una policy di write permissiva coerente con lo scope, o si esclude la tabella dall'ENABLE finché non risolto, per evitare il deny-all silenzioso sulle scritture.

### 5.4 Unificazione della regola di scope EF — una regola, una funzione `[✅ DECISO 2026-06-01]`

Risolve C7/R3 (§3, §6) e il buco B5 (§2.3): oggi la stessa regola "questo operatore può vedere questo emittente" vive in più implementazioni che non si parlano, con comportamenti divergenti (la RLS-read NON ha il bypass SUPER_ADMIN; esistono duplicati legacy `config.*` sul vecchio modello `ADMIN`). Decisione di Tid: **niente regola replicata, si unifica ora anche se costa.**

#### 5.4.1 Diagnosi sui corpi reali `[VERIFICATO]`

| Funzione | Shape | Chiave | Batch NULL | SUPER_ADMIN | Identità-attiva gate | Membership | Lang |
|---|---|---|---|---|---|---|---|
| `script.fn_check_user_emittente_scope` (write-guard) | bool | auth_user_id + PK | ✅ true | ✅ bypass | ✅ fail-closed | PK | plpgsql |
| `script.fn_scope_ef_whitelist` (RLS-read) | bool | identita_id + **SR** | — | **❌ MANCA (bug C7)** | ✅ (CTE inline) | SR | sql (inlineable) |
| `script.fn_get_emittenti_scope_pk_ids` (+ `_sr_ids` wrapper) | array | auth_user_id | — | ✅ → NULL | ✅ → `{}` | PK | plpgsql |
| `config.fn_check_user_emittente_scope` (LEGACY) | bool | auth_user_id + PK | ✅ | usa `ruolo_sistema=ADMIN` (modello vecchio) | ❌ | PK | plpgsql |

Note positive: la **famiglia "array" è già DRY** — `fn_get_emittenti_scope_pk_ids` è la canonica, `_sr_ids` ne è un wrapper thin, e condividono gli helper `script.fn_is_super_admin` + `script.fn_has_identita_attiva`. La divergenza vera è nella **famiglia "predicato booleano"** (RLS-read senza super_admin) + i **duplicati legacy** `config.*`.

#### 5.4.2 Principio: canonica + adattatori sottili + duale

Un *predicato booleano* e un *generatore di array* hanno shape diverse e non si fondono in un'unica funzione; ma devono avere **una sola sede della regola** da cui tutto deriva.

```text
            ┌──────────────────────────────────────────────┐
            │  CANONICA (la regola, una volta sola)         │
            │  fn_emittente_in_scope(auth_user_id, ef_pk)   │
            │  1. user NULL        → true  (batch)          │
            │  2. fn_is_super_admin→ true  (bypass)         │
            │  3. no identità OPERATORE attiva → false      │
            │  4. whitelist vuota  → true  (globale)        │
            │  5. else EXISTS membership (PK)               │
            └───────┬───────────────┬──────────────┬────────┘
       delega       │               │              │  duale (stessi helper)
        ┌───────────▼──┐   ┌────────▼────────┐   ┌─▼──────────────────────┐
        │ adapter SR   │   │ adapter PK      │   │ array gens (già DRY):  │
        │ (risolve     │   │ (passthrough)   │   │ _pk_ids canonica +     │
        │  SR→PK)      │   │                 │   │ _sr_ids wrapper        │
        └──────┬───────┘   └───────┬─────────┘   └────────────────────────┘
   policy fatture/lotti     policy prev/contr/off/doc/prat
   + trigger write          + trigger write
```

- **Write-guard** = chiama la canonica direttamente (la canonica *è* l'attuale `fn_check_user_emittente_scope`, già corretta nel comportamento).
- **RLS-read SR/PK** = adattatori sottili che delegano alla canonica → **il bypass SUPER_ADMIN entra gratis ovunque** (bug C7 chiuso per costruzione).
- **Array gens** = restano come sono (già condividono gli helper), legati alla canonica da un **test di dualità** (anti-divergenza).

#### 5.4.3 Decisioni di ingegneria `[✅ CONFERMATE da Tid]`

1. **Chiave attore = `auth_user_id`** (NON `identita_id`): è la chiave della tabella whitelist, del write-guard e del Python → unifica i tre. Le policy RLS passano `current_setting('app.current_user_id')::int` (GUC già presente). L'`identita_id` esce dalla regola.
2. **Canonica in `LANGUAGE sql STABLE`** (non plpgsql): resta **inlineable** dal planner nelle RLS (perf per-riga). L'attuale write-guard plpgsql va riscritto come SQL inlineable equivalente. Da benchmarkare (§7).
3. **`script.fn_is_super_admin`** deve accettare `auth_user_id` (integer) come input — `[DA VERIFICARE SU DB]` la firma; è l'unico input GUC disponibile nelle policy (`app.current_user_id`).

#### 5.4.4 Passi (estraibili poi in brief DB + brief BE/FE)

**Lato DB (`dev/db-tid`), in ordine di dipendenza:**

1. **Canonica** `script.fn_emittente_in_scope(p_auth_user_id int, p_emittente_fiscale_id bigint) RETURNS boolean` — `sql STABLE`, i 5 rami sopra. Può riusare il nome `fn_check_user_emittente_scope` (per non rompere il trigger esistente) oppure rinominare + alias di compatibilità.
2. **Adapter SR** `script.fn_scope_ef_whitelist(p_auth_user_id int, p_emittente_sr_id bigint)` → risolve SR→PK via `anagrafiche.emittenti_fiscali` e delega alla canonica. *(Cambio firma: oggi prende `identita_id`; gli unici chiamanti sono le policy dormienti, riscritte qui — nessuna produzione.)*
3. **Adapter PK** `script.fn_scope_ef_whitelist_pk(p_auth_user_id int, p_emittente_pk bigint)` → delega diretta. È anche la fn richiesta dall'Ondata 2 (§5.2.3).
4. **Riscrivere le policy EF** per passare `current_user_id` agli adapter: `rls_fatture_ef_whitelist` (SR) e le nuove policy Ondata 2 (PK) → SUPER_ADMIN ora coperto ovunque.
5. **Kill duplicati legacy**: drop `config.fn_check_user_emittente_scope` (modello `ADMIN`) e `config.fn_get_emittenti_scope*` previa verifica zero-caller `[DA VERIFICARE SU DB]`; dismettere `script.fn_get_emittenti_scope` legacy **senza guard** (buco B5).
6. **pgTAP**:
   - unit sulla canonica: 5 rami + NULL-batch + super_admin + identità inattiva + whitelist vuota/popolata;
   - **test di dualità** (l'anti-divergenza): per N utenti campione, asserire `fn_emittente_in_scope(u, X)` ⟺ `(fn_get_emittenti_scope_pk_ids(u) IS NULL OR X = ANY(fn_get_emittenti_scope_pk_ids(u)))`. Garantisce che predicato e array non divergano mai più senza forzarli a chiamarsi a vicenda.

**Lato BE (piccolo):** `PermissionResolver.get_emittenti_ids` (wrapper sulla `fn_get_emittenti_scope` legacy no-guard) → puntare alla canonica guarded; allineare i caller (`documenti`, `ai_assistant`, `parameter_repository.py:353`). **FE:** nessun impatto diretto previsto (lo scope è server-side); verificare solo che le liste filtrate non mostrino regressioni — da confermare in fase di estrazione del brief BE/FE.

#### 5.4.5 Costo e collocazione

Lavoro **DB-prevalente** (~6 changeset fn/policy + pgTAP) + ritocco BE. Non è lavoro extra rispetto alla RLS: gli adapter SR/PK **servono comunque** per Ondata 1/2 → è lo *stesso* lavoro fatto bene una volta. **Va PRIMA di qualsiasi `ENABLE`** (la policy fatture va riscritta per delegare alla canonica con super_admin).

---

## 6. Rischi e mitigazioni

> **BLOCKER in cima.** R1 e R-GUC falliscono in direzione "vede troppo / leak" SENZA errore: non emergono da uno smoke che testa solo i lockout.

| # | Rischio | Prob. | Impatto | Esito/Mitigazione |
|---|---|---|---|---|
| **R1** | **Viste senza `security_invoker` bypassano la RLS** (RLS cosmetica) | ALTA | CRITICO | `[VERIFICATO]` BLOCKER. Censire ogni vista/matview su tabelle del lotto (`pg_depend`), portare a `security_invoker=on`; matview da smaterializzare/filtrare. pgTAP di regressione che fallisce se esiste vista definer su tabella RLS. |
| **R-GUC** | **GUC session-scoped + `CONN_MAX_AGE=600` → leak cross-request** | MEDIA | CRITICO | `[VERIFICATO]` BLOCKER, bug modello. Transaction-local o reset-per-request fail-closed. Tocca BE. |
| **R2** | **`zeroerp_app` con BYPASSRLS → RLS inerte** | BASSA (rivisto) | CRITICO | Evidenza committata favorevole: `zeroerp_app` creato `LOGIN` senza BYPASSRLS → NOBYPASSRLS. `[DA VERIFICARE SU DB]` solo conferma attributo runtime. `ALTER ROLE ... NOBYPASSRLS` solo se la verifica live smentisce. Vedi C4/§11.8. |
| **R3** | **SUPER_ADMIN ristretto in lettura** (asimmetria read vs write/Python) | CERTA | ALTO | `[VERIFICATO]` Bug modello C7. Aggiungere branch SUPER_ADMIN alla policy. Unificare le 3 codifiche (write-guard / RLS-read / wrapper Python) a una fn canonica. |
| **R4** | **Job batch senza GUC → 0 righe sotto RLS** (UPDATE che "gira ok" su 0 righe) | MEDIA-ALTA | ALTO | `[VERIFICATO]` `fn_apply_chiusura_scadenze` → `SECURITY DEFINER` owner-bypass (pgAgent non è owner). |
| **R5** | **ENABLE con sole policy SELECT → deny-all su INSERT/UPDATE operatore** | MEDIA | ALTO | `[VERIFICATO]` Niente FORCE; non abilitare RLS su tabelle scritte senza policy di write o decisione esplicita. Write via trigger. |
| **R6** | **`emittente_*_id NULL` invisibile agli operatori ristretti** | BASSA (rivisto) | BASSO | `[VERIFICATO — vedi §11.5]` **In gran parte NON-problema.** Sui documenti l'emittente è **materializzato NOT NULL** (default incluso): `documenti_generati`/`preventivi`/`contratti`/`offerte` NOT NULL confermato; `fatture.emittente_soggetto_ruolo_id` da riconfermare. Il default-emittente (`emittenti_fiscali_billing_account` is_default+BA NULL, auto-creato da `trgfn_emittenti_fiscali_default_bootstrap`) è un emittente **reale con PK**, non un NULL. Residuo: confermare NOT NULL per tabella prima di ENABLE; per `ordini` (nuova colonna) backfill specific-or-default + NOT NULL. Caso NULL nei pgTAP solo come guard di non-regressione. |
| **R7** | **Report cross-EF tornano parziali** (totali sottostimati senza errore) | MEDIA | MEDIO-ALTO | `[DA VERIFICARE]` Cross-EF = azione di processo esplicita con autorizzazione (fn `SECURITY DEFINER` auditata), mai workaround di lettura (`feedback_lookup_skip_area_check`). |
| **R8** | **`zeroerp_app` unico ruolo applicativo** (admin+operatore stesso ruolo DB) | CERTA | MEDIO | `[VERIFICATO]` Enforcement 100% data-driven sul GUC, zero rete a livello ruolo. Formalizzare ruolo migrazione dedicato; valutare branch admin esplicito vs "whitelist vuota = globale". |
| **R9** | **ENABLE parziale per famiglia di join** (fatture sì, scadenze no → join incoerente) | BASSA | MEDIO | `[VERIFICATO]` ENABLE per famiglia di join atomica, non tabella isolata. |
| **R10** | **`fn_scope_ef_whitelist` STABLE rivalutata per riga** | BASSA | BASSO-MEDIO | `[VERIFICATO]` Vedi §7. Tabelle whitelist piccole; indici su colonne EF; verificare inlining. |

---

## 7. Performance e indici

`fn_scope_ef_whitelist` è `STABLE LANGUAGE sql` → valutata come predicato `USING` per riga. È un predicato **opaco/non sargable**: il planner non lo usa per index-scan diretto sulla colonna EF. L'indice serve quindi ai **filtri applicativi esistenti** (`WHERE emittente_fiscale_id = ANY(scope_pk)`) e alle list-view; la RLS opera come Filter residuo su un set già ridotto. Le tabelle interne (`user_emittenti_fiscali` unique 1:1, `emittenti_fiscali` poche decine) sono trascurabili.

### 7.1 Inventario indici EF `[VERIFICATO sui changeset]`

| Tabella | Colonna EF | Indice EF | Note |
|---|---|---|---|
| `vendite.fatture` | `emittente_soggetto_ruolo_id` | **SÌ** `ix_fatture_emittente_soggetto_ruolo_id` | `fk_index_policy.csv:292` |
| `vendite.fatture_scadenze` | `fattura_id` | **SÌ** `ix_fatture_scadenze_fattura_id` | `fk_index_policy.csv:306` |
| `vendite.preventivi` | `emittente_fiscale_id` | **SÌ** `ix_preventivi_emittente_fiscale_id` | `20260501-09-...:75` |
| `vendite.contratti` | `emittente_fiscale_id` | **NO esplicito** — atteso da FK-index policy | `20260526-02` (solo FK). Colonna recente: `[DA VERIFICARE SU DB]` che il job settimanale sia ciclato. |
| `vendite.offerte_commerciali` | `emittente_fiscale_id` | **NO esplicito** — atteso da policy | `20260524-03` |
| `documenti.documenti_generati` | `emittente_fiscale_id` | **NO esplicito** — atteso da policy | `20260429-56` |
| `pratiche.pratiche` | `emittente_fiscale_id` | **NO + NO auto** | `pratiche` NON è in `dbops.automation_scope` → indice non auto-generato. **GAP CERTO.** |
| `vendite.fatturazione_lotti` | `emittente_soggetto_ruolo_id` | `[DA VERIFICARE]` | coperto da FK-index policy se la FK esiste. |

### 7.2 Gap indici da colmare nel brief

1. **`pratiche.pratiche` — GAP CERTO:** `CREATE INDEX ix_pratiche_emittente_fiscale_id ON pratiche.pratiche(emittente_fiscale_id)` esplicito (o aggiungere `pratiche` ad `automation_scope`). Senza, la coda 3 livelli filtrata per EF fa seq-scan.
2. **`contratti`/`offerte`/`documenti_generati`:** NON affidarsi al job settimanale; aggiungere `CREATE INDEX IF NOT EXISTS` espliciti nel changeset del lotto 2 (come per `preventivi`). `[DA VERIFICARE SU DB]` se l'indice auto-generato esiste già sulle colonne recenti.
3. **`fatturazione_lotti`:** verificare FK+indice prima di includerla in ONDATA 1.

### 7.3 Benchmark obbligatori prima dell'ENABLE (DB con dati reali, ruolo NOBYPASSRLS + GUC OPERATORE+whitelist)

`EXPLAIN (ANALYZE, BUFFERS)` prima/dopo `ENABLE`:
1. lista fatture operatore (ONDATA 1) — atteso index-scan su `ix_fatture_emittente_soggetto_ruolo_id` + `fn_scope_ef_whitelist` come Filter; NON deve degenerare in seq-scan.
2. lista contratti/offerte/preventivi (ONDATA 2) con/senza indice EF.
3. coda pratiche per competenza (rischio certo: nessun indice).
4. write-path INSERT fatture/contratti con trigger guard (overhead atteso trascurabile).

**Soglia:** regressione di latenza ≤ **10%** sulle list-view operatore; nessuna transizione index→seq-scan per effetto RLS. Oltre soglia → indice EF obbligatorio prima dell'ENABLE.

---

## 8. Test pgTAP + smoke e2e

I test strutturali esistenti (`db/pgtap/rls/test-rls-policies-structure.sql`, 28 assert) coprono esistenza/cmd/permissive/USING ma NON il runtime (lo dichiarano a L16-18: serve ruolo non-BYPASSRLS). Servono nuovi file funzionali in `db/pgtap/rls/`, usando `SET LOCAL ROLE zeroerp_rls_test` + `set_config('app.*',...,true)` dentro `BEGIN/ROLLBACK`, con `ALTER TABLE ... ENABLE ROW LEVEL SECURITY` **dentro la transazione** (rollback → isolato).

### 8.1 `test-rls-fatture-ef-runtime.sql`
Fixture: EF_A/EF_B, op_whitelisted(EF_A), op_global(senza whitelist), fatture su entrambi. Casi:
1. operatore whitelist → vede solo EF_A; `count WHERE EF_B = 0`.
2. operatore whitelist-vuota → vede tutto (ramo `NOT EXISTS`, specchio test 5 della fn).
3. **connessione senza GUC → 0 righe (FAIL-CLOSED, comportamento atteso/voluto).**
4. ruolo presente ma `current_identita_id='' → NULL` → gate fn false → 0 righe.
5. ruolo non-OPERATORE (CLIENTE_PORTALE) con identità operatore → branch EF non passa, branch BA non trova ownership → 0 righe.
6. `SET LOCAL ROLE ..._bypass` (BYPASSRLS) → vede tutto (asserzione di consapevolezza).
7. identità inattiva (`attivo=false`) → 0 righe.
8. **caso NULL** (R6): fattura con `emittente_soggetto_ruolo_id IS NULL` + operatore whitelist → asserire la semantica decisa.

### 8.2 `test-rls-operatore-no-branch.sql` (guard negativo)
Per `ordini`/`fatture_scadenze`/`billing_account`/`acquisti.*` senza branch OPERATORE: con ENABLE + ruolo=OPERATORE → `count=0`. Documenta il danno dell'attivazione big-bang; cambia segno intenzionalmente se in futuro si aggiunge il branch.

### 8.3 `test-rls-vista-security-invoker.sql` (regressione C2/R1)
Su una `vw_*` che legge `vendite.fatture`, RLS attiva + GUC operatore-whitelist: se la vista è definer, asserire `count = tutte` (RLS bypassata) → **assert che FALLISCE finché la vista non passa a `security_invoker=on`**, poi va in verde con count filtrato. Trasforma il bug C2 in un cancello CI.

### 8.4 Smoke e2e (bash idempotente, `feedback_smoke_test_idempotenti`)
1. **Cleanup proattivo** (operatore smoke, riga whitelist, fatture-fixture con suffisso unico).
2. Seed: 2 EF, 1 operatore whitelist EF_A, ≥1 fattura per EF.
3. Login via endpoint JWT reale → token → percorso reale `set_jwt_gucs`.
4. GET lista fatture → assert: solo EF_A, zero EF_B.
5. **Diagnosi categoria** (cambia il destinatario del fix):
   - lista vuota → GUC non propagati (R-GUC) o ruolo BYPASSRLS sul lato sbagliato;
   - lista completa (anche EF_B) → vista definer (C2) **o** RLS non attiva **o** `zeroerp_app` BYPASSRLS (R2);
   - lista filtrata → verde.
6. Controprova whitelist-vuota → vede entrambe (fail-open).

> Lo smoke va eseguito SOLO dopo che R-GUC è risolto: una connessione singola maschera il leak cross-request, visibile solo sotto pool concorrente. Lo smoke deve testare ANCHE "non vede troppo" via ogni vista e dopo riciclo connessione, non solo i lockout.

---

## 9. Kill-switch e rollback

- **Kill-switch = `ALTER TABLE <schema>.<tabella> DISABLE ROW LEVEL SECURITY`**, per-tabella. Le policy restano in `pg_policies` (dormienti), ritorno immediato al comportamento pre-attivazione, senza DROP. DDL con `ACCESS EXCLUSIVE` lock brevissimo: safe e immediato. Consegnare un changeset `DISABLE` gemello pronto per OGNI tabella attivata.
- **NON usare `DROP POLICY` come rollback:** distrugge l'oggetto verificato dai test strutturali. `DISABLE` è reversibile con `ENABLE` simmetrico.
- **`FORCE` fuori scope** in questa fase (vedi §5.3).
- **Ordine di roll-out (tabella per tabella, NON big-bang):**
  - **Fase 0 (nessun ENABLE):** R-GUC risolto; C4/R2 verificato (`zeroerp_app` NOBYPASSRLS); `security_invoker=on` sulle `vw_` operatore su `vendite.fatture`; nuove fn create.
  - **Fase 1:** ENABLE su famiglia fatture (`fatture` + `fatture_scadenze` + `fatturazione_lotti`). Smoke + pgTAP funzionali verdi. Kill-switch armato.
  - **Fase 2** `[DECISIONE TID]`: ONDATA 2 PK (preventivi/contratti/offerte/documenti/pratiche) dopo `fn_scope_ef_whitelist_pk` + indici + trigger PK. Una tabella/famiglia per volta.
  - Criterio di promozione: pgTAP funzionale verde + smoke verde + finestra in cui gli operatori reali non riportano "vedo zero / vedo troppo".

---

## 10. Checklist operativa

**Prerequisiti bloccanti (Fase 0):**

- [ ] `[DA VERIFICARE SU DB]` `rolbypassrls` reale di `zeroerp_app` (atteso NOBYPASSRLS — evidenza committata favorevole, vedi C4); `ALTER ROLE ... NOBYPASSRLS` solo se la verifica live smentisce.
- [ ] `[DA VERIFICARE SU DB]` introspezione `reloptions`/owner/`pg_depend` delle `vw_`/matview su tabelle del lotto.
- [ ] Changeset `security_invoker=on` su tutte le `vw_` operatore interessate; decisione matview.
- [ ] **R-GUC ✅ deciso (§11.1):** reset GUC all'inizio richiesta (`process_request`), scrittura **incondizionata** dei 5 GUC (anonimo → vuoto), **fail-closed** se la scrittura fallisce. Spostare/duplicare il reset oggi su `process_response`. Tocca BE. Test: riciclo connessione sotto pool concorrente. Da fare PRIMA di ogni `ENABLE`.
- [ ] Ruoli pgTAP `zeroerp_rls_test` (NOBYPASSRLS) + `zeroerp_rls_test_bypass` (BYPASSRLS).
- [ ] **Migrazioni ✅ chiarito (§11.8):** girano come **`titodb`** (`scripts/liquibase5.sh`), non `postgres`. `[DA VERIFICARE SU DB]` che `titodb` sia superuser/BYPASSRLS (atteso). Niente nuovo ruolo da creare. Valutare rimozione di `db/liquibase-mirror.properties` (env di test obsoleto).

**Fn e policy:**
- [ ] `script.fn_scope_ef_whitelist_pk` creata + pgTAP (incl. whitelist-vuota e NULL).
- [ ] `script.fn_scope_ef_whitelist_via_fattura` creata + pgTAP.
- [ ] Branch SUPER_ADMIN aggiunto a `rls_fatture_ef_whitelist` e a tutte le nuove policy EF (C7/R3).
- [ ] Branch policy OPERATORE/EF su scadenze/preventivi/contratti/offerte/documenti_generati/pratiche.

**Write-side:**
- [ ] Ramo `mode='emittente_pk'` aggiunto a `script.trgfn_guard_emittente_scope`.
- [ ] Trigger guard attaccato a contratti/offerte/preventivi/documenti_generati/pratiche (PK) + scadenze (fattura).
- [ ] `[DA VERIFICARE SU DB]` `dbops.fn_apply_chiusura_scadenze`: SECURITY DEFINER owner-bypass se tocca tabelle RLS.

**Performance:**
- [ ] `CREATE INDEX ix_pratiche_emittente_fiscale_id` (gap certo).
- [ ] `CREATE INDEX IF NOT EXISTS` su contratti/offerte/documenti_generati (EF PK).
- [ ] `[DA VERIFICARE SU DB]` FK+indice su `fatturazione_lotti`.
- [ ] Benchmark EXPLAIN ANALYZE list (fatture/contratti/offerte/preventivi/pratiche) + write-path; soglia ≤10%, no index→seq-scan.

**Test e attivazione:**
- [ ] `test-rls-fatture-ef-runtime.sql` (8 casi incl. NULL e riciclo).
- [ ] `test-rls-operatore-no-branch.sql` (guard negativo).
- [ ] `test-rls-vista-security-invoker.sql` (regressione C2).
- [ ] Smoke e2e idempotente (cleanup proattivo + diagnosi categoria).
- [ ] Changeset ENABLE Fase 1 (famiglia fatture) + kill-switch `DISABLE` gemello.
- [ ] Verifica operatori reali nessun "vedo zero / vedo troppo".

**Decisioni di modello (gate ulteriori):**

- [ ] **`vendite.ordini` ✅ deciso (§11.4):** aggiungere colonna `emittente_fiscale_id` (PK snapshot) + backfill + NOT NULL a regime + indice FK + trigger guard write (`mode='emittente_pk'`) + policy RLS PK. Entra in Ondata 2.
- [ ] `[DECISIONE TID]` `pratiche.pratiche` dentro/fuori ONDATA 2.
- [ ] **Tabelle non-fatture ✅ deciso (§11.7):** `ordini`+`fatture_scadenze` rientrano (legate a fatture); `billing_account` rientra via scope efba (`fn_check_ba_visible_for_emittenti` ∩ whitelist operatore, famiglia distinta); `acquisti.*` rinviato a sviluppo futuro (non bloccante).

---

## 11. Questioni aperte / decisioni per Tid

1. **R-GUC (priorità massima, bug modello) — ✅ DECISO 2026-06-01.** GUC session-scoped + `CONN_MAX_AGE=600` = leak di scope cross-request quando la RLS morde.
   - **Decisione (Tid):** pulizia per-richiesta come meccanismo primario, ma **all'inizio della richiesta, incondizionata, fail-closed**. Tre proprietà:
     1. **Reset all'INIZIO** (`process_request`), non alla fine: lavagna pulita prima che qualsiasi query della nuova richiesta giri, indipendentemente da com'è finita la precedente.
     2. **Scrittura incondizionata dei 5 GUC** su OGNI richiesta: autenticata → valori reali (già fatto in `set_jwt_gucs`); anonima/fallita → stringa vuota. Oggi le richieste anonime NON toccano i GUC → ereditano: questo è il buco da chiudere.
     3. **Fail-closed sul fallimento:** se la scrittura dei GUC fallisce (`DatabaseError`), la richiesta si **interrompe** (non si serve). Caso peggiore = "operatore non vede niente", mai "vede troppo".
   - **Scartato — transaction-local** (`set_config(...,true)`): teoricamente superiore (è PostgreSQL a scartare il GUC a fine transazione), ma a `authenticate()`-time la view non ha ancora aperto la sua transazione → un `SET LOCAL` evaporerebbe prima delle query ([jwt_audit_authentication.py:163-169](/../../../backend/apps/core/api/jwt_audit_authentication.py)). Richiederebbe `ATOMIC_REQUESTS=True` globale: cambio architetturale pesante, NON giustificato come prerequisito RLS-EF.
   - **Stato attuale da correggere:** il reset esiste ma è su `process_response` (fine richiesta) ed è best-effort ([jwt_audit_middleware.py:120-142](/../../../backend/apps/core/middleware/jwt_audit_middleware.py)); se `process_response` non gira (eccezione a valle/crash/ritorno al pool) il leak sopravvive. Il commento `CONN_MAX_AGE=0 di default` in `jwt_audit_authentication.py:169` è un'assunzione **già falsa** (`settings.py:216` → default `600`).
   - **Impatto:** backend puro (ritocco middleware: spostare/duplicare il reset su `process_request` + scrittura incondizionata + abort se fallisce). NON tocca il DB. Si implementa e si testa (riciclo connessione sotto pool concorrente) **prima** di qualsiasi `ENABLE`. **Resta bloccante per l'attivazione RLS**, ma la soluzione è chiusa.
2. **C7/R3 (bug modello):** unificare le TRE codifiche divergenti della stessa regola scope (write-guard `fn_check_user_emittente_scope`, RLS-read `fn_scope_ef_whitelist`, wrapper Python `fn_get_emittenti_scope_pk_ids`) a una fn canonica, incluso il bypass SUPER_ADMIN, oggi assente nella policy EF.
3. **Doppia convenzione colonna EF (SR vs PK) — ✅ RISOLTO dalla decisione 2 (§5.4).** Non è una decisione separata: la canonica `fn_emittente_in_scope` (keyed PK) + i due adapter sottili (`fn_scope_ef_whitelist` SR→PK e `fn_scope_ef_whitelist_pk` PK) gestiscono entrambe le convenzioni. `fn_scope_ef_whitelist_pk` è creata subito (§5.4.4 passo 3), simmetria piena (`feedback_simmetria_modello_no_meta_scope`), niente rinvio.
4. **`vendite.ordini` senza colonna emittente — ✅ DECISO 2026-06-01:** si **aggiunge `emittente_fiscale_id`** (convenzione PK, snapshot, coerente con preventivi/contratti/offerte), così `ordini` rientra nello scope EF degli operatori. Brief DB: nuova colonna `vendite.ordini.emittente_fiscale_id` (NOT NULL a regime, default/backfill da decidere in fase brief — `[DA VERIFICARE SU DB]` sorgente del valore: testata documento / emittente del contratto/cliente), indice FK, trigger guard write (`mode='emittente_pk'`), policy RLS PK (adapter §5.4), index EF (§7). Passa da "NO — bloccato" a candidata **Ondata 2** (richiede `fn_scope_ef_whitelist_pk`).
5. **Semantica `emittente_*_id NULL` — ✅ CHIARITO 2026-06-01 (non-problema).** Il modello ha un **default-emittente** vivo (non solo doc): `emittenti_fiscali_billing_account` con `is_default=true` + `billing_account_id=NULL`, **auto-creato al primo emittente** da `trgfn_emittenti_fiscali_default_bootstrap` (changeset `20260123-03`), protetto da `trgfn_emittenti_fiscali_default_guard` + CHECK. È il pattern "gestore globale" (`feedback_gestore_globale_lookup`).
   - **Punto chiave:** il default opera a livello di **risoluzione** (BA→quale emittente emette), NON come NULL sulle righe documento. Sui documenti l'emittente risolto (specifico o default) è **materializzato come FK NOT NULL** (`documenti_generati`/`preventivi`/`contratti`/`offerte` NOT NULL verificato; `fatture` da riconfermare). Quindi **non esistono righe con emittente NULL** → niente special-casing NULL nelle policy: il default è un emittente reale con PK, soggetto a whitelist come gli altri.
   - **Unico NULL legittimo:** la mappatura `efba.billing_account_id = NULL` (riga di default) — risoluzione BA→emittente, NON scope RLS sulle righe.
   - **Azione residua:** confermare NOT NULL per ogni tabella prima di `ENABLE`; per `vendite.ordini` (colonna nuova, §11.4) backfill **specific-or-default** poi `SET NOT NULL`, come preventivi/contratti.
6. **Comportamento senza-GUC = FAIL-CLOSED (0 righe) — ✅ DECISO 2026-06-01.** "Mancano le info di identità" = i GUC sulla connessione sono vuoti: o per assenza di login valido, o perché `set_jwt_gucs` ha trovato l'identità non attiva (`identita_digitali`: `attivo=false` / fuori finestra `valido_dal..valido_al`) e ha lasciato i GUC vuoti + 401. In quel caso l'operatore vede **0 righe**.
   - **Confermato corretto** e reso esplicito nei pgTAP/smoke (§8.1 casi 3-4).
   - **"Vedere tutto" per i contesti di sistema** (job batch, migrazioni, report interni) NON si ottiene con fail-open, ma con **ruolo tecnico `BYPASSRLS`** (esplicito, auditabile) o ramo batch-NULL della canonica. Rilassare il cancello operatore a fail-open trasformerebbe un GUC mancante per *bug* (leak §11.1, endpoint che dimentica l'auth) in "vede tutto" silenzioso — l'opposto dell'obiettivo.
   - **Promemoria modello:** `anagrafiche.identita_digitali` è la **sorgente di verità** dell'identità (chi sei, veste, attivo, finestra); i GUC sono la sua **proiezione di sessione** letta dalla policy per riga (performance). La tabella viene letta a ogni auth da `set_jwt_gucs` + da `fn_has_identita_attiva`/resolver.
7. **Branch OPERATORE sulle tabelle non-fatture — ✅ DECISO 2026-06-01.**
   - **`vendite.ordini` e `vendite.fatture_scadenze`: RIENTRANO** (legate alle fatture). `fatture_scadenze` in Ondata 1 via `fn_scope_ef_whitelist_via_fattura` (§5.2.3); `ordini` in Ondata 2 con la colonna `emittente_fiscale_id` aggiunta (§11.4) → adapter PK.
   - **`anagrafiche.billing_account`: RIENTRA**, ma con scope **derivato dalla mappatura efba**, non da una colonna emittente sul BA. La regola: un operatore vede un BA se l'emittente del BA — risolto via `emittenti_fiscali_billing_account` con fallback `is_default` (specifico-o-default) — è nella sua whitelist EF. **Esiste già** `script.fn_check_ba_visible_for_emittenti(ba_id, emittenti_sr[])` (logica a 3 livelli: mapping specifico → fallback default → non visibile), già usata da `fn_search_soggetti_universale`/`fn_get_search_detail`. La policy OPERATORE su `billing_account` si costruisce su quella, intersecata con `fn_get_emittenti_scope_sr_ids(current_user_id)`. È una **famiglia di scope distinta** (BA-visibility-via-efba) da progettare nel lotto; allinea la RLS al filtro già applicato lato ricerca.
   - **`acquisti.*` (ordini/ddt): RIENTRERÀ in futuro**, fuori dal primo lotto. Oggi il dominio acquisti non porta identità emittente (ciclo passivo/fornitore) e il modulo è ancora da sviluppare; lo scope acquisti si definirà quando il dominio sarà costruito (potrà essere EF se si denormalizza un emittente, o uno scope diverso). **Non bloccante** per la RLS-EF operatori.
8. **Identità di migrazione — ✅ CHIARITO 2026-06-01.** Esiste già una separazione netta di ruoli, lo spirito del punto è soddisfatto:
   - **Migrazioni**: girano come **`titodb`** (utente dedicato) via `scripts/liquibase5.sh update` + `liquibase.properties` locale (non committato). **NON** `postgres`. L'assunzione "migrazioni come `postgres`" dell'analisi derivava da `db/liquibase-mirror.properties` (`username=postgres`), che è un **ambiente di test obsoleto/sbagliato** → da ignorare/rimuovere.
   - **Runtime app**: gira come **`zeroerp_app`** (`backend/.env` → `DB_USER`), creato `LOGIN` senza `BYPASSRLS` → **NOBYPASSRLS** di default → la RLS morde. `[DA VERIFICARE SU DB]` solo l'attributo runtime effettivo (provisioning fuori Liquibase).
   - **Azione residua:** confermare che `titodb` sia superuser o `BYPASSRLS` (così le migrazioni e i changeset `ENABLE` sono esenti dalla RLS in modo deterministico) — quasi certo essendo l'utente che crea schemi/ruoli `[DA VERIFICARE SU DB]`. Niente nuovo ruolo `zeroerp_migration` da creare: `titodb` è già l'identità di migrazione dedicata. Valutare la rimozione di `liquibase-mirror.properties` per non indurre in errore future analisi.

> **Nota di processo:** ogni azione DDL/policy/ENABLE/`ALTER ROLE` di questo brief va eseguita dal team DB su `dev/db-tid`. Il backend agent si limita a (a) write-side trigger via brief, (b) risoluzione R-GUC lato Python, (c) test pgTAP/smoke, (d) cablaggio scope read-side dove ancora applicativo. Nessuna esecuzione DB da parte del backend agent.
