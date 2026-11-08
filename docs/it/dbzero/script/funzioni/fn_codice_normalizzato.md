{% include-markdown "it/dbzero/script/manual/fn_codice_normalizzato.md" %}
# ⚙️ Funzione `fn_codice_normalizzato`

```sql
CREATE FUNCTION fn_codice_normalizzato(p_codice text)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_codice_normalizzato(p_codice text)
 RETURNS text
 LANGUAGE sql
 IMMUTABLE PARALLEL SAFE STRICT
AS $function$
    -- La forma di un codice dell'operatore: senza spazi ai lati, in
    -- maiuscolo con la mappatura Unicode completa (ß -> SS).
    SELECT upper(btrim(p_codice) COLLATE pg_catalog.pg_unicode_fast);
$function$

COMMENT ON FUNCTION script.fn_codice_normalizzato(p_codice text)
IS 'BB (2026-11-04): la forma di un codice dell''operatore, in un posto solo. upper(btrim(p_codice) COLLATE pg_unicode_fast): senza spazi ai lati, in maiuscolo con la mappatura Unicode COMPLETA della collation builtin (SS per la ß tedesca, FI per la legatura fi), uguale su ogni macchina; la collation del database (libc) darebbe la mappatura semplice e lascerebbe la ß minuscola. La chiamano il trigger dell''automazione CODICE_MAIUSCOLO (script.trgfn_codice_maiuscolo), il guard di forma di anagrafiche.emittenti_fiscali, le funzioni che cercano per codice una tabella del perimetro e le ricerche esatte del backend: nessuno ricopia la formula. ⚠️ Il risultato puo'' essere PIU'' LUNGO dell''input: chi scrive lascia normalizzare al trigger, che lo rifiuta con E_CODICE_TROPPO_LUNGO_IN_MAIUSCOLO se supera la colonna; chi cerca la usa nella WHERE, non in una variabile ancorata a una colonna varchar(n) (darebbe 22001 invece di «non trovato»). IMMUTABLE come upper(): cambia solo fra versioni maggiori di PostgreSQL con tabelle Unicode nuove, e per questo non si costruiscono indici su di lei (il valore e'' salvato gia'' normalizzato, l''UNIQUE sta sulla colonna). STRICT: NULL resta NULL. LANGUAGE sql, si incorpora. Richiesta BE brief-be-codice-maiuscolo §6.';
```

</div>

---
{% include-markdown "signature-core.md" %}
