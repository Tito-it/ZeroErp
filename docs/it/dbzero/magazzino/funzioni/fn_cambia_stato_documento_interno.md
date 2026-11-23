{% include-markdown "it/dbzero/magazzino/manual/fn_cambia_stato_documento_interno.md" %}
# ⚙️ Funzione `fn_cambia_stato_documento_interno`

```sql
CREATE FUNCTION fn_cambia_stato_documento_interno(p_famiglia text, p_documento_id bigint, p_stato text)
```

> 🔐 **Sicurezza**: `SECURITY DEFINER` — gira con i privilegi dell'owner `zeroerp_owner`: GRANT e RLS sono i suoi, non quelli di chi la chiama.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION magazzino.fn_cambia_stato_documento_interno(p_famiglia text, p_documento_id bigint, p_stato text)
 RETURNS text
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$
DECLARE
    v_utente config.user_override_oggetti.auth_user_id%TYPE;
    v_fam    record;
    v_riga   jsonb;
BEGIN
    -- Scopo: il gesto conferma, riapri o annulla di un documento
    --   interno: lo stato p_stato sulla testata. La matrice la fa
    --   rispettare il trigger. Ritorna lo stato scritto.
    v_utente := script.fn_utente_di_sessione('magazzino.fn_cambia_stato_documento_interno');
    PERFORM script.fn_guard_livello(
        v_utente, 'magazzino',
        (SELECT f.tabella FROM magazzino.fn_documento_interno_famiglia(p_famiglia) AS f),
        'TUTTO');

    SELECT b.* INTO v_fam
      FROM magazzino.fn_documento_interno_blocca(
               p_famiglia, p_documento_id, v_utente,
               'magazzino.fn_cambia_stato_documento_interno') AS b;

    -- La matrice (magazzino.fn_documento_interno_transizioni) e la
    -- porta POSTED le dice trgfn_documento_interno_guard_transizione;
    -- un valore fuori dal vocabolario lo ferma il CHECK della tabella.
    v_riga := script.fn_scrivi_riga_da_jsonb(
                  format('magazzino.%I', v_fam.tabella)::regclass,
                  jsonb_build_object(v_fam.colonna_stato, p_stato),
                  jsonb_build_object('id', p_documento_id));

    RETURN v_riga ->> v_fam.colonna_stato;
END;
$function$

COMMENT ON FUNCTION magazzino.fn_cambia_stato_documento_interno(p_famiglia text, p_documento_id bigint, p_stato text)
IS 'VERBO: i gesti conferma, riapri e annulla di un documento interno di magazzino (p_famiglia INVENTARIO, RETTIFICA, TRASFERIMENTO): scrive p_stato sulla testata. Passi: script.fn_guard_livello(utente, magazzino, <tabella della testata>, TUTTO) (E_PERMESSO_NEGATO); la testata nel perimetro, presa FOR UPDATE (magazzino.fn_documento_interno_blocca: E_MAG_DOCUMENTO_NON_TROVATO); la scrittura dello stato. La matrice degli stati la fa rispettare trgfn_documento_interno_guard_transizione, che legge magazzino.fn_documento_interno_transizioni (fuori matrice: E_MAG_DOCUMENTO_TRANSIZIONE_NON_AMMESSA); POSTED non si chiede, lo scrive solo la registrazione (E_MAG_DOCUMENTO_POSTED_SOLO_DA_OPERAZIONE); un valore fuori vocabolario lo ferma il CHECK della tabella. Lo stato uguale a quello di oggi non scrive niente. SECURITY DEFINER del proprietario, search_path bloccato. Ritorna lo stato scritto.';
```

</div>

---
{% include-markdown "signature-core.md" %}
