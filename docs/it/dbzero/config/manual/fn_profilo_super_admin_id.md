## 📘 Documentazione Concettuale – Funzione `config.fn_profilo_super_admin_id()`

> 👀 **Vedi anche**
>
> [config.profili_accesso](/dbzero/config/manual/profili_accesso)
> [config.fn_lega_profilo_identita](/dbzero/config/manual/fn_lega_profilo_identita) — chi scrive il legame
> [anagrafiche.fn_crea_risorsa_umana_v2](/dbzero/anagrafiche/manual/fn_crea_risorsa_umana_v2) — il primo lettore

---

### 🎯 Scopo Principale

(18-10-2026 — R-BE-11 del backend, regola del 2, ok di Tid;
`brief-db-processi-accensione-per-ambiente` §6.15)

**Quale profilo di accesso si lega a un operatore super admin.** Restituisce l'id dell'unico
profilo **attivo** di tipo `SUPER_ADMIN`.

| Caso | Esito |
| --- | --- |
| un solo profilo SUPER_ADMIN attivo | il suo id |
| nessuno, o più di uno | `E_CONFIG_MANCANTE`, con il numero dei profili trovati |

---

### Perché così

* **la chiave è il tipo**, non il codice né l'id: il codice si può cambiare e l'id del seed
  (9100) è vero solo finché il file di seed lo porta. Il tipo è la stessa chiave che usano i
  controlli «non togliere l'ultimo super admin»;
* **un profilo spento non si lega**;
* **due profili attivi non si scelgono per id**: il modello non vieta di averne due, e prenderne
  «il primo» sarebbe una scelta fatta a caso. Il sistema si ferma e lo dice.

---

### Chi la usa

* `anagrafiche.fn_crea_risorsa_umana_v2`, quando crea un operatore super admin;
* il backend, quando un operatore diventa super admin dalla maschera degli operatori.

⭐ Prima di questa funzione la stessa regola era scritta in quei due posti, ciascuno con la sua
query (regola del 2): una correzione fatta in uno solo li avrebbe fatti rispondere in due modi
diversi.

---

### Test

`db/pgtap/config/test-fn-profilo-super-admin-id-v1.sql`

---

{% include-markdown "signature-core.md" %}
