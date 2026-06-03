# Brief DB — Completare la RLS per la faccia OPERATORE (ERP classico)

> **✅ CHIUSO (team DB, `dev/db-tid`, 2026-06-03)** — migration `20260603-16..25`
> applicate, pgTAP verdi, documentazione allineata. Dettaglio in
> [§ RISOLTO](#risolto-team-db-2026-06-03). Documento spostato in `work-done`.
>
> **Per**: team DB (`dev/db-tid`). **Da**: BE/FE agent (`dev/backend-tid`), 2026-06-03.
> **Severità**: ALTA — bloccava ogni scrittura del ciclo attivo per l'operatore.
> Azione DB (DDL/policy) — il BE NON esegue, passa il brief
> (`feedback_db_actions_passaggio_team`). Bug logico di modello chiuso
> proattivamente (`feedback_bug_logici_modello`).

## Sintomo

Alla **creazione/modifica** di qualsiasi documento del ciclo attivo (operatore,
ERP classico, NON portale/shop):

```text
"new row violates row-level security policy for table \"<tabella>\""
```

Riprodotto su **preventivi, offerte commerciali, ordini** (stesso errore). Per
costruzione lo stesso vale per **tutte** le tabelle elencate sotto. Le **liste
(SELECT) funzionano**: il problema è solo in scrittura.

## Causa radice

La RLS (ondata 2) è stata **abilitata** (`ENABLE ROW LEVEL SECURITY`, no `FORCE`)
su 10 tabelle, ma su ciascuna esiste **solo** una policy di **lettura**
`rls_<t>_ef_whitelist` `AS PERMISSIVE FOR SELECT` (+ eventuali portale/shop, anch'esse
SELECT). **Manca del tutto la policy di scrittura** (`WITH CHECK`).

Il ruolo DB del BE è **non-owner** e **non `BYPASSRLS`** (i GUC `app.current_user_id`
/ `app.ruolo_applicativo` sono settati da `JwtAuditMiddleware`), quindi la RLS si
applica anche all'operatore: la `USING` della `ef_whitelist` autorizza la SELECT
in scope (liste OK), ma **nessuna policy ha un `WITH CHECK`** → ogni INSERT/UPDATE
è negato.

### Tabelle con RLS attiva + sola policy SELECT (perimetro completo)

| Schema.tabella | Policy lettura presente | Write policy operatore |
| --- | --- | --- |
| `anagrafiche.billing_account` | `rls_billing_account_ef_whitelist` | ❌ manca |
| `vendite.preventivi` | `rls_preventivi_ef_whitelist` | ❌ manca |
| `vendite.offerte_commerciali` | `rls_offerte_commerciali_ef_whitelist` | ❌ manca |
| `vendite.ordini` | `rls_ordini_ef_whitelist` | ❌ manca |
| `vendite.contratti` | `rls_contratti_ef_whitelist` | ❌ manca |
| `vendite.fatture` | `rls_fatture_ef_whitelist` | ❌ manca |
| `vendite.fatture_scadenze` | `rls_fatture_scadenze_ef_whitelist` | ❌ manca |
| `vendite.fatturazione_lotti` | `rls_fatturazione_lotti_ef_whitelist` | ❌ manca |
| `pratiche.pratiche` | `rls_pratiche_ef_whitelist` | ❌ manca |
| `documenti.documenti_generati` | `rls_documenti_generati_ef_whitelist` | ❌ manca |

Le tabelle **figlie** (`*_righe`, `*_righe_componenti`, `note_*`, `eccezioni`,
indirizzi, ecc.) **non** risultano `ENABLE`d → non servono policy lì (verificare
in fase di applicazione che nessuna sia stata abilitata altrove).

## Decisione di design (la soluzione completa, non il ripiego)

L'operatore deve restare **isolato per emittente anche in scrittura**: è
esattamente lo scopo per cui esistono le `ef_whitelist` in lettura. Quindi la
chiusura corretta NON è disabilitare la RLS né dare `BYPASSRLS` al ruolo BE
(toglierebbero anche lo scoping in lettura): è **aggiungere la copertura di
scrittura** alla stessa whitelist.

**Pattern raccomandato — estendere la `ef_whitelist` da `FOR SELECT` a `FOR ALL`
con `WITH CHECK` identico alla `USING`** (DROP+CREATE perché il `FOR` non è
alterabile; nome invariato → il registry `config.scope_policy` che referenzia per
nome resta valido). Esempio per ordini (replicare su tutte le 10, adattando la
colonna di scope per tabella):

```sql
DROP POLICY IF EXISTS rls_ordini_ef_whitelist ON vendite.ordini;
CREATE POLICY rls_ordini_ef_whitelist ON vendite.ordini
    AS PERMISSIVE
    FOR ALL
    USING (
        current_setting('app.ruolo_applicativo', true) = 'OPERATORE'
        AND script.fn_scope_ef_whitelist(
            NULLIF(current_setting('app.current_user_id', true), '')::integer,
            emittente_fiscale_id)
    )
    WITH CHECK (
        current_setting('app.ruolo_applicativo', true) = 'OPERATORE'
        AND script.fn_scope_ef_whitelist(
            NULLIF(current_setting('app.current_user_id', true), '')::integer,
            emittente_fiscale_id)
    );
```

In alternativa, lasciare la SELECT-only e **aggiungere** una policy gemella
`rls_<t>_ef_whitelist_write` `FOR ALL` (o INSERT+UPDATE+DELETE) con la stessa
`USING`/`WITH CHECK`. Esito identico; scelta stilistica del team DB. Le policy
portale/shop restano `FOR SELECT` finché non esistono le loro API di scrittura.

## Punti da verificare in applicazione (gotcha)

1. **Colonna di scope per tabella**. Le tabelle convenzione-PK
   (`preventivi/offerte/ordini/contratti/pratiche/documenti_generati`) usano
   `emittente_fiscale_id` + `script.fn_scope_ef_whitelist(user_id, emittente_fiscale_id)`.
   **`billing_account`, `fatture`, `fatture_scadenze`, `fatturazione_lotti`** vanno
   verificate: copiare la `USING` già esistente nella rispettiva
   `ef_whitelist` e riusarla **identica** nel `WITH CHECK` (qualunque sia la
   colonna/fn di scope).
2. **Emittente in-scope al momento del CHECK**. Il `WITH CHECK` è valutato **dopo**
   i BEFORE trigger: su preventivi/offerte/ordini/contratti l'`emittente_fiscale_id`
   è derivato da `trgfn_*_default_emittente` dalla GUC quando il payload è NULL →
   per l'operatore è sempre il proprio emittente, che è in whitelist → il CHECK
   passa. **Da confermare** per `billing_account` (anagrafica master): l'operatore
   che crea un BA deve impostare un emittente in-scope, altrimenti il CHECK
   (correttamente) rifiuta.
3. **Righe create dalla pipeline fatturazione** (`fatture`, `fatture_scadenze`,
   `fatturazione_lotti`). Se il `LottoPipelineRunner` gira sotto la connessione
   operatore, il `WITH CHECK` passa (emittente del lotto = emittente operatore).
   Se invece gira sotto un **job/cron con ruolo di sistema**, quel ruolo deve
   essere `BYPASSRLS` (o avere una policy di sistema dedicata): verificare il ruolo
   con cui viene eseguita la pipeline batch.
4. **UPDATE**: `emittente_fiscale_id` è immutabile (trigger lock) → il `WITH CHECK`
   in UPDATE resta in-scope. OK.
5. **Admin globale / multi-emittente**: `fn_check_user_emittente_scope` ritorna lo
   scope pieno (whitelist multipla); il CHECK passa per qualsiasi emittente scelto
   in quel set.

## Verifica post-fix (pgTAP + smoke)

- pgTAP per ciascuna delle 10 tabelle: INSERT operatore con emittente in-scope →
  **OK**; INSERT con emittente fuori scope → **rifiutato**; SELECT resta filtrata
  in scope (invariato); UPDATE in-scope → OK.
- Smoke applicativo (operatore): creazione preventivo / offerta / **ordine** dal
  drawer → 200; conferma ordine + push → 200; emissione documento (genera
  fattura/lotto) → 200.

## Ripiego di emergenza (NON la soluzione)

Solo se serve sbloccare l'ambiente prima del fix sopra, esiste il kill-switch
(rollback di `20260601-39` per le sue 5 tabelle): `ALTER TABLE ... DISABLE ROW
LEVEL SECURITY`. Lascia però l'operatore **senza isolamento per emittente**:
usare solo come tampone temporaneo, non come chiusura.

## Nota: non è il codice applicativo

Il BE/FE di ordini (e preventivi/offerte) è corretto: stesso payload/flusso,
falliscono identicamente. Il gap è esclusivamente nella **copertura policy RLS in
scrittura** (DDL).

---

## RISOLTO (team DB, 2026-06-03)

Migration `20260603-16..25` (00_schema): ogni `rls_<t>_ef_whitelist` estesa da
`FOR SELECT` a **`FOR ALL` con `WITH CHECK` = `USING`** (nome invariato →
registry `config.scope_policy` valido).

**File prodotti:**

- Migration `00_schema`: `20260603-16` preventivi, `-17` offerte_commerciali,
  `-18` ordini, `-19` contratti, `-20` pratiche, `-21` documenti_generati,
  `-22` fatture, `-23` fatture_scadenze, `-24` fatturazione_lotti,
  `-25` billing_account (caso speciale, vedi punto 1).
- pgTAP (`db/pgtap/rls/`): `test-rls-write-policies-structure.sql` (strutturale,
  33 assert: tutte e 10 `FOR ALL`+`WITH CHECK` + policy `_ins`),
  `test-rls-preventivi-ef-whitelist-write.sql` (funzionale, UPDATE in-scope=1 /
  off-scope=0 / no-ruolo=0 / kill-switch=1, due operatori distinti),
  `test-rls-policies-structure.sql` aggiornato (`rls_fatture_ef_whitelist` ora `ALL`).
- Doc allineati: `postgresql/row-level-security.md` (ownership/`FORCE`),
  `guide/architettura-multi-face-auth.md` §6, `guide/architettura-permessi-e-autorizzazioni.md`,
  `guide/risorse-umane-e-accessi.md`, e nota **SUPERATA** su
  `dev/work-done/analisi-attivazione-rls-operatori.md` §5.1.

**Verifica esito:** stato DB confermato (10 policy `cmd=ALL` + `with_check`, più
`rls_billing_account_ef_whitelist_ins` `INSERT`); **suite RLS 8/8 PASS**. Batch
**non impattati**: pgAgent gira come `postgres` superuser (BYPASSRLS) → esente
anche con funzioni `SECURITY INVOKER` (R4 in `analisi-attivazione-rls-db.md`).

Tre scoperte rispetto al brief:

1. **`billing_account` — NON `WITH CHECK = USING`** (gotcha #2 confermato come bug
   reale). Il mapping efba che definisce lo scope è creato da un trigger **`AFTER
   INSERT`** (`trg_billing_account_z90_link_ef_ins`), mentre la `WITH CHECK` è
   valutata *durante* l'INSERT → `via_efba` rifiuterebbe ogni BA nuovo di operatore
   con scope ristretto. Soluzione (migration `-25`): policy principale `FOR ALL`
   `via_efba` (SELECT/UPDATE/DELETE) **+ policy gemella `_ins` `FOR INSERT`
   gate-only** (`ruolo=OPERATORE`). Chi può creare è già imposto dal guard BEFORE
   `guard_admin_globale`; lo scope post-insert lo stabilisce il trigger AFTER.

2. **Disallineamento nella GUIDA, non nel codice** (`row-level-security.md`
   corretto). La guida diceva "tabelle owned da `zeroerp_app` → `FORCE`
   obbligatorio": falso. `zeroerp_app` è **non-owner `NOBYPASSRLS`** → `ENABLE` da
   solo basta, `FORCE` non serve (e seguirlo avrebbe assoggettato i percorsi
   owner/batch). Il punto del brief (niente `FORCE`/`BYPASSRLS`) è corretto.

3. **Gap latente acquisti/shop** (fuori dalle 10, ma stesso schema). `acquisti.ordini`,
   `acquisti.ddt`, `shop.shop_ricevute` hanno policy `FOR SELECT` ma **non sono
   `ENABLE`d**: nessun blocco oggi. Inoltre su `ordini`/`billing_account`/`fatture*`
   le policy **portale/shop sono solo SELECT**: quando arriverà il write-path shop
   (checkout come `SHOP_CUSTOMER`), servirà la stessa copertura `WITH CHECK` per
   quel ruolo, altrimenti l'INSERT shop sarà bloccato identicamente.
