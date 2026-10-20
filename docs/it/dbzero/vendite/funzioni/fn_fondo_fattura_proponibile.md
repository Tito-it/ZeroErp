{% include-markdown "it/dbzero/vendite/manual/fn_fondo_fattura_proponibile.md" %}
# ⚙️ Funzione `fn_fondo_fattura_proponibile`

```sql
CREATE FUNCTION fn_fondo_fattura_proponibile(p_fattura_sorgente_id bigint, p_tipo_fondo_fattura_id bigint)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_fondo_fattura_proponibile(p_fattura_sorgente_id bigint, p_tipo_fondo_fattura_id bigint)
 RETURNS numeric
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_totale_a_pagare vendite.fatture.totale_a_pagare%TYPE;
    v_importo         vendite.fatture_fondi_fattura_source.importo%TYPE;
BEGIN
    -- Guard di parametro: un id nullo o non positivo e' un
    -- errore del chiamante, non un «niente da proporre».
    IF p_fattura_sorgente_id IS NULL OR p_fattura_sorgente_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'fn_fondo_fattura_proponibile', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_fattura_sorgente_id', 'valore', p_fattura_sorgente_id),
            NULL::uuid, 'p_fattura_sorgente_id obbligatorio e > 0');
    END IF;

    IF p_tipo_fondo_fattura_id IS NULL OR p_tipo_fondo_fattura_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'fn_fondo_fattura_proponibile', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_tipo_fondo_fattura_id', 'valore', p_tipo_fondo_fattura_id),
            NULL::uuid, 'p_tipo_fondo_fattura_id obbligatorio e > 0');
    END IF;

    -- =========================================================
    -- 1) IL DOCUMENTO. Deve essere una fattura DEFINITIVA, «di
    --    minimo» (dentro la banda delle due soglie) e con la
    --    utility attribuita.
    --
    --    ⚠️ `utility_id IS NOT NULL` e' qui e non nel chiamante:
    --    la generazione filtra `f.utility_id = p_utility_id`, e
    --    un NULL non e' uguale a niente. Una fattura senza
    --    utility non e' «da decidere piu' tardi»: e'
    --    IRRAGGIUNGIBILE da qualunque giro, e la vista
    --    vw_fondi_fattura_da_decidere la mostra per questo.
    --
    --    ⚠️ Stato nullo o fuori vocabolario: nessuna riga,
    --    quindi NULL. Fail-closed.
    -- =========================================================
    SELECT f.totale_a_pagare
      INTO v_totale_a_pagare
      FROM vendite.fatture f
      JOIN config.stati_doc_fiscale sd
        ON sd.id = f.stato_doc_fiscale_id
       AND sd.codice_interno = 'DEFINITIVA'
     WHERE f.id = p_fattura_sorgente_id
       AND f.minimo IS TRUE
       AND f.utility_id IS NOT NULL;

    IF NOT FOUND OR v_totale_a_pagare IS NULL THEN
        RETURN NULL;
    END IF;

    -- =========================================================
    -- 2) L'ATTO UNICO. Se un atto esiste gia' — in QUALUNQUE
    --    stato — non c'e' niente da proporre.
    --
    --    ⚠️ Anche ANNULLATO, ed e' il caso che spiega la scelta:
    --    quell'annullamento e' una decisione, e riproporre il
    --    fondo sarebbe l'elenco che chiede ogni giorno di
    --    rifare una cosa che qualcuno ha deciso di non fare.
    -- =========================================================
    IF EXISTS (
        SELECT 1
          FROM vendite.fatture_fondi_fattura_source s
         WHERE s.fattura_sorgente_id   = p_fattura_sorgente_id
           AND s.tipo_fondo_fattura_id = p_tipo_fondo_fattura_id
    ) THEN
        RETURN NULL;
    END IF;

    -- =========================================================
    -- 3) IL NUMERO. Nessun atto esiste, quindi non c'e' nessun
    --    contributo proprio da scorporare: p_source_id = NULL.
    -- =========================================================
    v_importo := vendite.fn_saldo_sorgente_fondo(p_fattura_sorgente_id, NULL);

    IF v_importo IS NULL OR v_importo = 0 THEN
        RETURN NULL;
    END IF;

    -- =========================================================
    -- 4) LA CORRISPONDENZA col documento.
    --
    --    ⚠️ Segno + valore assoluto, MAI «fra 0 e il totale»:
    --    su una sorgente a credito gli estremi si invertono e
    --    l'intervallo diventa vuoto — una porta chiusa
    --    travestita da controllo, e proprio su meta' della
    --    banda.
    --
    --    ℹ️ Questa e' la stessa regola del guard trigger
    --    trgfn_fondi_source_guard_importo. Qui e' una risposta
    --    («non lo propongo»), li' e' un rifiuto. La differenza
    --    non e' cosmetica: l'automatismo non deve fermarsi, la
    --    scrittura sbagliata si'.
    -- =========================================================
    IF sign(v_importo) <> sign(v_totale_a_pagare)
       OR abs(v_importo) > abs(v_totale_a_pagare) THEN
        RETURN NULL;
    END IF;

    RETURN v_importo;
END;
$function$

COMMENT ON FUNCTION vendite.fn_fondo_fattura_proponibile(p_fattura_sorgente_id bigint, p_tipo_fondo_fattura_id bigint)
IS 'L''importo che il giro di fatturazione scriverebbe OGGI per la coppia (fattura sorgente, tipo di fondo), oppure NULL se non farebbe niente. NULL e'' una risposta piena — «nessuna proposta» — e non uno zero: l''importo zero sulla tabella non e'' nemmeno ammesso. Restituisce NULL se la sorgente non e'' DEFINITIVA, non e'' di minimo (fuori dalla banda delle due soglie), non ha utility_id, ha gia'' un atto in QUALUNQUE stato (anche ANNULLATO: quell''annullamento e'' una decisione, e riproporlo sarebbe chiedere ogni giorno di rifare cio'' che qualcuno ha deciso di non fare), oppure se il numero e'' zero o non CORRISPONDE al documento. ⭐ E'' l''UNICA definizione dell''inviluppo: dal changeSet 20260815-20 anche fn_genera_fondi_fattura_source la consuma invece di riscriverla nel proprio WHERE — due copie della stessa domanda danno prima o poi due risposte diverse, e il divario si vedrebbe come un elenco che propone cio'' che l''automatismo non crea. ⚠️ Deliberatamente NON STABLE, benche'' il piano la prevedesse tale: e'' costruita su fn_saldo_sorgente_fondo, che e'' VOLATILE perche'' chiama funzioni pagamenti.* VOLATILE. ⚠️ utility_id IS NOT NULL sta QUI e non nello scope del chiamante: una fattura senza utility non e'' irrisolta, e'' irraggiungibile da qualunque giro (il filtro e'' `=`, e NULL non e'' uguale a niente) — la vista vw_fondi_fattura_da_decidere la mostra proprio per questo. D-9 di brief-db-fondo-fattura-ricalcolo-e-governo §8.2.';
```

</div>

---
{% include-markdown "signature-core.md" %}
