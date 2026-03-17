## 📘 Documentazione Concettuale – Tabella `anagrafiche.risorse_umane`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
>
[anagrafiche.soggetti](/dbzero/anagrafiche/tabelle/soggetti)
> [anagrafiche.soggetti_ruoli](/dbzero/anagrafiche/tabelle/soggetti_ruoli)
> [config.qualifiche](/dbzero/config/tabelle/qualifiche)
> [config.unita_organizzative](/dbzero/config/tabelle/unita_organizzative)
> [anagrafiche.risorse_umane_auth_user](/dbzero/anagrafiche/tabelle/risorse_umane_auth_user)
>
Approfondimento funzioni:
>
[anagrafiche.trgfn_risorse_umane_guard_ruolo](/dbzero/anagrafiche/funzioni/trgfn_risorse_umane_guard_ruolo)

---

### 🎯 Scopo Principale


(latest review 06-01-26)
La tabella **`anagrafiche.risorse_umane`** rappresenta le persone (dipendenti, consulenti,
collaboratori) associate a un soggetto tramite un ruolo di tipo **`RISORSA_UMANA`**.
Consente di collegare ogni risorsa a una **qualifica** e, opzionalmente, a una
**unita organizzativa**.

---

### Collegamenti principali

* `soggetto_ruolo_id` → `anagrafiche.soggetti_ruoli(id)`
* `qualifica_id` → `config.qualifiche(id)`
* `unita_organizzativa_id` → `config.unita_organizzative(id)` (opzionale)

---

### Regole

* Il `soggetto_ruolo_id` deve avere `tipo_ruolo` = **RISORSA_UMANA**.
* `soggetto_id` deve corrispondere al soggetto del ruolo indicato.
* `valido_al` non puo essere precedente a `valido_dal`.
* Un solo record per `soggetto_ruolo_id` (unicita).
* L'eventuale collegamento a `django.auth_user` avviene tramite tabella ponte
  `anagrafiche.risorse_umane_auth_user`.

---

### Note operative

* Il campo `meta` consente estensioni future senza alterare lo schema.
* I campi audit sono standardizzati come nel resto dell'anagrafica.

---

{% include-markdown "signature-core.md" %}
