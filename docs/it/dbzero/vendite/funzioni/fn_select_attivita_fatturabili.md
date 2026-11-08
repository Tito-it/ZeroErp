{% include-markdown "it/dbzero/vendite/manual/fn_select_attivita_fatturabili.md" %}
# ⚙️ Funzione `fn_select_attivita_fatturabili`

```sql
CREATE FUNCTION fn_select_attivita_fatturabili(p_competenza_mese date, p_tipo_doc_fiscale_id bigint, p_lock_batch_id uuid, p_lock boolean, p_data_fatturazione date, p_billing_account_id bigint, p_utility_id integer, p_valuta_id integer, p_emittente_soggetto_ruolo_id bigint, p_area_geografica_id bigint, p_limit integer, p_gruppi text[])
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_select_attivita_fatturabili(p_competenza_mese date, p_tipo_doc_fiscale_id bigint, p_lock_batch_id uuid DEFAULT NULL::uuid, p_lock boolean DEFAULT false, p_data_fatturazione date DEFAULT script.fn_data_operativa(), p_billing_account_id bigint DEFAULT NULL::bigint, p_utility_id integer DEFAULT NULL::integer, p_valuta_id integer DEFAULT NULL::integer, p_emittente_soggetto_ruolo_id bigint DEFAULT NULL::bigint, p_area_geografica_id bigint DEFAULT NULL::bigint, p_limit integer DEFAULT NULL::integer, p_gruppi text[] DEFAULT NULL::text[])
 RETURNS SETOF vendite.attivita_fatturabili
 LANGUAGE plpgsql
AS $function$
-- Scopo: seleziona (e opzionalmente blocca) le attivita' fatturabili
--        eleggibili di un perimetro, marcandole stato_esecuzione=PENDING.
-- rev 2026-06-19: FOR UPDATE OF a (lock ristretto ad attivita_fatturabili).
-- rev 2026-07-27 (brief emissione mirata A4): p_gruppi restringe la
--        selezione ai GRUPPI FATTURABILI richiesti. E' il secondo e
--        decisivo punto di applicazione del perimetro mirato: qui si
--        filtrano le AF GIA' ESISTENTI, che il filtro sul pull
--        (fn_emit_attivita_fatturabili_da_commessa) non puo' vedere.
DECLARE
    v_competenza vendite.attivita_fatturabili.competenza_mese%TYPE;
    v_data_fatturazione vendite.fatture.data%TYPE;
    v_where TEXT;
    v_join TEXT;
    v_limit TEXT;
    v_sql TEXT;
BEGIN
    IF p_competenza_mese IS NULL THEN
        PERFORM script.fn_log_and_raise_error('vendite', 'fn_select_attivita_fatturabili', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_competenza_mese', 'valore', NULL), NULL::uuid, 'p_competenza_mese obbligatoria');
    END IF;
    IF p_tipo_doc_fiscale_id IS NULL THEN
        PERFORM script.fn_log_and_raise_error('vendite', 'fn_select_attivita_fatturabili', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_tipo_doc_fiscale_id', 'valore', NULL), NULL::uuid, 'p_tipo_doc_fiscale_id obbligatorio');
    END IF;
    IF p_lock AND p_lock_batch_id IS NULL THEN
        PERFORM script.fn_log_and_raise_error('vendite', 'fn_select_attivita_fatturabili', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_lock_batch_id', 'valore', NULL), NULL::uuid, 'p_lock_batch_id obbligatorio quando p_lock=true');
    END IF;

    v_competenza := date_trunc('month', p_competenza_mese)::DATE;
    v_data_fatturazione := COALESCE(p_data_fatturazione, script.fn_data_operativa());

    v_where := ' WHERE a.approvato IS TRUE AND a.fatturato IS FALSE AND a.sospesa IS FALSE AND COALESCE(a.lock_in_fatturazione, false) IS FALSE'
        || ' AND (a.posticipa_al IS NULL OR a.posticipa_al <= ' || quote_literal(v_data_fatturazione) || ')'
        || ' AND a.competenza_mese <= ' || quote_literal(v_competenza)
        || ' AND a.tipo_doc_fiscale_id = ' || quote_literal(p_tipo_doc_fiscale_id);

    -- 🔴 D1+D2 — IL PERIMETRO CONSEGNATO, e da qui in poi il rifiuto DECIDE.
    --   Fino al 2026-09-04 il perimetro di un giro era «tutto cio' che e'
    --   libero e in competenza»: una riga liberata da un giro disfatto era
    --   indistinguibile da una appena consegnata dal pull, quindi la commessa
    --   che il pull aveva RESPINTO finiva in fattura lo stesso — e senza
    --   nessun errore, perche' quella fattura di troppo e' una fattura
    --   normale.
    --   ⇒ Adesso si fattura solo cio' che il pull di QUESTO giro ha firmato.
    --
    -- ⭐ IL PERIMETRO NON SI PUO' DIMENTICARE, ed e' il punto della forma.
    --   Non c'e' nessun interruttore da ricordarsi di accendere: chi lucchetta
    --   e' gia' OBBLIGATO a dichiarare il proprio giro (il guard qui sopra
    --   pretende `p_lock_batch_id` quando `p_lock`), e dichiarare il giro
    --   SIGNIFICA prendersi il suo perimetro. Le due cose non possono piu'
    --   divergere perche' sono lo stesso parametro.
    --
    -- ⚠️ La condizione e' sulla PRESENZA del giro e non su `p_lock`, e non e'
    --   la stessa cosa: cosi' anche un'anteprima che dichiara il proprio giro
    --   vede ESATTAMENTE cio' che il giro vero prendera'. Un'anteprima
    --   filtrata diversamente dal giro e' peggio di nessuna anteprima —
    --   mostra un elenco che poi non si avvera.
    --   Una chiamata senza giro (`p_lock_batch_id` NULL, quindi per forza
    --   senza lucchetto) resta senza filtro: non fattura niente e non puo'
    --   fare danni.
    IF p_lock_batch_id IS NOT NULL THEN
        v_where := v_where || ' AND a.emit_batch_id = ' || quote_literal(p_lock_batch_id);
    END IF;

    IF p_billing_account_id IS NOT NULL THEN v_where := v_where || ' AND a.billing_account_id = ' || quote_literal(p_billing_account_id); END IF;
    IF p_utility_id IS NOT NULL THEN v_where := v_where || ' AND ba.utility_id = ' || quote_literal(p_utility_id); END IF;
    IF p_valuta_id IS NOT NULL THEN v_where := v_where || ' AND a.valuta_id = ' || quote_literal(p_valuta_id); END IF;
    IF p_emittente_soggetto_ruolo_id IS NOT NULL THEN
        v_where := v_where || ' AND a.billing_account_id IS NOT NULL AND anagrafiche.fn_get_emittente_fiscale_id(a.billing_account_id) = ' || quote_literal(p_emittente_soggetto_ruolo_id);
    END IF;
    IF p_area_geografica_id IS NOT NULL THEN v_where := v_where || ' AND a.area_geografica_id = ' || quote_literal(p_area_geografica_id); END IF;

    -- ============================================
    -- EMISSIONE MIRATA (rev 2026-07-27): filtro per gruppo.
    -- ============================================
    -- Il join alla riga di commessa si aggiunge SOLO quando il
    -- filtro e' attivo: senza p_gruppi la query resta identica a
    -- prima, sia come forma sia come piano (garanzia G1).
    -- commessa_attivita_id e' NOT NULL su attivita_fatturabili,
    -- quindi l'INNER JOIN non perde righe.
    -- L'array entra come letterale quotato + cast, coerente con
    -- gli altri parametri iniettati sopra.
    v_join := '';
    IF p_gruppi IS NOT NULL THEN
        v_join := ' JOIN vendite.commesse_attivita ca ON ca.id = a.commessa_attivita_id';
        v_where := v_where
            || ' AND vendite.fn_gruppo_fatturabile_key_di_attivita(ca.sorgente_tipo_id, ca.segment_key, ca.commessa_id) = ANY ('
            || quote_literal(p_gruppi::text) || '::text[])';
    END IF;

    v_limit := CASE WHEN p_limit IS NOT NULL THEN ' LIMIT ' || p_limit::TEXT ELSE '' END;

    IF p_lock THEN
        -- ⚠️ FOR UPDATE OF a: il lock resta ristretto ad
        -- attivita_fatturabili anche in presenza del join. Non
        -- estenderlo a ca: serializzerebbe la fatturazione con le
        -- operazioni di commessa.
        v_sql := 'WITH candidati AS (SELECT a.id FROM vendite.attivita_fatturabili a JOIN anagrafiche.billing_account ba ON ba.id = a.billing_account_id' || v_join || v_where || ' ORDER BY a.data_attivita, a.id' || v_limit || ' FOR UPDATE OF a SKIP LOCKED) UPDATE vendite.attivita_fatturabili a SET lock_in_fatturazione = true, lock_batch_id = ' || quote_literal(p_lock_batch_id) || ', stato_esecuzione = ''PENDING'', data_update = now(), user_update = current_user FROM candidati c WHERE a.id = c.id AND a.fatturato IS FALSE AND COALESCE(a.lock_in_fatturazione, false) IS FALSE RETURNING a.*';
    ELSE
        v_sql := 'WITH candidati AS (SELECT a.id FROM vendite.attivita_fatturabili a JOIN anagrafiche.billing_account ba ON ba.id = a.billing_account_id' || v_join || v_where || ' ORDER BY a.data_attivita, a.id' || v_limit || ') SELECT a.* FROM vendite.attivita_fatturabili a JOIN candidati c ON c.id = a.id ORDER BY a.data_attivita, a.id';
    END IF;

    RETURN QUERY EXECUTE v_sql;
END;
$function$

COMMENT ON FUNCTION vendite.fn_select_attivita_fatturabili(p_competenza_mese date, p_tipo_doc_fiscale_id bigint, p_lock_batch_id uuid, p_lock boolean, p_data_fatturazione date, p_billing_account_id bigint, p_utility_id integer, p_valuta_id integer, p_emittente_soggetto_ruolo_id bigint, p_area_geografica_id bigint, p_limit integer, p_gruppi text[])
IS 'Le attivita'' fatturabili eleggibili di un perimetro, con lucchetto facoltativo. Eleggibile: approvata, non fatturata, non sospesa, non gia'' in fatturazione, con posticipa_al raggiunto alla data di fatturazione (p_data_fatturazione, default script.fn_data_operativa()), competenza_mese non oltre il mese di p_competenza_mese, del tipo documento p_tipo_doc_fiscale_id. p_competenza_mese e p_tipo_doc_fiscale_id sono obbligatori (E_PARAMETRO_INVALIDO). Filtri facoltativi: billing account, utility (del billing account), valuta, emittente (anagrafiche.fn_get_emittente_fiscale_id del billing account), area geografica, p_limit. p_lock_batch_id e'' il giro: con un giro si prendono solo le attivita'' che il pull di quel giro ha firmato (emit_batch_id), anche senza lucchetto, cosi'' un''anteprima vede cio'' che il giro prendera''. p_lock = true pretende il giro (E_PARAMETRO_INVALIDO) e blocca le righe con FOR UPDATE OF a SKIP LOCKED, scrivendo lock_in_fatturazione, lock_batch_id e stato_esecuzione = PENDING; p_lock = false e'' una lettura senza scritture. p_gruppi restringe ai gruppi fatturabili richiesti: NULL nessuna restrizione, array vuoto zero righe, chiave inesistente zero righe senza errore. Senza questo filtro un giro mirato consumerebbe le attivita'' gia'' esistenti di altri gruppi nello stesso perimetro, perche'' nessun altro criterio sa nulla della provenienza. attivita_fatturabili non porta una provenienza propria: il gruppo si legge dalla riga di commessa, col JOIN su commessa_attivita_id (NOT NULL, quindi non perde righe) e vendite.fn_gruppo_fatturabile_key_di_attivita; il JOIN si aggiunge solo con p_gruppi valorizzato. Il lucchetto resta ristretto ad attivita_fatturabili (FOR UPDATE OF a): esteso a commesse_attivita serializzerebbe la fatturazione con le operazioni di commessa. Restituisce le righe in ordine di data_attivita, id.';
```

</div>

---
{% include-markdown "signature-core.md" %}
