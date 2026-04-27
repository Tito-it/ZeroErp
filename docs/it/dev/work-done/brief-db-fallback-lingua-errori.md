# Brief DB — Fallback lingua nei messaggi di errore

> **Destinatario**: team DB (branch `dev/db-tid`)
> **Richiesta da**: backend agent (sessione 2026-04-23, pianificazione i18n UI)
> **Priorità**: bassa (prerequisito per rollout incrementale traduzioni EN)
>
> **STATO 2026-04-23**: ✅ **LANDED** su `dev/db-tid` — changelog
> `20_code/script/20260423-02-update-fn-get-messaggio-e-log-raise-fallback-lingua-mctit.yaml`
> (2 sub-changeSet: `-02-01` per `fn_get_messaggio`, `-02-02` per `fn_log_and_raise_error`).
>
> **Migliorie applicate dal team DB rispetto al brief**:
>
> * Implementazione single-query `WHERE lingua IN (lingua_eff, 'it') ORDER BY (lingua = lingua_eff) DESC LIMIT 1` invece del pattern "2 SELECT + IF/EXISTS" proposto. Un round-trip invece di due; semantica "riga intera vince" naturale (niente mix causa/soluzione tra lingue).
> * Fix opportunistico `IMMUTABLE → STABLE` su `fn_get_messaggio` (bug latente: legge tabella, IMMUTABLE era scorretto).
> * Due sub-changeSet separati in sequenza con dipendenza esplicita, invece di un singolo changeSet monolitico.
>
> **Follow-up**: rigenerare la doc autogenerata in `docs/it/dbzero/script/funzioni/fn_get_messaggio.md` e `fn_log_and_raise_error.md` (attualmente ferme alla versione pre-fallback).

## 1. Scopo

Consentire il **rollout incrementale** delle traduzioni EN (e future) in `config.messaggi_errore` senza dover tradurre tutti i codici errore in un colpo solo. Oggi, se la GUC `myapp.user_language='en'` è impostata e una riga EN manca per un dato codice, l'utente vede il messaggio placeholder `[MESSAGGIO NON DEFINITO: <codice>]` (cfr. [fn_get_messaggio](../../dbzero/script/funzioni/fn_get_messaggio)). Serve un **fallback esplicito alla lingua di default `'it'`** per ogni lookup su `config.messaggi_errore`.

## 2. Contesto attuale

- `config.messaggi_errore` ha dimensione lingua (`codice, lingua`) con UNIQUE su `(codice, lingua)` e FK a `config.lingue`.
- Default `lingua = 'it'`.
- Le righe IT sono popolate; EN arriveranno in modo incrementale.
- Due funzioni consumano la tabella:
  - `script.fn_get_messaggio(codice, valore, lingua)` — recupera il template messaggio.
  - `script.fn_log_and_raise_error(...)` — oltre al messaggio recupera `causa` e `soluzione` con query diretta.

Entrambe leggono la GUC `myapp.user_language` (coalesce su `'it'`), ma **nessuna delle due** tenta un secondo lookup in IT se il primo lookup nella lingua richiesta non trova riga.

## 3. Modifiche richieste

### 3.1 `script.fn_get_messaggio`

File riferimento: [docs/it/dbzero/script/funzioni/fn_get_messaggio.md](../../dbzero/script/funzioni/fn_get_messaggio.md)

**Comportamento richiesto**:

1. Risolve `lingua_eff` come oggi (parametro → GUC → `'it'`).
2. Prova `SELECT messaggio FROM config.messaggi_errore WHERE codice=p_codice AND lingua=lingua_eff`.
3. **Se non trova riga e `lingua_eff <> 'it'`**: ri-prova con `lingua='it'`.
4. Se nemmeno il fallback IT trova riga → stringa placeholder attuale `[MESSAGGIO NON DEFINITO: <codice>]` (nessuna regressione).
5. La formattazione `format(tmpl, p_valore)` resta invariata.

**Firma**: invariata (`p_codice text, p_valore text DEFAULT NULL, p_lingua text DEFAULT NULL`).

**Proposta implementativa (bozza SQL)**:

```sql
CREATE OR REPLACE FUNCTION script.fn_get_messaggio(
  p_codice text,
  p_valore text DEFAULT NULL,
  p_lingua text DEFAULT NULL
) RETURNS text
LANGUAGE plpgsql IMMUTABLE
AS $function$
DECLARE
  tmpl         text;
  lingua_eff   text;
  v_default_lingua CONSTANT text := 'it';
BEGIN
  lingua_eff := coalesce(
    p_lingua,
    current_setting('myapp.user_language', true),
    v_default_lingua
  );

  SELECT messaggio INTO tmpl
    FROM config.messaggi_errore
   WHERE codice = p_codice
     AND lingua = lingua_eff;

  -- Fallback IT se la lingua richiesta non ha la riga e non stavamo già cercando IT
  IF tmpl IS NULL AND lingua_eff <> v_default_lingua THEN
    SELECT messaggio INTO tmpl
      FROM config.messaggi_errore
     WHERE codice = p_codice
       AND lingua = v_default_lingua;
  END IF;

  IF tmpl IS NULL THEN
    RETURN '[MESSAGGIO NON DEFINITO: ' || p_codice || ']';
  END IF;

  IF p_valore IS NOT NULL THEN
    RETURN format(tmpl, p_valore);
  ELSE
    RETURN tmpl;
  END IF;
END;
$function$;
```

### 3.2 `script.fn_log_and_raise_error`

File riferimento: [docs/it/dbzero/script/funzioni/fn_log_and_raise_error.md](../../dbzero/script/funzioni/fn_log_and_raise_error.md)

**Punto da modificare**: blocco "3) Recupera causa e hint" (righe 46-51 della definizione attuale), che oggi fa:

```sql
SELECT causa, soluzione
  INTO v_detail, v_hint
  FROM config.messaggi_errore
 WHERE codice = p_error_code
   AND lingua = v_lang;
```

**Comportamento richiesto**: stesso pattern di `fn_get_messaggio` — se la coppia `(codice, v_lang)` non ha riga e `v_lang <> 'it'`, ritentare con `lingua = 'it'`.

**Proposta implementativa**:

```sql
-- 3) Recupera causa e hint con fallback IT
SELECT causa, soluzione
  INTO v_detail, v_hint
  FROM config.messaggi_errore
 WHERE codice = p_error_code
   AND lingua = v_lang;

IF v_detail IS NULL AND v_hint IS NULL AND v_lang <> 'it' THEN
  SELECT causa, soluzione
    INTO v_detail, v_hint
    FROM config.messaggi_errore
   WHERE codice = p_error_code
     AND lingua = 'it';
END IF;
```

**Firma**: invariata.

**Nota**: la condizione di riprova è sul fatto che *entrambi* `causa` e `soluzione` siano NULL, perché nella tabella sono nullable. Se anche solo uno dei due è valorizzato per la lingua richiesta, si considera la riga "trovata" e non si fa fallback (evita di mescolare causa/hint fra lingue).

**Alternativa più robusta** (preferita): usare un `EXISTS` sulla riga per lingua, così il fallback è attivato solo se la riga **proprio non esiste**:

```sql
IF NOT EXISTS (
    SELECT 1 FROM config.messaggi_errore
     WHERE codice = p_error_code AND lingua = v_lang
  ) AND v_lang <> 'it' THEN
  SELECT causa, soluzione
    INTO v_detail, v_hint
    FROM config.messaggi_errore
   WHERE codice = p_error_code
     AND lingua = 'it';
END IF;
```

Scegliere l'approccio EXISTS: più semantico (riga esiste in EN ma `causa` non ancora tradotto → mantieni NULL EN, non mescolare).

## 4. Costante centralizzata (opzionale ma consigliata)

Per evitare di hardcodare `'it'` in due funzioni, valutare una **funzione helper** o una **costante SQL** tipo:

```sql
CREATE OR REPLACE FUNCTION script.fn_default_lingua()
RETURNS text
LANGUAGE sql IMMUTABLE
AS $$ SELECT 'it'::text $$;
```

E usarla in entrambe le funzioni. Vantaggi: se un domani il default cambia, si tocca un punto solo. Svantaggi: piccola overhead di call.

Decisione finale al team DB — se considerato over-engineering, hardcodare `'it'` va bene (è il codice ISO della lingua di default del progetto, stabile).

## 5. Test pgTAP

File da creare/estendere: `db/pgtap/script/test_fn_get_messaggio.sql` e `db/pgtap/script/test_fn_log_and_raise_error.sql`.

### Test `fn_get_messaggio`

Fixtures:

```sql
INSERT INTO config.messaggi_errore (codice, lingua, messaggio, causa, soluzione) VALUES
  ('TEST_FALLBACK_1', 'it', 'Messaggio IT', 'causa IT', 'soluzione IT'),
  ('TEST_FALLBACK_1', 'en', 'Message EN', 'cause EN', 'solution EN'),
  ('TEST_FALLBACK_2', 'it', 'Solo IT', NULL, NULL);
  -- Nessuna riga EN per TEST_FALLBACK_2
```

Casi:

1. `fn_get_messaggio('TEST_FALLBACK_1', NULL, 'en')` → `'Message EN'` (match diretto).
2. `fn_get_messaggio('TEST_FALLBACK_1', NULL, 'it')` → `'Messaggio IT'` (match diretto).
3. `fn_get_messaggio('TEST_FALLBACK_2', NULL, 'en')` → `'Solo IT'` (fallback IT, no placeholder).
4. `fn_get_messaggio('TEST_INESISTENTE', NULL, 'en')` → `'[MESSAGGIO NON DEFINITO: TEST_INESISTENTE]'` (nemmeno in IT).
5. Con `SET myapp.user_language = 'en'` + `fn_get_messaggio('TEST_FALLBACK_2', NULL, NULL)` → `'Solo IT'`.

### Test `fn_log_and_raise_error`

Casi:

1. Codice presente in EN con causa/soluzione → la RAISE EXCEPTION usa DETAIL/HINT EN.
2. Codice presente solo in IT con `myapp.user_language='en'` → RAISE EXCEPTION usa message+DETAIL+HINT IT (fallback completo).
3. Codice presente in EN ma con `causa=NULL` — comportamento con approccio EXISTS: mantiene EN (causa NULL non forza fallback).

## 6. File coinvolti / dipendenze

- `db/changelog/migrations_v2/20_code/script/` — nuovo changelog `YYYYMMDD-NN-update-fn-get-messaggio-fallback-it.yaml` e `YYYYMMDD-NN-update-fn-log-and-raise-error-fallback-it.yaml` (oppure un singolo changelog se vi è preferenza).
- Entrambe le funzioni già esistono in `20_code` → si applica la convenzione dei changelog con numerazione successiva (NO modifiche in-place ai changelog mergiati — cfr. AGENTS.md "Liquibase v2 Workflow").
- Dopo land: rigenerare doc autogenerata (`docs/it/dbzero/script/funzioni/fn_get_messaggio.md` e `fn_log_and_raise_error.md`) tramite script standard del progetto.
- Aggiornamento doc concettuale in `docs/it/dbzero/script/manual/` non necessario se il contratto resta invariato; comunque consigliato aggiungere un paragrafo "Fallback lingua" in entrambi i manual.

## 7. Conferma di land

Il backend agent attende conferma di land su `dev/db-tid` prima di procedere con:

- Middleware Django per `SET LOCAL myapp.user_language` (fuori scope questa sessione)
- Rollout incrementale traduzioni EN in `config.messaggi_errore`

## 8. Note

- Non introduce breaking change: senza righe EN in tabella, il comportamento con GUC `myapp.user_language='it'` è identico a oggi.
- La funzione resta `IMMUTABLE`: il fallback è deterministico a parità di stato tabella.
- Non richiede modifiche a `config.messaggi_errore` né a `config.lingue`.

---

*Brief DB — Fallback lingua messaggi errore. 2026-04-23. Backend agent.*
