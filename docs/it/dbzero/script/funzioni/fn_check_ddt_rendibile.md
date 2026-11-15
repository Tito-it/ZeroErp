{% include-markdown "it/dbzero/script/manual/fn_check_ddt_rendibile.md" %}
# ⚙️ Funzione `fn_check_ddt_rendibile`

```sql
CREATE FUNCTION fn_check_ddt_rendibile(p_ddt_id bigint)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_check_ddt_rendibile(p_ddt_id bigint)
 RETURNS jsonb
 LANGUAGE plpgsql
 STABLE
AS $function$
-- rev 2026-11-14 (brief-db-stati-documento-dal-vocabolario, giro 6e-bis): i
--   valori di DDT_NON_CONSEGNATO sono quelli della frase, nessuno.
-- Scopo: elencare i motivi per cui da una bolla non nasce un reso.
--   Funzione PURA (fn_check_*): [] = lecito.
--   Consumatori: vendite.trgfn_resi_guard_ddt_consegnato (solleva il
--   primo) e script.fn_available_actions_ddt (can_genera_reso).
--   Brief: brief-db-stati-documento-dal-vocabolario §6.22 (D-RESO).
DECLARE
  -- L'elenco dei motivi: nessuna colonna di cui sia il riflesso.
  v_motivi jsonb := '[]'::jsonb;
  v_ddt    vendite.ddt%ROWTYPE;
  v_stato  config.stati_doc_ddt.codice_interno%TYPE;
BEGIN
  IF p_ddt_id IS NULL OR p_ddt_id <= 0 THEN
    PERFORM script.fn_log_and_raise_error(
      'script', 'fn_check_ddt_rendibile', 'E_PARAMETRO_INVALIDO',
      jsonb_build_object('parametro', 'ddt_id', 'valore', p_ddt_id),
      NULL::uuid, 'ddt_id obbligatorio (>0)');
  END IF;

  SELECT d.* INTO v_ddt
    FROM vendite.ddt d
   WHERE d.id = p_ddt_id;

  -- 1. Una bolla di TRASFERIMENTO fra depositi non genera un reso: la
  --    merce e' rimasta nostra (e' entrata nel magazzino di arrivo alla
  --    consegna), un reso la farebbe rientrare una seconda volta, con un
  --    accredito verso chi non l'ha comprata. Si riconosce dalla causale
  --    di magazzino della sua causale di trasporto (TRASF_OUT). Prima
  --    dello stato: e' la risposta vera anche su una bolla consegnata.
  IF FOUND AND vendite.fn_ddt_causale_magazzino(v_ddt) = 'TRASF_OUT' THEN
    RETURN jsonb_build_array(jsonb_build_object(
      'codice',     'E_RESO_DA_DDT_TRASFERIMENTO',
      'reason',     'DDT_TRASFERIMENTO',
      'reason_key', 'vendite.ddt.genera_reso_reason.trasferimento',
      'dettaglio',  jsonb_build_object('ddt_id', v_ddt.id),
      'valori',     jsonb_build_array(COALESCE(v_ddt.numero, v_ddt.id::text))));
  END IF;

  -- 2. Si rende cio' che e' stato consegnato: CONSEGNATO e' la
  --    destinazione del processo di consegna, e si nomina col codice
  --    (S-3). Una bolla assente non e' consegnata (stato 'NULL').
  SELECT sdd.codice_interno INTO v_stato
    FROM config.stati_doc_ddt sdd
   WHERE sdd.id = v_ddt.stato_doc_ddt_id;

  IF v_stato IS DISTINCT FROM 'CONSEGNATO' THEN
    v_motivi := v_motivi || jsonb_build_object(
      'codice',     'E_RESO_DDT_NON_CONSEGNATO',
      'reason',     'DDT_NON_CONSEGNATO',
      'reason_key', 'vendite.ddt.genera_reso_reason.non_consegnato',
      'dettaglio',  jsonb_build_object('ddt_id', p_ddt_id,
                                       'stato_ddt', COALESCE(v_stato, 'NULL')),
      -- Nessun valore: la frase del codice non ha segnaposti, e i valori
      -- sono esattamente i suoi (script/test-catalogo-messaggi-errore-completo,
      -- test 7). L'id e lo stato della bolla stanno nel dettaglio.
      'valori',     jsonb_build_array());
  END IF;

  RETURN v_motivi;
END;
$function$

COMMENT ON FUNCTION script.fn_check_ddt_rendibile(p_ddt_id bigint)
IS 'Pure check: i motivi per cui da una bolla non nasce un reso; [] = lecito. Nell''ordine (si esce al primo): E_RESO_DA_DDT_TRASFERIMENTO (reason DDT_TRASFERIMENTO, reason_key vendite.ddt.genera_reso_reason.trasferimento, valori il numero della bolla) per una bolla di trasferimento fra depositi, riconosciuta dalla causale di magazzino TRASF_OUT (vendite.fn_ddt_causale_magazzino); E_RESO_DDT_NON_CONSEGNATO (reason DDT_NON_CONSEGNATO, reason_key vendite.ddt.genera_reso_reason.non_consegnato, nessun valore: la frase non ha segnaposti) per una bolla che non e'' in CONSEGNATO, la destinazione del processo di consegna, o che non c''e'' (stato NULL). dettaglio {ddt_id} e {ddt_id, stato_ddt}: l''id e lo stato della bolla stanno li''. Sede unica della regola: la leggono vendite.trgfn_resi_guard_ddt_consegnato, che solleva il primo motivo, e script.fn_available_actions_ddt, che ne fa can_genera_reso. Parametro non valido: E_PARAMETRO_INVALIDO.';
```

</div>

---
{% include-markdown "signature-core.md" %}
