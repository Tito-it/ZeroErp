# ⚙️ Funzione `trgfn_email_allegato_guard_solo_bozza`

```sql
CREATE FUNCTION trgfn_email_allegato_guard_solo_bozza()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION config.trgfn_email_allegato_guard_solo_bozza()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$

DECLARE
  v_riga      config.email_allegato%ROWTYPE;   -- NEW, o OLD sul DELETE
  -- ⚠️ bigint[] nudo: `%TYPE[]` non e' sintassi PostgreSQL. E' un
  --   array di config.email_outbox.id (bigint).
  v_bozze     bigint[];                         -- una, due se cambia bozza
  v_bozza_id  config.email_outbox.id%TYPE;
  v_stato     text;   -- dal lettore: RETURNS TABLE(stato text, ...)
  v_etichetta text;   -- idem
  v_verbo     text;   -- la frase per l'operatore, non una colonna
BEGIN
  -- =========================================================
  -- Scopo:
  --   Gli allegati di una mail si aggiungono, modificano e
  --   tolgono SOLO finche' la mail e' una bozza DRAFT. Dopo
  --   l'invio l'allegato e' anche storia del log.
  --   ⭐ Unica eccezione: l'aggancio al log (UPDATE del solo
  --   email_log_id verso un valore), che il backend fa a
  --   bozza READY e rifa' a ogni nuovo tentativo.
  -- =========================================================
  IF TG_OP = 'DELETE' THEN
    v_riga := OLD;
  ELSE
    v_riga := NEW;
  END IF;

  -- ── L'aggancio al log: passa ──────────────────────────
  IF TG_OP = 'UPDATE'
     AND NEW.email_log_id IS NOT NULL
     AND (to_jsonb(NEW) - 'email_log_id') = (to_jsonb(OLD) - 'email_log_id') THEN
    RETURN NEW;
  END IF;

  v_verbo := CASE TG_OP
               WHEN 'INSERT' THEN 'aggiungere'
               WHEN 'UPDATE' THEN 'modificare'
               ELSE               'togliere'
             END;

  -- ── Le bozze da guardare ──────────────────────────────
  -- Su UPDATE anche quella di provenienza: spostare un allegato
  -- da una mail spedita a una bozza e' comunque toccare la
  -- mail spedita.
  v_bozze := ARRAY[]::bigint[];
  IF TG_OP = 'UPDATE' AND OLD.email_outbox_id IS NOT NULL THEN
    v_bozze := v_bozze || OLD.email_outbox_id;
  END IF;
  IF v_riga.email_outbox_id IS NOT NULL
     AND NOT (v_riga.email_outbox_id = ANY (v_bozze)) THEN
    v_bozze := v_bozze || v_riga.email_outbox_id;
  END IF;

  -- ── Nessuna bozza, ma un log: e' storia ───────────────
  IF cardinality(v_bozze) = 0
     AND (v_riga.email_log_id IS NOT NULL
          OR (TG_OP = 'UPDATE' AND OLD.email_log_id IS NOT NULL)) THEN
    PERFORM script.fn_log_and_raise_error(
      'config', TG_NAME::text, 'E_EMAIL_ALLEGATO_NON_BOZZA',
      jsonb_build_object('table',      TG_TABLE_SCHEMA || '.' || TG_TABLE_NAME,
                         'id',         v_riga.id,
                         'email_log_id', v_riga.email_log_id,
                         'operazione', TG_OP),
      NULL::uuid,
      'La mail',
      'registrata nel log, senza bozza',
      v_verbo);
  END IF;

  FOREACH v_bozza_id IN ARRAY v_bozze LOOP
    v_stato := NULL;
    v_etichetta := NULL;

    SELECT t.stato, t.etichetta
      INTO v_stato, v_etichetta
      FROM script.fn_get_stato_testata_documento('EMAIL', v_bozza_id) AS t;

    -- Assente: CASCADE dalla bozza (gia' ammesso solo in DRAFT
    -- dal guard della bozza), o FK che parlera'. Si passa.
    CONTINUE WHEN v_stato IS NULL;

    IF v_stato <> 'DRAFT' THEN
      PERFORM script.fn_log_and_raise_error(
        'config', TG_NAME::text, 'E_EMAIL_ALLEGATO_NON_BOZZA',
        jsonb_build_object('table',           TG_TABLE_SCHEMA || '.' || TG_TABLE_NAME,
                           'id',              v_riga.id,
                           'email_outbox_id', v_bozza_id,
                           'stato',           v_stato,
                           'operazione',      TG_OP),
        NULL::uuid,
        v_etichetta,
        v_stato,
        v_verbo);
    END IF;
  END LOOP;

  RETURN v_riga;
END;
$function$

COMMENT ON FUNCTION config.trgfn_email_allegato_guard_solo_bozza()
IS 'Gli allegati di una mail si aggiungono, modificano e tolgono solo finche'' la sua bozza (config.email_outbox) e'' DRAFT: dopo l''invio l''allegato e'' anche storia del log. Unica eccezione: l''aggancio al log, cioe'' un UPDATE che cambia solo email_log_id verso un valore — il backend lo fa a bozza READY e lo rifa'' a ogni nuovo tentativo. Bozza assente = CASCADE dalla bozza (ammesso solo in DRAFT da vendite.trgfn_doc_guard_delete_solo_bozza) o FK che parlera'': passa. Allegato con log e senza bozza: storia, rifiutato. Lo stato si legge da script.fn_get_stato_testata_documento (SECURITY DEFINER), perche'' la bozza ha la RLS. Codice E_EMAIL_ALLEGATO_NON_BOZZA. Brief: brief-db-email-visibilita-per-ambito. rev 2026-09-25. ⭐ rev 2026-10-19 (20261019-63, brief-db-grammatica-unica-documenti lotto 2a, G-1 di Tid): la grammatica delle testate passa ai codici delle sorgenti (DDT -> DDT_VENDITA, ORDINE -> ORDINE_VENDITA, OFFERTA -> OFFERTA_COMMERCIALE, RESO -> RESO_VENDITA, EMAIL_BOZZA -> EMAIL; PREVENTIVO, CONTRATTO, COMMESSA, FATTURA invariati); dove sopra si legge un codice corto come selettore, oggi vale il codice della sorgente.';
```

---
{% include-markdown "signature-core.md" %}
