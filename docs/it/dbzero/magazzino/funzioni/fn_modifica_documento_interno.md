{% include-markdown "it/dbzero/magazzino/manual/fn_modifica_documento_interno.md" %}
# ⚙️ Funzione `fn_modifica_documento_interno`

```sql
CREATE FUNCTION fn_modifica_documento_interno(p_famiglia text, p_documento_id bigint, p_dati jsonb)
```

> 🔐 **Sicurezza**: `SECURITY DEFINER` — gira con i privilegi dell'owner `zeroerp_owner`: GRANT e RLS sono i suoi, non quelli di chi la chiama.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION magazzino.fn_modifica_documento_interno(p_famiglia text, p_documento_id bigint, p_dati jsonb)
 RETURNS jsonb
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$
DECLARE
    v_utente  config.user_override_oggetti.auth_user_id%TYPE;
    v_fam     record;
    v_ammesse text[];   -- nomi di colonna: nessuna colonna di cui siano il riflesso
    v_riga    jsonb;
BEGIN
    -- Scopo: il gesto «modifica la testata» di un documento
    --   interno: il delta p_dati sulle colonne modificabili, con
    --   il documento in DRAFT. Ritorna la testata.
    v_utente := script.fn_utente_di_sessione('magazzino.fn_modifica_documento_interno');
    PERFORM script.fn_guard_livello(
        v_utente, 'magazzino',
        (SELECT f.tabella FROM magazzino.fn_documento_interno_famiglia(p_famiglia) AS f),
        'TUTTO');

    SELECT b.* INTO v_fam
      FROM magazzino.fn_documento_interno_blocca(
               p_famiglia, p_documento_id, v_utente,
               'magazzino.fn_modifica_documento_interno') AS b;

    v_ammesse := magazzino.fn_documento_interno_colonne_ammesse(v_fam.famiglia, 'testata', 'modifica');
    PERFORM script.fn_guard_campi_ammessi(
        p_dati, v_ammesse,
        'magazzino', 'magazzino.fn_modifica_documento_interno',
        jsonb_build_object('famiglia', v_fam.famiglia, 'documento_id', p_documento_id));

    -- La testata si modifica in bozza, come le righe: lo dice la
    -- capability (can_edit_testata), e nessun trigger lo fa sulla
    -- testata. Un delta vuoto non scrive niente: passa anche fuori
    -- bozza, e ritorna la testata.
    IF v_fam.stato <> 'DRAFT' AND p_dati <> '{}'::jsonb THEN
        PERFORM script.fn_log_and_raise_error(
            'magazzino', 'magazzino.fn_modifica_documento_interno',
            'E_MAG_DOCUMENTO_TESTATA_CONGELATA',
            jsonb_build_object('famiglia', v_fam.famiglia, 'documento_id', p_documento_id,
                               'stato', v_fam.stato),
            NULL::uuid,
            v_fam.stato);
    END IF;

    v_riga := script.fn_scrivi_riga_da_jsonb(
                  format('magazzino.%I', v_fam.tabella)::regclass,
                  p_dati, jsonb_build_object('id', p_documento_id));

    RETURN (SELECT jsonb_object_agg(e.key, e.value)
              FROM jsonb_each(v_riga) AS e
             WHERE e.key = 'id' OR e.key = ANY (v_ammesse));
END;
$function$

COMMENT ON FUNCTION magazzino.fn_modifica_documento_interno(p_famiglia text, p_documento_id bigint, p_dati jsonb)
IS 'VERBO: il gesto «modifica la testata» di un documento interno di magazzino (p_famiglia INVENTARIO, RETTIFICA, TRASFERIMENTO). p_dati e'' il delta: si scrivono solo le chiavi mandate, una chiave a null scrive NULL, un delta vuoto non scrive niente. Passi: script.fn_guard_livello(utente, magazzino, <tabella della testata>, TUTTO) (E_PERMESSO_NEGATO, anche per una famiglia che non esiste); la testata nel perimetro, presa FOR UPDATE (magazzino.fn_documento_interno_blocca: E_MAG_DOCUMENTO_NON_TROVATO); p_dati oggetto con le sole chiavi della lista modifica di magazzino.fn_documento_interno_colonne_ammesse (E_CAMPO_NON_AMMESSO col nome del campo): la data, e per l''inventario la descrizione; il documento in DRAFT, altrimenti E_MAG_DOCUMENTO_TESTATA_CONGELATA; la scrittura con script.fn_scrivi_riga_da_jsonb, coi trigger della tabella. Lo stato non e'' un campo: ha il suo verbo. SECURITY DEFINER del proprietario, search_path bloccato. Ritorna la testata: id e colonne modificabili.';
```

</div>

---
{% include-markdown "signature-core.md" %}
