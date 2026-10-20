{% include-markdown "it/dbzero/script/manual/trgfn_doc_guard_emittente_ba.md" %}
# ⚙️ Funzione `trgfn_doc_guard_emittente_ba`

```sql
CREATE FUNCTION trgfn_doc_guard_emittente_ba()
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.trgfn_doc_guard_emittente_ba()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
  -- TG_ARGV: [0] etichetta del documento, [1] colonna che lo
  -- identifica, [2] colonna dell'emittente, [3] codice d'errore.
  v_tipo        text;
  v_col_ident   text;
  v_col_emit    text;
  v_codice      config.codici_errore.codice%TYPE;
  v_new         jsonb;
  v_ba          anagrafiche.billing_account.id%TYPE;
  v_emittente   bigint;  -- id della colonna [2]: emittente_fiscale_id o emittente_soggetto_ruolo_id
  v_atteso      bigint;  -- lo stesso, risolto dal BA
  v_documento   text;
  v_nome        text;
  v_nome_atteso text;
  v_ba_codice   anagrafiche.billing_account.codice%TYPE;
  v_contesto    jsonb;
BEGIN
  -- =========================================================
  -- Scopo:
  --   Un documento di vendita e' emesso dall'azienda del suo
  --   cliente: l'emittente e' quello che il billing account
  --   risolve. Building block, montato BEFORE INSERT OR UPDATE OF
  --   (billing_account_id, <colonna dell'emittente>).
  -- ⚠️ BA NULL: esce, su ogni tabella. Dove il BA e' NOT NULL
  --   parla il vincolo, che si controlla dopo i BEFORE ROW; dove e'
  --   NULL ammesso (DDT, reso) non c'e' niente da confrontare.
  -- ⚠️ I risolutori possono propagare E_EMITTENTE_DEFAULT_MISSING:
  --   e' un difetto di configurazione, non si maschera.
  -- =========================================================
  v_new := to_jsonb(NEW);

  -- ── Argomenti: errore di MONTAGGIO, non di dato ───────────
  IF COALESCE(array_length(TG_ARGV, 1), 0) <> 4
     OR TG_OP NOT IN ('INSERT', 'UPDATE')
     OR TG_ARGV[2] NOT IN ('emittente_fiscale_id', 'emittente_soggetto_ruolo_id')
     OR NOT (v_new ? TG_ARGV[1])
     OR NOT (v_new ? TG_ARGV[2])
     OR NOT (v_new ? 'billing_account_id') THEN
    PERFORM script.fn_log_and_raise_error(
      'database', TG_NAME::text, 'E_DOC_RIGHE_LOCK_MONTAGGIO',
      jsonb_build_object('trigger', TG_NAME,
                         'table',   TG_TABLE_SCHEMA || '.' || TG_TABLE_NAME,
                         'evento',  TG_OP,
                         'tg_argv', TG_ARGV),
      NULL::uuid,
      TG_NAME::text,
      TG_TABLE_SCHEMA || '.' || TG_TABLE_NAME,
      'attesi: etichetta del documento, colonna che lo identifica, colonna dell''emittente (emittente_fiscale_id | emittente_soggetto_ruolo_id) e codice d''errore, su una tabella con billing_account_id');
  END IF;

  v_tipo      := TG_ARGV[0];
  v_col_ident := TG_ARGV[1];
  v_col_emit  := TG_ARGV[2];
  v_codice    := TG_ARGV[3];

  v_ba := (v_new ->> 'billing_account_id')::bigint;
  IF v_ba IS NULL THEN
    RETURN NEW;
  END IF;

  v_emittente := (v_new ->> v_col_emit)::bigint;
  IF v_col_emit = 'emittente_fiscale_id' THEN
    v_atteso := anagrafiche.fn_get_emittente_fiscale_pk(v_ba);
  ELSE
    v_atteso := anagrafiche.fn_get_emittente_fiscale_id(v_ba);
  END IF;

  IF v_emittente IS NOT DISTINCT FROM v_atteso THEN
    RETURN NEW;
  END IF;

  -- ── La frase: nomi, non id (D-2) ─────────────────────────
  v_documento := v_tipo || ' '
                 || COALESCE(v_new ->> v_col_ident, '#' || (v_new ->> 'id'));

  -- Il nome dell'azienda: dal ruolo dell'emittente al soggetto.
  -- Con la PK dell'emittente si passa da emittenti_fiscali.
  SELECT s.ragione_sociale_completa INTO v_nome
    FROM anagrafiche.soggetti_ruoli sr
    JOIN anagrafiche.soggetti s ON s.id = sr.soggetto_id
   WHERE sr.id = CASE WHEN v_col_emit = 'emittente_fiscale_id'
                      THEN (SELECT ef.soggetto_ruolo_id FROM anagrafiche.emittenti_fiscali ef
                             WHERE ef.id = v_emittente)
                      ELSE v_emittente END;
  SELECT s.ragione_sociale_completa INTO v_nome_atteso
    FROM anagrafiche.soggetti_ruoli sr
    JOIN anagrafiche.soggetti s ON s.id = sr.soggetto_id
   WHERE sr.id = CASE WHEN v_col_emit = 'emittente_fiscale_id'
                      THEN (SELECT ef.soggetto_ruolo_id FROM anagrafiche.emittenti_fiscali ef
                             WHERE ef.id = v_atteso)
                      ELSE v_atteso END;
  SELECT ba.codice INTO v_ba_codice
    FROM anagrafiche.billing_account ba
   WHERE ba.id = v_ba;

  v_contesto := jsonb_build_object(
      'tabella',             TG_TABLE_SCHEMA || '.' || TG_TABLE_NAME,
      'id',                  v_new -> 'id',
      'billing_account_id',  v_ba,
      'colonna',             v_col_emit,
      'emittente',           v_emittente,
      'emittente_atteso',    v_atteso);
  -- `campo` solo se l'errore e' di una persona: su un TECNICO
  -- (la commessa) non c'e' un campo da accendere.
  IF EXISTS (SELECT 1 FROM config.codici_errore ce
              WHERE ce.codice = v_codice AND ce.classe <> 'TECNICO') THEN
    v_contesto := v_contesto || jsonb_build_object('campo', v_col_emit);
  END IF;

  PERFORM script.fn_log_and_raise_error(
    'database', TG_NAME::text, v_codice,
    v_contesto,
    (v_new ->> 'tx_id')::uuid,
    v_documento,
    COALESCE(v_nome,        '#' || COALESCE(v_emittente::text, '?')),
    COALESCE(v_nome_atteso, '#' || COALESCE(v_atteso::text, '?')),
    COALESCE(v_ba_codice,   '#' || v_ba::text));
  -- fn_log_and_raise_error solleva: non si arriva qui.
  RETURN NEW;
END;
$function$

COMMENT ON FUNCTION script.trgfn_doc_guard_emittente_ba()
IS 'Building block (2026-10-10, brief-db-guard-emittente-ba-unico): l''emittente di un documento di vendita e'' quello che il suo billing account risolve. BEFORE INSERT OR UPDATE OF (billing_account_id, <colonna dell''emittente>) FOR EACH ROW; TG_ARGV = [0] etichetta del documento, [1] colonna che lo identifica, [2] colonna dell''emittente (emittente_fiscale_id -> anagrafiche.fn_get_emittente_fiscale_pk; emittente_soggetto_ruolo_id -> anagrafiche.fn_get_emittente_fiscale_id), [3] codice d''errore (E_DOC_EMITTENTE_BA_INCOERENTE per preventivo, offerta, contratto, ordine, DDT, reso; E_COMMESSA_EMITTENTE_BA_INCOERENTE, TECNICO, per la commessa). BA NULL: esce. VARIADIC: documento, nome dell''azienda indicata, nome di quella del cliente (soggetti.ragione_sociale_completa, o l''id), codice del BA; nel contesto gli id, e `campo` solo se il codice non e'' TECNICO; tx_id della riga. Montaggio errato: E_DOC_RIGHE_LOCK_MONTAGGIO. I risolutori possono propagare E_EMITTENTE_DEFAULT_MISSING. Regola del 2: sostituisce trgfn_{preventivi,offerte_commerciali,contratti,ordini,ddt,resi,commesse}_guard_emittente_ba (ritirate da 20261010-19).';
```

</div>

---
{% include-markdown "signature-core.md" %}
