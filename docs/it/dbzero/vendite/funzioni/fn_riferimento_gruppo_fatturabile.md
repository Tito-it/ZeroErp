{% include-markdown "it/dbzero/vendite/manual/fn_riferimento_gruppo_fatturabile.md" %}
# ⚙️ Funzione `fn_riferimento_gruppo_fatturabile`

```sql
CREATE FUNCTION fn_riferimento_gruppo_fatturabile(p_gruppo_key text)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_riferimento_gruppo_fatturabile(p_gruppo_key text)
 RETURNS text
 LANGUAGE plpgsql
 STABLE
AS $function$
-- Scopo: il RIFERIMENTO leggibile di un gruppo fatturabile — cioe'
--        cio' che una persona riconosce al posto della chiave.
--        'ORDINE_VENDITA:01a06ce4-…' -> 'ORD0036004'.
-- Ritorna: il numero del documento; se non c'e', il codice della
--        commessa; se non c'e' nemmeno quello, la CHIAVE GREZZA.
-- ⚠️ NON SOLLEVA MAI: la chiama una lista.
DECLARE
    v_key         text := NULLIF(btrim(COALESCE(p_gruppo_key, '')), '');
    v_src         record;
    v_documento   vendite.commesse_sorgenti.sorgente_id%TYPE;
    v_numero      text;
    v_commessa_id vendite.commesse.id%TYPE;
    v_codice      vendite.commesse.codice%TYPE;
BEGIN
    -- ⚠️ NULL entra e NULL esce: sulla scheda Critiche una chiave
    --    assente vuol dire «la segnalazione e' del GIRO», e li' non
    --    c'e' nessun documento da nominare. Inventare un'etichetta
    --    direbbe una cosa falsa.
    IF v_key IS NULL THEN
        RETURN NULL;
    END IF;

    SELECT * INTO v_src
      FROM vendite.fn_split_gruppo_fatturabile_key(v_key);

    -- Il documento e il suo numero, dalla sede unica della
    -- risoluzione polimorfa. Non risolve niente da se': legge il
    -- `label_selector` che la sorgente dichiara a catalogo.
    SELECT d.documento_id, d.documento_numero
      INTO v_documento, v_numero
      FROM vendite.fn_get_sorgente_documento_ref(
               v_src.sorgente_tipo_id, v_src.sorgente_uid) d;

    -- Il contenitore, quando il numero manca.
    -- * Forma sourceless ('MAN:<commessa_id>'): un documento non c'e'
    --   per progetto, la commessa e' nella chiave.
    -- * Forma documento senza numero (un consumo): la commessa
    --   APERTA in cui il documento sta, la sola che il push
    --   riconosce. Regola d'incontro: l'id del documento e l'uid
    --   della chiave, la colonna che il key_selector non usa e' NULL
    --   nel link. Il BB della chiave da' NULL, non solleva, su un
    --   uid fuori forma.
    IF v_src.commessa_id IS NOT NULL THEN
        v_commessa_id := v_src.commessa_id;
    ELSIF NULLIF(btrim(COALESCE(v_numero, '')), '') IS NULL
          AND v_src.sorgente_tipo_id IS NOT NULL THEN
        v_commessa_id := vendite.fn_commessa_viva_di_sorgente(
            v_src.sorgente_tipo_id,
            v_documento,
            script.fn_sorgente_chiave_uuid(v_src.sorgente_uid));
    END IF;

    IF v_commessa_id IS NOT NULL THEN
        SELECT c.codice INTO v_codice
          FROM vendite.commesse c WHERE c.id = v_commessa_id;
    END IF;

    -- IL RIPIEGO A TRE LIVELLI, e l'ultimo non e' una resa: la
    -- chiave grezza e' esattamente cio' che l'operatore vedeva
    -- prima di questa funzione.
    -- ⚠️ Stessa scala di vw_dash_competenza_gruppi.riferimento. La
    --    vista non la chiama, per non risolvere due volte per riga
    --    (le serve anche documento_id dallo stesso LATERAL, e la
    --    commessa la conosce dal gruppo): la seconda scrittura e'
    --    dichiarata e presidiata da un pgTAP che chiede alle due la
    --    stessa stringa, anche per un documento senza numero.
    RETURN COALESCE(
        NULLIF(btrim(COALESCE(v_numero, '')), ''),
        NULLIF(btrim(COALESCE(v_codice, '')), ''),
        v_key);
END;
$function$

COMMENT ON FUNCTION vendite.fn_riferimento_gruppo_fatturabile(p_gruppo_key text)
IS 'Il RIFERIMENTO leggibile di un gruppo fatturabile: cio'' che una persona riconosce al posto della chiave, ''ORDINE_VENDITA:01a06ce4-…'' diventa ''ORD0036004''. La usa la scheda Critiche del lotto (vendite.fn_list_lotto_segnalazioni), dove la gruppo_key serve al pulsante (fn_escludi_documento_da_giro la vuole), non all''occhio. Compone vendite.fn_split_gruppo_fatturabile_key e vendite.fn_get_sorgente_documento_ref, che risolve il documento e il suo numero leggendo il label_selector dichiarato dalla sorgente a catalogo. Ripiego a TRE livelli: il numero del documento; poi il codice della commessa, che per la forma sourceless ''MAN:<id>'' sta nella chiave e per un documento senza numero (un consumo) e'' la commessa aperta in cui il documento sta (vendite.fn_commessa_viva_di_sorgente); poi la CHIAVE GREZZA, che e'' esattamente cio'' che si vedeva prima, quindi peggiorare e'' impossibile. Un documento che non sta in una commessa aperta ripiega sulla chiave. NULL entra e NULL esce: una chiave assente vuol dire «la segnalazione e'' del GIRO», e li'' non c''e'' nessun documento da nominare. NON SOLLEVA MAI: la chiama una lista. Stessa scala di ripiego di vw_dash_competenza_gruppi.riferimento, che NON la chiama per non risolvere due volte per riga: la seconda scrittura e'' dichiarata e presidiata da un pgTAP che chiede alle due la stessa stringa sulla stessa chiave, per un documento con numero e per uno senza. STABLE, SECURITY INVOKER.';
```

</div>

---
{% include-markdown "signature-core.md" %}
