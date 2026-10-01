## 📘 Documentazione Concettuale – Funzione trigger `config.trgfn_credenziali_guard_ultimo_super_admin()`

> 👀 **Vedi anche**
>
> **La regola:** [script.fn_check_almeno_un_super_admin_attivo](/dbzero/script/funzioni/fn_check_almeno_un_super_admin_attivo)
>
> **I gemelli:** [anagrafiche.trgfn_identita_digitali_guard_ultimo_super_admin](/dbzero/anagrafiche/funzioni/trgfn_identita_digitali_guard_ultimo_super_admin) · [config.trgfn_profili_accesso_bindings_guard_ultimo_super_admin](/dbzero/config/funzioni/trgfn_profili_accesso_bindings_guard_ultimo_super_admin)

---

### 🎯 Scopo Principale
(scritta il 25-09-2026)

Impedisce che il **blocco dell'amministratore** lasci il sistema senza nessun
SUPER_ADMIN in grado di entrare. È la terza porta della stessa regola: le altre
due sono la disattivazione di un'identità e quella di un binding.

Scatta solo quando una credenziale passa da «non bloccata» a «bloccata», e solo
se quella credenziale portava un SUPER_ADMIN attivo. Allora chiede alla regola —
`fn_check_almeno_un_super_admin_attivo`, che dal 2026-09-25 considera non
raggiungibile un SUPER_ADMIN bloccato — e, se non resta nessuno, rifiuta con
`E_PROFILO_ULTIMO_SUPER_ADMIN`: la stessa frase dei gemelli.

---

### Storia

* 2026-09-25 — nasce (`20260925-18`).

{% include-markdown "signature-core.md" %}
