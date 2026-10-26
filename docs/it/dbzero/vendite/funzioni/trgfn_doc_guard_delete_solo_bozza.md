{% include-markdown "it/dbzero/vendite/manual/trgfn_doc_guard_delete_solo_bozza.md" %}
# ⚙️ Funzione `trgfn_doc_guard_delete_solo_bozza`

```sql
CREATE FUNCTION trgfn_doc_guard_delete_solo_bozza()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_doc_guard_delete_solo_bozza()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$

DECLARE
  v_documento text;
  v_stato     text;
  v_etichetta text;
BEGIN
  -- =========================================================
  -- Scopo:
  --   Un documento (DDT, ordine, bozza email) si cancella SOLO
  --   finche' e' in bozza. Regola di dominio, decisa da Tid il
  --   2026-08-26; la bozza email entra il 2026-09-25.
  --
  -- ⚠️ Nessuna lettura sotto RLS qui: lo stato sta su OLD, cioe'
  --    sulla riga che il chiamante sta gia' cancellando. Si
  --    legge solo il codice dello stato dal vocabolario, che
  --    RLS non ha (sulla bozza email lo stato e' gia' il codice).
  -- =========================================================
  IF TG_TABLE_NAME = 'ddt' THEN
    v_documento := 'DDT_VENDITA';
    v_etichetta := concat('DDT ', COALESCE(OLD.numero, '#' || OLD.id::text));
    SELECT s.codice_interno::text
      INTO v_stato
      FROM config.stati_doc_ddt s
     WHERE s.id = OLD.stato_doc_ddt_id;

  ELSIF TG_TABLE_NAME = 'ordini' THEN
    v_documento := 'ORDINE_VENDITA';
    v_etichetta := concat('Ordine ', COALESCE(OLD.numero, '#' || OLD.id::text));
    SELECT s.codice_interno::text
      INTO v_stato
      FROM config.stati_doc_ordini s
     WHERE s.id = OLD.stato_doc_ordine_id;

  ELSIF TG_TABLE_SCHEMA = 'config' AND TG_TABLE_NAME = 'email_outbox' THEN
    -- rev 2026-09-25: la bozza email. Lo stato e' gia' il codice.
    v_documento := 'EMAIL';
    v_etichetta := concat('La mail «', left(OLD.oggetto, 80), '»');
    v_stato     := OLD.stato::text;

  ELSE
    -- Errore di MONTAGGIO, come nel gemello di riga.
    PERFORM script.fn_log_and_raise_error(
      'script', 'trgfn_doc_guard_delete_solo_bozza', 'E_DOC_TIPO_NON_GESTITO',
      jsonb_build_object('table', TG_TABLE_NAME, 'id', OLD.id),
      NULL::uuid,
      TG_TABLE_NAME);
  END IF;

  -- ⚠️ IS DISTINCT FROM e non <>: se il vocabolario non
  --    restituisse lo stato (riga di stato mancante, che la FK
  --    non dovrebbe permettere) il guard RIFIUTA. Fail-closed:
  --    su un verbo distruttivo il default e' il no.
  IF v_stato IS DISTINCT FROM 'DRAFT' THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite', 'trgfn_doc_guard_delete_solo_bozza', 'E_DELETE_DOC_NON_BOZZA',
      jsonb_build_object('table', TG_TABLE_NAME,
                         'id', OLD.id,
                         'documento', v_documento,
                         'stato', v_stato),
      NULL::uuid,
      v_etichetta,
      COALESCE(v_stato, '<sconosciuto>'));
  END IF;

  RETURN OLD;
END;
$function$

COMMENT ON FUNCTION vendite.trgfn_doc_guard_delete_solo_bozza()
IS 'Un documento (vendite.ddt, vendite.ordini) si cancella SOLO finche'' e'' in bozza. Nasce il 2026-08-26 da una decisione di Tid: la regola viveva solo nel backend, in due frozenset Python (_STATI_MODIFICABILI = {DRAFT} in ddt_service e ordini_service), quindi ogni altro percorso la saltava. ⛔ E senza questo guard il suo gemello di riga (vendite.trgfn_dlt_block_ordrig_ddtrig, rev 20260826-21) sarebbe FAIL-OPEN: le righe sono in ON DELETE CASCADE dalla testata e — provato con tabelle temporanee — in un BEFORE DELETE di riga innescato da un cascade la testata risulta gia'' cancellata, quindi il guard di riga non puo'' leggerne lo stato. Il cascade sarebbe la porta di servizio. ⭐ I due guard sono UNA COPPIA: togliendone uno l''altro non si indebolisce, diventa aggirabile. ⚠️ IS DISTINCT FROM ''DRAFT'' e non <>: se il vocabolario non restituisse lo stato il guard rifiuta — su un verbo distruttivo il default e'' il no. ⚠️ Nessuna lettura sotto RLS: lo stato sta su OLD, e il vocabolario config.stati_doc_* non ha RLS. Fascia _a10_ perche'' i BEFORE ROW girano in ordine alfabetico e il rifiuto deve precedere trg_*_z90_storico_upd_dlt. Non generica di proposito: due testate, due tabelle di stato, due nomi di colonna — una versione parametrizzata costerebbe SQL dinamico su due assi per coprire due casi. ⭐ rev 2026-10-19 (20261019-67, brief-db-grammatica-unica-documenti lotto 2a, G-1 di Tid): la grammatica delle testate passa ai codici delle sorgenti (DDT -> DDT_VENDITA, ORDINE -> ORDINE_VENDITA, OFFERTA -> OFFERTA_COMMERCIALE, RESO -> RESO_VENDITA, EMAIL_BOZZA -> EMAIL; PREVENTIVO, CONTRATTO, COMMESSA, FATTURA invariati); dove sopra si legge un codice corto come selettore, oggi vale il codice della sorgente.';
```

</div>

---
{% include-markdown "signature-core.md" %}
