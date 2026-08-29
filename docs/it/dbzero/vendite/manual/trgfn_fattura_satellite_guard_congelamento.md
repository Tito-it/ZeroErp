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
> • ~~`vendite.trgfn_fatture_righe_guard_congelamento` — l'originale da cui è clonata~~
>   → ⛔ **non esiste più dal 2026-08-30**: è stata **riassorbita qui** (`D34`).
>   Era la stessa funzione scritta due giorni prima, senza il parametro.

---
### 🎯 Scopo Principale
(latest review 02-08-2026)

Impedisce di modificare i **satelliti** di una fattura dopo che il documento è
**congelato**: da lì non si fa più `INSERT`, `UPDATE` né `DELETE`.

È **una sola funzione parametrica**, montata su più tabelle, non una copia per
tabella. ⭐ **E dal 2026-08-30 lo è davvero**: prima le righe di fattura avevano
una funzione tutta loro, identica a questa tranne in due punti. Ora sono qui
dentro anche loro (`D34`).

> ⚠️ **La soglia non è più `DRAFT`/`EMESSA` scritta qui dentro** (rev 2026-08-30,
> `D33`). Si legge da `config.stati_doc_fiscale.congela_fiscale`, che è **la**
> sede della domanda «da che punto in poi il documento non si tocca». Il
> comportamento non è cambiato — sui sei stati esistenti colonna e lista dicevano
> la stessa cosa — è cambiato **quante cose vanno toccate** il giorno che il
> confine si sposta.
>
> ⭐ E il confine è **`DEFINITIVA`**, non `EMESSA`: da `EMESSA` si torna in bozza,
> `EMESSA → DRAFT` è una transizione ammessa.

---

### Come si monta

`TG_ARGV[0]` = nome della **colonna FK** che porta alla fattura.
`TG_ARGV[1]` = **codice errore** da sollevare, **opzionale**. Montaggi vivi:

| Tabella | `TG_ARGV[0]` | `TG_ARGV[1]` | Note |
|---|---|---|---|
| `vendite.fatture_scadenze` | `fattura_id` | — | `BEFORE ROW ins/upd/dlt` |
| `vendite.fatture_indirizzi` | `fattura_id` | — | idem |
| `vendite.fatture` | `id` | — | con `UPDATE OF emittente_snapshot, cliente_snapshot` |
| `vendite.fatture_righe` | `fattura_id` | `E_FATTURA_RIGA_CONGELATA` | ⭐ dal 2026-08-30 |

⚠️ Omettere il secondo argomento **non è un errore**: `TG_ARGV` fuori range dà
`NULL`, e il codice ricade sul valore di sempre. È per questo che i tre montaggi
preesistenti non sono stati toccati.

---

### ⛔ ~~Un argomento solo, e un codice errore solo~~ — **decisione RIBALTATA il 2026-08-30**

> ~~Il piano prevedeva un secondo `TG_ARGV` col codice errore per tabella. È stato
> scartato: **due argomenti dove ne basta uno sono due posti in cui sbagliare il
> montaggio**, e `error_policies.py` mappa comunque un codice solo.~~

⚠️ **La premessa era vera quando è stata scritta e non lo è più.** Verificato il
2026-08-30: il backend mappa **due** codici, con messaggi **diversi** per
l'operatore —

| Codice | Cosa legge l'operatore |
| --- | --- |
| `E_FATTURA_RIGA_CONGELATA` | «…non consente più di modificare **le righe**.» |
| `E_FATTURA_SATELLITE_CONGELATO` | «…non consente più di modificare **questi dati**.» |

⭐ **Ed è proprio quella premessa a rendere necessario il parametro.** Fondendo la
guardia delle righe qui dentro *senza* il secondo argomento, le righe si
sarebbero prese il codice dei satelliti: il database avrebbe continuato a
rifiutare la scrittura — quindi **niente sarebbe sembrato rotto** — e l'operatore
avrebbe letto il messaggio generico al posto del suo. Un difetto che non fa
rumore.

L'argomento originale («due posti in cui sbagliare il montaggio») resta valido e
si paga volentieri: il secondo argomento è **opzionale**, i montaggi che non lo
usano non sono cambiati, e in cambio è sparita **un'intera funzione duplicata**.

🔒 Che il montaggio sia giusto lo verifica
`db/pgtap/vendite/test-guard-congelamento-fusione-v1.sql`, che guarda **il
messaggio** e non solo lo `SQLSTATE`: i due codici sollevano entrambi `P0001`, e
un test sul solo stato d'errore sarebbe verde anche col codice sbagliato.

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
