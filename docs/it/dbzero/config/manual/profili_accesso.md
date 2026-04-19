## 📘 Documentazione Concettuale – Tabella `config.profili_accesso`

> 👀 **Vedi anche**
>
Architettura di riferimento:
>
[Architettura Multi-Face Auth](/guide/architettura-multi-face-auth)
> [Architettura Permessi e Autorizzazioni](/guide/architettura-permessi-e-autorizzazioni)
>
Tabelle correlate:
>
[config.profili_accesso_aree](/dbzero/config/tabelle/profili_accesso_aree)
> [config.profili_accesso_azioni](/dbzero/config/tabelle/profili_accesso_azioni)
> [config.profili_accesso_bindings](/dbzero/config/tabelle/profili_accesso_bindings)
> [config.profili_reparto_aree](/dbzero/config/tabelle/profili_reparto_aree) (tabella legacy, in coesistenza)

---
### 🎯 Scopo Principale
(latest revision 18-04-2026)

La tabella **`config.profili_accesso`** è l'**header di un profilo di accesso**:
raggruppa un set coerente di capability (livelli per area funzionale e flag
per azione di processo) che può essere assegnato a una o più entità di dominio.

È il **rimpiazzo generalizzato** di `config.profili_reparto_aree`, che oggi
mescola header + dettagli + binding legato esclusivamente a un reparto.
Il nuovo modello separa i tre concetti:

* **Header** (questa tabella) → classifica e definisce il profilo
* **Dettagli** ([`profili_accesso_aree`](/dbzero/config/tabelle/profili_accesso_aree), [`profili_accesso_azioni`](/dbzero/config/tabelle/profili_accesso_azioni)) → capability
* **Binding** ([`profili_accesso_bindings`](/dbzero/config/tabelle/profili_accesso_bindings)) → chi riceve il profilo

---

### Colonne chiave

| Colonna | Scopo |
|---------|-------|
| `tipo` | `config.tipo_profilo_accesso`: `REPARTO` / `PORTALE` / `AD_HOC`. Vincola il tipo di binding ammesso. |
| `codice` | Identificativo univoco del profilo (es. `REPARTO_AMM`, `CLIENTE_PORTALE_STANDARD`, `AD_HOC_UTENTE_42`). |
| `descrizione` | Descrizione leggibile a UI e documentazione. |
| `attivo` | Soft flag. Se `false`, il profilo non viene applicato nella risoluzione dei permessi. |

---

### Tipologie di profilo

| Tipo | Uso | Binding ammesso |
|------|-----|-----------------|
| `REPARTO` | Profili degli operatori interni, tipicamente legati a un reparto (`unita_organizzativa`). Un profilo per reparto, creato dalla migrazione dati con codice `REPARTO_<codice_interno>`. | `unita_organizzativa_id` |
| `PORTALE` | Preset condivisi per utenti di portale (clienti, fornitori, shop). Un profilo per `ruolo_applicativo`. | `ruolo_applicativo` |
| `AD_HOC` | Profili speciali assegnati a una singola identità digitale. Alternativa agli `user_override_*` quando serve un set organico di capability. | `identita_digitale_id` |

La coerenza `tipo ↔ tipo di binding` è garantita dal guard
[`trgfn_profili_accesso_bindings_guard_coerenza`](/dbzero/config/funzioni/trgfn_profili_accesso_bindings_guard_coerenza).

---

### Profili seed portali

Il seed iniziale (`80_data/changelog/20260418-43-upsert-profili-accesso-portale`)
crea 3 profili `PORTALE` standard:

| Codice | Aree LETTURA | Binding → ruolo_applicativo |
|--------|---------------|-----------------------------|
| `CLIENTE_PORTALE_STANDARD` | vendite, pagamenti | `CLIENTE_PORTALE` |
| `FORNITORE_PORTALE_STANDARD` | acquisti, pagamenti | `FORNITORE_PORTALE` |
| `SHOP_CUSTOMER_STANDARD` | vendite, pagamenti | `SHOP_CUSTOMER` |

Id range dedicato 9001-9003 per evitare collisioni con gli id `REPARTO`
generati dalla migrazione dati.

---

### Relazione con il modello legacy

Fino al cutover di `script.fn_resolve_livello_area` e compagnia (§4.8 del
WIP multi-face-auth), le tabelle legacy `profili_reparto_aree/azioni` **restano
in uso** come sorgente primaria per gli operatori. La migrazione dati
(`80_data/changelog/20260418-42-migrate-profili-reparto-to-profili-accesso`)
replica il contenuto legacy nel nuovo modello in modalità non distruttiva,
permettendo di sviluppare la nuova catena di risoluzione in parallelo e
di fare il cutover con feature flag.

---

{% include-markdown "signature-core.md" %}
