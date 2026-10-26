{% include-markdown "it/dbzero/script/manual/trgfn_prevent_modification_generic.md" %}
# ⚙️ Funzione `trgfn_prevent_modification_generic`

```sql
CREATE FUNCTION trgfn_prevent_modification_generic()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.trgfn_prevent_modification_generic()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo: guard generico montato su piu' tabelle per vietare
--   UPDATE/DELETE. Solleva sempre: la sola presenza del trigger
--   e' la regola.
--   rev 2026-08-06: il nome passato al log era il letterale
--   'trgfn_prevent_parameters_audit_modification', funzione che
--   nel database non esiste piu'. Ogni errore di questo guard
--   finiva in dbops.error_log sotto un pezzo fantasma. Ora e'
--   TG_NAME: lo mette il trigger che scatta, quindi non puo'
--   invecchiare — ed e' anche piu' informativo, perche' dice
--   QUALE dei trigger montati ha rifiutato. Brief terzo lato
--   §15.4c.
BEGIN

  PERFORM script.fn_log_and_raise_error(
      'database',
      TG_NAME,
      'E_TABELLA_OP_NON_CONSENTITA',
      jsonb_build_object(
        'nome_tabella', TG_TABLE_NAME,
        'trigger_op',        TG_OP
      ),
      NULL::uuid,
      TG_TABLE_NAME::text,
      TG_OP::text
    );

  -- rev 2026-08-04 (bonifica riferimenti morti, F6): manca(va) il RETURN.
  --   Oggi la riga sopra solleva sempre, quindi il flusso non ci arriva —
  --   ma «non ci arriva mai» e' una proprieta' di
  --   script.fn_log_and_raise_error, non di questa funzione. Il giorno in
  --   cui quella diventasse non-fatale in qualche ramo, una trigger
  --   function che cade oltre il proprio END solleva 2F005 al posto
  --   dell'errore di dominio. Il RETURN NULL e' anche la risposta giusta
  --   nel merito: BEFORE ROW, l'operazione va annullata.
  RETURN NULL;
END;
$function$

COMMENT ON FUNCTION script.trgfn_prevent_modification_generic()
IS 'Segnala errore su attività non consentite sulle tabelle. rev 2026-08-06: il nome registrato in dbops.error_log e'' TG_NAME e non piu'' il letterale ''trgfn_prevent_parameters_audit_modification'', funzione che non esiste piu'' nel database — il diario degli errori puntava a un pezzo fantasma e chi indagava partiva da un nome inesistente. Una funzione generica montata su N tabelle non ha UN nome da dichiarare: TG_NAME dice quale trigger ha rifiutato. Brief brief-db-be-terzo-lato-presidio-codici §15.4c.';
```

</div>

---
{% include-markdown "signature-core.md" %}
