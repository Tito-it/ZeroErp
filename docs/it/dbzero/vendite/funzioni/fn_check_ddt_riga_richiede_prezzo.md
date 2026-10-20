{% include-markdown "it/dbzero/vendite/manual/fn_check_ddt_riga_richiede_prezzo.md" %}
# ⚙️ Funzione `fn_check_ddt_riga_richiede_prezzo`

```sql
CREATE FUNCTION fn_check_ddt_riga_richiede_prezzo(p_riga_ddt_id bigint)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_check_ddt_riga_richiede_prezzo(p_riga_ddt_id bigint)
 RETURNS boolean
 LANGUAGE plpgsql
 STABLE
AS $function$
-- Scopo: dire se la riga di DDT indicata appartiene a un documento
--   che VENDE, cioe' che ha una causale di trasporto fatturabile.
--   PURA (fn_check_*): non solleva e non scrive, secondo
--   linee-guida-sql §5.
DECLARE
    v_fatturabile boolean;
BEGIN
    -- Guard di parametro: un id nullo o non positivo e' un difetto
    -- del chiamante, ma qui la funzione non solleva — risponde
    -- TRUE, cioe' il comportamento severo.
    IF p_riga_ddt_id IS NULL OR p_riga_ddt_id <= 0 THEN
        RETURN TRUE;
    END IF;

    SELECT ct.fatturabile
      INTO v_fatturabile
      FROM vendite.ddt_righe dr
      JOIN vendite.ddt d
        ON d.id = dr.ddt_id
      LEFT JOIN config.causali_trasporto ct
        ON ct.id = d.causale_trasporto_id
     WHERE dr.id = p_riga_ddt_id;

    -- ⚠️ FAIL-CLOSED. Sotto RLS «non trovata» non distingue «non
    --   esiste» da «non la vedo»: nel dubbio si tiene il
    --   comportamento di prima (prezzo richiesto). Sbagliare qui
    --   costa una richiesta di prezzo di troppo; sbagliare al
    --   contrario manda uno zero in fattura.
    --   ⛔ Si guarda FOUND, non una variabile-sentinella. La
    --   prima stesura faceva `SELECT ct.fatturabile, TRUE INTO
    --   v_fatturabile, v_trovata` con v_trovata inizializzata a
    --   FALSE — e non funzionava: SELECT INTO senza righe non
    --   lascia le variabili come stanno, le AZZERA. v_trovata
    --   diventava NULL, `NOT NULL` non e' vero, il ramo non
    --   scattava e la funzione cadeva sul COALESCE finale
    --   rispondendo FALSE, cioe' l'esatto contrario del
    --   fail-closed. Trovato dal test sull'id inesistente.
    IF NOT FOUND THEN
        RETURN TRUE;
    END IF;

    -- Causale assente (bozza): l'intento non e' ancora dichiarato
    -- e non si inventa. Presidia il gate all'emissione.
    RETURN COALESCE(v_fatturabile, FALSE);
END;
$function$

COMMENT ON FUNCTION vendite.fn_check_ddt_riga_richiede_prezzo(p_riga_ddt_id bigint)
IS 'TRUE se la riga di DDT appartiene a un documento che vende (causale di trasporto fatturabile). PURA: non solleva, non scrive. Consumata dalla clausola WHEN del trigger che vieta il prezzo zero sui componenti obbligatori, per non dover insegnare la nozione di causale alla funzione trigger condivisa con preventivi, ordini e contratti. Causale ASSENTE -> FALSE: in bozza il NULL e'' legittimo e il presidio e'' il gate all''emissione (DL-28). Riga non leggibile -> TRUE, fail-closed: sotto RLS «non trovata» non distingue «non esiste» da «non la vedo», e dei due errori possibili solo quello opposto arriva in fattura. Brief: brief-ddt-righe-senza-prezzo §9 slice C (C3).';
```

</div>

---
{% include-markdown "signature-core.md" %}
