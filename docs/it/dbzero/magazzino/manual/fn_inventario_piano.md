## 📘 Documentazione Concettuale – Funzione `magazzino.fn_inventario_piano`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
> • [magazzino.inventari](/dbzero/magazzino/tabelle/inventari), [magazzino.inventari_righe](/dbzero/magazzino/tabelle/inventari_righe)
> • [magazzino.movimenti](/dbzero/magazzino/tabelle/movimenti) — il registro contro cui si confronta
>
Approfondimento funzioni:
> • [magazzino.fn_posta_inventario](/dbzero/magazzino/funzioni/fn_posta_inventario) — chi lo legge per postare
> • [script.fn_check_riga_magazzino](/dbzero/script/funzioni/fn_check_riga_magazzino) — l'esito `NON_POSTABILE`
>
Guide: brief `brief-db-magazzino-lotto-2-motore` (§3 D-L2-n, §6-ter C8)

---
### 🎯 Scopo Principale

(rev 2026-09-18 — Lotto 2 del magazzino)

**Che cosa scriverà il posting, prima di confermare.** Il caso da cui nasce: l'articolo A sta
in UX a registro, l'inventario lo conta in UY. Postare carica UY e lascia UX com'è — può
essere giusto (spostato senza documento) ma *qualcuno deve saperlo prima*. Il numero lo dà il
database, in una funzione sola che il drawer legge al passaggio a `CONFIRM` e che il posting
legge per scrivere: ciò che l'operatore vede è esattamente ciò che verrà registrato.

Una riga per ogni **posizione** (articolo × ubicazione × lotto × seriale) che il registro del
magazzino **ha** o che il conteggio **nomina**, per gli articoli contati:

| `esito` | Che cos'è |
| --- | --- |
| `INV_INIZIALE` | riga contata con differenza positiva su un articolo **mai movimentato** in questo magazzino: il primo carico |
| `RETT_POS` / `RETT_NEG` | riga contata con differenza: verrà postata così |
| `INVARIATA` | riga contata, differenza zero: nessun movimento |
| `NON_CONTATA` | posizione a registro con giacenza che nessuna riga copre (`riga_id` e `qta_contata` vuoti): **resta com'è**. Informazione, non blocco — l'operatore può aggiungere una riga (UX = 0, o UX = 10) o lasciare |
| `NON_POSTABILE` | riga che la primitiva rifiuterebbe — articolo non gestito, lotto/seriale/ubicazione mancanti o non ammessi — con `posting_blocco_reason` e `_reason_key` dal primo motivo di [fn_check_riga_magazzino](/dbzero/script/funzioni/fn_check_riga_magazzino): la stessa funzione che la primitiva chiama |

Per correggere una `NON_POSTABILE` o aggiungere una riga il documento **torna in bozza**
(`CONFIRM → DRAFT`): è la ragione per cui quella transizione esiste.

`SECURITY INVOKER`, sotto la row level security dell'operatore: una testata fuori perimetro dà
zero righe (il 404 lo dà l'applicazione sulla testata).

Presidio: `db/pgtap/magazzino/test-fn-posta-inventario-v1.sql` (1, 5, 6, 12-15).

---

### Storia

* 2026-09-18 — nasce con il Lotto 2 (`20260918-22`).

---

{% include-markdown "it/dbzero/magazzino/_dominio-magazzino.md" %}

---

{% include-markdown "signature-core.md" %}
