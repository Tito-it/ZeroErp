## Documentazione Concettuale – Funzione `script.fn_check_almeno_un_super_admin_attivo`

> **Vedi anche**
>
[Architettura Multi-Face Auth](/guide/architettura-multi-face-auth)
>
**Tabelle correlate:**
>
[config.profili_accesso](/dbzero/config/tabelle/profili_accesso)
> [config.profili_accesso_bindings](/dbzero/config/tabelle/profili_accesso_bindings)
> [anagrafiche.identita_digitali](/dbzero/anagrafiche/tabelle/identita_digitali)
>
**Trigger guard che la consumano:**
>
[config.trgfn_profili_accesso_bindings_guard_ultimo_super_admin](/dbzero/config/funzioni/trgfn_profili_accesso_bindings_guard_ultimo_super_admin)
> [anagrafiche.trgfn_identita_digitali_guard_ultimo_super_admin](/dbzero/anagrafiche/funzioni/trgfn_identita_digitali_guard_ultimo_super_admin)

---
### 🎯 Scopo Principale
(latest review 19-04-2026)

Helper puro di check (non solleva mai errori): ritorna `true` se nel
sistema esiste almeno **un'identità utilizzabile oggi** con **un binding attivo**
verso un `profili_accesso` di tipo `SUPER_ADMIN`, su una credenziale non bloccata.

È la fonte di verità unica della condizione "il sistema ha un
amministratore raggiungibile" per:

1. `config.trgfn_profili_accesso_bindings_guard_ultimo_super_admin` (su
   UPDATE/DELETE di `profili_accesso_bindings`);
2. `anagrafiche.trgfn_identita_digitali_guard_ultimo_super_admin` (su
   UPDATE `attivo` di `identita_digitali`).

Entrambi i trigger chiamano questa funzione post-transizione: se
ritorna `false`, l'operazione viene abortita con
`E_PROFILO_ULTIMO_SUPER_ADMIN`.

---

### Input / Output

Nessun parametro. Ritorna `BOOLEAN`.

| Stato rilevato | Risultato |
|---|---|
| Esiste un'identità utilizzabile oggi con binding attivo verso un profilo `SUPER_ADMIN` attivo, su una credenziale non bloccata | `true` |
| Nessuna combinazione valida (sistema in lockout) | `false` |

---

### Condizione: almeno un SUPER_ADMIN **senza scadenza**

Dal 07-10-2026 (brief `brief-db-veste-utilizzabile`, decisione di Tid) la condizione è
**«esiste almeno un SUPER_ADMIN che non scade»**, letta da
[fn_identita_super_admin_senza_scadenza](/dbzero/script/funzioni/fn_identita_super_admin_senza_scadenza):
binding e profilo `SUPER_ADMIN` attivi, identità utilizzabile oggi, **nessuna data di
fine** né sulla veste né sul rapporto, credenziale non bloccata.

Perché non basta «attivo»: i trigger che la chiamano scattano su una **scrittura**, e
una data che passa non scrive niente. Se tutti gli amministratori avessero una data di
fine, il calendario lascerebbe il sistema senza, e nessun guard lo vedrebbe. La garanzia
si chiede quindi sulla scrittura che **mette** la data: i guard su veste
([trgfn_identita_digitali_guard_ultimo_super_admin](/dbzero/anagrafiche/funzioni/trgfn_identita_digitali_guard_ultimo_super_admin))
e rapporto
([trgfn_risorse_umane_guard_ultimo_super_admin](/dbzero/anagrafiche/funzioni/trgfn_risorse_umane_guard_ultimo_super_admin))
la fermano finché non resta un altro amministratore che non scade.

*(Storia: fino al 07-10-2026 bastava `identita_digitali.attivo`, e un amministratore
già scaduto contava come raggiungibile; dal 25-09-2026 c'era anche il blocco della
credenziale.)*

Il binding deve essere di tipo **AD_HOC** (col `identita_digitale_id`
valorizzata): le altre forme (REPARTO/PORTALE) non portano SUPER_ADMIN
per convenzione (il profilo SUPER_ADMIN ha `tipo = 'SUPER_ADMIN'` che
è compatibile solo con binding AD_HOC — vedi guard di coerenza).

---

### Regole implementative

* `LANGUAGE sql STABLE` — read-only (non inlineabile: contiene `EXISTS`).
* Single `EXISTS` short-circuit: appena trovato un admin valido ritorna
  `true` senza scansionare oltre.
* Nessun parametro: lo stato è globale, non "per utente".
* **Non solleva errori** — la raise è responsabilità dei trigger caller.

---

### Riferimenti

* [WIP multi-face-auth §13.3.6](/dev/work-done/sviluppo-multi-face-auth)
* Codice errore `E_PROFILO_ULTIMO_SUPER_ADMIN` (id 384) in
  `config.messaggi_errore`.

---

{% include-markdown "signature-core.md" %}
