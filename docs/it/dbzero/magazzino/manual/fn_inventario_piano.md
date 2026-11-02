## 📘 Documentazione Concettuale – Funzione `magazzino.fn_inventario_piano`

> **Ultimo aggiornamento**: 1 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [magazzino.inventari](/dbzero/magazzino/tabelle/inventari) — la testata dell'inventario
> * [magazzino.inventari_righe](/dbzero/magazzino/tabelle/inventari_righe) — le righe contate
> * [magazzino.movimenti](/dbzero/magazzino/tabelle/movimenti) — il registro contro cui si confronta
>
> Approfondimento funzioni:
>
> * [magazzino.fn_posta_inventario](/dbzero/magazzino/funzioni/fn_posta_inventario) — chi lo legge per postare
> * [script.fn_check_riga_magazzino](/dbzero/script/funzioni/fn_check_riga_magazzino) — l'esito `NON_POSTABILE`

---

### 🎯 Scopo Principale

**Che cosa scriverà il posting di un inventario, prima di confermare**: una riga per ogni
posizione del magazzino che il registro ha o che il conteggio nomina, con l'esito che avrà.

Il caso da cui nasce: l'articolo A sta in UX a registro, l'inventario lo conta in UY. Postare
carica UY e lascia UX com'è — può essere giusto (spostato senza documento) ma *qualcuno deve
saperlo prima*. Il numero lo dà il database, in una funzione sola che il drawer legge al
passaggio a `CONFIRM` e che il posting legge per scrivere: ciò che l'operatore vede è
esattamente ciò che verrà registrato.

---

### Una riga per posizione

Una **posizione** è la combinazione di articolo, ubicazione, lotto e seriale. Il piano ne dà
una per ogni posizione che il registro del magazzino **ha** (con giacenza diversa da zero) o
che il conteggio **nomina**, limitandosi agli articoli contati:

| `esito` | Che cos'è |
| --- | --- |
| `INV_INIZIALE` | riga contata con differenza positiva su un articolo **mai movimentato** in questo magazzino: il primo carico |
| `RETT_POS` / `RETT_NEG` | riga contata con differenza: verrà postata così |
| `INVARIATA` | riga contata, differenza zero: nessun movimento |
| `NON_CONTATA` | posizione a registro con giacenza che nessuna riga copre (`riga_id` e `qta_contata` vuoti): **resta com'è**. Informazione, non blocco — l'operatore può aggiungere una riga (UX = 0, o UX = 10) o lasciare |
| `NON_POSTABILE` | riga che la primitiva rifiuterebbe — articolo non gestito, lotto/seriale/ubicazione mancanti o non ammessi — con `posting_blocco_reason` e `posting_blocco_reason_key` dal primo motivo di [fn_check_riga_magazzino](/dbzero/script/funzioni/fn_check_riga_magazzino): la stessa funzione che la primitiva chiama |

Per correggere una `NON_POSTABILE` o aggiungere una riga il documento **torna in bozza**
(da `CONFIRM` a `DRAFT`): è la ragione per cui quella transizione esiste.

---

### Legge con gli occhi dell'operatore

La funzione gira con i permessi di chi la chiama, sotto la sicurezza di riga dell'operatore:
una testata fuori perimetro dà zero righe (il «non trovato» lo dà l'applicazione sulla
testata).

---

### Codici errore

* `E_MAG_CHIAMATA_NON_VALIDA` — l'inventario manca o non è un identificativo valido: chi
  chiama è rotto.

---

### Test

`db/pgtap/magazzino/test-fn-posta-inventario-v1.sql` (test 1, 5, 6, 12-15).

---

### Note di migrazione

* 2026-09-18 — nasce con `brief-db-magazzino-lotto-2-motore` (§3 D-L2-n, §6-ter C8).

---

{% include-markdown "it/dbzero/magazzino/_dominio-magazzino.md" %}

---

{% include-markdown "signature-core.md" %}
