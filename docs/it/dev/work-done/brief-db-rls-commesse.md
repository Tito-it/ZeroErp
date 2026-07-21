# Brief DB — RLS scope emittente su `vendite.commesse` + `vendite.commesse_attivita`

> **Tipo**: brief operativo per il **team DB** · **Target**: `dev/db-tid` · **Data**: 2026-07-20
> · **Owner**: Tid · **Stato**: 🟢 **P1–P4 APPLICATI + pgTAP VERDI + COMMITTATI (2026-07-20)**
> su `dev/db-tid` (§4). **Restano gate BE** prima della **release Fase C**: **G-1**
> (probe-first su N5/N7/sblocco — no-op silenzioso vs 404) e **G-2** (WITH CHECK push da
> operatore). Sono verifiche/smoke lato BE, non bloccano la correttezza DB già testata.
>
> **Origine**: punto **P-6** di
> [brief-be-fe-processi-fatturazione.md](brief-be-fe-processi-fatturazione.md) §3
> (revisione critica 2026-07-20, finding CONFERMATO). Completa l'ondata RLS operatori:
> [analisi-attivazione-rls-operatori.md](../work-done/analisi-attivazione-rls-operatori.md)
> classificava `vendite.commesse` «NO in prima battuta» segnalando già l'asimmetria
> lettura/scrittura (§ tabelle escluse).
>
> **Sintesi**: le **scritture** sulla famiglia commesse sono raggiungibili **cross-emittente**:
> `POST /commesse/<id>/attivita/approva/` (nuovo, Fase A), `POST /commesse/<id>/stato/` e i
> tre endpoint prezzi N5/N7/sblocco (pre-esistenti) verificano solo l'esistenza della
> commessa; le fn DB (`fn_approva_commessa_attivita`, `fn_cambia_stato_commessa`,
> `fn_riallinea_prezzo`, …) non hanno guard emittente; le tabelle non hanno RLS. Un operatore
> con il permesso azione ma scope emittente X può scrivere su commesse dell'emittente Y
> passando l'id. La soluzione è la stessa della famiglia fatture: **policy EF_WHITELIST +
> ENABLE RLS**, nessuna toppa applicativa per-endpoint (le difese applicative restano
> defense-in-depth dove già esistono, es. scope in-vista di `vw_dash_competenza_attivita`).

---

## 1. Perché ora (contesto in tre righe)

Il cockpit (Fasi A+B committate) ha dato alle commesse la prima superficie di **scrittura
in app** (approvazione, stato, prezzi). Con la Fase C la dashboard diventerà il punto dove
si lancia anche il giro di fatturazione: chiudere il buco **prima** della release C evita
di rilasciare un cockpit che permette scritture fuori scope. Le letture si sistemano
gratis nello stesso colpo (oggi anche `fn_get_commessa_stato`/`fn_list_commessa_attivita`
sono unscoped: qualsiasi id è leggibile).

## 2. Modello (mirror della famiglia fatture — nessuna invenzione)

| Tabella | Colonna scope | Policy | Adapter |
| --- | --- | --- | --- |
| `vendite.commesse` | `emittente_soggetto_ruolo_id` (bigint, **nullable**, FK `fk_commesse_emittente`) | `rls_commesse_ef_whitelist` — PERMISSIVE **FOR ALL**, USING + WITH CHECK, gate `app.ruolo_applicativo = 'OPERATORE'` | **`script.fn_scope_ef_whitelist_via_sr(auth_user_id, emittente_soggetto_ruolo_id)`** (esistente — stessa policy di `vendite.fatture`, migration `20260601-08`) |
| `vendite.commesse_attivita` | nessuna colonna emittente (satellite: `commessa_id` NOT NULL) | `rls_commesse_attivita_ef_whitelist` — PERMISSIVE FOR ALL, USING + WITH CHECK via padre | **nuovo adapter `script.fn_scope_ef_whitelist_via_commessa(p_auth_user_id integer, p_commessa_id bigint)`** — mirror di `fn_scope_ef_whitelist_via_fattura` (usato da `fatture_scadenze`): risolve `commessa_id → emittente_soggetto_ruolo_id` e delega a `fn_scope_ef_whitelist_via_sr`. STABLE, sql, nessuna logica whitelist duplicata |

Note di modello:

* **`emittente_soggetto_ruolo_id` NULL** (commesse legacy/pre-lane): l'adapter SR è già
  **fail-closed** per costruzione — SR NULL → canonica con EF NULL → `false` se la
  whitelist dell'operatore è valorizzata, `true` per admin globale/super admin. Semantica
  risultante: commessa senza emittente visibile/scrivibile **solo** ad admin globale.
  È il comportamento voluto (chi ha uno scope non deve toccare ciò che non è attribuito).
* **NO FORCE** (parità famiglia: `relrowsecurity=t`, `relforcerowsecurity=f`): l'owner
  `zeroerp_app` bypassa finché non arriva l'ondata FORCE coordinata; il canale batch
  (`system_process_context`, ruolo BYPASSRLS) resta esente per costruzione.
* **Nessuna colonna denormalizzata** su `commesse_attivita`: la policy passa dal padre
  (stesso pattern `fatture_scadenze`; una riga attività non cambia mai commessa).

## 3. Impatti sul software esistente (verificati, nessuna modifica BE richiesta)

* **Web (operatore)**: le fn commesse sono SECURITY INVOKER e i repository girano sulla
  connessione request con i GUC popolati → con la policy attiva le letture filtrano da
  sole e le scritture fuori scope muoiono nell'UPDATE (0 righe). Il probe di esistenza
  del service (`get_commessa_stato_codice is None → 404 E_COMMESSA_NOT_FOUND`) produce
  automaticamente il **404 identico all'inesistente** per gli id fuori scope — stessa UX
  della famiglia fatture, nessun leak.
* **Push orchestrator da endpoint** (`POST /commesse/push/run/`, contesto operatore):
  INSERT/UPDATE di commesse derivano da documenti sorgente già scoped → il WITH CHECK
  passa per costruzione. Da smoke-testare comunque (vedi §5).
* **Batch/cron** (`run_fatturazione_batch`, pull AF): canale sistema BYPASSRLS → nessun
  impatto.
* **`vw_dash_competenza_*`**: già scope in-vista; con RLS si somma (defense-in-depth),
  nessuna doppia esclusione anomala (stesso predicato whitelist).

## 4. Changeset richiesti (naming per data, un changeSet per file) — **SCRITTI**

1. **P1** [`20_code/script/20260720-04-create-fn-scope-ef-whitelist-via-commessa-mctit.yaml`](../../../../db/changelog/migrations_v2/20_code/script/20260720-04-create-fn-scope-ef-whitelist-via-commessa-mctit.yaml)
   — adapter `fn_scope_ef_whitelist_via_commessa(integer, vendite.commesse.id%TYPE)`, mirror
   `via_fattura`, `runOnChange`. `p_auth_user_id` resta `integer` (ref `django.*` → no `%TYPE`).
2. **P2** [`00_schema/vendite/20260720-05-enable-rls-commesse-ef-whitelist-mctit.yaml`](../../../../db/changelog/migrations_v2/00_schema/vendite/20260720-05-enable-rls-commesse-ef-whitelist-mctit.yaml)
   — policy `rls_commesse_ef_whitelist` (via_sr su `emittente_soggetto_ruolo_id`) + `ENABLE`
   (NO FORCE). Mirror esatto `20260713-17-enable-rls-resi-ef-whitelist` (preconditions
   colonna+fn, DROP POLICY IF EXISTS, COMMENT, rollback disable+drop).
3. **P3** [`00_schema/vendite/20260720-06-enable-rls-commesse-attivita-ef-whitelist-mctit.yaml`](../../../../db/changelog/migrations_v2/00_schema/vendite/20260720-06-enable-rls-commesse-attivita-ef-whitelist-mctit.yaml)
   — policy `rls_commesse_attivita_ef_whitelist` via padre (`via_commessa` su `commessa_id`)
   con `ENABLE` (NO FORCE). **Applicare dopo P1** (dipende dall'adapter).
4. **P4 (pgTAP)** [`db/pgtap/rls/test-rls-commesse-ef-whitelist-write.sql`](../../../../db/pgtap/rls/test-rls-commesse-ef-whitelist-write.sql)
   — `plan(5)`, ENABLE+FORCE locale alla tx su fixture da dati esistenti (commessa in-scope +
   2 operatori): in-scope/off-scope/no-ruolo su `commesse` + scope-via-padre su
   `commesse_attivita`. Soft-skip se fixture non costruibile.

## 5. Verifica attesa + pgTAP

```sql
-- policy attive, RLS abilitata non forzata (parità famiglia)
SELECT c.relname, c.relrowsecurity, c.relforcerowsecurity
FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname='vendite' AND c.relname IN ('commesse','commesse_attivita');
-- atteso: entrambe t / f

SELECT polname, polcmd FROM pg_policy
WHERE polrelid IN ('vendite.commesse'::regclass, 'vendite.commesse_attivita'::regclass);
-- atteso: rls_commesse_ef_whitelist (*), rls_commesse_attivita_ef_whitelist (*)
```

pgTAP: `db/pgtap/rls/test-rls-commesse-ef-whitelist-write.sql` (ENABLE+FORCE locale alla tx,
fixture da dati esistenti): operatore in scope scrive; fuori scope UPDATE morto (0 righe);
no-ruolo 0 righe (fail-closed); `commesse_attivita` segue il padre. ✅ **`plan(5)` verde
(2026-07-20)**.

> **Nota di implementazione**: l'adapter satellite è `fn_scope_ef_whitelist_via_commessa`
> ([manuale](/dbzero/script/funzioni/fn_scope_ef_whitelist_via_commessa)); `p_auth_user_id`
> resta `integer` (ref `django.*` → no `%TYPE`, [[feedback_django_refs_in_liquibase]]),
> `p_commessa_id` usa `vendite.commesse.id%TYPE`.

Smoke applicativo post-apply (lato BE, lo faccio io): approva/stato/prezzi su commessa in
scope OK, su commessa fuori scope → 404; `POST /commesse/push/run/` da operatore genera
commesse normalmente.

## 6. Fuori scope

* FORCE ROW LEVEL SECURITY (ondata coordinata separata, tutta la famiglia).
* `commesse_push_log` e tabelle diagnostiche (nessuna superficie operatore).
* Guard applicativi per-endpoint lato BE: **non si fanno** (sarebbero il quick-fix
  asimmetrico che si è scelto di evitare; la difesa è la RLS).

*Le azioni DB non le esegue l'agent ([[feedback_db_actions_passaggio_team]]): questo brief
passa al team DB su `dev/db-tid`.*
