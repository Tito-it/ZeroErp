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

---
### 🎯 Scopo Principale
(latest revision 04-05-2026 — modello legacy `profili_reparto_*` dismesso)

La tabella **`config.profili_accesso`** è l'**header di un profilo di accesso**:
raggruppa un set coerente di capability (livelli per area funzionale e flag
per azione di processo) che può essere assegnato a una o più entità di dominio.

E' la sorgente unica di verita' per le capability. Il modello separa
chiaramente i tre concetti (rispetto al precedente legacy
`profili_reparto_aree`, che mescolava header + dettagli + binding legato
solo a un reparto):

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
| `richiede_secondo_fattore` | Chi ha questo profilo deve usare il **secondo fattore** (dal 29-09-2026). Vedi sotto. |

---

### Il profilo privilegiato e il secondo fattore
(29-09-2026)

Alcuni profili danno poteri che vanno protetti più di una password: gestire
utenti e permessi, per esempio. Chi amministra i profili li **segna** con
`richiede_secondo_fattore`, e chi riceve quel profilo deve entrare con il codice
del telefono oltre alla password.

* ⭐ **L'obbligo segue i binding**: chi riceve il profilo ha l'obbligo, chi lo
  perde non l'ha più. Nessun segno da ricordare sulle singole persone.
* ⛔ **Il profilo `SUPER_ADMIN` ha il segno sempre**, e non si può spegnere: lo
  impedisce un vincolo sulla tabella
  (`chk_profili_accesso_super_admin_secondo_fattore`).
* Il segno vale **su tutte le porte**: la persona ha una password sola, e il
  secondo fattore protegge quella, anche quando entra dal portale.
* L'altra ragione per l'obbligo è un segno sulla **credenziale** della singola
  persona ([config.credenziali](/dbzero/config/tabelle/credenziali)). La
  risposta che mette insieme le due è una sola:
  [fn_totp_obbligatorio](/dbzero/script/funzioni/fn_totp_obbligatorio).

Perché un segno e non una regola che deduce il privilegio dalle aree e dai
livelli: **quali poteri contano è una scelta di chi amministra**, non un fatto
del modello, e un elenco di aree scritto in una funzione diventa vecchio alla
prima area nuova (decisione D-T1 di Tid, brief-db-secondo-fattore-totp).

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

### Storia del cutover

Il modello legacy `config.profili_reparto_aree/_azioni` e' stato dismesso
il 2026-05-04 (changeSet `20260505-02-drop-profili-reparto`). I dati pre-cutover
sono stati migrati nel modello nuovo dal backfill non distruttivo
`20260418-42-migrate-profili-reparto-to-profili-accesso` (con codice
profilo `REPARTO_<codice_interno>` per ogni unita organizzativa). Dal
04-05-2026 i 4 resolver (`fn_resolve_livello_area`,
`fn_check_azione_processo`, `fn_get_user_permissions_map`,
`fn_get_user_actions_map`) leggono solo dal modello generalizzato.

---

{% include-markdown "signature-core.md" %}
