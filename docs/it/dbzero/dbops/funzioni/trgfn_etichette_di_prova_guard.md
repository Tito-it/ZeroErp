# ⚙️ Funzione `trgfn_etichette_di_prova_guard`

```sql
CREATE FUNCTION trgfn_etichette_di_prova_guard()
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.trgfn_etichette_di_prova_guard()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_ambiente dbops.installazione.ambiente%TYPE;
    v_chiave   dbops.credenziali_di_prova.chiave%TYPE;
BEGIN
    -- =========================================================
    -- Scopo:
    --   Un'etichetta di prova nasce solo in un'installazione
    --   SVILUPPO, e poi non cambia e non si toglie.
    --
    -- Regole:
    --   - INSERT: la regola pura sull'ambiente vero
    --     (dbops.fn_dati_di_sviluppo_ammessi_su_valori); ambiente
    --     non dichiarato: E_CONFIG_MANCANTE dal lettore;
    --   - UPDATE, DELETE (riga) e TRUNCATE (istruzione): sempre
    --     rifiutati.
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
IS 'Guard delle etichette di prova (dbops.credenziali_di_prova, dbops.soggetti_di_prova). INSERT: ammesso solo se dbops.fn_dati_di_sviluppo_ammessi_su_valori(script.fn_ambiente_installazione()), altrimenti E_DATI_DI_SVILUPPO_IN_PRODUZIONE (lo stesso codice del verbo dei dati di sviluppo: e'' la stessa decisione); ambiente non dichiarato: E_CONFIG_MANCANTE. UPDATE, DELETE (trigger di riga) e TRUNCATE (trigger di istruzione): sempre rifiutati con E_ETICHETTA_DI_PROVA_IMMUTABILE, perche'' togliere un''etichetta nasconderebbe la radice al presidio. Il proprietario puo'' disattivare il trigger: la difesa contro un DBA malevolo sono i ruoli. Brief: brief-db-processi-accensione-per-ambiente (R-4).';
```

</div>

---
{% include-markdown "signature-core.md" %}
