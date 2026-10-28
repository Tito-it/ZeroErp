{% include-markdown "it/dbzero/script/manual/fn_scope_ef_whitelist_via_contabile.md" %}
# ⚙️ Funzione `fn_scope_ef_whitelist_via_contabile`

```sql
CREATE FUNCTION fn_scope_ef_whitelist_via_contabile(p_auth_user_id integer, p_contabile_id bigint)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_scope_ef_whitelist_via_contabile(p_auth_user_id integer, p_contabile_id bigint)
 RETURNS boolean
 LANGUAGE sql
 STABLE COST 5000
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
IS 'Scope dell''operatore su una DISTINTA contabile: risolve distinta -> emittente (dal 2026-09-15 leggendo pagamenti.vendite_contabili.emittente_soggetto_ruolo_id, prima per la catena canale -> conto -> soggetto -> emittente) e delega alla canonica. Serve alle policy dei satelliti (righe, manifesto dei lotti), che dalla testata prendono il perimetro. ⭐ Rev 2026-09-15 (brief distinta-numerata-sul-registro, D3): una distinta INTERNA (fondo fattura, sistemazione) e'' del suo emittente come il lotto o l''atto da cui nasce, quindi qui risponde TRUE per lui e FALSE per gli altri — fino a quel giorno rispondeva FALSE a tutti («non e'' il canale di nessuno»), e la testata era visibile a tutti: quel ramo non descrive piu'' il modello. ⭐ Resta SECURITY INVOKER come le sorelle perche'' e'' il risolutore a essere DEFINER: leggendo pagamenti.vendite_contabili, la cui policy chiama la gemella via_sr, da INVOKER sarebbe una ricorsione.';
```

</div>

---
{% include-markdown "signature-core.md" %}
