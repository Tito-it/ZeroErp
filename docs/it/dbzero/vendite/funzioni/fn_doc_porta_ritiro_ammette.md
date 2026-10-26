# ⚙️ Funzione `fn_doc_porta_ritiro_ammette`

```sql
CREATE FUNCTION fn_doc_porta_ritiro_ammette(p_documento character varying, p_testata_id bigint, p_tabella regclass, p_cambiate text[])
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_doc_porta_ritiro_ammette(p_documento character varying, p_testata_id bigint, p_tabella regclass, p_cambiate text[] DEFAULT NULL::text[])
 RETURNS boolean
 LANGUAGE sql
 STABLE
AS $function$

    -- Scopo: dire se una scrittura e' il ritiro dei legami di
    --   QUESTO documento dopo la conferma. Vedi l'intestazione.
    -- Parametri polimorfi (documento, testata): tipi nudi.
    SELECT p_documento IS NOT NULL
       AND p_testata_id IS NOT NULL
       AND COALESCE(current_setting('zeroerp.doc_ritira_legami', true), '')
           = p_documento || ':' || p_testata_id::text
       AND script.fn_is_proprietario_tabella(p_tabella)
       AND CASE
             -- La testata: il guard dell'annullo (provenienza).
             WHEN p_tabella = CASE p_documento
                                WHEN 'DDT_VENDITA'        THEN 'vendite.ddt'::regclass
                                WHEN 'ORDINE_VENDITA'     THEN 'vendite.ordini'::regclass
                                WHEN 'PREVENTIVO' THEN 'vendite.preventivi'::regclass
                                WHEN 'CONTRATTO'  THEN 'vendite.contratti'::regclass
                                -- rev 2026-10-26 (20261026-22, §13, O-4).
                                WHEN 'OFFERTA_COMMERCIALE' THEN 'vendite.offerte_commerciali'::regclass
                              END
               THEN true
             -- DDT: si cancellano i legami con ordini e resi.
             WHEN p_documento = 'DDT_VENDITA'
               THEN p_cambiate IS NULL
                    AND p_tabella IN ('vendite.ordini_righe_fulfillment'::regclass,
                                      'vendite.resi_righe_riconsegne'::regclass)
             -- ORDINE: la riga si stacca dal preventivo (D-2).
             WHEN p_documento = 'ORDINE_VENDITA'
               THEN p_cambiate IS NOT NULL
                    AND p_tabella = 'vendite.ordini_righe'::regclass
                    AND p_cambiate <@ ARRAY['preventivo_riga_id', 'data_update',
                                            'user_update', 'tx_id']
             ELSE false
           END;
$function$

COMMENT ON FUNCTION vendite.fn_doc_porta_ritiro_ammette(p_documento character varying, p_testata_id bigint, p_tabella regclass, p_cambiate text[])
IS 'BB (2026-10-11, brief-db-annullo-documento-con-legami D-4): la porta del ritiro dei legami. Vero se la GUC transazionale zeroerp.doc_ritira_legami vale ''<DOCUMENTO>:<id>'' (la apre vendite.fn_documento_ritira_legami, dopo la conferma), chi scrive e'' il proprietario della tabella (script.fn_is_proprietario_tabella: i verbi DEFINER, mai una GUC accesa dall''applicazione) e la scrittura e'' una di quelle che il ritiro fa: la testata del documento (il guard dell''annullo, per i legami di provenienza); DDT: DELETE su vendite.ordini_righe_fulfillment e vendite.resi_righe_riconsegne; ORDINE: UPDATE di vendite.ordini_righe che cambia solo preventivo_riga_id (piu'' data_update, user_update, tx_id). p_cambiate NULL = DELETE o testata. Allowlist. Lettori: vendite.trgfn_ddt_riga_legame_guard, vendite.trgfn_doc_righe_lock_fuori_bozza, vendite.trgfn_doc_guard_annullo_con_legami. Prende il posto della GUC zeroerp.ddt_annullo della bolla. SECURITY INVOKER. ⭐ rev 2026-10-19 (20261019-50, brief-db-grammatica-unica-documenti lotto 2a, G-1 di Tid): la grammatica delle testate passa ai codici delle sorgenti (DDT -> DDT_VENDITA, ORDINE -> ORDINE_VENDITA, OFFERTA -> OFFERTA_COMMERCIALE, RESO -> RESO_VENDITA, EMAIL_BOZZA -> EMAIL; PREVENTIVO, CONTRATTO, COMMESSA, FATTURA invariati); dove sopra si legge un codice corto come selettore, oggi vale il codice della sorgente. p_documento ancorato a config.sorgenti.codice_interno%TYPE: la firma passa da text a character varying (DROP + CREATE, nessun dipendente registrato). ⭐ rev 2026-10-26 (20261026-22, brief-modello-documento-vendita §13, O-4 di Tid): + OFFERTA_COMMERCIALE, la sola testata (vendite.offerte_commerciali): il legame dell''offerta e'' di provenienza, e la porta serve al guard dell''annullo dopo la conferma.';
```

</div>

---
{% include-markdown "signature-core.md" %}
