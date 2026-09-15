## 📘 Documentazione Concettuale – Tabella `magazzino.valore_giacenza`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
> • [magazzino.movimenti](/dbzero/magazzino/tabelle/movimenti) — il registro da cui si ricostruisce
>
Approfondimento viste:
> • [magazzino.vw_giacenza](/dbzero/magazzino/views/vw_giacenza) — la quantità
> • [magazzino.vw_costo_medio](/dbzero/magazzino/views/vw_costo_medio) — il costo medio (valore / quantità)
> • [magazzino.vw_giacenza_valorizzata](/dbzero/magazzino/views/vw_giacenza_valorizzata) — la situazione
>
Guide: brief `brief-db-magazzino-lotto-1-terreno-vuoto` (§4.6) · analisi carico e scarico (§7-ter, M-4)

---
### 🎯 Scopo Principale

(rev 2026-09-15 — Lotto 1 del magazzino; si chiamava `costo_medio`)

**Quanto vale la giacenza** di un articolo in un magazzino. Una riga per coppia
(articolo, magazzino), con il **valore** totale corrente.

È una **copia ricostruibile** del registro, non una fonte: la tiene aggiornata la primitiva
di scrittura (Lotto 2) e in qualunque momento si può rifare **ri-sommando** i costi scritti
sui movimenti — le entrate al costo del documento, le uscite alla media corrente. Non è una
ri-esecuzione: i costi unitari stanno sul registro, e sommarli basta.

---

### La quantità non sta qui

Fino al 14-09 la tabella portava anche `qta`, ed era una seconda giacenza da tenere allineata
alla prima. La quantità vive **solo** nel registro (`vw_giacenza` = somma dei movimenti); il
costo medio è `valore / quantità`, calcolato dalle viste mettendo insieme **due fonti** —
per questo, se una riga di valore manca per una giacenza che c'è, la vista lo mostra
(`valore` e `costo_medio` a `NULL`) invece di nasconderlo.

---

### Nessuna nota

Una copia non ha un autore: chi vuole dire qualcosa di un valore di giacenza lo dice
dell'articolo o del magazzino. La partizione `note_costo_medio` è stata ritirata e
`COSTO_MEDIO` non è più un tipo ammesso dal padre `magazzino.note`.

---

### Chi può vedere e scrivere

Nel perimetro RLS via magazzino (`rls_valore_giacenza_ef_whitelist`): un operatore vede i
valori dei magazzini del proprio emittente. Meccanismo comune:
[Linee guida SQL — sezione 10](/linee-guida-sql#10-row-level-security-rls).

⚠️ La FK verso `catalogo.articoli` mancava fino al 15-09: una riga poteva puntare a un
articolo inesistente. Ora c'è. Presidio:
`db/pgtap/magazzino/test-valore-giacenza-forma-v1.sql`.

---

{% include-markdown "it/dbzero/magazzino/_dominio-magazzino.md" %}

---

{% include-markdown "signature-core.md" %}
