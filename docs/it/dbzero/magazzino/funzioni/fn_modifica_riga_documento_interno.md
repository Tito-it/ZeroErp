{% include-markdown "it/dbzero/magazzino/manual/fn_modifica_riga_documento_interno.md" %}
# ⚙️ Funzione `fn_modifica_riga_documento_interno`

```sql
CREATE FUNCTION fn_modifica_riga_documento_interno(p_famiglia text, p_documento_id bigint, p_riga_id bigint, p_dati jsonb)
```

> 🔐 **Sicurezza**: `SECURITY DEFINER` — gira con i privilegi dell'owner `zeroerp_owner`: GRANT e RLS sono i suoi, non quelli di chi la chiama.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION magazzino.fn_modifica_riga_documento_interno(p_famiglia text, p_documento_id bigint, p_riga_id bigint, p_dati jsonb)
 RETURNS jsonb
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$
DECLARE
    v_utente  config.user_override_oggetti.auth_user_id%TYPE;
    v_fam     record;
    v_ammesse text[];   -- nomi di colonna: nessuna colonna di cui siano il riflesso
    v_c       integer;  -- un conteggio: niente da ancorare
    v_riga    jsonb;
BEGIN
    -- Scopo: il gesto «modifica la riga» di un documento interno:
    --   il delta p_dati sulle colonne modificabili. Ritorna la riga.
    v_utente := NULLIF(current_setting('app.current_user_id', true), '')::integer;
    PERFORM script.fn_guard_livello(
        v_utente, 'magazzino',
        (SELECT f.tabella FROM magazzino.fn_documento_interno_famiglia(p_famiglia) AS f),
        'TUTTO');

    SELECT b.* INTO v_fam
      FROM magazzino.fn_documento_interno_blocca(
               p_famiglia, p_documento_id, v_utente,
               'magazzino.fn_modifica_riga_documento_interno') AS b;

    -- La riga e' di quel documento (la testata e' gia' nel perimetro).
    EXECUTE format('SELECT count(*) FROM magazzino.%I r WHERE r.id = $1 AND r.%I = $2',
                   v_fam.tabella_righe, v_fam.colonna_fk)
       INTO v_c
      USING p_riga_id, p_documento_id;
    IF v_c = 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'magazzino', 'magazzino.fn_modifica_riga_documento_interno',
            'E_MAG_DOCUMENTO_RIGA_NON_TROVATA',
            jsonb_build_object('famiglia', v_fam.famiglia, 'documento_id', p_documento_id,
                               'riga_id', p_riga_id),
            NULL::uuid,
            COALESCE(p_riga_id::text, '(nessuna)'));
    END IF;

    v_ammesse := magazzino.fn_documento_interno_colonne_ammesse(v_fam.famiglia, 'riga', 'modifica');
    PERFORM script.fn_guard_campi_ammessi(
        p_dati, v_ammesse,
        'magazzino', 'magazzino.fn_modifica_riga_documento_interno',
        jsonb_build_object('famiglia', v_fam.famiglia, 'documento_id', p_documento_id,
                           'riga_id', p_riga_id));

    -- La testata in DRAFT la chiede il guard delle righe
    -- (E_MAG_DOCUMENTO_RIGHE_CONGELATE), per ogni scrittore.
    v_riga := script.fn_scrivi_riga_da_jsonb(
                  format('magazzino.%I', v_fam.tabella_righe)::regclass,
                  p_dati, jsonb_build_object('id', p_riga_id));

    RETURN (SELECT jsonb_object_agg(e.key, e.value)
              FROM jsonb_each(v_riga) AS e
             WHERE e.key = 'id' OR e.key = ANY (v_ammesse));
END;
$function$

COMMENT ON FUNCTION magazzino.fn_modifica_riga_documento_interno(p_famiglia text, p_documento_id bigint, p_riga_id bigint, p_dati jsonb)
IS 'VERBO: il gesto «modifica la riga» di un documento interno di magazzino (p_famiglia INVENTARIO, RETTIFICA, TRASFERIMENTO), individuata dentro il suo documento (p_documento_id, p_riga_id). p_dati e'' il delta: si scrivono solo le chiavi mandate, una chiave a null scrive NULL, un delta vuoto non scrive niente. Passi: script.fn_guard_livello(utente, magazzino, <tabella della testata>, TUTTO) (E_PERMESSO_NEGATO); la testata nel perimetro, presa FOR UPDATE (magazzino.fn_documento_interno_blocca: E_MAG_DOCUMENTO_NON_TROVATO); la riga e'' di quel documento, altrimenti E_MAG_DOCUMENTO_RIGA_NON_TROVATA; p_dati oggetto con le sole chiavi della lista modifica di magazzino.fn_documento_interno_colonne_ammesse (E_CAMPO_NON_AMMESSO col nome del campo); la scrittura con script.fn_scrivi_riga_da_jsonb, coi trigger della riga (testata in DRAFT: E_MAG_DOCUMENTO_RIGHE_CONGELATE; posizione, quantita'', azienda). SECURITY DEFINER del proprietario, search_path bloccato. Ritorna la riga: id e colonne modificabili.';
```

</div>

---
{% include-markdown "signature-core.md" %}
