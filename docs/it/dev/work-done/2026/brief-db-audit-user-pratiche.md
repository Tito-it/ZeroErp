# Brief DB — Audit utente reale su `pratiche.*`: schema fuori da `automation_scope`

> **Tipo documento**: brief operativo **per il team DB** (canale `dev/db-tid`).
> **Priorità**: 🟠 ALTA — bug di audit/tracciabilità: ogni scrittura su `pratiche.*`
> è attribuita a `zeroerp_app` (ruolo di connessione) invece che all'operatore reale.
> **Data**: 2026-06-18 (chiuso 2026-06-19) · **Stato**: ✅ **COMPLETATO** — applicato e
> verificato live (l'attribuzione utente reale su `pratiche.*`, giornale incluso, ora funziona).
>
> **Esito**: **Part A** — `pratiche,*all` aggiunto a `dbops.automation_scope`
> (`automation_scope.csv` riga 12). **Part B** — risolta in forma **conforme al framework**
> (anziché il default-change GUC proposto qui): migration `20260618-04` aggiunge le colonne
> standard `data_update`/`user_update` alle 5 tabelle append-only (`giornale`,
> `allegati_pratiche`, `allegati_flussi`, `template_flussi_prerequisiti`,
> `template_flussi_canali`), così l'automation `AUDIT_UPDATE` le copre da sola (trigger
> `trg_giornale_audit_data_user_upd` → `script.trgfn_audit_data_user_generic`, presente in
> doc autogen). Nessun trigger custom. Confermato live: il giornale registra l'operatore reale
> dalla GUC `app.jwt_user`.

---

## 1. Sintomo

Su tutte le tabelle `pratiche.*` (incluso il **giornale**) `user_insert`/`user_update`
registrano **sempre `zeroerp_app`**, non l'operatore reale. Es.:
`FLUSSO_STATO_CAMBIATO` loggato con `user_insert = zeroerp_app`.

**Controprova**: `anagrafiche.soggetti` (e vendite, catalogo, ecc.) registrano
**correttamente l'utente reale**. La GUC `app.jwt_user` è quindi popolata e leggibile
durante le scritture (lo prova soggetti). Il problema è **isolato allo schema `pratiche`**.

## 2. Causa radice — `pratiche` non è in `dbops.automation_scope`

L'audit utente NON è cablato tabella-per-tabella: è un'**automation `dbops`**. La regola
è universale — `dbops.automation_rules` riga `id=2`: `rule_type=AUDIT_UPDATE`,
`target_schema=*all`, `target_table=*all`, `name_template=trg_{table}_audit_data_user_upd`,
`params={audit_ts: data_update, audit_user: user_update}`.

…ma `dbops.fn_run_automations_audit_update` scansiona **solo le tabelle degli schemi
in scope**, risolti da `fn_resolve_scope`/`fn_table_in_scope` sulla tabella
**`dbops.automation_scope`** (`80_data/sql/dbops/automation_scope.csv`):

```text
anagrafiche, catalogo, config, storico, vendite, acquisti,
contabilita, magazzino, pagamenti, documenti, dbops(sessioni_utente)
```

**`pratiche` NON è presente.** → nessuna tabella `pratiche.*` riceve il trigger
`script.trgfn_audit_data_user_generic` → `user_insert`/`user_update` restano sul
**default di colonna `CURRENT_USER`** = `zeroerp_app`. Omissione risalente alla nascita
dello schema `pratiche` (2026-03), successiva alla definizione dello scope.

> NB: l'esclusione vale per **tutte** le automation (non solo audit): `pratiche` non
> riceve nemmeno tx_id / attivo / storico / lock_columns / delete_block. Valutare se
> portarlo pienamente in scope è coerente (come ogni altro schema di dominio) o se
> serve un perimetro mirato — vedi §4 e §5.

## 3. Fix — Parte A: aggiungere `pratiche` allo scope

Aggiungere la riga a `dbops.automation_scope`:

```text
pratiche,*all
```

(via il loader CSV `80_data/sql/dbops/automation_scope.csv` + relativo changeset
`loadUpdateData`, coerente con le altre righe), **poi re-eseguire le automation** sul
DB. L'automation AUDIT è idempotente (`existence_strategy=BOTH`: salta se il trigger
esiste già) e gated per regola → ri-eseguibile in sicurezza.

Effetto: le tabelle `pratiche` con **`data_update` + `user_update`** ricevono
`script.trgfn_audit_data_user_generic` (BEFORE INSERT OR UPDATE) → `user_insert` (su
INSERT) e `user_update` (su UPDATE) dalla GUC `app.jwt_user`. Tabelle coperte:
`pratiche`, `flussi`, `note_pratiche`, `note_flussi`, `sospensioni`,
`pratiche_sorgenti`, `calcoli_tempo`, `tipi_prestazione`, `handler_flussi`,
`template_flussi`, `regole_generazione`, `formule_tempo`, `azioni_ui`.

> **⚠️ Dry-run prima.** Portare `pratiche` in scope attiva **tutte** le automation su
> di esso. Eseguire prima in **dry-run** (`p_dry_run = true`) e ispezionare cosa
> verrebbe creato (audit/tx_id/attivo/storico/lock_columns/delete_block) per evitare
> sorprese (es. storicizzazione indesiderata). Lo `storico_provision` agisce solo sulle
> tabelle col flag `storicizza`; `attivo`/`delete_block` solo dove pertinenti. Se si
> vuole **solo** l'audit in prima battuta, eseguire mirato `fn_run_automations_audit_update`
> dopo aver aggiunto lo scope (senza lanciare le altre), poi valutare le restanti.

## 4. Fix — Parte B: giornale e tabelle append-only (solo `user_insert`)

`giornale`, `allegati_pratiche`, `allegati_flussi`, `template_flussi_prerequisiti`,
`template_flussi_canali` hanno **solo `user_insert`** (no `data_update`/`user_update`,
sono append-only/immutabili). L'automation AUDIT le **salta** (gate su esistenza di
`user_update`). Per queste, fix col **default di colonna** GUC-aware:

```sql
ALTER TABLE pratiche.giornale
  ALTER COLUMN user_insert
  SET DEFAULT COALESCE(NULLIF(current_setting('app.jwt_user', true), ''), CURRENT_USER);
-- idem: allegati_pratiche, allegati_flussi, template_flussi_prerequisiti, template_flussi_canali
```

Le righe del **giornale** sono inserite dai trigger `trgfn_*_giornale_*` **senza**
elencare `user_insert` → si applica il nuovo default → legge `app.jwt_user`. **Nessuna
modifica ai trigger del giornale.** (Per l'INSERT il default basta; non c'è path UPDATE
su tabelle immutabili.)

> Alternativa a B: una variante insert-only di `trgfn_audit_data_user_generic` (solo
> `user_insert`) come regola/automation dedicata. Il default-change è però sufficiente
> e meno invasivo per tabelle append-only.

## 5. Backfill

Righe storiche restano `zeroerp_app` (dbdev rigenerabile, no produzione). Verificare con
**pratiche/flussi NUOVI** dopo l'applicazione. Eventuale backfill = UPDATE mirato fuori
scope.

## 6. Criterio di accettazione

- Nuova pratica/flusso/nota + cambio stato flusso da operatore loggato →
  `user_insert` (e `user_update` sulle tabelle del gruppo A) = **username reale**
  (GUC `app.jwt_user`), non `zeroerp_app`.
- Giornale (`FLUSSO_STATO_CAMBIATO`, ecc.) → `user_insert` = utente reale.
- Sessione senza GUC (batch/job) → fallback `CURRENT_USER` (invariato, fail-safe).
- pgTAP: con `set_config('app.jwt_user','mario.rossi',false)` un INSERT su
  `pratiche.flussi` e su `pratiche.giornale` → `user_insert='mario.rossi'`; senza GUC →
  `user_insert=current_user`. Trigger audit presente sulle tabelle del gruppo A dopo il
  re-run delle automation.

## 7. Note

- GUC `app.jwt_user`: propagata da `apps.core.api.jwt_audit_authentication.set_jwt_gucs`
  (session-scoped, reset a inizio richiesta dal `JwtAuditMiddleware`). **Nessun
  intervento BE necessario**: già funzionante (provato da `anagrafiche.soggetti`).
- Dopo il fix, lo schema `pratiche` si allinea al pattern di audit/automation degli
  altri schemi di dominio.
