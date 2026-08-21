## 📘 Documentazione Concettuale – Tabella `config.ambiti`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
> • [magazzino.ambito_causale](/dbzero/magazzino/tabelle/ambito_causale)
> • [magazzino.causali](/dbzero/magazzino/tabelle/causali)

---
### 🎯 Scopo Principale

(rev 2026-08-21)

⛔ **Tabella orfana: vuota e non referenziata da nulla.**

Doveva essere il vocabolario degli **ambiti**, la dimensione trasversale con cui qualificare
le causali. Quel ruolo è stato però assunto da un'altra tabella, e questa è rimasta indietro.

---

### 🔴 Che cosa dice la misura (2026-08-21)

| Misura | Valore |
| --- | --- |
| Righe | **0** |
| FK entranti | **nessuna** |
| Chi la referenzia | **nessuno** |

Il ruolo che le era destinato lo svolge **`magazzino.ambito_causale`**, che è un vocabolario
**autonomo** — nessuna FK verso qui — e che è **popolato** con sei voci:
`VENDITE`, `ACQUISTI`, `ODL`, `TRASF`, `INVENTARIO`, `GENERICO`.

La FK reale è:

```sql
magazzino.causali.ambito_causale_id  →  magazzino.ambito_causale(id)
```

⚠️ **Non `ambito_id` verso `config.ambiti`**, come il nome delle due tabelle lascerebbe
supporre. Sono due oggetti con nomi vicini e nessun legame: la somiglianza è precisamente ciò
che rende facile sbagliarsi — è successo scrivendo la prima versione di questa pagina, dove
la relazione era stata data per esistente senza verificarla, ed è stata corretta lo stesso
giorno controllando `pg_constraint`.

---

### Che cosa farne

Non è un residuo dimenticato di una migrazione: è una tabella **superata da un'altra** prima
di essere usata. Vuota e senza referenti, il costo di tenerla è nullo e il costo di toglierla
pure — a differenza degli oggetti della fascia H, che la timeline v1 ricrea a ogni
ricostruzione, questa nasce in `migrations_v2` e un `DROP` forward-only la eliminerebbe
davvero.

La decisione utile non è però il `DROP`: è **verificare se il progetto vuole un vocabolario
di ambiti trasversale** (magazzino *e* acquisti *e* vendite) oppure se l'ambito è per sua
natura una proprietà delle sole causali di magazzino. Oggi la risposta di fatto è la seconda,
e `config.ambiti` è la traccia di una prima intenzione diversa.

⚠️ Finché resta, va saputo che **è vuota**: un `JOIN` su di essa non restituisce mai righe, e
chi la trovasse cercando «gli ambiti» starebbe guardando la tabella sbagliata.

---

### La struttura, per memoria

`codice`, `descrizione`, audit, più `extra_country` (`jsonb`) — che prevedeva attributi
specifici per nazione, indizio di un disegno più ambizioso di quello poi realizzato in
`magazzino.ambito_causale`.

⚠️ `descrizione` è di tipo `character` e non `varchar`: un `char(n)` **spazia a destra**, e i
confronti con `=` ne risentono.

---

{% include-markdown "signature-core.md" %}
