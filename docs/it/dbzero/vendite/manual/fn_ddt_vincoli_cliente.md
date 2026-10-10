## 📘 Documentazione Concettuale – Funzione `vendite.fn_ddt_vincoli_cliente()`

> 👀 **Vedi anche**
>
> • [vendite.trgfn_ddt_guard_cliente_sorgente](/dbzero/vendite/funzioni/trgfn_ddt_guard_cliente_sorgente) — il guard che solleva
> • [script.fn_available_actions_ddt](/dbzero/script/funzioni/fn_available_actions_ddt) — la capability che spegne il campo

---

### 🎯 Scopo Principale

(nata il 2026-10-11, brief `brief-db-testata-dopo-emissione`, §11, R-DB-1)

Dice **da dove viene il cliente di una bolla**, cioè che cosa gli impedisce di cambiare. Una
riga per vincolo:

| Vincolo | Quando | Cosa porta |
| --- | --- | --- |
| `SORGENTE` | la bolla nasce da un ordine o da un reso | il cliente della sorgente; l'etichetta vuota se la sorgente non si trova |
| `FULFILLMENT` | la bolla evade già righe d'ordine | l'ordine evaso |

Nessuna riga: il cliente della bolla è libero, e in bozza si sceglie (D-2 di
`brief-db-esecutivi-ba-coppia`).

È la regola scritta una volta sola. Il guard la usa per rifiutare il cambio di cliente, la
capability per spegnere il campo nel form. I due non possono più dissentire: prima la
capability spegneva il cliente su ogni bolla, anche quella senza sorgente.

Gira con i permessi di chi scrive, come il guard: ordine, reso ed evasioni si leggono sotto la
sua visibilità.
