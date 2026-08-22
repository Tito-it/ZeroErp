{% include-markdown "it/dbzero/pagamenti/manual/fn_annulla_sistemazione.md" %}
# ⚙️ Funzione `fn_annulla_sistemazione`

```sql
CREATE FUNCTION fn_annulla_sistemazione(p_sistemazione_id bigint, p_motivo text)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION pagamenti.fn_annulla_sistemazione(p_sistemazione_id bigint, p_motivo text DEFAULT NULL::text)
 RETURNS character varying
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_stato pagamenti.sistemazioni.stato%TYPE;
BEGIN
    -- =========================================================
    -- Scopo:
    --   Scartare un atto di sistemazione, lasciandolo a registro
    --   con la ragione per cui e' stato scartato.
    --
    -- ⛔ NON ricontrolla lo stato: su un atto gia' terminale parla
    --   trgfn_sistemazioni_guard_transizione, che dice anche in
    --   che stato si trova. Due sedi per la stessa regola sono
    --   due sedi che prima o poi divergono.
    -- =========================================================

    UPDATE pagamenti.sistemazioni s
       SET stato  = 'ANNULLATA',
           -- ⭐ Il motivo si FONDE: se l'atto ne aveva gia' uno e la
           --   chiamata arriva vuota, si tiene quello che c'era.
           --   Se restano entrambi vuoti non passa — il guard dei
           --   dati lo pretende, perche' una decisione scartata
           --   senza una ragione non si ricostruisce.
           motivo = COALESCE(NULLIF(btrim(p_motivo), ''), s.motivo)
     WHERE s.id = p_sistemazione_id
    RETURNING s.stato INTO v_stato;

    -- ⚠️ Zero righe vuol dire due cose che devono restare
    --   indistinguibili: l'atto non esiste, oppure la row security
    --   non lo fa vedere a chi sta chiedendo. Distinguerle direbbe
    --   a chi e' fuori perimetro che quell'atto c'e'.
    IF NOT FOUND THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'pagamenti.fn_annulla_sistemazione',
            'E_SISTEMAZIONE_NON_TROVATA',
            jsonb_build_object('detail', 'sistemazione inesistente o fuori perimetro',
                               'sistemazione_id', p_sistemazione_id),
            NULL::uuid,
            p_sistemazione_id::text
        );
    END IF;

    RETURN v_stato;
END
$function$

COMMENT ON FUNCTION pagamenti.fn_annulla_sistemazione(p_sistemazione_id bigint, p_motivo text)
IS 'Scarta un atto di sistemazione lasciandolo a REGISTRO con la ragione per cui e'' stato scartato — annullare non e'' cancellare, ed e'' il senso stesso di avere un registro: l''eccedenza continuera'' a comparire nell''elenco (e'' vera, non se n''e'' andata) e chi guarda trovera'' scritto perche'' la volta scorsa si e'' deciso di lasciarla li''. ⭐ Non e'' una madre: scrive una riga sola. Esiste per due ragioni — dare il messaggio giusto a «quell''atto non c''e''», che sotto la row security vuol dire anche «non e'' tuo» e le due cose devono restare indistinguibili, e far arrivare il motivo nello stesso gesto invece di chiederlo con un UPDATE a parte. ⛔ NON ricontrolla lo stato: su un atto gia'' terminale parla trgfn_sistemazioni_guard_transizione con E_SISTEMAZIONE_IMMUTABILE, che dice anche in che stato si trova. ⭐ Il motivo si fonde e non si sovrascrive: se l''atto ne aveva gia'' uno e la chiamata arriva vuota, si tiene quello che c''era.';
```

---
{% include-markdown "signature-core.md" %}
