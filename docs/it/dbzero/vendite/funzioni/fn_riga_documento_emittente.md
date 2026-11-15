# ⚙️ Funzione `fn_riga_documento_emittente`

```sql
CREATE FUNCTION fn_riga_documento_emittente(p_tabella text, p_riferimento_id bigint)
```

> 🔐 **Sicurezza**: `SECURITY DEFINER` — gira con i privilegi dell'owner `zeroerp_owner`: GRANT e RLS sono i suoi, non quelli di chi la chiama.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_riga_documento_emittente(p_tabella text, p_riferimento_id bigint)
 RETURNS bigint
 LANGUAGE plpgsql
 STABLE SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'pg_temp'
AS $function$
DECLARE
    v_emittente anagrafiche.emittenti_fiscali.soggetto_ruolo_id%TYPE;
BEGIN
    -- =========================================================
    -- Scopo:
    --   il soggetto_ruolo dell'azienda che emette il documento a
    --   cui appartiene una riga (riferimento = la testata) o un
    --   componente (riferimento = la riga principale).
    -- =========================================================
    CASE p_tabella
        WHEN 'preventivi_righe' THEN
            SELECT ef.soggetto_ruolo_id INTO v_emittente
              FROM vendite.preventivi d
              JOIN anagrafiche.emittenti_fiscali ef ON ef.id = d.emittente_fiscale_id
             WHERE d.id = p_riferimento_id;
        WHEN 'ordini_righe' THEN
            SELECT ef.soggetto_ruolo_id INTO v_emittente
              FROM vendite.ordini d
              JOIN anagrafiche.emittenti_fiscali ef ON ef.id = d.emittente_fiscale_id
             WHERE d.id = p_riferimento_id;
        WHEN 'contratti_righe' THEN
            SELECT ef.soggetto_ruolo_id INTO v_emittente
              FROM vendite.contratti d
              JOIN anagrafiche.emittenti_fiscali ef ON ef.id = d.emittente_fiscale_id
             WHERE d.id = p_riferimento_id;
        WHEN 'ddt_righe' THEN
            SELECT ef.soggetto_ruolo_id INTO v_emittente
              FROM vendite.ddt d
              JOIN anagrafiche.emittenti_fiscali ef ON ef.id = d.emittente_fiscale_id
             WHERE d.id = p_riferimento_id;
        WHEN 'offerte_commerciali_eccezioni' THEN
            SELECT ef.soggetto_ruolo_id INTO v_emittente
              FROM vendite.offerte_commerciali d
              JOIN anagrafiche.emittenti_fiscali ef ON ef.id = d.emittente_fiscale_id
             WHERE d.id = p_riferimento_id;
        WHEN 'preventivi_righe_componenti' THEN
            SELECT ef.soggetto_ruolo_id INTO v_emittente
              FROM vendite.preventivi_righe r
              JOIN vendite.preventivi d ON d.id = r.preventivo_id
              JOIN anagrafiche.emittenti_fiscali ef ON ef.id = d.emittente_fiscale_id
             WHERE r.id = p_riferimento_id;
        WHEN 'ordini_righe_componenti' THEN
            SELECT ef.soggetto_ruolo_id INTO v_emittente
              FROM vendite.ordini_righe r
              JOIN vendite.ordini d ON d.id = r.ordine_id
              JOIN anagrafiche.emittenti_fiscali ef ON ef.id = d.emittente_fiscale_id
             WHERE r.id = p_riferimento_id;
        WHEN 'contratti_righe_componenti' THEN
            SELECT ef.soggetto_ruolo_id INTO v_emittente
              FROM vendite.contratti_righe r
              JOIN vendite.contratti d ON d.id = r.contratto_id
              JOIN anagrafiche.emittenti_fiscali ef ON ef.id = d.emittente_fiscale_id
             WHERE r.id = p_riferimento_id;
        WHEN 'ddt_righe_componenti' THEN
            SELECT ef.soggetto_ruolo_id INTO v_emittente
              FROM vendite.ddt_righe r
              JOIN vendite.ddt d ON d.id = r.ddt_id
              JOIN anagrafiche.emittenti_fiscali ef ON ef.id = d.emittente_fiscale_id
             WHERE r.id = p_riferimento_id;
        WHEN 'offerte_commerciali_eccezioni_componenti' THEN
            SELECT ef.soggetto_ruolo_id INTO v_emittente
              FROM vendite.offerte_commerciali_eccezioni r
              JOIN vendite.offerte_commerciali d ON d.id = r.offerta_id
              JOIN anagrafiche.emittenti_fiscali ef ON ef.id = d.emittente_fiscale_id
             WHERE r.id = p_riferimento_id;
        ELSE
            PERFORM script.fn_log_and_raise_error(
                'vendite', 'fn_riga_documento_emittente', 'E_TRIGGER_ARGOMENTI_INVALIDI',
                jsonb_build_object('tabella', p_tabella),
                NULL::uuid,
                concat('tabella non prevista: vendite.', p_tabella));
    END CASE;

    RETURN v_emittente;
END;
$function$

COMMENT ON FUNCTION vendite.fn_riga_documento_emittente(p_tabella text, p_riferimento_id bigint)
IS 'Il soggetto_ruolo dell''azienda che emette il documento di una riga o di un componente (anagrafiche.emittenti_fiscali.soggetto_ruolo_id della testata), NULL se il riferimento non c''e''. p_tabella e'' il nome della tabella della riga (righe principali e componenti di preventivi, ordini, contratti, DDT e offerte); p_riferimento_id e'' la testata per una riga principale, la riga principale per un componente. Una tabella fuori da queste dieci solleva E_TRIGGER_ARGOMENTI_INVALIDI. SECURITY DEFINER: chi la legge e'' un guard, e la risposta non deve dipendere dalla RLS di chi scrive. La legge vendite.trgfn_riga_documento_guard_listino_provenienza.';
```

</div>

---
{% include-markdown "signature-core.md" %}
