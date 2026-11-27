## 📘 Documentazione Concettuale – Funzione `config.fn_lega_profilo_identita()`

> **Ultimo aggiornamento**: 26 novembre 2026
>
> 👀 **Vedi anche**
>
> * [config.fn_applica_lega_profilo_identita](/dbzero/config/manual/fn_applica_lega_profilo_identita) — la primitiva che scrive il legame
> * [config.fn_lega_profilo_reparto](/dbzero/config/manual/fn_lega_profilo_reparto) — le gemelle: il reparto e lo slegare
> * [config.profili_accesso_bindings](/dbzero/config/manual/profili_accesso_bindings) — i legami
> * [Architettura permessi e autorizzazioni](/guide/architettura-permessi-e-autorizzazioni) — §4.5 chi scrive profili e legami

### 🎯 Scopo

**Il verbo con cui il SUPER_ADMIN lega un'identità a un profilo di accesso.** Un'identità ha un profilo
solo: legarla di nuovo allo stesso profilo non cambia niente; legarla a un profilo diverso, mentre ne ha già
uno, è rifiutato dal vincolo della tabella, non sostituito in silenzio.

È la strada dell'endpoint di amministrazione degli operatori (il SUPER_ADMIN dato o tolto a una persona).

### ⛔ Il permesso

È `SECURITY DEFINER` col `search_path` fissato, e nella prima riga chiede il SUPER_ADMIN all'utente di sessione
(`script.fn_guard_super_admin`): un altro operatore, o nessun utente, riceve `E_PERMESSO_NEGATO`. È lo stesso
controllo dell'endpoint, quindi chi arriva dal backend non riceve un rifiuto nuovo.

Il legame lo scrive la primitiva
[fn_applica_lega_profilo_identita](/dbzero/config/manual/fn_applica_lega_profilo_identita), che l'applicazione
non esegue. La chiamano direttamente anche le funzioni che creano un'identità senza un SUPER_ADMIN in sessione
(la risorsa umana, l'utente tecnico, il provisioning di sviluppo). La tabella dei legami è in sola lettura per
l'applicazione.

---

### Test

`db/pgtap/config/test-fn-scrivi-profilo-accesso-v1.sql`, `db/pgtap/config/test-porta-tabelle-accesso-v1.sql`.

---

{% include-markdown "signature-core.md" %}
