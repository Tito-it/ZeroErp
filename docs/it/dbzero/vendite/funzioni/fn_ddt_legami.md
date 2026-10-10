# ⚙️ Funzione `fn_ddt_legami`

```sql
CREATE FUNCTION fn_ddt_legami(p_ddt_id bigint)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.fn_ddt_legami(p_ddt_id bigint)
 RETURNS TABLE(ddt_riga_id bigint, riga_nr integer, origine text, origine_riga_id bigint, qta numeric)
 LANGUAGE sql
 STABLE
AS $function$
    SELECT dr.id, dr.riga_nr, 'ORDINE'::text, f.ordine_riga_id, f.qta_evasa::numeric
      FROM vendite.ddt_righe dr
      JOIN vendite.ordini_righe_fulfillment f ON f.ddt_riga_id = dr.id
     WHERE dr.ddt_id = p_ddt_id
    UNION ALL
    SELECT dr.id, dr.riga_nr, 'RESO'::text, rr.resi_riga_id, rr.qta::numeric
      FROM vendite.ddt_righe dr
      JOIN vendite.resi_righe_riconsegne rr ON rr.ddt_riga_id = dr.id
     WHERE dr.ddt_id = p_ddt_id;
$function$

COMMENT ON FUNCTION vendite.fn_ddt_legami(p_ddt_id bigint)
IS 'I legami di una bolla, riga per riga (2026-10-11, brief-db-ddt-righe-evase-dall-ordine D-8): una riga per legame, origine ORDINE (vendite.ordini_righe_fulfillment: origine_riga_id = riga d''ordine, qta = qta_evasa) o RESO (vendite.resi_righe_riconsegne: origine_riga_id = riga di reso, qta del ponte). Risponde a «quali quantita'' tornano all''origine se annullo questa bolla»: sede unica per l''avviso (vendite.trgfn_ddt_guard_transizione, E_DDT_ANNULLO_CON_LEGAMI), la conferma e il ritiro (vendite.fn_annulla_ddt) e la finestra di conferma del backend. Niente etichette di documento: per il gesto «vai al documento» il backend usa il lineage (vendite.vw_documento_lineage_archi), che risponde a un''altra domanda (da quali documenti viene la bolla, a livello di testata). origine_riga_id e qta polimorfi, tipi nudi dichiarati. SECURITY INVOKER.';
```

---
{% include-markdown "signature-core.md" %}
