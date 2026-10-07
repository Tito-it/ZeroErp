## 📘 Documentazione Concettuale – Trigger Function `anagrafiche.trgfn_risorse_umane_guard_ultimo_super_admin`

> 👀 **Vedi anche**
>
> [script.fn_check_almeno_un_super_admin_attivo](/dbzero/script/funzioni/fn_check_almeno_un_super_admin_attivo) ·
> [script.fn_identita_super_admin_senza_scadenza](/dbzero/script/funzioni/fn_identita_super_admin_senza_scadenza) ·
> [anagrafiche.trgfn_identita_digitali_guard_ultimo_super_admin](/dbzero/anagrafiche/funzioni/trgfn_identita_digitali_guard_ultimo_super_admin) (il gemello sulla veste)
>
> Guida: [Risorse umane e accessi](/guide/risorse-umane-e-accessi)

---
### 🎯 Scopo Principale
(nata il 07-10-2026, `20_code/anagrafiche/20261007-20`; brief `brief-db-veste-utilizzabile`,
decisione di Tid)

**Il rapporto di lavoro dell'ultimo amministratore che non scade non si chiude.**
Dal 07-10-2026 un operatore entra solo finché vale anche il suo rapporto, e la data
«Valido al» del dettaglio operatore è proprio quella del rapporto. Una data di fine
sul rapporto toglie quindi la garanzia quanto una sulla veste, e il sistema deve
avere sempre almeno un SUPER_ADMIN senza scadenza.

Trigger: `trg_risorse_umane_a10_guard_ultimo_super_admin_upd`, `AFTER UPDATE` su
`anagrafiche.risorse_umane`, fase `_a10_`, con `WHEN` sul cambio di `attivo`,
`valido_dal`, `valido_al` o `soggetto_ruolo_id`.

### Quando scatta

1. Solo le scritture che **riducono** la garanzia: spegnere il rapporto, dargli una
   data di fine, spostarne l'inizio nel futuro, spostarlo su un altro soggetto_ruolo
   (la veste dell'amministratore resterebbe senza rapporto). Togliere una data di
   fine o riaprire il rapporto (il reinvio dell'invito) passano sempre.
2. Solo se sul soggetto_ruolo del rapporto c'è una veste OPERATORE con un binding
   SUPER_ADMIN attivo.
3. Poi chiede a
   [fn_check_almeno_un_super_admin_attivo](/dbzero/script/funzioni/fn_check_almeno_un_super_admin_attivo),
   **dopo** la scrittura: se non resta nessun SUPER_ADMIN senza scadenza, rifiuta con
   `E_PROFILO_ULTIMO_SUPER_ADMIN`.

Lo spegnimento del rapporto lo ferma già prima
[trgfn_risorse_umane_guard_identita_attiva](/dbzero/anagrafiche/funzioni/trgfn_risorse_umane_guard_identita_attiva),
se la veste operatore è accesa («figli prima, padre poi»). Qui resta perché non costa
niente e copre il caso in cui quel guard non parla.

### Codice errore

`E_PROFILO_ULTIMO_SUPER_ADMIN` (id 384). Contesto jsonb: `op`, `risorsa_umana_id`,
`identita_digitale_id`, `attivo`, `valido_dal`, `valido_al` della riga nuova.

### Test

`db/pgtap/anagrafiche/test-super-admin-senza-scadenza-v1.sql` (casi 8, 9, 13).

---

{% include-markdown "signature-core.md" %}
