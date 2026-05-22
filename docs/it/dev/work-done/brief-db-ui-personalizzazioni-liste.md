# Brief Team DB — Allineamenti `ui.*` post-Blocco A/B (personalizzazioni liste) [LANDED 2026-05-07]

> **Status**: ✅ **LANDED** — Team DB ha applicato tutte e 4 le richieste su `dev/db-tid` (changeset `20260507-01..04`). pgTAP **12/12 verdi** (uno in più del previsto: test 3b separato sulla colonna sensibile).
>
> **Deviazioni applicate dal team DB rispetto al brief originario**:
>
> - **DB-4 cast GUC blindato**: invece del cast diretto `NULLIF(...)::config.ruolo_applicativo` proposto, il cast e' avvolto in un blocco `EXCEPTION WHEN invalid_text_representation THEN NULL`. Se la GUC contiene un valore non-ENUM (corruzione, downgrade, test arbitrari), fallback silenzioso a NULL = legacy "tutte le vesti", invece di propagare un'eccezione all'utente. Comportamento piu' robusto. Backend non vede differenza: `JwtAuditAuthentication` scrive sempre valori corretti.
> - **Trigger aggiuntivo non richiesto**: aggiunto `trg_ui_lista_preferenza_utente_z90_clear_preset_base_ts_upd` — quando un preset viene eliminato, l'`ON DELETE SET NULL` di DB-2 azzera `preset_base_id` e questo trigger azzera *anche* `preset_base_data_update`. Coerente: un timestamp di confronto senza preset di riferimento sarebbe dato fantasma. **Impatto FE**: il badge "preset aggiornato" (DEF-2) deve controllare `preset_base_id IS NOT NULL` prima di confrontare i timestamp; vedi `sviluppo-personalizzazioni-liste.md` §10.2 per la condizione completa.
>
> Nessun altro scostamento. Backend agent puo' procedere con Blocchi C+D (commit `dev/backend-tid` ancora pendente al 2026-05-07).
>
> ---
>
> **Target team**: DB (`dev/db-tid`) — ✅ applicato 2026-05-07
> **Origine**: backend agent (`dev/backend-tid`), sessione 2026-05-06 — analisi critica post-A/B su DB landed
> **Impatto**: schema `ui` (1 ALTER TABLE + 1 ALTER FK + 1 fn `runOnChange:true` + 1 trigger aggiuntivo) + `db/pgtap/ui/test-fn-resolve-lista-config.sql` (esteso a 12 scenari)

**Data:** 2026-05-06
**Riferimento:** [`sviluppo-personalizzazioni-liste.md`](../work-in-progress/sviluppo-personalizzazioni-liste.md) §10.2
**Branch:** `dev/db-tid`
**Priorita':** alta — bloccante per Blocco E (prima lista reale `anagrafiche.clienti`); non bloccante per Blocco C (backend) e D (frontend), che possono procedere in parallelo
**Origine:** backend agent (`dev/backend-tid`), sessione 2026-05-06 — analisi critica post-A/B su DB landed

---

## Contesto

I Blocchi A (DDL schema `ui`) e B (codice DB: 2 trigger + `fn_resolve_lista_config`) sono atterrati il 2026-05-06 (changelog `20260506-01..12` + pgTAP `test-fn-resolve-lista-config.sql` 9/9 verdi).

L'analisi critica del backend agent ha rilevato 4 punti di allineamento da chiudere prima del Blocco E (seed catalogo + preset di `anagrafiche.clienti`), per evitare di re-seedare CSV su DDL/fn da correggere. Tre interventi sono locali a `ui.*`, uno (DB-4) e' coerente con il pattern dei resolver `script.fn_*` GUC-aware.

Niente di questo blocca lo sviluppo Backend (Blocco C) o Frontend (Blocco D) della WIP: il contratto API e' stabile, le 4 modifiche sono trasparenti per i chiamanti.

---

## DB-1 — `ui.lista_preset.emittente_fiscale_id`: INTEGER → BIGINT

**Cosa**

```sql
ALTER TABLE ui.lista_preset
  ALTER COLUMN emittente_fiscale_id TYPE BIGINT;
```

**Perche'**

`anagrafiche.emittenti_fiscali.id` e' `BIGINT` (verificato in [`docs/it/dbzero/anagrafiche/tabelle/emittenti_fiscali.md`](../../dbzero/anagrafiche/tabelle/emittenti_fiscali.md)). Il DDL atterrato in [`20260506-04-ddl-ui-lista-preset-mctit.yaml`](../../../../db/changelog/migrations_v2/00_schema/ui/20260506-04-ddl-ui-lista-preset-mctit.yaml) usa `INTEGER`. La FK funziona perche' Postgres coerce, ma:

- `fn_resolve_lista_config` usa gia' `anagrafiche.emittenti_fiscali.id%TYPE` per il parametro → BIGINT lato funzione, INTEGER lato tabella: incoerenza visibile a chi legge il modello;
- al primo INSERT con id `> 2^31` (improbabile ma non impossibile su istanze long-running con generatore globale) si avrebbe overflow silente del cast.

**Impatto**

- Tabella vuota in dev (no seed pre-A/B) → ALTER istantaneo, nessun rischio;
- Nessun chiamante BE da modificare: il backend non e' ancora stato scritto.

**Migration consigliata**

Nuovo changeset (preferibile a modifica del DDL gia' mergiato — vedi [AGENTS.md §Liquibase v2 Workflow](../../../../.codex/AGENTS.md)): `20260507-NN-alter-ui-lista-preset-emittente-bigint-mctit.yaml`.

---

## DB-2 — FK `ui.lista_preferenza_utente.preset_base_id` → `ON DELETE SET NULL`

**Cosa**

```sql
ALTER TABLE ui.lista_preferenza_utente
  DROP CONSTRAINT fk_lista_preferenza_utente_lista_preset;

ALTER TABLE ui.lista_preferenza_utente
  ADD CONSTRAINT fk_lista_preferenza_utente_lista_preset
  FOREIGN KEY (preset_base_id) REFERENCES ui.lista_preset(id) ON DELETE SET NULL;
```

**Perche'**

`preset_base_id` e' un **riferimento storico** (lo dice anche il `COMMENT ON COLUMN` in [`20260506-06-ddl-ui-lista-preferenza-utente-mctit.yaml`](../../../../db/changelog/migrations_v2/00_schema/ui/20260506-06-ddl-ui-lista-preferenza-utente-mctit.yaml) riga 88: *"preset da cui e' partita la personalizzazione (riferimento storico)"*).

Oggi la FK e' `ON DELETE NO ACTION` di default: l'eliminazione di un preset (operazione admin legittima quando si rinnova un preset di sistema/ruolo) richiede di prima ripulire tutte le `lista_preferenza_utente` che lo referenziano, oppure fallisce con `foreign_key_violation`. Le preferenze utente non hanno motivo di essere distrutte solo perche' il preset di base e' stato eliminato — la `configurazione` JSONB e' autonoma.

`ON DELETE SET NULL` mantiene la preferenza utente intatta e azzera solo il puntatore storico, coerente con l'intento del campo.

**Impatto**

- Nessun cambio di comportamento osservabile finche' non si elimina un preset;
- Tabella vuota → nessun rischio di rifiutare l'ALTER per dati incoerenti.

**Migration consigliata**

`20260507-NN-alter-fk-ui-preferenza-preset-on-delete-set-null-mctit.yaml`.

---

## DB-3 — `fn_resolve_lista_config` Step 2b: cascata preset di ruolo ordinata per `priorita`

**Cosa**

In [`fn_resolve_lista_config`](../../dbzero/ui/funzioni/fn_resolve_lista_config.md), Step 2b (cascata preset di profilo) e' attualmente:

```sql
-- 2b. Preset di profilo (se nessuna preferenza personale)
IF v_config_colonne IS NULL AND array_length(v_profili_ids, 1) > 0 THEN
  SELECT (...colonne via subquery...), lp.ordinamento_default, ...
    INTO v_config_colonne, v_ordinamento, v_filtri, v_pagina_dim
    FROM ui.lista_preset lp
   WHERE lp.lista_id           = v_lista_id
     AND lp.ambito             = 'ruolo'
     AND lp.profilo_accesso_id = ANY(v_profili_ids)
     AND lp.is_default         = TRUE
     AND lp.attivo             = TRUE
   LIMIT 1;
END IF;
```

Va cambiato in (versione GUC-aware, vedi anche DB-4 sotto):

```sql
-- 2b. Preset di profilo (se nessuna preferenza personale)
-- Ordinato per priorita ASC: AD_HOC (1) prevale su REPARTO/PORTALE (2)
IF v_config_colonne IS NULL AND array_length(v_profili_ids, 1) > 0 THEN
  SELECT (...colonne via subquery...), lp.ordinamento_default, ...
    INTO v_config_colonne, v_ordinamento, v_filtri, v_pagina_dim
    FROM ui.lista_preset lp
    JOIN script.fn_get_profili_accesso_applicabili(
           p_auth_user_id,
           NULLIF(current_setting('app.ruolo_applicativo', true), '')::config.ruolo_applicativo
         ) pa
      ON pa.profilo_accesso_id = lp.profilo_accesso_id
   WHERE lp.lista_id     = v_lista_id
     AND lp.ambito       = 'ruolo'
     AND lp.is_default   = TRUE
     AND lp.attivo       = TRUE
   ORDER BY pa.priorita ASC
   LIMIT 1;
END IF;
```

**Perche'**

Quando un utente ha **piu' profili applicabili** (caso normale post-multi-face: AD_HOC binding diretto + PORTALE/REPARTO via reparto), entrambi possono avere `is_default=TRUE` per la stessa lista. Senza `ORDER BY pa.priorita ASC`, il `LIMIT 1` sceglie un preset arbitrario.

Lo stesso ordinamento e' gia' usato nello Step 4 della funzione (DISTINCT ON sui permessi colonna). Manca solo qui per coerenza.

**Impatto**

- Funzione `runOnChange: true`, una sola modifica di `CREATE OR REPLACE`;
- Test pgTAP: aggiungere uno scenario "utente con 2 profili (prio 1 + prio 2) entrambi con preset is_default → vince il prio 1". Gli altri 9 scenari esistenti continuano a passare.

---

## DB-4 — `fn_resolve_lista_config` Step 1: filtro veste corrente (GUC-aware)

**Cosa**

In [`fn_resolve_lista_config`](../../dbzero/ui/funzioni/fn_resolve_lista_config.md), Step 1 attualmente:

```sql
-- 1. Risolvi profili applicabili (1-arg, ricade su DEFAULT NULL)
SELECT ARRAY_AGG(profilo_accesso_id) INTO v_profili_ids
  FROM script.fn_get_profili_accesso_applicabili(p_auth_user_id);
```

Va cambiato in:

```sql
-- 1. Risolvi profili applicabili filtrati per la veste corrente.
-- GUC vuota (job/shell/test che non setta) -> NULL -> 2-arg con NULL si
-- comporta come la 1-arg legacy (tutte le vesti): zero rischio regressione.
SELECT ARRAY_AGG(profilo_accesso_id) INTO v_profili_ids
  FROM script.fn_get_profili_accesso_applicabili(
    p_auth_user_id,
    NULLIF(current_setting('app.ruolo_applicativo', true), '')::config.ruolo_applicativo
  );
```

**Perche'**

`script.fn_get_profili_accesso_applicabili` ha firma 2-arg `(auth_user_id INTEGER, ruolo_applicativo config.ruolo_applicativo DEFAULT NULL)`. Chiamata con 1 arg ricade su NULL → ritorna profili di **tutte** le vesti dell'utente.

Caso reale: Mario Rossi ha `auth_user` unico legato a 2 identita': OPERATORE (dipendente) + SHOP_CUSTOMER (cliente shop). Quando apre `/admin/anagrafiche/clienti` (veste OPERATORE), `fn_resolve_lista_config` somma i profili di **entrambe** le identita': il preset di ruolo applicato e i permessi colonna mescolano "Amministrazione" e "Cliente shop" — incoerente.

Il claim JWT della richiesta corrente e' propagato da `JwtAuditAuthentication` nella GUC `app.ruolo_applicativo`. Leggerla dentro la fn e passarla alla 2-arg risolve il filtro veste.

**Fallback automatico**: `current_setting('...', true)` con `missing_ok=true` torna stringa vuota se la GUC non e' settata; `NULLIF(...,'')` la collassa a NULL; la 2-arg con NULL ha il comportamento legacy. Quindi:

- richiesta HTTP autenticata (FE Mario-OPERATORE) → GUC = 'OPERATORE' → filtra correttamente;
- shell DBA, job pgAgent, test pgTAP che non setta GUC → fallback al comportamento attuale.

**Coerenza con il resto del modulo `script.fn_*`**

Gli altri 4 resolver permessi (`fn_resolve_livello_area`, `fn_check_azione_processo`, `fn_get_user_permissions_map`, `fn_get_user_actions_map`) **chiamano gia' tutti la 1-arg** (vedi [`20260420-11-update-fn-resolver-multi-veste-mctit.yaml`](../../../../db/changelog/migrations_v2/20_code/script/20260420-11-update-fn-resolver-multi-veste-mctit.yaml) e file correlati): hanno la stessa identica incoerenza, su scala maggiore.

**Punto importante per il team DB:** DB-4 corregge solo `fn_resolve_lista_config`. La stessa correzione GUC-aware andrebbe replicata sugli altri 4 resolver in un task trasversale separato, ma non e' in scope di questo brief — segnalo solo che il pattern e' allineato a quello che sara' il fix globale, quando si decidera' di farlo.

**Impatto**

- Stessa migration `runOnChange: true` di DB-3 (entrambi modificano la stessa funzione);
- Test pgTAP: aggiungere uno scenario "utente con 2 identita' (OPERATORE + CLIENTE_PORTALE) e GUC settata → vede solo i profili della veste GUC". Lo scenario "GUC vuota → fallback comportamento legacy" e' gia' implicitamente coperto dai 9 esistenti.

---

## Migration consigliata — riepilogo

3 changeset, in ordine:

| # | File proposto | Tipo | Modifica |
| - | ------------- | ---- | -------- |
| 1 | `00_schema/ui/20260507-NN-alter-ui-lista-preset-emittente-bigint-mctit.yaml` | DDL | DB-1: `ALTER COLUMN ... TYPE BIGINT` |
| 2 | `90_end/20260507-NN-alter-fk-ui-preferenza-preset-on-delete-set-null-mctit.yaml` | DDL | DB-2: drop+recreate FK con `ON DELETE SET NULL` |
| 3 | `20_code/ui/20260507-NN-update-fn-ui-resolve-lista-config-mctit.yaml` | Code (`runOnChange: true`) | DB-3 + DB-4 in unico `CREATE OR REPLACE FUNCTION` |

NB: il file 3 va creato **nuovo**, non modificato il `20260506-12` mergiato (regola Liquibase v2: mai modificare changelog gia' pushati su GitHub — vedi [AGENTS.md §Liquibase v2 Workflow](../../../../.codex/AGENTS.md)).

## Test pgTAP

Estendere [`db/pgtap/ui/test-fn-resolve-lista-config.sql`](../../../../db/pgtap/ui/test-fn-resolve-lista-config.sql) con 2 nuovi scenari:

1. **Cascata preset di ruolo deterministica**: utente con 2 profili applicabili (AD_HOC prio 1, REPARTO prio 2), entrambi con preset `is_default=TRUE` per stessa lista → vince il preset del profilo prio 1.
2. **Filtro veste GUC-aware**: utente con 2 identita' attive (OPERATORE + CLIENTE_PORTALE), profili distinti per ciascuna veste, ciascuno con preset `is_default=TRUE`. Eseguire 2 volte la fn con `SET LOCAL app.ruolo_applicativo = 'OPERATORE'` e poi `'CLIENTE_PORTALE'` — ognuna deve restituire il preset della rispettiva veste.

Lo scenario 9 esistente ("Lista inesistente → errore `E_UI_LISTA_NON_TROVATA`") e gli altri 8 continuano a passare.

---

## Cosa NON si chiede al team DB

- Indici aggiuntivi sulle 6 tabelle `ui.*`: non in scope (la `dbops.fk_index_policy` ha gia' coperto le 8 FK in [`20260506-09-upsert-dbops-fk-index-policy-ui-mctit.yaml`](../../../../db/changelog/migrations_v2/80_data/changelog/20260506-09-upsert-dbops-fk-index-policy-ui-mctit.yaml)). Se emergono hot path nei test post-Blocco E, ottimizziamo dopo.
- Registrazione di `ui` in `config.aree_funzionali`: non serve. Il backend usera' `DomainAPIView + skip_area_check=True` (meta-API trasversale, vedi WIP §11/Blocco C).
- Modifiche al filtro veste sugli altri 4 resolver permessi (`fn_resolve_livello_area`, ecc.): task trasversale separato, fuori scope di questo brief.

---

## Risposta attesa

Quando i 3 changeset sono atterrati su `dev/db-tid`:

1. confermare che i 9 + 2 = 11 test pgTAP passano;
2. linkare i changeset effettivi (numerazione finale potrebbe differire);
3. segnalare eventuali deviazioni dal brief (es. preferenza per un'altra forma del fallback NULL).

A quel punto il backend agent procede con Blocco C (apps/ui/) e Blocco D (componenti FE) gia' allineati al comportamento corretto.
