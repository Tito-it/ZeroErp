## 📘 Documentazione Concettuale – Trigger Function `config.trgfn_profili_accesso_bindings_guard_coerenza`

> 👀 **Vedi anche**
>
Architettura di riferimento:
>
[Architettura Multi-Face Auth](/guide/architettura-multi-face-auth)
> [Architettura Permessi e Autorizzazioni](/guide/architettura-permessi-e-autorizzazioni)
>
**Approfondimento tabelle:**
>
[config.profili_accesso_bindings](/dbzero/config/tabelle/profili_accesso_bindings)
> [config.profili_accesso](/dbzero/config/tabelle/profili_accesso)
>
**Approfondimento funzioni:**
>
[script.fn_log_and_raise_error](/dbzero/script/funzioni/fn_log_and_raise_error)

---
### 🎯 Scopo Principale
(latest review 18-04-2026)
La trigger function
**`config.trgfn_profili_accesso_bindings_guard_coerenza()`** verifica che il
**tipo di binding** (colonna valorizzata) sia coerente con il **tipo del
profilo di accesso** a cui il binding fa riferimento.

Trigger BEFORE INSERT OR UPDATE su
[`config.profili_accesso_bindings`](/dbzero/config/tabelle/profili_accesso_bindings),
fase `a10` (guard fail-fast).

---

### Regole applicate

| Tipo profilo | Colonna binding attesa |
|--------------|-----------------------|
| `REPARTO` | `unita_organizzativa_id` |
| `PORTALE` | `ruolo_applicativo` |
| `AD_HOC` | `identita_digitale_id` |

Un profilo `REPARTO` legato a un `ruolo_applicativo` è una configurazione
illogica: il guard la blocca con errore esplicito, anche se il CHECK xor
della tabella ammetterebbe la riga.

---

### Relazione con il CHECK xor

Il trigger **si somma** al CHECK
`chk_profili_accesso_bindings_xor` che garantisce "esattamente una colonna
tra uo/identità/ruolo valorizzata". I due vincoli hanno scopi complementari:

| Livello | Cosa verifica |
|---------|---------------|
| `chk_profili_accesso_bindings_xor` (CHECK) | *Quante* colonne NOT NULL: esattamente una. |
| `trgfn_profili_accesso_bindings_guard_coerenza` (trigger) | *Quale* colonna NOT NULL deve essere: coerente col tipo del profilo. |

---

### Ottimizzazione: `UPDATE OF`

Il trigger è installato con clausola `UPDATE OF` sulle 4 colonne rilevanti
(`profilo_accesso_id`, `unita_organizzativa_id`, `identita_digitale_id`,
`ruolo_applicativo`): **non scatta** se l'UPDATE tocca solo
`attivo`/`meta`/audit. Zero overhead per modifiche di stato.

---

### Errori sollevati

| Codice | Quando |
|--------|--------|
| `E_PARAMETRO_INVALIDO` | Caso limite: `profilo_accesso_id` non trovato (la FK dovrebbe impedirlo, ma fail-fast esplicito). |
| `E_PROFILO_ACCESSO_BINDING_INCOERENTE` | Colonna binding valorizzata non coerente col tipo del profilo. |
| `E_PROFILO_ACCESSO_TIPO_NON_GESTITO` | Ramo `ELSE` del dispatch: nuovo valore dell'enum `tipo_profilo_accesso` senza regola qui (anti-bypass). |

---

### Esempi di configurazioni rifiutate

* Profilo `tipo=REPARTO` con `ruolo_applicativo='CLIENTE_PORTALE'` → errore
  `E_PROFILO_ACCESSO_BINDING_INCOERENTE` (atteso `unita_organizzativa_id`).
* Profilo `tipo=PORTALE` con `unita_organizzativa_id=42` → stesso errore
  (atteso `ruolo_applicativo`).
* Profilo `tipo=AD_HOC` con `ruolo_applicativo='SHOP_CUSTOMER'` → stesso errore
  (atteso `identita_digitale_id`).

---

{% include-markdown "signature-core.md" %}
