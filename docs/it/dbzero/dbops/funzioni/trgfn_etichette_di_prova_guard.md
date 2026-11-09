{% include-markdown "it/dbzero/dbops/manual/trgfn_etichette_di_prova_guard.md" %}
# ⚙️ Funzione `trgfn_etichette_di_prova_guard`

```sql
CREATE FUNCTION trgfn_etichette_di_prova_guard()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.trgfn_etichette_di_prova_guard()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_ambiente     dbops.installazione.ambiente%TYPE;
    v_chiave       dbops.credenziali_di_prova.chiave%TYPE;
    -- la radice dell'etichetta esiste ancora: nessuna colonna di cui sia il riflesso
    v_radice_viva  boolean := true;
BEGIN
    -- =========================================================
    -- Scopo:
    --   Un'etichetta di prova nasce solo in un'installazione
    --   SVILUPPO, non cambia, e si toglie solo insieme alla
    --   sua radice.
    --
    -- Regole:
    --   - INSERT: la regola pura sull'ambiente vero
    --     (dbops.fn_dati_di_sviluppo_ammessi_su_valori); ambiente
    --     non dichiarato: E_CONFIG_MANCANTE dal lettore;
    --   - DELETE (riga): ammesso solo se la radice non c'e' piu'
    --     (la cascata della FK); la radice non verificabile
    --     vale viva (fail-closed);
    --   - UPDATE, DELETE con la radice viva e TRUNCATE
    --     (istruzione): rifiutati.
    -- =========================================================
    IF TG_OP = 'INSERT' THEN
        v_ambiente := script.fn_ambiente_installazione();
        IF NOT dbops.fn_dati_di_sviluppo_ammessi_su_valori(v_ambiente) THEN
            PERFORM script.fn_log_and_raise_error(
                'dbops', 'trgfn_etichette_di_prova_guard', 'E_DATI_DI_SVILUPPO_IN_PRODUZIONE',
                jsonb_build_object('tabella',  TG_TABLE_NAME,
                                   'chiave',   NEW.chiave,
                                   'ambiente', v_ambiente),
                NULL::uuid,
                v_ambiente);
        END IF;
        RETURN NEW;
    END IF;

    IF TG_OP = 'DELETE' AND TG_LEVEL = 'ROW' THEN
        IF TG_TABLE_NAME = 'credenziali_di_prova' THEN
            IF to_regclass('django.auth_user') IS NOT NULL THEN
                SELECT EXISTS (SELECT 1 FROM django.auth_user au WHERE au.id = OLD.auth_user_id)
                  INTO v_radice_viva;
            END IF;
        ELSIF TG_TABLE_NAME = 'soggetti_di_prova' THEN
            SELECT EXISTS (SELECT 1 FROM anagrafiche.soggetti s WHERE s.id = OLD.soggetto_id)
              INTO v_radice_viva;
        END IF;

        IF NOT v_radice_viva THEN
            RETURN OLD;
        END IF;
    END IF;

    -- Nel TRUNCATE (trigger di istruzione) OLD non c'e'.
    IF TG_LEVEL = 'ROW' THEN
        v_chiave := OLD.chiave;
    END IF;

    PERFORM script.fn_log_and_raise_error(
        'dbops', 'trgfn_etichette_di_prova_guard', 'E_ETICHETTA_DI_PROVA_IMMUTABILE',
        jsonb_build_object('tabella',    TG_TABLE_NAME,
                           'operazione', TG_OP,
                           'chiave',     v_chiave),
        NULL::uuid,
        COALESCE(v_chiave, TG_TABLE_NAME::text));

    RETURN NULL;
END;
$function$

COMMENT ON FUNCTION dbops.trgfn_etichette_di_prova_guard()
IS 'Guard delle etichette di prova (dbops.credenziali_di_prova, dbops.soggetti_di_prova). INSERT: ammesso solo dove l''installazione ammette i dati di sviluppo (dbops.fn_dati_di_sviluppo_ammessi_su_valori), altrimenti E_DATI_DI_SVILUPPO_IN_PRODUZIONE; ambiente non dichiarato: E_CONFIG_MANCANTE. DELETE di una riga: ammesso solo se la sua radice non c''e'' piu'' (django.auth_user per una credenziale, anagrafiche.soggetti per un soggetto), cioe'' dentro la cascata della FK: un''etichetta si toglie solo insieme a cio'' che etichetta. Se la radice non si puo'' verificare (django.auth_user assente) vale viva. UPDATE, DELETE con la radice viva e TRUNCATE: E_ETICHETTA_DI_PROVA_IMMUTABILE.';
```

</div>

---
{% include-markdown "signature-core.md" %}
