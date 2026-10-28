{% include-markdown "it/dbzero/dbops/manual/fn_sorgenti_orfane_perimetro.md" %}
# ⚙️ Funzione `fn_sorgenti_orfane_perimetro`

```sql
CREATE FUNCTION fn_sorgenti_orfane_perimetro()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_sorgenti_orfane_perimetro()
 RETURNS TABLE(tabella regclass, col_tipo name, col_riga name, col_uid name)
 LANGUAGE sql
 STABLE
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$
    -- Scopo: il gemello «esiste» di fn_sorgenti_orfane — le tabelle con una FK
    --   verso config.sorgenti sulla colonna del tipo E le due colonne di chiave
    --   (modello A tipizzato). Derivato dal catalogo, non da un elenco.
    SELECT c.conrelid::regclass      AS tabella,
           a.attname                 AS col_tipo,
           'sorgente_riga'::name     AS col_riga,
           'sorgente_uid'::name      AS col_uid
      FROM pg_constraint c
      JOIN pg_attribute a ON a.attrelid = c.conrelid AND a.attnum = ANY (c.conkey)
     WHERE c.contype = 'f'
       AND c.confrelid = 'config.sorgenti'::regclass
       AND array_length(c.conkey, 1) = 1
       AND EXISTS (SELECT 1 FROM pg_attribute r
                    WHERE r.attrelid = c.conrelid AND r.attname = 'sorgente_riga' AND NOT r.attisdropped)
       AND EXISTS (SELECT 1 FROM pg_attribute u
                    WHERE u.attrelid = c.conrelid AND u.attname = 'sorgente_uid' AND NOT u.attisdropped)
       -- ⭐ E il guard TIPIZZATO montato: e' lui il contratto del modello A
       --   («tipo => esattamente una chiave, che punta al bersaglio di
       --   key_selector»). Le tabelle di vendite con la stessa FK e le stesse
       --   colonne (attivita_fatturabili, fatture_righe, ...) hanno un'altra
       --   semantica — riga = la riga del documento, uid = il documento — e
       --   senza questo filtro davano 112 falsi orfani su dev (18-09). Entrano
       --   quando prendono il guard (roll-out D-3, cantiere dbops).
       AND EXISTS (SELECT 1 FROM pg_trigger tg
                    JOIN pg_proc tp ON tp.oid = tg.tgfoid
                   WHERE tg.tgrelid = c.conrelid
                     AND NOT tg.tgisinternal
                     AND tp.proname = 'trgfn_guard_sorgente_polimorfa_tipizzata')
     ORDER BY 1;
$function$

COMMENT ON FUNCTION dbops.fn_sorgenti_orfane_perimetro()
IS 'Il PERIMETRO di dbops.fn_sorgenti_orfane, reso visibile: le tabelle con una FK verso config.sorgenti su una colonna sola (sorgente_tipo_id), le due colonne sorgente_riga / sorgente_uid E il guard trgfn_guard_sorgente_polimorfa_tipizzata montato — e'' il guard il contratto del modello A (tipo => una chiave verso il bersaglio di key_selector). Le tabelle di vendite con FK e colonne ma senza guard hanno un''altra semantica e restano fuori finche'' non lo prendono (D-3). Derivato dal catalogo (pg_constraint + pg_trigger), non da un elenco: una tabella nuova con quella forma entra da sola. Il pgTAP asserisce che le sei di magazzino ci sono: un presidio che esamina zero tabelle e'' verde e muto. Brief: brief-db-magazzino-lotto-2-motore, sezione 4.7.';
```

</div>

---
{% include-markdown "signature-core.md" %}
