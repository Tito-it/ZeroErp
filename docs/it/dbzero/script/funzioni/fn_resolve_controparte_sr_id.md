{% include-markdown "it/dbzero/script/manual/fn_resolve_controparte_sr_id.md" %}
# ⚙️ Funzione `fn_resolve_controparte_sr_id`

```sql
CREATE FUNCTION fn_resolve_controparte_sr_id(p_modo text, p_valore bigint)
```

> 🔐 **Sicurezza**: `SECURITY DEFINER` — gira con i privilegi dell'owner `zeroerp_owner`: GRANT e RLS sono i suoi, non quelli di chi la chiama.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_resolve_controparte_sr_id(p_modo text, p_valore bigint)
 RETURNS bigint
 LANGUAGE plpgsql
 STABLE SECURITY DEFINER COST 5000
 SET search_path TO 'pg_catalog', 'pg_temp'
AS $function$
DECLARE
    v_sr_id anagrafiche.soggetti_ruoli.id%TYPE;
BEGIN
    -- =========================================================
    -- Scopo:
    --   Dire DI QUALE CONTROPARTE e' una riga, e nient'altro: il
    --   soggetto_ruolo (cliente o fornitore) raggiunto da p_valore
    --   secondo p_modo, o NULL se il riferimento non porta a nessuno.
    --
    -- ⭐ Perche' SECURITY DEFINER: le catene passano da tabelle con la
    --   RLS accesa. Lette dalla policy di un figlio, ogni lettura
    --   rieseguirebbe la policy del padre per ogni riga. La domanda di
    --   FATTO («di chi e'») e quella di PERMESSO («la vedo») restano
    --   separate: la seconda e' della policy, con
    --   script.fn_scope_sr_perimetro. Sorella di
    --   script.fn_resolve_emittente_fiscale_id.
    -- ⚠️ Dipende dalla RLS ABILITATA ma NON FORZATA: il proprietario la
    --   salta (linee-guida-sql §10.5).
    -- =========================================================

    IF p_valore IS NULL THEN
        RETURN NULL;
    END IF;

    IF p_modo = 'billing_account' THEN
        -- Il cliente del billing account.
        SELECT ba.soggetto_ruolo_id
          INTO v_sr_id
          FROM anagrafiche.billing_account ba
         WHERE ba.id = p_valore;

    ELSIF p_modo = 'fattura' THEN
        -- Il cliente della fattura e' quello del suo billing account:
        --   la regola BA_OWNERSHIP (config.scope_policy).
        SELECT ba.soggetto_ruolo_id
          INTO v_sr_id
          FROM vendite.fatture f
          JOIN anagrafiche.billing_account ba
            ON ba.id = f.billing_account_id
         WHERE f.id = p_valore;

    ELSIF p_modo = 'fattura_sdi' THEN
        -- L'invio SDI e' della sua fattura.
        SELECT ba.soggetto_ruolo_id
          INTO v_sr_id
          FROM vendite.fatture_sdi s
          JOIN vendite.fatture f
            ON f.id = s.fattura_id
          JOIN anagrafiche.billing_account ba
            ON ba.id = f.billing_account_id
         WHERE s.id = p_valore;

    ELSIF p_modo = 'ordine' THEN
        -- Il cliente dell'ordine e' la sua colonna (rev 2026-10-21, 20261021-33).
        SELECT o.soggetto_ruolo_id
          INTO v_sr_id
          FROM vendite.ordini o
         WHERE o.id = p_valore;

    ELSIF p_modo = 'ordine_riga' THEN
        -- La riga e' del suo ordine (rev 2026-10-21, 20261021-33).
        SELECT o.soggetto_ruolo_id
          INTO v_sr_id
          FROM vendite.ordini_righe r
          JOIN vendite.ordini o
            ON o.id = r.ordine_id
         WHERE r.id = p_valore;

    -- ⭐ I modi del canale SHOP (rev 2026-10-21, 20261021-37): la controparte
    --   della riga SOLO se la riga e' nata dallo shop. La veste SHOP_CUSTOMER
    --   vede le proprie righe di quel canale e nessun'altra: un ordine o un
    --   billing account del proprio soggetto, ma nato da ADMIN, non sono suoi
    --   da shop. Fuori canale -> NULL, cioe' nessuno.
    ELSIF p_modo = 'billing_account_shop' THEN
        SELECT ba.soggetto_ruolo_id
          INTO v_sr_id
          FROM anagrafiche.billing_account ba
         WHERE ba.id = p_valore
           AND ba.canale_origine = 'SHOP'::config.canale_origine;

    ELSIF p_modo = 'ordine_shop' THEN
        SELECT o.soggetto_ruolo_id
          INTO v_sr_id
          FROM vendite.ordini o
         WHERE o.id = p_valore
           AND o.canale_origine = 'SHOP'::config.canale_origine;

    ELSIF p_modo = 'ordine_riga_shop' THEN
        SELECT o.soggetto_ruolo_id
          INTO v_sr_id
          FROM vendite.ordini_righe r
          JOIN vendite.ordini o
            ON o.id = r.ordine_id
         WHERE r.id = p_valore
           AND o.canale_origine = 'SHOP'::config.canale_origine;

    ELSE
        -- ⛔ Non si restituisce NULL: un errore di battitura in una
        --    policy la chiuderebbe in silenzio, e nessuno saprebbe perche'.
        PERFORM script.fn_log_and_raise_error(
            'database',
            'script.fn_resolve_controparte_sr_id',
            'E_PARAMETRO_INVALIDO',
            jsonb_build_object(
                'detail', 'Modo di risoluzione sconosciuto',
                'modo',   p_modo,
                'valore', p_valore
            ),
            NULL::uuid,
            format(
                'il modo di risoluzione della controparte «%s» non esiste: '
                'sono ammessi billing_account, fattura, fattura_sdi, ordine, ordine_riga, '
                'billing_account_shop, ordine_shop e ordine_riga_shop',
                p_modo
            )
        );
    END IF;

    RETURN v_sr_id;
END
$function$

COMMENT ON FUNCTION script.fn_resolve_controparte_sr_id(p_modo text, p_valore bigint)
IS 'Dice DI QUALE CONTROPARTE e'' una riga: il soggetto_ruolo (cliente o fornitore) raggiunto da p_valore secondo p_modo, o NULL se il riferimento non porta a nessuno. Modi: billing_account (il cliente del BA), fattura (il cliente del BA della fattura, regola BA_OWNERSHIP), fattura_sdi (quello della sua fattura), ordine (il cliente dell''ordine, rev 2026-10-21, 20261021-33), ordine_riga (quello del suo ordine); billing_account_shop, ordine_shop, ordine_riga_shop (la stessa controparte, ma solo se la riga e'' nata dal canale SHOP: altrimenti NULL; rev 2026-10-21, 20261021-37). Un modo sconosciuto SOLLEVA E_PARAMETRO_INVALIDO, non risponde NULL. SECURITY DEFINER del PROPRIETARIO, non di un superuser: le catene passano da tabelle sotto RLS, e lette dalla policy di un figlio rieseguirebbero per ogni riga la policy del padre. Risponde solo alla domanda di FATTO: il permesso e'' della policy, con script.fn_scope_sr_perimetro (linee-guida-sql §10.3). Sorella di script.fn_resolve_emittente_fiscale_id. search_path bloccato. Rev 2026-10-21 (20261021-30, giro 2 di brief-db-perimetro-una-volta-famiglie-residue).';
```

</div>

---
{% include-markdown "signature-core.md" %}
