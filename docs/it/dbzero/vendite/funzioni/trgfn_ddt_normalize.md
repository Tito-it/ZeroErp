{% include-markdown "it/dbzero/vendite/manual/trgfn_ddt_normalize.md" %}
# ⚙️ Funzione `trgfn_ddt_normalize`

```sql
CREATE FUNCTION trgfn_ddt_normalize()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_ddt_normalize()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
  -- Il BA cambia su questo UPDATE: le copie non toccate dal
  -- chiamante seguono il BA nuovo.
  v_ba_cambiato boolean;
BEGIN
  -- =========================================================
  -- Scopo: normalizzazione DDT su INSERT/UPDATE.
  --   1. anno/data se numero presente (INSERT).
  --   2. eredita billing/utility/valuta/emittente dall'ordine
  --      sorgente (ORDINE_VENDITA, lookup per codice_interno) su
  --      INSERT se non gia' valorizzati.
  --   3. fallback emittente da billing_account (standalone).
  --   2-bis. (rev 2026-10-10) destinatario e utility dal BA, col BB
  --      script.fn_cliente_dal_billing_account (INSERT e cambio in
  --      bozza di BA, destinatario o utility).
  -- =========================================================
  -- 1. anno/data
  IF TG_OP = 'INSERT' AND (NEW.numero IS NOT NULL AND btrim(NEW.numero) <> '') THEN
    IF NEW.anno IS NULL OR NEW.anno = 0 THEN
      NEW.anno := EXTRACT(YEAR FROM script.fn_data_operativa())::smallint;
    END IF;
    IF NEW.data IS NULL THEN
      NEW.data := script.fn_data_operativa();
    END IF;
  END IF;
  -- 2. eredita billing/utility/valuta/emittente da ordine sorgente
  IF TG_OP = 'INSERT'
     AND NEW.sorgente_tipo_id IS NOT NULL
     AND NEW.sorgente_uid IS NOT NULL
     AND (NEW.billing_account_id IS NULL
          OR NEW.utility_id IS NULL
          OR NEW.valuta_id IS NULL
          OR NEW.emittente_fiscale_id IS NULL)
  THEN
    IF EXISTS (
      SELECT 1 FROM config.sorgenti
      WHERE id = NEW.sorgente_tipo_id AND codice_interno = 'ORDINE_VENDITA'
    ) THEN
      SELECT
        COALESCE(NEW.billing_account_id, o.billing_account_id),
        COALESCE(NEW.utility_id, ba.utility_id),
        COALESCE(NEW.valuta_id, o.valuta_id),
        COALESCE(NEW.emittente_fiscale_id, o.emittente_fiscale_id)
      INTO
        NEW.billing_account_id,
        NEW.utility_id,
        NEW.valuta_id,
        NEW.emittente_fiscale_id
      FROM vendite.ordini o
      LEFT JOIN anagrafiche.billing_account ba
        ON ba.id = o.billing_account_id
      WHERE o.uid = NEW.sorgente_uid
      LIMIT 1;
    END IF;
  END IF;
  -- 2-bis. Destinatario e utility (rev 2026-10-10,
  --   brief-db-esecutivi-ba-coppia §10.2 domanda 2, regola del 2): col
  --   BA sono COPIE di cio' che il BA dice. Cosa valgono lo dice il BB
  --   (le scrive se mancano, E_DOC_CLIENTE_DIVERSO_DA_BA se
  --   dissentono); QUANDO, lo dice il DDT:
  --   * su INSERT;
  --   * su un UPDATE che tocca BA, destinatario o utility (in bozza:
  --     fuori le blocca trg_ddt_a05_lock_fuori_bozza_upd). Se il BA
  --     cambia, la copia che il chiamante non ha toccato va al BB come
  --     NULL e segue il BA nuovo.
  --   Un BA tolto toglie la utility (CHECK «tutti e due o nessuno») e
  --   lascia il destinatario, che senza BA e' libero.
  IF NEW.billing_account_id IS NOT NULL THEN
    IF TG_OP = 'INSERT'
       OR NEW.billing_account_id IS DISTINCT FROM OLD.billing_account_id
       OR NEW.destinatario_soggetto_ruolo_id IS DISTINCT FROM OLD.destinatario_soggetto_ruolo_id
       OR NEW.utility_id IS DISTINCT FROM OLD.utility_id
    THEN
      v_ba_cambiato := TG_OP = 'UPDATE'
                       AND NEW.billing_account_id IS DISTINCT FROM OLD.billing_account_id;
      SELECT f.soggetto_ruolo_id, f.utility_id
        INTO NEW.destinatario_soggetto_ruolo_id, NEW.utility_id
        FROM script.fn_cliente_dal_billing_account(
                 NEW.billing_account_id,
                 CASE WHEN v_ba_cambiato
                           AND NEW.destinatario_soggetto_ruolo_id IS NOT DISTINCT FROM OLD.destinatario_soggetto_ruolo_id
                      THEN NULL ELSE NEW.destinatario_soggetto_ruolo_id END,
                 CASE WHEN v_ba_cambiato
                           AND NEW.utility_id IS NOT DISTINCT FROM OLD.utility_id
                      THEN NULL ELSE NEW.utility_id END,
                 'DDT ' || COALESCE(NEW.numero, '#' || NEW.id::text),
                 'destinatario_soggetto_ruolo_id',
                 NEW.tx_id) f;
    END IF;
  ELSIF TG_OP = 'UPDATE'
        AND OLD.billing_account_id IS NOT NULL
        AND NEW.utility_id IS NOT DISTINCT FROM OLD.utility_id THEN
    NEW.utility_id := NULL;
  END IF;
  -- 3. fallback standalone: emittente da billing_account (convenzione PK).
  IF TG_OP = 'INSERT'
     AND NEW.emittente_fiscale_id IS NULL
     AND NEW.billing_account_id IS NOT NULL
  THEN
    NEW.emittente_fiscale_id :=
      anagrafiche.fn_get_emittente_fiscale_pk(NEW.billing_account_id);
  END IF;
  RETURN NEW;
END;
$function$

COMMENT ON FUNCTION vendite.trgfn_ddt_normalize()
IS 'Normalize DDT: anno/data; eredita billing/utility/valuta/emittente da ordine sorgente (ORDINE_VENDITA, per codice_interno) su INSERT; fallback emittente da billing_account (fn_get_emittente_fiscale_pk). rev 2026-07-10 (§15 emittente). rev 2026-10-09 (brief-db-esecutivi-ba-coppia, D-4/D-5): punto 2-bis, utility e destinatario sono copie del billing account. rev 2026-10-10 (stesso brief, §10.2 domanda 2, regola del 2): il cosa del 2-bis lo dice il BB script.fn_cliente_dal_billing_account — copie scritte se mancano, E_DOC_CLIENTE_DIVERSO_DA_BA se dissentono (prima il 23503 di fk_ddt_ba_cliente, che resta la rete sotto); il quando resta qui — INSERT, e UPDATE in bozza di BA, destinatario o utility, con la copia non toccata che segue il BA nuovo. Un BA tolto toglie la utility e lascia il destinatario.';
```

</div>

---
{% include-markdown "signature-core.md" %}
