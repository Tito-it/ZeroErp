# ⚙️ Funzione `fn_check_ddt_riga_correggi_qta_evasa`

```sql
CREATE FUNCTION fn_check_ddt_riga_correggi_qta_evasa(p_ddt_riga_id bigint)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_check_ddt_riga_correggi_qta_evasa(p_ddt_riga_id bigint)
 RETURNS jsonb
 LANGUAGE plpgsql
 STABLE
AS $function$

DECLARE
  v_riga_nr    vendite.ddt_righe.riga_nr%TYPE;
  v_ddt_id     vendite.ddt_righe.ddt_id%TYPE;
  v_sorgente   config.sorgenti.codice_interno%TYPE;
  -- Stato ed etichetta dal lettore del lock
  -- (script.fn_get_stato_testata_documento, RETURNS TABLE di text):
  -- composti, nessuna colonna di cui siano il riflesso.
  v_stato      text;
  v_etichetta  text;
  -- CONTEGGI: nessuna colonna da ancorare.
  v_ful        bigint;
  v_ric        bigint;
BEGIN
  -- =========================================================
  -- Scopo:
  --   La quantita' evasa di questa riga di DDT si corregge ora,
  --   col verbo vendite.fn_ddt_riga_correggi_qta_evasa? Funzione
  --   PURA (fn_check_*): [] se si', il primo motivo se no, NULL se
  --   la riga non si vede (RLS di chi chiede).
  --   Consumatori: il verbo (solleva il primo motivo) e
  --   vendite.vw_ddt_righe_dettaglio (correggi_qta_evasa_blocco).
  -- =========================================================
  IF p_ddt_riga_id IS NULL OR p_ddt_riga_id <= 0 THEN
    PERFORM script.fn_log_and_raise_error(
      'script', 'script.fn_check_ddt_riga_correggi_qta_evasa',
      'E_VENDITE_CHIAMATA_NON_VALIDA',
      jsonb_build_object('p_ddt_riga_id', p_ddt_riga_id),
      NULL::uuid, 'script.fn_check_ddt_riga_correggi_qta_evasa',
      'p_ddt_riga_id (obbligatorio, maggiore di zero)');
  END IF;

  -- La riga e la sorgente del suo DDT, sotto la RLS di chi chiede.
  SELECT dr.riga_nr, dr.ddt_id, s.codice_interno
    INTO v_riga_nr, v_ddt_id, v_sorgente
    FROM vendite.ddt_righe dr
    JOIN vendite.ddt d ON d.id = dr.ddt_id
    LEFT JOIN config.sorgenti s ON s.id = d.sorgente_tipo_id
   WHERE dr.id = p_ddt_riga_id;

  IF NOT FOUND THEN
    RETURN NULL;
  END IF;

  SELECT t.stato, t.etichetta
    INTO v_stato, v_etichetta
    FROM script.fn_get_stato_testata_documento('DDT_VENDITA', v_ddt_id) AS t;

  -- 1. Lo stato: la frase e' quella del lock delle righe.
  IF v_stato IS DISTINCT FROM 'DRAFT' THEN
    RETURN jsonb_build_array(jsonb_build_object(
      'codice',     'E_RIGA_DOC_NON_BOZZA',
      'reason',     'DDT_NON_IN_BOZZA',
      'reason_key', 'vendite.ddt.correggi_qta_evasa_reason.ddt_non_in_bozza',
      'dettaglio',  jsonb_build_object('stato', v_stato),
      'valori',     jsonb_build_array(v_etichetta, v_stato, 'modificare')));
  END IF;

  -- 2. La riga a mano: il predicato e' vendite.fn_ddt_riga_evasa
  --    (sede unica di «riga evasa»).
  IF NOT vendite.fn_ddt_riga_evasa(p_ddt_riga_id) THEN
    RETURN jsonb_build_array(jsonb_build_object(
      'codice',     'E_DDT_RIGA_NON_EVASA',
      'reason',     'RIGA_NON_EVASA',
      'reason_key', 'vendite.ddt.correggi_qta_evasa_reason.riga_non_evasa',
      'dettaglio',  jsonb_build_object('ddt_riga_id', p_ddt_riga_id),
      'valori',     jsonb_build_array(v_riga_nr::text, v_etichetta)));
  END IF;

  -- 3. La bolla non dichiara un'origine (D-2, D-7): un legame scritto
  --    a mano su una bolla standalone.
  IF v_sorgente IS NULL OR v_sorgente NOT IN ('ORDINE_VENDITA', 'RESO_VENDITA') THEN
    RETURN jsonb_build_array(jsonb_build_object(
      'codice',     'E_DDT_RIGA_NON_EVASA',
      'reason',     'DDT_SENZA_ORIGINE',
      'reason_key', 'vendite.ddt.correggi_qta_evasa_reason.ddt_senza_origine',
      'dettaglio',  jsonb_build_object('sorgente', v_sorgente),
      'valori',     jsonb_build_array(v_riga_nr::text, v_etichetta)));
  END IF;

  -- 4. Una quantita' sola non sa dividersi fra piu' legami dello
  --    stesso tipo.
  SELECT (SELECT count(*) FROM vendite.ordini_righe_fulfillment f
           WHERE f.ddt_riga_id = p_ddt_riga_id),
         (SELECT count(*) FROM vendite.resi_righe_riconsegne rr
           WHERE rr.ddt_riga_id = p_ddt_riga_id)
    INTO v_ful, v_ric;
  IF v_ful > 1 OR v_ric > 1 THEN
    RETURN jsonb_build_array(jsonb_build_object(
      'codice',     'E_DDT_RIGA_EVASA_LEGAMI_MULTIPLI',
      'reason',     'LEGAMI_MULTIPLI',
      'reason_key', 'vendite.ddt.correggi_qta_evasa_reason.legami_multipli',
      'dettaglio',  jsonb_build_object('fulfillment', v_ful, 'riconsegne', v_ric),
      'valori',     jsonb_build_array(v_riga_nr::text, v_etichetta)));
  END IF;

  RETURN jsonb_build_array();
END;
$function$

COMMENT ON FUNCTION script.fn_check_ddt_riga_correggi_qta_evasa(p_ddt_riga_id bigint)
IS 'Check dell''azione di riga «correggi la quantita'' evasa» (2026-10-11, brief-db-ddt-righe-evase-dall-ordine D-2, D-7, linee-guida-sql §12.5): funzione pura. NULL: riga assente o non visibile (RLS). []: ammessa. Altrimenti il primo motivo, in quest''ordine (l''ordine e'' il contratto: il verbo solleva il primo): DDT_NON_IN_BOZZA (E_RIGA_DOC_NON_BOZZA, valori etichetta, stato, verbo — la frase del lock delle righe); RIGA_NON_EVASA (E_DDT_RIGA_NON_EVASA: riga a mano, vendite.fn_ddt_riga_evasa falso); DDT_SENZA_ORIGINE (E_DDT_RIGA_NON_EVASA: la bolla non ha come sorgente un ordine o un reso, cioe'' il legame e'' stato scritto a mano su una bolla standalone); LEGAMI_MULTIPLI (E_DDT_RIGA_EVASA_LEGAMI_MULTIPLI, TECNICO: piu'' di un fulfillment o piu'' di un ponte di ri-consegna sulla stessa riga, forma che nessuna madre produce). Dal D-7 la ri-consegna di un reso si corregge come la riga da ordine. reason_key vendite.ddt.correggi_qta_evasa_reason.*; valori numero di riga ed etichetta del DDT. Consumatori: il verbo vendite.fn_ddt_riga_correggi_qta_evasa e la colonna correggi_qta_evasa_blocco di vendite.vw_ddt_righe_dettaglio. ⭐ rev 2026-10-19 (20261019-56, brief-db-grammatica-unica-documenti lotto 2a, G-1 di Tid): la grammatica delle testate passa ai codici delle sorgenti (DDT -> DDT_VENDITA, ORDINE -> ORDINE_VENDITA, OFFERTA -> OFFERTA_COMMERCIALE, RESO -> RESO_VENDITA, EMAIL_BOZZA -> EMAIL; PREVENTIVO, CONTRATTO, COMMESSA, FATTURA invariati); dove sopra si legge un codice corto come selettore, oggi vale il codice della sorgente.';
```

</div>

---
{% include-markdown "signature-core.md" %}
