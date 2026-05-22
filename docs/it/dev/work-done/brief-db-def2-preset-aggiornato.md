# Brief DB — DEF-2 "Preset aggiornato": colonna ignore + flag in `fn_resolve_lista_config`

> **Tipo**: feature DB (DDL + fn aggiornamento + trigger update + pgTAP).
> **Branch**: `dev/db-tid`.
> **Autore brief**: backend agent (Tid, sessione 2026-05-11).
> **Origine**: roadmap `sviluppo-personalizzazioni-liste_def.md` → DEF-2.
> **Decisioni operative chiuse da Tid 2026-05-11**:
> 1. Logica calcolo flag: **lato DB** in `fn_resolve_lista_config` (single source of truth).
> 2. Comportamento "Ignora": **tombstone separato** `preset_aggiornato_ignored_at TIMESTAMPTZ NULL` (lo snapshot funzionale resta puro; una FUTURA modifica del preset fa riapparire il banner).
> 3. UX banner FE: `<Message severity="info">` inline sopra la lista, dismissable (out of scope DB).

## Obiettivo funzionale

Quando un admin SUPER_ADMIN modifica un preset di sistema/ruolo/emittente fiscale,
gli utenti che hanno una preferenza personale derivata da quel preset devono vedere
un banner non intrusivo: *"La configurazione del tuo ruolo e' stata aggiornata. Vedi novita'?"*

L'utente puo':
- **Vedi novita'**: apre la modale di personalizzazione (gia' esistente); al successivo save, il banner sparisce (lo snapshot si riallinea naturalmente).
- **Ignora**: setta `preset_aggiornato_ignored_at = NOW()`; il banner sparisce e resta sparito finche' il preset non viene modificato di nuovo (cioe' finche' `preset.data_update > preset_aggiornato_ignored_at`).

## Cosa esiste gia' (Blocco B / F.2 atterrati)

- `ui.lista_preferenza_utente.preset_base_id` (FK opzionale a `ui.lista_preset`)
- `ui.lista_preferenza_utente.preset_base_data_update` (snapshot di `ui.lista_preset.data_update` al momento del save preferenza utente)
- Trigger `trg_ui_lista_preferenza_utente_z90_clear_preset_base_ts_upd` su `BEFORE UPDATE`:
  esegue `ui.trgfn_ui_lista_preferenza_utente_z90_clear_preset_base_ts()` che azzera `preset_base_data_update` quando cambia `preset_base_id`.
- BE Python `ListaPreferenzaService.upsert` salva lo snapshot ad ogni save (`UiRepository.get_preset_base_snapshot`).

## Modifiche DB richieste

### 1. DDL — aggiungere colonna `preset_aggiornato_ignored_at`

Nuova migration `00_schema/ui/2026MMDD-NN-add-col-lista-preferenza-utente-preset-aggiornato-ignored-at-mctit.yaml`:

```sql
ALTER TABLE ui.lista_preferenza_utente
  ADD COLUMN preset_aggiornato_ignored_at TIMESTAMPTZ NULL;

COMMENT ON COLUMN ui.lista_preferenza_utente.preset_aggiornato_ignored_at IS
  'Tombstone: quando l''utente preme "Ignora" sul banner "preset aggiornato", '
  'qui viene scritto NOW(). Il flag `preset_aggiornato` torna TRUE solo se '
  'preset.data_update > preferenza.preset_aggiornato_ignored_at (cioe'' il '
  'preset e'' stato modificato DI NUOVO dopo l''ignore).';
```

Nessun INDEX: la colonna e' letta solo dalla `fn_resolve_lista_config` per la
preferenza dell'utente corrente (lookup gia' su PK / UNIQUE `(auth_user_id, lista_id)`).

### 2. Aggiornare trigger `trgfn_ui_lista_preferenza_utente_z90_clear_preset_base_ts`

Quando cambia `preset_base_id`, oltre ad azzerare `preset_base_data_update`, azzerare ANCHE `preset_aggiornato_ignored_at`.

**Why**: cambiare preset di base equivale a un "reset" della relazione utente↔preset; il tombstone storico riferiva al vecchio preset e perde significato.

Nuova migration `20_code/ui/2026MMDD-NN-update-trgfn-ui-lista-preferenza-utente-clear-preset-ts-include-ignored-mctit.yaml` con `runOnChange: true` (in deroga sulla fn — non si tocca la funzione gia' mergiata, si crea una nuova versione).

```sql
CREATE OR REPLACE FUNCTION ui.trgfn_ui_lista_preferenza_utente_z90_clear_preset_base_ts()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
  -- Quando cambia il preset di base (riferimento storico), gli stati derivati
  -- (snapshot data_update + tombstone ignore) perdono significato.
  IF NEW.preset_base_id IS DISTINCT FROM OLD.preset_base_id THEN
    NEW.preset_base_data_update := NULL;
    NEW.preset_aggiornato_ignored_at := NULL;
  END IF;
  RETURN NEW;
END;
$$;
```

### 2b. Fallback `COALESCE(data_update, data_insert)` per preset mai modificati

**Problema rilevato 2026-05-11 in smoke test BE**: i preset seedati hanno
`lista_preset.data_update = NULL` finche' un admin non ne modifica almeno
un campo. Se un utente salva la sua preferenza prima di quel primo
update, lo snapshot `preset_base_data_update` viene salvato a NULL —
il confronto `preset.data_update > snapshot` diventa `NULL > NULL` =>
NULL/false => banner mai visibile.

Il BE Python ha gia' applicato il fallback:
`get_preset_base_snapshot` ora ritorna
`COALESCE(lp.data_update, lp.data_insert)` come `snapshot_ts`.

Per simmetria, la `fn_resolve_lista_config` DEVE usare lo stesso pattern
nel confronto del flag (step 2.5):

```sql
v_preset_base_ts_corrente TIMESTAMPTZ;
...
SELECT COALESCE(lp.data_update, lp.data_insert)
  INTO v_preset_base_ts_corrente
  FROM ui.lista_preset lp
 WHERE lp.id = v_pref_preset_base_id;

v_preset_aggiornato := (
       v_pref_preset_base_data_update IS NOT NULL
   AND v_preset_base_ts_corrente IS NOT NULL
   AND v_preset_base_ts_corrente > v_pref_preset_base_data_update
   AND (
         v_pref_preset_aggiornato_ignored_at IS NULL
     OR  v_pref_preset_aggiornato_ignored_at < v_preset_base_ts_corrente
   )
);
```

Senza questo fallback, qualunque preferenza salvata su un preset mai
modificato resta cieca alle modifiche future del preset.

### 3. Aggiornare `ui.fn_resolve_lista_config` — espone `preset_aggiornato: bool`

Nuova migration `20_code/ui/2026MMDD-NN-update-fn-resolve-lista-config-preset-aggiornato-mctit.yaml` con `runOnChange: true`.

**Logica**: dopo il passo 2 (cascata configurazione), se la riga corrente proviene da una preferenza utente con `preset_base_id` non-null e `preset_base_data_update` non-null, leggere `lista_preset.data_update` corrente del preset di base e calcolare:

```
preset_aggiornato = (
      v_pref_preset_base_id IS NOT NULL
  AND v_pref_preset_base_data_update IS NOT NULL
  AND v_preset_base_data_update > v_pref_preset_base_data_update
  AND (
        v_pref_preset_aggiornato_ignored_at IS NULL
    OR  v_pref_preset_aggiornato_ignored_at < v_preset_base_data_update
  )
)
```

Aggiungere al JSONB di output la chiave `preset_aggiornato` (boolean, sempre presente, default `FALSE` quando la preferenza utente non esiste o `preset_base_id IS NULL`).

**Pseudo-codice** (il team DB conosce la struttura interna):

```sql
-- Step 2.5 (dopo aver risolto la cascata): lookup preset_base_data_update corrente
v_preset_base_data_update TIMESTAMPTZ := NULL;
IF v_source_kind = 'preferenza_utente' AND v_pref_preset_base_id IS NOT NULL THEN
  SELECT lp.data_update
    INTO v_preset_base_data_update
    FROM ui.lista_preset lp
   WHERE lp.id = v_pref_preset_base_id;
END IF;

v_preset_aggiornato := (
       v_pref_preset_base_data_update IS NOT NULL
   AND v_preset_base_data_update IS NOT NULL
   AND v_preset_base_data_update > v_pref_preset_base_data_update
   AND (
         v_pref_preset_aggiornato_ignored_at IS NULL
     OR  v_pref_preset_aggiornato_ignored_at < v_preset_base_data_update
   )
);

-- Step 6 build JSONB: aggiungere chiave
RETURN jsonb_build_object(
  'colonne',           v_colonne,
  'ordinamento',       v_ordinamento,
  'filtri',            v_filtri,
  'pagina_dimensione', v_pagina_dimensione,
  'colonne_nuove',     v_colonne_nuove,
  'preset_aggiornato', v_preset_aggiornato  -- NEW DEF-2
);
```

### 4. Aggiornare doc manual `fn_resolve_lista_config.md`

Aggiungere nella tabella "Risultato" la chiave `preset_aggiornato`:

```
| preset_aggiornato | boolean | TRUE se il preset di base e' stato modificato dopo lo snapshot della preferenza utente E l'utente non ha dismissato il banner per quella versione del preset. FALSE in tutti gli altri casi (no preferenza, preferenza senza preset_base_id, snapshot allineato, ignore attivo). |
```

Aggiungere step 2.5 nella sezione "Algoritmo".

### 5. pgTAP test

Nuovo file `db/pgtap/ui/test-fn-resolve-lista-config-preset-aggiornato-v1.sql`:

**Indice test (1..N)** (in commento all'inizio del file):

1. Setup: lista test + preset di sistema + 1 utente
2. Caso A: preferenza utente con `preset_base_data_update` allineato al `preset.data_update` corrente → `preset_aggiornato = FALSE`
3. Caso B: simula admin che modifica il preset (`UPDATE lista_preset SET ... WHERE id = ...`) → snapshot < data_update corrente → `preset_aggiornato = TRUE`
4. Caso C: dopo caso B, setto `preset_aggiornato_ignored_at = NOW()` → `preset_aggiornato = FALSE`
5. Caso D: dopo caso C, modifico DI NUOVO il preset (`UPDATE lista_preset...`) → `data_update > ignored_at` → `preset_aggiornato = TRUE` di nuovo
6. Caso E: nessuna preferenza utente (cade su preset di sistema) → `preset_aggiornato = FALSE` (no preferenza, no snapshot)
7. Caso F: cambio `preset_base_id` di una preferenza → trigger azzera entrambi gli snapshot → `preset_aggiornato = FALSE`

## Smoke post-fix DB (lato BE backend agent)

```bash
# Sul webserver, dopo che il team DB ha pushato:
# 1. Restart gunicorn (no cambi BE Python richiesti per la sola colonna; sara'
#    aggiunto un endpoint nuovo dal backend agent in PR separata).
pkill -HUP -f "gunicorn zeroerp_backend"

# 2. Smoke fn DB
psql -c "SELECT ui.fn_resolve_lista_config('anagrafiche.clienti', <user_id>, NULL) -> 'preset_aggiornato';"
# atteso: FALSE (se l'utente ha preferenza con snapshot allineato)
# atteso: TRUE (se hai eseguito test caso B in mezzo)
```

## Lavoro BE/FE in parallelo (NON in scope di questo brief)

Il backend agent procede in parallelo con:

- **BE Python**:
  - `UiService.get_lista_config` passthrough naturale del nuovo campo `preset_aggiornato` (gia' restituito dalla fn DB nel JSONB).
  - Nuovo endpoint `POST /api/v1/ui/liste/<codice>/preferenze/ignore-preset-update/` → SET `preset_aggiornato_ignored_at = NOW()` per (user, lista). Idempotente.
  - Nuovo metodo `UiRepository.set_preset_aggiornato_ignored(auth_user_id, lista_id)`.
  - Nuovo error code `E_UI_PREFERENZA_NON_TROVATA` (404 se l'utente non ha preferenza salvata sulla lista).
  - Test unitari su service + view (mock DB advisory).

- **FE Vue**:
  - `useListaConfig` espone `presetAggiornato` (computed dal config.value.preset_aggiornato).
  - Nuova API client `ignorePresetUpdate(codice)` axios POST.
  - `<Message severity="info">` inline in `ListaConfigurabile` (o `ClientiSearchTable` come pilota) con CTA `Vedi novita'` → apre modale personalizzazione + `Ignora` → chiama API + chiude banner.
  - i18n IT/EN nuove chiavi `lista_config.preset_aggiornato_*`.

## Note di rollback

- DROP della colonna `preset_aggiornato_ignored_at`: safe (NULL ammesso, nessuna FK / vincolo dipendente).
- Ripristinare versione precedente della fn `fn_resolve_lista_config`: contratto API regredisce a senza `preset_aggiornato` → FE non visualizza il banner ma non rompe (composable usa `?? false` come fallback).
- Ripristinare versione precedente del trigger: nessun side-effect (la colonna nuova resta orfana).

## Riferimenti

- Roadmap: [sviluppo-personalizzazioni-liste_def.md](../work-in-progress/sviluppo-personalizzazioni-liste_def.md) sezione DEF-2.
- Doc fn corrente: [docs/it/dbzero/ui/manual/fn_resolve_lista_config.md](../../dbzero/ui/manual/fn_resolve_lista_config.md).
- Doc tabella: [docs/it/dbzero/ui/manual/lista_preferenza_utente.md](../../dbzero/ui/manual/lista_preferenza_utente.md).
- Pattern complementare gia' esistente: `colonne_nuove` (>0 = "nuove colonne nel catalogo disponibili"). DEF-2 introduce il segnale parallelo "preset modificato dall'admin".
