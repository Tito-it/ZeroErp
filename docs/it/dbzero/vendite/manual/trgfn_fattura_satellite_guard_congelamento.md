## 📘 Documentazione Concettuale – Trigger function `vendite.trgfn_fattura_satellite_guard_congelamento`

> 👀 **Vedi anche**
>
> **Tabelle sorvegliate:**
>
> • [vendite.fatture_scadenze](/dbzero/vendite/tabelle/fatture_scadenze) · [vendite.fatture_indirizzi](/dbzero/vendite/tabelle/fatture_indirizzi)
> • [vendite.fatture](/dbzero/vendite/tabelle/fatture) — colonne `emittente_snapshot` / `cliente_snapshot`
>
> **Parenti:**
>
> • [vendite.trgfn_fatture_righe_guard_congelamento](/dbzero/vendite/funzioni/trgfn_fatture_righe_guard_congelamento) — l'originale da cui è clonata

---
### 🎯 Scopo Principale
(latest review 02-08-2026)

Impedisce di modificare i **satelliti** di una fattura dopo che il documento ha
superato la soglia fiscale: oltre `DRAFT`/`EMESSA` non si fa più `INSERT`,
`UPDATE` né `DELETE`.

È **una sola funzione parametrica**, montata su più tabelle, non una copia per
tabella.

---

### Come si monta

`TG_ARGV[0]` = nome della **colonna FK** che porta alla fattura. Montaggi vivi:

| Tabella | `TG_ARGV[0]` | Note |
|---|---|---|
| `vendite.fatture_scadenze` | `fattura_id` | `BEFORE ROW ins/upd/dlt` |
| `vendite.fatture_indirizzi` | `fattura_id` | idem |
| `vendite.fatture` | `id` | con `UPDATE OF emittente_snapshot, cliente_snapshot` |

---

### 🔴 Un argomento solo, e un codice errore solo

Il piano prevedeva un secondo `TG_ARGV` col codice errore per tabella. È stato
scartato: **due argomenti dove ne basta uno sono due posti in cui sbagliare il
montaggio**, e `error_policies.py` mappa comunque un codice solo. La tabella
finisce nel messaggio e nel payload, dove serve a chi legge senza moltiplicare la
superficie di configurazione.

Codice unico: **`E_FATTURA_SATELLITE_CONGELATO`**.

---

### ⚠️ L'uscita anticipata su stato NULL non è difensivismo

Se lo stato della fattura è `NULL` il guard **esce senza bloccare**.

Serve alla `DELETE` in **CASCADE** dalla testata: senza quel ramo, una fattura
congelata non sarebbe più cancellabile — il satellite bloccherebbe la
cancellazione del padre, e il reset del lotto morirebbe su un trigger. È
esercitato da un test apposta.

---

### 🚪 Il bypass GUC

Come gli altri guard di dominio, riconosce la GUC di manutenzione del reset lotto.
Il reset **rientra** nella bozza, quindi deve poter riscrivere i satelliti.

⚠️ Da non confondere con il guard di **uscita** da DRAFT, che invece **non ha
bypass**: lì il bypass sarebbe una porta di servizio sull'emissione.

---

### Perché `fatture_riepiloghi_iva` è fuori perimetro

Non è una svista. La sua riscrittura passa da
`fn_ricalcola_riepilogo_iva_fattura`, che la soglia ce l'ha già dentro.

🔴 **Conseguenza da conoscere**: esiste quindi una strada per riscrivere i
riepiloghi lasciando la testata al valore vecchio. È il motivo per cui il guard
di coerenza alla numerazione (D-K) verifica anche che i riepiloghi **quadrino**
con i totali di testata — un controllo che sembrerebbe ridondante e non lo è.

---
{% include-markdown "signature-core.md" %}
