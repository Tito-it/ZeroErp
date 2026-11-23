{% include-markdown "it/dbzero/magazzino/manual/fn_documento_interno_famiglia.md" %}
# ⚙️ Funzione `fn_documento_interno_famiglia`

```sql
CREATE FUNCTION fn_documento_interno_famiglia(p_famiglia text)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION magazzino.fn_documento_interno_famiglia(p_famiglia text)
 RETURNS TABLE(famiglia text, tabella text, tabella_righe text, colonna_fk text, colonna_stato text, colonna_magazzino text, guc_posting text)
 LANGUAGE sql
 IMMUTABLE ROWS 1
AS $function$
    -- Scopo: il registro delle famiglie dei documenti interni.
    --   Una riga per la famiglia chiesta, nessuna se non esiste.
    SELECT f.*
      FROM (VALUES
        ('INVENTARIO',    'inventari',     'inventari_righe',     'inventario_id',
         'stato_mag_inventario', 'magazzino_id',      'zeroerp.magazzino_posting_inventario'),
        ('RETTIFICA',     'rettifiche',    'rettifiche_righe',    'rettifica_id',
         'stato_mag_rettifiche', 'magazzino_id',      'zeroerp.magazzino_posting_rettifica'),
        ('TRASFERIMENTO', 'trasferimenti', 'trasferimenti_righe', 'trasferimento_id',
         'stato_trasferimento',  'magazzino_id_from', 'zeroerp.magazzino_posting_trasferimento')
      ) AS f(famiglia, tabella, tabella_righe, colonna_fk, colonna_stato,
             colonna_magazzino, guc_posting)
     WHERE f.famiglia = p_famiglia;
$function$

COMMENT ON FUNCTION magazzino.fn_documento_interno_famiglia(p_famiglia text)
IS 'Il registro delle famiglie dei documenti interni di magazzino (INVENTARIO, RETTIFICA, TRASFERIMENTO): per la famiglia chiesta, la tabella della testata, quella delle righe, la colonna che lega la riga alla testata, la colonna di stato, il magazzino che fa da perimetro (per il trasferimento quello di partenza) e la GUC con cui l''operazione di registrazione apre la porta POSTED. Nessuna riga per una famiglia che non esiste: il codice lo sceglie chi chiama. La tabella della testata e'' anche l''oggetto del permesso dei verbi (model_name di script.fn_guard_livello), per la testata e per le righe. Una funzione e non una tabella: una famiglia nuova vuole tabelle, trigger e vincoli, non si configura. IMMUTABLE. La leggono i verbi comuni dei documenti interni e script.fn_check_documento_interno_registrabile.';
```

</div>

---
{% include-markdown "signature-core.md" %}
