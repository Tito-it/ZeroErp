{% include-markdown "it/dbzero/dbops/manual/vw_operatori_senza_emittente.md" %}
# 🔍 View `vw_operatori_senza_emittente`

> 📝 **Descrizione**
>
> Diagnostica degli operatori configurati a META': identita' OPERATORE attiva, NON super admin, e nessuna riga in config.user_emittenti_fiscali. Col perimetro fail-closed queste persone non vedono NULLA, e il difetto non si annuncia: nessun errore, solo schermate vuote. DEVE restare a zero righe: una riga qui e' qualcuno che apre l'applicazione e non trova niente. Il super admin e' escluso di proposito (il suo perimetro passa da fn_is_super_admin). Per assegnare l'emittente mancante si usa la funzione di dominio script.fn_change_user_emittenti_scope(auth_user_id, ARRAY[ef_id]), non un INSERT a mano.

> 🔐 **Sicurezza**: definer (default delle viste) — le tabelle sotto si leggono con i privilegi dell'owner `zeroerp_owner`, e la RLS che vale e' la sua, non quella di chi interroga.

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE VIEW dbops.vw_operatori_senza_emittente AS
SELECT DISTINCT idg.auth_user_id,
    sr.id AS soggetto_ruolo_id,
    s.id AS soggetto_id,
    s.ragione_sociale_completa AS operatore,
    idg.attivo AS identita_attiva
   FROM ((anagrafiche.identita_digitali idg
     JOIN anagrafiche.soggetti_ruoli sr ON ((sr.id = idg.soggetto_ruolo_id)))
     JOIN anagrafiche.soggetti s ON ((s.id = sr.soggetto_id)))
  WHERE ((idg.ruolo_applicativo = 'OPERATORE'::config.ruolo_applicativo) AND idg.attivo AND (NOT script.fn_is_super_admin(idg.auth_user_id)) AND (NOT (EXISTS ( SELECT 1
           FROM config.user_emittenti_fiscali uef
          WHERE (uef.auth_user_id = idg.auth_user_id)))));
```

</div>


---
{% include-markdown "signature-core.md" %}
