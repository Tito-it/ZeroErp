{% include-markdown "it/dbzero/vendite/manual/trgfn_commesse_default_emittente.md" %}
# ⚙️ Funzione `trgfn_commesse_default_emittente`

```sql
CREATE FUNCTION trgfn_commesse_default_emittente()
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_commesse_default_emittente()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
BEGIN
    -- =========================================================
    -- Scopo:
    --   L'emittente della commessa non e' un attributo che
    --   qualcuno sceglie: e' la sua CHIAVE DI PERIMETRO, e si
    --   deriva dal billing account. Qui la si riempie quando
    --   arriva NULL.
    --
    -- Regole:
    --   - valore gia' dichiarato -> si esce subito (a giudicarlo
    --     ci pensa trgfn_commesse_guard_emittente_ba: qui non si
    --     sovrascrive mai in silenzio una scelta esplicita);
    --   - altrimenti si deriva dal BA con la funzione di casa,
    --     che e' la stessa usata da fn_build_fattura_key per
    --     scegliere il registro: «emittente della commessa» e
    --     «emittente che fattura» sono la stessa affermazione.
    -- =========================================================

    -- 1) Skip se gia' valorizzato esplicitamente nel payload.
    IF NEW.emittente_soggetto_ruolo_id IS NOT NULL THEN
        RETURN NEW;
    END IF;

    -- 2) Derivazione dal billing account.
    --    ⭐ Nessun guard sul NULL a valle: la funzione SOLLEVA
    --    (E_EMITTENTE_DEFAULT_MISSING) invece di tornare NULL —
    --    e' la proprieta' che finora garantiva da sola il valore
    --    su questa colonna.
    --    ⚠️ NEW.billing_account_id e' NOT NULL, quindi non c'e'
    --    nessun ramo «BA assente» da saltare come nei sei
    --    fratelli documento.
    NEW.emittente_soggetto_ruolo_id :=
        anagrafiche.fn_get_emittente_fiscale_id(NEW.billing_account_id);

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION vendite.trgfn_commesse_default_emittente()
IS 'BEFORE INSERT su vendite.commesse: riempie emittente_soggetto_ruolo_id derivandolo dal billing account (anagrafiche.fn_get_emittente_fiscale_id) quando il payload lo lascia NULL. ⭐ Estende di un anello la famiglia gia'' in servizio su ordini, preventivi, contratti, ddt, offerte_commerciali e resi (trgfn_*_default_emittente + trgfn_*_guard_emittente_ba): vendite.commesse era l''unica tabella del ciclo che porta un emittente e non aveva ne'' il riempitore ne'' il guard. ⭐ Con una differenza VOLUTA: nei sei fratelli il default si prende dall''OPERATORE (script.fn_resolve_emittente_for_user sulla GUC app.current_user_id) perche'' sono documenti che una persona crea in un form; la commessa non la crea nessuno a mano — nasce dal push — quindi il suo emittente si prende dal BILLING ACCOUNT. E'' la decisione D-1: sempre derivato, mai passato da fuori. ⛔ Non sovrascrive MAI un valore gia'' presente nel payload: a giudicarlo ci pensa vendite.trgfn_commesse_guard_emittente_ba, e una normalizzazione muta sarebbe la forma in cui un test diventa verde smettendo di verificare. ⭐ Nessun guard sul NULL residuo, e non e'' un''omissione: fn_get_emittente_fiscale_id solleva E_EMITTENTE_DEFAULT_MISSING invece di tornare NULL. ⚠️ Solo BEFORE INSERT: un UPDATE che azzera la colonna lo respinge il NOT NULL, e far seguire il valore a un cambio di billing_account_id sarebbe una propagazione silenziosa su una colonna di perimetro — chi sposta la commessa di cliente deve dichiarare anche l''emittente. ⭐ Effetto collaterale portante: PostgreSQL valuta il WITH CHECK della RLS sulla riga FINALE, cioe'' dopo i trigger BEFORE, quindi da qui in poi rls_commesse_ef_whitelist giudica l''emittente vero invece di un NULL fail-closed. ⚠️ I BEFORE ROW scattano in ordine alfabetico: default_ precede guard_, ed e'' l''unico ordine che funziona. Piano: brief-db-emittente-commessa-invariante, L1.';
```

</div>

---
{% include-markdown "signature-core.md" %}
