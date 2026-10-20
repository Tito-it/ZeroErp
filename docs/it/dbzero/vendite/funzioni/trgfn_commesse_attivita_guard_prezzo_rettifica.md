{% include-markdown "it/dbzero/vendite/manual/trgfn_commesse_attivita_guard_prezzo_rettifica.md" %}
# ⚙️ Funzione `trgfn_commesse_attivita_guard_prezzo_rettifica`

```sql
CREATE FUNCTION trgfn_commesse_attivita_guard_prezzo_rettifica()
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_commesse_attivita_guard_prezzo_rettifica()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
BEGIN
    -- =========================================================
    -- Scopo:
    --   Il prezzo di una riga RETTIFICA e' una CITAZIONE della
    --   riga di fattura che rettifica (fn_accredita_riga_reso,
    --   N-1: copiato, mai ricalcolato). Cambiarlo farebbe
    --   accreditare un importo diverso da quello fatturato, cioe'
    --   una nota di credito che non corrisponde al documento che
    --   dichiara di correggere.
    -- Regole:
    --   - blocca il CAMBIO di prezzo_snapshot o prezzo_bloccato
    --     sulle righe tipo_movimento = 'RETTIFICA';
    --   - in QUALUNQUE stato: la citazione e' sbagliata anche
    --     prima dell'emissione — anzi soprattutto prima, perche'
    --     e' li' che i tre percorsi di pricing la toccherebbero;
    --   - `IS DISTINCT FROM`: una riscrittura dello STESSO valore
    --     passa, cosi' l'ON CONFLICT DO UPDATE dell'upsert non si
    --     rompe.
    -- ⚠️ Nessun bypass di manutenzione, a differenza del gemello
    --   sulla quantita': verificato che il reset lotto scrive su
    --   questa tabella solo `stato_emissione`, quindi non
    --   incontra questo guard. Una porta di servizio sul prezzo di
    --   una nota di credito dev'essere una decisione, mai
    --   un'eredita'.
    -- Decisione di Tid, 2026-08-20. brief nota di credito §42.2.
    -- =========================================================
    IF OLD.tipo_movimento = 'RETTIFICA'
       AND (NEW.prezzo_snapshot IS DISTINCT FROM OLD.prezzo_snapshot
            OR NEW.prezzo_bloccato IS DISTINCT FROM OLD.prezzo_bloccato) THEN
        PERFORM script.fn_log_and_raise_error(
            'database', TG_NAME, 'E_COMMESSA_ATTIVITA_PREZZO_RETTIFICA_IMMUTABILE',
            jsonb_build_object(
                'id', OLD.id,
                'segment_key', OLD.segment_key,
                'stato_emissione', OLD.stato_emissione,
                'prezzo_old', OLD.prezzo_snapshot,
                'prezzo_new', NEW.prezzo_snapshot,
                'bloccato_old', OLD.prezzo_bloccato,
                'bloccato_new', NEW.prezzo_bloccato),
            NULL::uuid, OLD.id::text, OLD.segment_key
        );
    END IF;

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION vendite.trgfn_commesse_attivita_guard_prezzo_rettifica()
IS 'Guard immutabilita PREZZO delle righe RETTIFICA di vendite.commesse_attivita: blocca il CAMBIO di prezzo_snapshot o prezzo_bloccato, in qualunque stato. Il prezzo di una rettifica non e'' un dato da tenere aggiornato, e'' una CITAZIONE della riga di fattura che rettifica (fn_accredita_riga_reso, N-1: copiato da vendite.fatture_righe, mai ricalcolato e mai riletto dal listino): cambiarlo accrediterebbe un importo diverso da quello fatturato, cioe'' una nota di credito che non corrisponde al documento che dichiara di correggere. ⚠️ STA NEL DATABASE E NON NEL BACKEND perche'' il prezzo si scrive con una UPDATE DIRETTA (update_attivita_prezzo nel repository), non da una funzione madre: un controllo applicativo sarebbe una convenzione e non un blocco, e chiunque scrivesse quella colonna per un''altra strada lo aggirerebbe senza accorgersene — stessa ragione per cui tipo_movimento e'' una colonna con CHECK e non una chiave di meta. ⭐ Blocca il CAMBIAMENTO e non la scrittura (IS DISTINCT FROM): una UPDATE che riscrive lo stesso valore passa, cosi'' l''ON CONFLICT DO UPDATE di fn_upsert_commessa_attivita non si rompe. ⚠️ NON dipende da stato_emissione, a differenza del gemello sulla quantita'': quello protegge un fatto gia'' uscito, questo una citazione — che e'' sbagliata anche prima di uscire, anzi soprattutto prima, perche'' e'' li'' che i tre percorsi di pricing (riallinea, variazione eccezionale, sblocca) la toccherebbero. ⛔ Nessun bypass di manutenzione: verificato che il reset lotto (fn_cleanup_fatture_by_ids) scrive su questa tabella solo stato_emissione. prezzo_da_riallineare NON e'' fra le colonne guardate — misurato che nessun percorso lo porta a true su una rettifica. Errore E_COMMESSA_ATTIVITA_PREZZO_RETTIFICA_IMMUTABILE (936). Decisione di Tid 2026-08-20, brief-design-note-credito-resi §42.2.';
```

</div>

---
{% include-markdown "signature-core.md" %}
