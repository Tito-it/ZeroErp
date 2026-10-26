{% include-markdown "it/dbzero/script/manual/fn_check_commessa_chiudibile.md" %}
# ⚙️ Funzione `fn_check_commessa_chiudibile`

```sql
CREATE FUNCTION fn_check_commessa_chiudibile(p_commessa_id bigint)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_check_commessa_chiudibile(p_commessa_id bigint)
 RETURNS jsonb
 LANGUAGE plpgsql
 STABLE
AS $function$
-- Scopo: elencare i motivi che impediscono la CHIUSURA di una
--   commessa. Funzione PURA (fn_check_*): nessun raise di dominio,
--   nessuna scrittura. Consumatori: il guard di transizione (che
--   solleva il codice del primo motivo) e fn_available_actions_commessa
--   (che espone l'azione disabled + reasons).
--   Brief: brief-db-guard-uscita-commessa-e-capabilities §3.2.
-- Ritorna: [] se chiudibile; altrimenti array ordinato di
--   {codice, reason, reason_key, dettaglio}.
DECLARE
  v_motivi  jsonb   := '[]'::jsonb;
  v_pendenti integer;
  v_codice  vendite.commesse.codice%TYPE;
BEGIN
  -- Guard parametro (AGENTS.md): id assente o non valido e' un errore
  -- di programmazione, non una condizione di dominio.
  IF p_commessa_id IS NULL OR p_commessa_id <= 0 THEN
    PERFORM script.fn_log_and_raise_error(
      'script','fn_check_commessa_chiudibile','E_PARAMETRO_INVALIDO',
      jsonb_build_object('parametro','commessa_id','valore',p_commessa_id),
      NULL::uuid, 'commessa_id obbligatorio (>0)');
  END IF;

  -- MOTIVO 1 — righe approvate e non ancora emesse (D2).
  -- Congiunzione sui DUE assi distinti: stato_approvazione e
  -- stato_emissione sono colonne separate con CHECK separati.
  -- Sono le righe che fn_list_commesse_emittibili avrebbe raccolto:
  -- chiudere sopra di esse le perde, e CHIUSA e' irreversibile.
  -- Indice: ix_commesse_attivita_commessa_stati.
      -- ⭐ LA CHIAVE VISIBILE, dal 2026-09-09. Non serve a DECIDERE — il
      --   verdetto non la guarda — ma a COMPORRE la frase del motivo che
      --   questa funzione ha scelto: «%s: ...» vuole il nome che una persona
      --   riconosce, non l'id. Finche' i `valori` li metteva il chiamante,
      --   glieli dava NEW; adesso il codice e la sua frase escono dallo stesso
      --   posto, che e' tutto il senso di §12.5.2.
      -- ⚠️ Dentro un trigger BEFORE questa SELECT legge la riga PRE-modifica,
      --   mentre il chiamante usava NEW. Sulle transizioni di stato le due
      --   coincidono (una transizione non rinomina il documento) ed e' anzi il
      --   valore che l'operatore ha davanti sullo schermo — ma va detto, non
      --   dato per scontato.
  SELECT c.codice INTO v_codice
    FROM vendite.commesse c
   WHERE c.id = p_commessa_id;

  SELECT count(*)
    INTO v_pendenti
    FROM vendite.commesse_attivita ca
   WHERE ca.commessa_id = p_commessa_id
     AND ca.stato_approvazione = 'APPROVATA'
     AND ca.stato_emissione    = 'NON_EMESSA';

  IF v_pendenti > 0 THEN
    v_motivi := v_motivi || jsonb_build_object(
      'codice',     'E_COMMESSA_CHIUSURA_CON_RIGHE_PENDENTI',
      'reason',     'RIGHE_DA_EMETTERE',
      'reason_key', 'vendite.commesse.azione_reason.righe_da_emettere',
      'dettaglio',  v_pendenti,
      -- «Commessa %s: chiusura non consentita, %s riga/e approvate ...»
      'valori',     jsonb_build_array(COALESCE(v_codice, p_commessa_id::text),
                                      v_pendenti));
  END IF;

  RETURN v_motivi;
END;
$function$

COMMENT ON FUNCTION script.fn_check_commessa_chiudibile(p_commessa_id bigint)
IS 'Funzione PURA (fn_check_*): motivi ostativi alla chiusura di una commessa. Ritorna [] se chiudibile, altrimenti array di {codice, reason, reason_key, dettaglio}. Motivo unico: esistono righe APPROVATA+NON_EMESSA (codice 559) — quelle che fn_list_commesse_emittibili avrebbe raccolto, e CHIUSA e'' terminale/irreversibile. Speculare al guard di INGRESSO ->PRONTA_FATTURAZIONE (E_COMMESSA_NESSUNA_RIGA_APPROVATA). Rende sicuro l''arco IN_ESECUZIONE->CHIUSA. Sorgente UNICA condivisa da vendite.trgfn_commesse_guard_transizione (solleva) e script.fn_available_actions_commessa (espone enabled/reasons). rev 2026-07-24.';
```

</div>

---
{% include-markdown "signature-core.md" %}
