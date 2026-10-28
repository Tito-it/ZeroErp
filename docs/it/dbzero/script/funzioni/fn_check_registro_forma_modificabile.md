{% include-markdown "it/dbzero/script/manual/fn_check_registro_forma_modificabile.md" %}
# ⚙️ Funzione `fn_check_registro_forma_modificabile`

```sql
CREATE FUNCTION fn_check_registro_forma_modificabile(p_registro_id bigint)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_check_registro_forma_modificabile(p_registro_id bigint)
 RETURNS jsonb
 LANGUAGE plpgsql
 STABLE
 SET search_path TO 'pg_catalog', 'public'
AS $function$
DECLARE
    v_motivi    jsonb := '[]'::jsonb;
    v_codice    vendite.registri_fatturazione.codice%TYPE;
    v_ultimo    vendite.registri_fatturazione_progressivi.last_numero%TYPE;
    v_contatori bigint;
BEGIN
    -- =========================================================
    -- Scopo:
    --   Elencare i motivi che impediscono di CAMBIARE LA FORMA
    --   DEL NUMERO di un registro (prefisso, suffisso,
    --   lunghezza_numero). Funzione PURA (fn_check_*): nessuna
    --   scrittura, nessun raise di dominio.
    --   Consumatori: il guard che rifiuta l'UPDATE, e la
    --   maschera del registro, che tiene i tre campi in sola
    --   lettura e dice PERCHE'.
    --
    -- Ritorna: [] se la forma si puo' cambiare; altrimenti array
    --   ORDINATO di {codice, reason, reason_key, dettaglio,
    --   valori} (§12.5.1). Oggi il motivo e' UNO SOLO.
    --
    -- ⭐ IL PREDICATO E' «HA CONSEGNATO UN NUMERO», non «ha una
    --   riga di contatore»: vendite.fn_get_next_progressivo
    --   inserisce la riga a last_numero = 0 e NELLA STESSA
    --   CHIAMATA la porta a >= 1, quindi una riga ferma a 0
    --   significa che da quel bucket non e' mai uscito niente.
    --   ⚠️ E' di proposito piu' stretto del predicato della
    --   disattivazione (HA_PROGRESSIVI), che guarda `attivo` a
    --   prescindere dal contatore: la' si protegge il contatore
    --   in quanto tale, qui il danno comincia col primo numero.
    --
    -- ⛔ serie_default NON e' qui: entra nella chiave del
    --   contatore, quindi cambiarla apre una serie nuova che
    --   distingue i documenti — ed e' il modo legittimo di
    --   aprirne una. Vedi l'intestazione del changeSet.
    --
    -- ⚠️ SECURITY INVOKER: si leggono solo
    --   vendite.registri_fatturazione e
    --   vendite.registri_fatturazione_progressivi, e nessuna
    --   delle due ha la RLS (verificato 2026-09-01). Un DEFINER
    --   sarebbe un privilegio senza un caso che lo chieda.
    -- =========================================================

    -- Guard di parametro: un id assente o non positivo non esce
    -- da nessuna interfaccia, lo produce un chiamante rotto.
    IF p_registro_id IS NULL OR p_registro_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'script', 'fn_check_registro_forma_modificabile',
            'E_VENDITE_CHIAMATA_NON_VALIDA',
            jsonb_build_object('parametro', 'p_registro_id',
                               'valore', p_registro_id),
            NULL::uuid,
            'script.fn_check_registro_forma_modificabile',
            'identificativo del registro non valido');
    END IF;

    SELECT r.codice INTO v_codice
      FROM vendite.registri_fatturazione r
     WHERE r.id = p_registro_id;

    -- ⚠️ Qui «non esiste» e' davvero «non esiste»: nessuna delle
    --   due tabelle ha la RLS, quindi non c'e' il caso «non lo
    --   vedo».
    -- ⭐ E non si risponde []: sarebbe «la forma si puo'
    --   cambiare», che su una riga inesistente e' una frase
    --   senza senso. Stesso ramo della gemella
    --   script.fn_check_registro_disattivabile.
    IF NOT FOUND THEN
        PERFORM script.fn_log_and_raise_error(
            'script', 'fn_check_registro_forma_modificabile',
            'E_VENDITE_CHIAMATA_NON_VALIDA',
            jsonb_build_object('registro_id', p_registro_id),
            NULL::uuid,
            'script.fn_check_registro_forma_modificabile',
            concat('registro ', p_registro_id, ' inesistente'));
    END IF;

    -- ---- MOTIVO 1 — ha gia' consegnato un numero -------------
    -- ⚠️ `last_numero > 0` e non `attivo`: un contatore spento
    --   che ha gia' numerato ha comunque prodotto documenti con
    --   la forma di adesso, e quelli non si disfano.
    SELECT count(*), max(p.last_numero)
      INTO v_contatori, v_ultimo
      FROM vendite.registri_fatturazione_progressivi p
     WHERE p.registro_id = p_registro_id
       AND p.last_numero > 0;

    IF v_contatori > 0 THEN
        v_motivi := v_motivi || jsonb_build_object(
            'codice',     'E_REGISTRO_FORMA_NUMERO_IMMUTABILE',
            'reason',     'HA_NUMERATO',
            'reason_key', 'amministrazione.registri_fatturazione.forma_blocco.ha_numerato',
            'dettaglio',  jsonb_build_object('registro_id',   p_registro_id,
                                             'codice',        v_codice,
                                             'contatori',     v_contatori,
                                             'ultimo_numero', v_ultimo),
            -- ⭐ I due valori riempiono i due %s del messaggio a
            --   catalogo, nell'ordine: il codice del sezionale e
            --   l'ultimo numero consegnato. ⛔ Nessun nome di
            --   parametro o di colonna: qui dentro va cio' che
            --   una PERSONA legge.
            'valori',     jsonb_build_array(v_codice, v_ultimo::text));
    END IF;

    RETURN v_motivi;
END;
$function$

COMMENT ON FUNCTION script.fn_check_registro_forma_modificabile(p_registro_id bigint)
IS 'Pure check (§12.5.1): i motivi che impediscono di CAMBIARE LA FORMA DEL NUMERO di un registro — prefisso, suffisso, lunghezza_numero. Ritorna [] se la modifica e'' ammessa, altrimenti array ORDINATO di {codice, reason, reason_key, dettaglio, valori}. NOMINA il codice e non solleva (salvo i due guard di chiamata). Consumatori: vendite.trgfn_registri_fatturazione_guard_forma_numero, che la CHIAMA per rifiutare (§12.5.2), e la maschera del registro, che tiene i tre campi in sola lettura e dice perche''. ⭐ IL PREDICATO E'' «HA CONSEGNATO UN NUMERO», non «ha una riga di contatore»: vendite.fn_get_next_progressivo inserisce la riga a last_numero = 0 e nella stessa chiamata la porta a >= 1, quindi una riga ferma a 0 significa che da quel bucket non e'' mai uscito niente. ⚠️ E'' di proposito PIU'' STRETTO del predicato della disattivazione (script.fn_check_registro_disattivabile, motivo HA_PROGRESSIVI), che guarda `attivo` a prescindere dal contatore: la'' si protegge il contatore in quanto tale, qui il danno comincia col PRIMO numero consegnato — due divieti imparentati, non lo stesso divieto. ⛔ PERCHE'' IL DIVIETO ESISTE: cambiare la forma non fa ripartire il contatore, lo lascia proseguire — quindi sullo stesso sezionale convivono due forme con numeri consecutivi, e nessun vincolo se ne accorge perche'' la coppia (forma, numero) non e'' vincolata da nessuna parte. E'' la stessa specie di difetto riparato dal cantiere del prefisso il 2026-08-31 (difetto A: forma identica, contatore ripartito da 1) presa dal verso opposto. ⛔ serie_default NON E'' COPERTA, e per due ragioni indipendenti: entra nella chiave del contatore (uq_regprog_key), quindi cambiarla apre un bucket nuovo sotto una serie che distingue i documenti — che e'' il modo legittimo di aprire una serie — e il mirror CSV 80_data/sql/vendite/registri_fatturazione.csv (runOnChange, validCheckSums ANY) la riscrive a OGNI migrate: un BEFORE UPDATE OF serie_default scatta anche a valore invariato e farebbe fallire il migrate. ⚠️ RESIDUO DICHIARATO: il COMMENT della tabella dice che cambiare serie_default su un registro vivo «sposta il sezionale» — resta vero e resta senza presidio, ed e'' un''altra decisione. ⚠️ SECURITY INVOKER ed e'' motivato: si leggono solo vendite.registri_fatturazione e vendite.registri_fatturazione_progressivi, nessuna delle due con RLS (verificato 2026-09-01) — la gemella e'' DEFINER perche'' legge vendite.fatture, che ce l''ha. ⚠️ Registro inesistente: si SOLLEVA E_VENDITE_CHIAMATA_NON_VALIDA invece di rispondere [], perche'' «la forma si puo'' cambiare» su una riga che non esiste e'' una frase senza senso. ⛔ Il `reason` non porta il prefisso E_, riservato ai codici a catalogo (§12.5.1). ⚠️ La reason_key amministrazione.registri_fatturazione.forma_blocco.ha_numerato e'' un DEBITO VERSO IL FE (§12.3): va nei locales it/en nello stesso giro del lavoro frontend. Piano: brief-be-fe-crud-registri-di-numerazione, sezione 8 (D-2).';
```

</div>

---
{% include-markdown "signature-core.md" %}
