{% include-markdown "it/dbzero/script/manual/fn_doc_stato_modello.md" %}
# ⚙️ Funzione `fn_doc_stato_modello`

```sql
CREATE FUNCTION fn_doc_stato_modello(p_testata regclass)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_doc_stato_modello(p_testata regclass)
 RETURNS TABLE(colonna_stato text, vocabolario regclass, matrice regclass, colonna_da text, colonna_a text, colonna_vivo text, filtro text)
 LANGUAGE sql
 STABLE
AS $function$
    -- Scopo: dove sta lo stato di una testata e quale matrice ne
    --   dice i passaggi. Tipi nudi: nomi di colonna e tabelle,
    --   nessuna colonna di cui siano il riflesso.
    -- Nessuna riga: la testata non ha (ancora) una matrice.
    SELECT m.col, m.voc, m.mat, m.da, m.a, m.vivo, m.filtro
      FROM (VALUES
        ('vendite.preventivi'::regclass,          'stato_doc_preventivo_id', 'config.stati_doc_preventivi'::regclass, 'config.transizioni_stati_preventivi'::regclass,  'stato_da_id',   'stato_a_id',  'attivo',  ''),
        ('vendite.offerte_commerciali'::regclass, 'stato_doc_offerta_id',    'config.stati_doc_offerte'::regclass,    'config.stati_doc_offerte_transizioni'::regclass, 'stato_da_id',   'stato_a_id',  'attivo',  ''),
        ('vendite.contratti'::regclass,           'stato_doc_contratto_id',  'config.stati_doc_contratti'::regclass,  'config.transizioni_stati_contratti'::regclass,   'stato_da_id',   'stato_a_id',  'attivo',  ''),
        ('vendite.ordini'::regclass,              'stato_doc_ordine_id',     'config.stati_doc_ordini'::regclass,     'config.transizioni_stati_ordini'::regclass,      'stato_da_id',   'stato_a_id',  'attivo',  ''),
        ('vendite.ddt'::regclass,                 'stato_doc_ddt_id',        'config.stati_doc_ddt'::regclass,        'config.transizioni_stati_ddt'::regclass,         'stato_da_id',   'stato_a_id',  'attivo',  ''),
        ('vendite.resi'::regclass,                'stato_doc_reso_id',       'config.stati_doc_reso'::regclass,       'config.transizioni_stati_reso'::regclass,        'stato_da_id',   'stato_a_id',  'attivo',  ''),
        ('vendite.commesse'::regclass,            'stato_commessa_id',       'vendite.stati_commessa'::regclass,      'vendite.transizioni_stati_commessa'::regclass,   'stato_da_id',   'stato_a_id',  'attivo',  ''),
        ('vendite.fatture'::regclass,             'stato_doc_fiscale_id',    'config.stati_doc_fiscale'::regclass,    'config.stati_doc_fiscale_transizioni'::regclass, 'stato_from_id', 'stato_to_id', 'ammesso', 'AND t.solo_lotto IS FALSE'),
        ('vendite.fatturazione_lotti'::regclass,  'stato_doc_fiscale_id',    'config.stati_doc_fiscale'::regclass,    'config.stati_doc_fiscale_transizioni'::regclass, 'stato_from_id', 'stato_to_id', 'ammesso', 'AND t.solo_fattura IS FALSE')
      ) AS m(tab, col, voc, mat, da, a, vivo, filtro)
     WHERE m.tab = p_testata;
$function$

COMMENT ON FUNCTION script.fn_doc_stato_modello(p_testata regclass)
IS 'BB del modello del documento: per una testata, dove sta il suo stato (colonna_stato, vocabolario) e quale matrice ne dice i passaggi (matrice, con i nomi delle sue colonne da / a / passaggio vivo, e il filtro in piu'' della fattura e del lotto, che condividono config.stati_doc_fiscale_transizioni). Nessuna riga: la testata non ha una matrice. E'' codice, non configurazione: una testata nuova entra riscrivendo la funzione. Consumatori: il verbo comune (script.fn_doc_passaggio, script.fn_doc_scrivi_stato), la porta script.trgfn_doc_stato_solo_dal_verbo, la fixture dbops.fn_pgtap_porta_a_stato. Brief: brief-modello-documento-vendita §7 (S-2, Tid 2026-10-25).';
```

</div>

---
{% include-markdown "signature-core.md" %}
