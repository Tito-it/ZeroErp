# ⚙️ Funzione `fn_resolve_emittente_sr_id`

```sql
CREATE FUNCTION fn_resolve_emittente_sr_id(p_modo text, p_valore bigint)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_resolve_emittente_sr_id(p_modo text, p_valore bigint)
 RETURNS bigint
 LANGUAGE plpgsql
 STABLE SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'pg_temp'
AS $function$
DECLARE
    v_sr_id anagrafiche.soggetti_ruoli.id%TYPE;
BEGIN
    -- =========================================================
    -- Scopo:
    --   Dire DI CHI E' una riga, in convenzione SR, e nient'altro.
    --   Risponde un soggetto_ruolo_id, oppure NULL se il
    --   riferimento non porta a nessuna entita'.
    --
    -- ⭐ Gemello di script.fn_resolve_emittente_fiscale_id sulla
    --   convenzione SR. Il doppio binario PK/SR e' una scelta
    --   dichiarata del progetto (refactor-emittente-id-canonico,
    --   2026-05-02), non un residuo.
    --
    -- ⭐ Qui e' una COPIA, non una ricerca: lotti, commesse e
    --   fatture portano gia' la colonna. Nessun JOIN.
    --
    -- ⚠️ SECURITY DEFINER: le tre tabelle hanno la ROW SECURITY
    --   accesa. Letta da un utente fuori perimetro la riga non
    --   c'e', e «non la vedo» non e' «non esiste».
    --
    -- ⚠️ Dipende dalla RLS abilitata e NON forzata (il
    --   proprietario la salta). Con un FORCE va rivista.
    -- =========================================================

    IF p_valore IS NULL THEN
        RETURN NULL;
    END IF;

    IF p_modo = 'lotto' THEN
        SELECT l.emittente_soggetto_ruolo_id
          INTO v_sr_id
          FROM vendite.fatturazione_lotti l
         WHERE l.id = p_valore;

    ELSIF p_modo = 'commessa' THEN
        SELECT c.emittente_soggetto_ruolo_id
          INTO v_sr_id
          FROM vendite.commesse c
         WHERE c.id = p_valore;

    ELSIF p_modo = 'fattura' THEN
        SELECT f.emittente_soggetto_ruolo_id
          INTO v_sr_id
          FROM vendite.fatture f
         WHERE f.id = p_valore;

    ELSE
        -- ⛔ Non si restituisce NULL: nel giornale un NULL vuol
        --    dire «riga rifiutata», e un refuso in un CREATE
        --    TRIGGER diventerebbe un diario che smette di
        --    scrivere senza dirlo.
        PERFORM script.fn_log_and_raise_error(
            'database',
            'script.fn_resolve_emittente_sr_id',
            'E_PARAMETRO_INVALIDO',
            jsonb_build_object(
                'detail', 'Modo di risoluzione sconosciuto',
                'modo',   p_modo,
                'valore', p_valore
            ),
            NULL::uuid,
            format(
                'il modo di risoluzione dell''emittente «%s» non esiste: '
                'sono ammessi lotto, commessa e fattura',
                p_modo
            )
        );
    END IF;

    RETURN v_sr_id;
END
$function$

COMMENT ON FUNCTION script.fn_resolve_emittente_sr_id(p_modo text, p_valore bigint)
IS 'Risolve il soggetto_ruolo_id dell''emittente di una riga FUORI dalla row security. ⭐ Gemello in convenzione SR di script.fn_resolve_emittente_fiscale_id: il doppio binario PK/SR e'' una scelta dichiarata del progetto (refactor-emittente-id-canonico, 2026-05-02). Modi: lotto | commessa | fattura — e in tutti e tre e'' una COPIA della colonna del padre, non una ricerca. ⚠️ SECURITY DEFINER perche'' le tre tabelle hanno la RLS accesa: per un utente fuori perimetro la riga non c''e'', e «non la vedo» non e'' «non esiste». ⚠️ Dipende dalla RLS abilitata e NON forzata (il proprietario la salta): con un FORCE va rivista. ⛔ Un modo sconosciuto SOLLEVA: restituire NULL farebbe smettere di scrivere il giornale in silenzio.';
```

</div>

---
{% include-markdown "signature-core.md" %}
