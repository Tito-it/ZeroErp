## 📘 Documentazione Concettuale – Funzione `dbops.fn_codice_maiuscolo_perimetro`

> **Ultimo aggiornamento**: 4 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [dbops.automazione_codice_eccezioni](/dbzero/dbops/tabelle/automazione_codice_eccezioni) — le colonne escluse
> * [dbops.automation_scope](/dbzero/dbops/tabelle/automation_scope) — l'ambito delle automazioni
>
> Approfondimento funzioni:
>
> * [dbops.fn_run_automations_codice_maiuscolo](/dbzero/dbops/funzioni/fn_run_automations_codice_maiuscolo) — il motore che esegue le azioni
> * [script.trgfn_codice_maiuscolo](/dbzero/script/funzioni/trgfn_codice_maiuscolo) — il trigger di cui si dice se è dovuto
> * [dbops.fn_resolve_scope](/dbzero/dbops/funzioni/fn_resolve_scope) e [dbops.fn_table_in_scope](/dbzero/dbops/funzioni/fn_table_in_scope) — schemi e tabelle dell'ambito
>
> Guide:
>
> * [Framework di automazione DB](/guide/automazione-db) — §4.8, l'automazione CODICE_MAIUSCOLO

---

### 🎯 Scopo Principale

Dice, tabella per tabella, se il trigger che salva il codice in maiuscolo è **dovuto**, quali trigger
su quella funzione sono **vivi** e l'**azione** che allinea le due cose. È la sede unica della
regola: la leggono il motore, la convergenza di ogni migrate, il pgTAP di presidio e la bonifica una
tantum delle righe già scritte. Una regola scritta in quattro posti prima o poi risponde in quattro
modi.

---

### Il perimetro

Una tabella è nel perimetro se:

* è una tabella ordinaria di uno schema dell'ambito (`fn_resolve_scope`, con l'elenco della corsa o
  quello del registro), schema `storico` escluso — le tabelle ombra ricordano, non si normalizzano;
* passa `fn_table_in_scope`;
* ha una colonna `codice` di tipo stringa e non generata.

Il trigger è **dovuto** se la tabella è nel perimetro e non è in `dbops.automazione_codice_eccezioni`.

---

### Le azioni

| Azione | Quando |
| --- | --- |
| `CREA` | dovuto, nessun trigger vivo |
| `RIGENERA` | dovuto, più di un trigger vivo |
| `TOGLIE` | non dovuto e vivo: un'eccezione nuova, una colonna tolta, una tabella uscita dall'ambito |
| `NULL` | già a posto |

⭐ Converge nei due sensi: un registro che monta e non smonta dice una cosa e il database un'altra.
Un trigger rimasto su una tabella senza più la colonna farebbe fallire ogni sua scrittura.

⚠️ Il trigger vivo si riconosce dalla **funzione**, mai dal nome: un nome lungo PostgreSQL lo
tronca. E i trigger vivi si cercano solo negli schemi della corsa: con un elenco esplicito, un
trigger di un altro schema non diventa un `TOGLIE`.

---

### Test

`db/pgtap/dbops/test-codice-maiuscolo-v1.sql`: su tutto il database nessuna azione (test 5); lo
schema di prova costruisce CREA, una colonna non stringa fuori perimetro, TOGLIE da eccezione e da
colonna tolta (test 9, 20, 22).

---

{% include-markdown "signature-core.md" %}
