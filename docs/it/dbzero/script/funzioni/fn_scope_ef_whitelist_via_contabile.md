{% include-markdown "it/dbzero/script/manual/fn_scope_ef_whitelist_via_contabile.md" %}
# ⚙️ Funzione `fn_scope_ef_whitelist_via_contabile`

```sql
CREATE FUNCTION fn_scope_ef_whitelist_via_contabile(p_auth_user_id integer, p_contabile_id bigint)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION script.fn_scope_ef_whitelist_via_contabile(p_auth_user_id integer, p_contabile_id bigint)
 RETURNS boolean
 LANGUAGE sql
 STABLE
AS $function$
    -- Come la gemella, ma partendo dalla DISTINTA: la riga
    -- contabile il canale non ce l'ha in colonna, ce l'ha la sua
    -- testata.
    -- ⚠️ Distinta INTERNA (fondo fattura, compensazione): canale
    --   non ce n'e', l'emittente resta NULL e la risposta e'
    --   FALSE. ⭐ Ed e' esattamente cio' che serve: le RIGHE di una
    --   distinta interna non devono vedersi in giro. Che la
    --   TESTATA di quella distinta sia invece visibile e'
    --   una decisione diversa, e sta scritta nella policy — non
    --   qui dentro, cosi' chi legge la policy la vede.
    SELECT script.fn_check_user_emittente_scope(
        p_auth_user_id,
        script.fn_resolve_emittente_fiscale_id('contabile', p_contabile_id)
    );
$function$

COMMENT ON FUNCTION script.fn_scope_ef_whitelist_via_contabile(p_auth_user_id integer, p_contabile_id bigint)
IS 'Scope dell''operatore su una DISTINTA contabile: risolve distinta -> canale -> conto -> soggetto -> emittente e delega alla canonica. Serve alla policy della RIGA, che il canale lo raggiunge solo passando dalla testata. ⚠️ Su una distinta INTERNA (fondo fattura, compensazione), che canale non ha, risponde FALSE — ed e'' cio'' che serve: le righe di una distinta interna non devono vedersi in giro, e il loro perimetro lo da'' la fattura che portano. Che la TESTATA di quella distinta sia invece visibile e'' una decisione diversa, scritta nella policy. ⭐ Resta SECURITY INVOKER come le sorelle perche'' e'' il risolutore a essere DEFINER: leggendo pagamenti.vendite_contabili, la cui policy chiama questa funzione, da INVOKER sarebbe una ricorsione infinita.';
```

---
{% include-markdown "signature-core.md" %}
