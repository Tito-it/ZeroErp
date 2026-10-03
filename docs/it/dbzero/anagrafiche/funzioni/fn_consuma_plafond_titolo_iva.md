{% include-markdown "it/dbzero/anagrafiche/manual/fn_consuma_plafond_titolo_iva.md" %}
# ⚙️ Funzione `fn_consuma_plafond_titolo_iva`

```sql
CREATE FUNCTION fn_consuma_plafond_titolo_iva(p_titolo_iva_id bigint, p_fattura_id bigint, p_imponibile numeric, p_data_movimento date, p_fattura_riga_id bigint, p_tx_id uuid)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION anagrafiche.fn_consuma_plafond_titolo_iva(p_titolo_iva_id bigint, p_fattura_id bigint, p_imponibile numeric, p_data_movimento date, p_fattura_riga_id bigint DEFAULT NULL::bigint, p_tx_id uuid DEFAULT NULL::uuid)
 RETURNS TABLE(quota_coperta numeric, quota_ordinaria numeric, residuo_dopo numeric, movimento_id bigint)
 LANGUAGE plpgsql
AS $function$
-- Scopo: consumare la capienza di un titolo IVA per UNA riga (o per
--   la sola fattura, riga NULL) e ritornare la RIPARTIZIONE fra parte
--   coperta e parte ordinaria (P2).
--   Perimetro: dal 2026-10-03 e' l'INVOLUCRO a una riga di
--   anagrafiche.fn_consuma_plafond_titolo_iva_righe, che e' la sede
--   delle regole (guard, lock D15-bis, validita', titolo senza tetto,
--   idempotenza, capienza): qui non se ne ricopia nessuna.
--   Firma e risultato invariati: i chiamanti non cambiano.
--   Brief: brief-db-bom-flag-quantita-e-kit-in-fattura §11 (D-5).
DECLARE
    v_r record;
BEGIN
    SELECT g.quota_coperta, g.quota_ordinaria, g.residuo_dopo, g.movimento_id
      INTO v_r
      FROM anagrafiche.fn_consuma_plafond_titolo_iva_righe(
               p_titolo_iva_id,
               p_fattura_id,
               ARRAY[p_fattura_riga_id],
               ARRAY[p_imponibile],
               p_data_movimento,
               p_tx_id) g;

    quota_coperta   := v_r.quota_coperta;
    quota_ordinaria := v_r.quota_ordinaria;
    residuo_dopo    := v_r.residuo_dopo;
    movimento_id    := v_r.movimento_id;
    RETURN NEXT;
END;
$function$

COMMENT ON FUNCTION anagrafiche.fn_consuma_plafond_titolo_iva(p_titolo_iva_id bigint, p_fattura_id bigint, p_imponibile numeric, p_data_movimento date, p_fattura_riga_id bigint, p_tx_id uuid)
IS 'La primitiva di consumo del plafond a UNA riga (D15-bis di brief-db-be-iva-risolutore-e-regime-cliente): ritorna la RIPARTIZIONE che P2 pretende, quota coperta dal titolo + quota che torna all''aliquota ordinaria, la cui somma e'' sempre l''imponibile passato. ⭐ Dal 2026-10-03 (brief-db-bom-flag-quantita-e-kit-in-fattura §11, D-5) e'' l''INVOLUCRO a una riga di anagrafiche.fn_consuma_plafond_titolo_iva_righe, che consuma per un GRUPPO di righe (un kit) con una frazione sola ed e'' la sede delle regole: guard, LOCK di riga sul titolo, validita'', titolo senza tetto (copre tutto e non scrive), idempotenza (la stessa fattura e riga non consuma due volte), capienza GREATEST(residuo, 0). Firma e risultato invariati. 🔴 Il lock non e'' prudenziale: due transizioni a DEFINITIVA in parallelo, senza lock, consumano la stessa capienza e mandano il plafond sotto zero IN SILENZIO. ⚠️ Il lock non basta e la seconda meta'' e'' DICHIARATA: l''ordine deterministico (data documento, poi numero) e'' del ciclo che chiama. ⭐ Ritorna una RIPARTIZIONE e non un numero (§2.7.3). ⛔ NON e'' il risolutore, che e'' STABLE e non consuma (D14), e non fa la restituzione della nota di credito (P4), che e'' un INSERT nel registro con importo negativo. I7 di brief-db-be-iva-risolutore-e-regime-cliente.';
```

---
{% include-markdown "signature-core.md" %}
