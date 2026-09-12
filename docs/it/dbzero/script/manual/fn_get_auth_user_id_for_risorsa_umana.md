## 📘 Documentazione Concettuale – Funzione `script.fn_get_auth_user_id_for_risorsa_umana`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
[anagrafiche.identita_digitali](/dbzero/anagrafiche/tabelle/identita_digitali)
> [anagrafiche.risorse_umane](/dbzero/anagrafiche/tabelle/risorse_umane)
>
**Approfondimento funzioni:**
>
[script.fn_get_uo_id_for_user](/dbzero/script/funzioni/fn_get_uo_id_for_user) — la gemella nel verso opposto (utente → risorsa umana → UO)

---
### 🎯 Scopo Principale
(nata il 12-09-2026, `20_code/script/20260912-17`)

Risponde a una domanda sola: **«questa risorsa umana, quale utente Django
ha?»**. Percorre la catena dalla madre — `risorse_umane` → `soggetto_ruolo_id`
→ `identita_digitali` con `ruolo_applicativo = 'OPERATORE'` → `auth_user_id` —
e torna `NULL` se la risorsa non ha un'identità operatore.

⭐ **Perché esiste (regola del 2).** Due funzioni (`fn_notify_cambio_reparto`,
`trgfn_risorse_umane_sync_auth_user_active`) risolvevano l'utente leggendo la
**vista col nome vecchio** `risorse_umane_auth_user`. Quando la vista è stata
ritirata (`90_end/20260912-26`), la stessa catena riscritta due volte sarebbe
stata la regola del 2 violata alla seconda riga: la sede è una.

---

### Parametri e risultato

| Nome | Tipo | Note |
| --- | --- | --- |
| `p_risorsa_umana_id` | `anagrafiche.risorse_umane.id%TYPE` | l'id della risorsa umana; per un id inesistente torna `NULL` (nessun guard: i chiamanti lo fanno prima) |
| *ritorno* | `anagrafiche.identita_digitali.auth_user_id%TYPE` | l'`auth_user_id`, oppure `NULL` |

`LANGUAGE sql`, `STABLE`, `SECURITY INVOKER`: legge come chi la chiama.

---

### ⚠️ Non filtra su `attivo`, ed è voluto

I due chiamanti vogliono l'utente collegato **anche se l'identità è spenta**:
il sync di `is_active` deve poterlo *spegnere*, la notifica di cambio reparto
deve poterlo *nominare*. Se ce n'è più d'una (il modello lo ammette), vince
quella attiva, poi la più recente (`ORDER BY id.attivo DESC, id.id DESC`).
Chi vuole **solo** le identità attive filtra da sé — è ciò che fa il guard
[`trgfn_risorse_umane_guard_identita_attiva`](/dbzero/anagrafiche/funzioni/trgfn_risorse_umane_guard_identita_attiva),
che ha un predicato suo.

---

### Presidio

`db/pgtap/anagrafiche/test-risorse-umane-guard-identita-attiva-v1.sql` (test 2):
la fixture creata dalla madre `fn_crea_operatore_v2` è legata nel verso
RU → utente da questa funzione.

---

{% include-markdown "signature-core.md" %}
