## 📘 Documentazione Concettuale – Funzione `script.fn_guard_super_admin()`

> 👀 **Vedi anche**
>
> **La regola che applica:** [script.fn_is_super_admin](/dbzero/script/funzioni/fn_is_super_admin) — la stessa del backend
>
> **Il gemello per le azioni di processo:** [script.fn_guard_azione](/dbzero/script/funzioni/fn_guard_azione)
>
> **Chi la chiama:** [fn_blocca_credenziale](/dbzero/script/funzioni/fn_blocca_credenziale) · [fn_sblocca_credenziale](/dbzero/script/funzioni/fn_sblocca_credenziale)

---

### 🎯 Scopo Principale
(scritta il 25-09-2026)

È il guard con cui un verbo di scrittura chiede che **chi agisce sia un
SUPER_ADMIN**. Si chiama nella prima riga del verbo: se la risposta è no, il verbo
si ferma prima di toccare qualunque cosa.

Serve dove un'operazione appartiene all'**amministrazione del software** e non a
un'area funzionale: `amm_software` non è un'area del catalogo, è una porta del
backend riservata ai SUPER_ADMIN. Un'azione di processo non avrebbe un'area a cui
appartenere; il verbo chiede la stessa regola della porta.

---

### Cosa risponde

| Situazione | Esito |
| --- | --- |
| chi agisce è SUPER_ADMIN, in veste OPERATORE | niente: il verbo prosegue |
| chi agisce non è SUPER_ADMIN | `E_PERMESSO_NEGATO`, lo stesso codice e la stessa frase del backend |
| è SUPER_ADMIN ma entra da un'altra porta (portale, shop) | `E_PERMESSO_NEGATO`: il controllo di contesto è di `fn_is_super_admin` |
| nessun utente in sessione | `E_PERMESSO_NEGATO`, con `senza_utente = true` nel contesto |

L'utente arriva come parametro; il verbo lo legge dalla sessione:

```sql
PERFORM script.fn_guard_super_admin(
    NULLIF(current_setting('app.current_user_id', true), '')::integer);
```

---

### Storia

* 2026-09-25 — nasce con i due verbi di blocco della credenziale (`20260925-06`):
  la seconda occorrenza dello stesso controllo, quindi un building block.

{% include-markdown "signature-core.md" %}
