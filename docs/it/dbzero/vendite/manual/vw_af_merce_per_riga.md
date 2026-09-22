## 📘 Documentazione Concettuale – Vista `vendite.vw_af_merce_per_riga`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
>
[vendite.attivita_fatturabili](/dbzero/vendite/tabelle/attivita_fatturabili)
> [vendite.commesse_attivita](/dbzero/vendite/tabelle/commesse_attivita)
> [vendite.ddt_righe](/dbzero/vendite/tabelle/ddt_righe)
> [vendite.ordini_righe](/dbzero/vendite/tabelle/ordini_righe)
>
La funzione di cui questa vista è la proiezione:
>
[vendite.fn_af_merce_per_riga](/dbzero/vendite/funzioni/fn_af_merce_per_riga) — lo stesso conto, per le chiavi di segmento che le si chiedono
>
Viste collegate:
>
[vw_partite_merce](vw_partite_merce.md)
> [vw_situazione_merce_ordine](vw_situazione_merce_ordine.md)
> Brief autorevole: `docs/it/dev/work-done/brief-design-partita-merce-generalizzata.md` §9, slice S1

---
### 🎯 Scopo Principale
(latest review 2026-09-21)

`vendite.vw_af_merce_per_riga` risponde a **una sola domanda**, e la risponde per tutti:

> *«Di questa riga di documento, quanti pezzi sono stati fatturati?»*

Nient'altro. Non decide se è giusto, non sottrae niente, non giudica: **traduce**. Da una parte
ci sono le attività fatturabili — le righe che la macchina della fatturazione produce — e
dall'altra ci sono le righe dei documenti che le persone leggono: righe d'ordine e righe di
DDT. Questa vista è il ponte fra le due.

> ⭐ **Il conto non sta più qui: sta in
> [`fn_af_merce_per_riga`](/dbzero/vendite/funzioni/fn_af_merce_per_riga), e questa vista ne è
> la proiezione senza filtro** — un corpo solo. Chi legge *tutto* (i pgTAP)
> legge la vista; chi legge per documento — la partita, la situazione per riga d'ordine — chiama la
> funzione con le chiavi di segmento delle righe che gli servono, e paga quelle, non la storia
> intera della fatturazione. È il motivo per cui questa vista era diventata «il pavimento» del conto
> della merce: l'unico pezzo ancora letto intero, e quello che cresce con le fatture.

⭐ **Esiste perché quella traduzione ha due trappole**, e finché stava dentro il contatore le
faceva inciampare tutti quelli che la usavano.

---

### Trappola 1 — le due corsie, e i due numeri che si somigliano

La merce può essere fatturata per due strade, a seconda di come è configurato il cliente:

| Corsia | Significa |
|---|---|
| `ORD` | si fattura **l'ordine** appena è confermato, e la spedizione viene quando viene |
| `DDT` | si fattura **la spedizione**, quando la merce è partita |

La vista espone la corsia in una colonna, e il numero di riga in un'altra.

> ⚠️ **`riga_id` da solo non vuol dire niente.** Con corsia `ORD` è una riga d'ordine, con
> corsia `DDT` è una riga di DDT — e i due numeri arrivano da **contatori diversi**: la riga
> d'ordine 172 e la riga di DDT 172 non hanno alcun rapporto fra loro. Chi legge questa vista
> deve usare **sempre le due colonne insieme**.

---

### Trappola 2 — i kit, e perché i numeri sembravano sbagliati

Quando si vende un articolo **composito** — un kit, cioè un prodotto fatto di più pezzi — la
fatturazione non lo tratta come un oggetto solo: lo **scompone** e ne fattura i componenti, uno
per uno, ciascuno con la sua quantità.

Il risultato, se si sommano ingenuamente, è un numero che non significa nulla:

```text
consegnato:   1 kit
fatturato:    3   ← ma non sono 3 kit: sono i 3 componenti di UN kit
```

Sono due unità di misura diverse, e sottrarle è come sottrarre chili da metri.

✅ **La vista rimette tutto in unità del padre**, cioè in kit. Può farlo perché al momento della
fatturazione viene annotato, su ciascun componente, **per quanto è stato moltiplicato**
(`meta → coeff_qta`). Basta dividere per tornare indietro:

```text
componente A:  20 pezzi ÷ coefficiente 2    = 10 kit
componente B:  10 pezzi ÷ coefficiente 1    = 10 kit
componente C:   5 pezzi ÷ coefficiente 0.5  = 10 kit
                                              ────────
                                              10 kit
```

Si prende **il massimo, non la somma**: i componenti sono tre *letture della stessa quantità di
kit*, non tre addendi.

> ⚠️ **E si pretende che concordino.** Se i tre valori non danno lo stesso numero — succede se
> un kit è stato fatturato solo a metà — la quantità di kit è **ambigua**, e la vista lo dice
> con `misurabile = false` invece di scegliere il valore più comodo.

---

### `misurabile`: la colonna che dice «non lo so»

Vale `false` in tre casi, tutti relativi ai kit:

* manca il coefficiente di moltiplicazione;
* il coefficiente c'è ma non è un numero;
* i componenti non concordano sulla quantità del padre.

In tutti e tre la colonna `quantita` contiene **comunque** un numero — ed è proprio per questo
che `misurabile` esiste: serve a dire che quel numero **non va usato**.

> **Zero e «non lo so» non sono la stessa cosa.** Un conto che vale zero è un'affermazione; un
> conto che non si sa fare è un'astensione. Chi confonde le due mostra a un operatore un saldo
> a posto dove in realtà nessuno ha saputo calcolarlo.

---

### ⚠️ `tipo_movimento` si vede, e NON si filtra

Il vocabolario dei movimenti è `NORMALE`, `RETTIFICA`, `ONERE`. Questa vista li espone tutti e
**non ne scarta nessuno**: chi la usa applica il filtro che gli serve — oggi, in pratica,
`NORMALE`.

Non è pigrizia, è una porta lasciata aperta. Quando arriverà la **nota di credito**, l'accredito
nascerà come movimento di `RETTIFICA` e dovrà **abbassare** il fatturato. Con questa forma
diventa una riga di codice in chi legge; se il filtro stesse qui dentro, bisognerebbe rifare la
base su cui poggia tutto il conto della merce.

---

### 📑 Campi chiave esposti

* **Chiave**: `corsia` + `riga_id` + `tipo_movimento` — sempre tutti e tre insieme
* **Il numero**: `quantita`, nell'unità di misura della riga di documento
* **L'attendibilità**: `misurabile`
* **Diagnostica**: `da_componenti` (la quantità viene da un kit scomposto), `voci` (quante
  attività concorrono)

---

### Esempio d'uso

```sql
-- Quanti pezzi sono stati fatturati per la riga di DDT 17163?
SELECT quantita, misurabile
FROM vendite.vw_af_merce_per_riga
WHERE corsia = 'DDT' AND riga_id = 17163 AND tipo_movimento = 'NORMALE';

-- I kit il cui conto non si riesce a fare: da guardare, non da ignorare.
SELECT corsia, riga_id, quantita
FROM vendite.vw_af_merce_per_riga
WHERE da_componenti AND NOT misurabile;
```

---

### Note operative

* **Non guarda lo stato di emissione.** L'esistenza stessa dell'attività fatturabile *è* la
  frontiera: la crea l'emissione e non viene mai cancellata. Non serve interrogare nessuno stato.
* **Vede solo le corsie `ORD` e `DDT`.** Preventivi, contratti e consumi hanno le loro chiavi e
  non sono merce che si muove: restano fuori.
* **Il coefficiente dei kit è un contratto fra due parti lontane** — lo scrive il push su
  commessa, lo legge la generazione delle righe di fattura, e in mezzo nulla lo verificava.
  Questa vista è il terzo lettore, e il primo che **se ne accorge** quando manca: invece di
  produrre un numero sbagliato, si dichiara non misurabile.
* `security_invoker=on`: la vista è letta con i permessi di chi interroga, quindi la RLS di
  scope resta attiva — attraverso la funzione, che è `INVOKER` e `BEGIN ATOMIC`, quindi visibile
  al presidio delle viste. ⚠️ Chi la modifica con `CREATE OR REPLACE` **deve ri-specificare la
  reloption**: non è visibile in `pg_get_viewdef` e verrebbe azzerata in silenzio.
* ⚠️ **Colonne per nome, non `SELECT *`**: il `RETURNS TABLE` della funzione perde il typmod di
  `tipo_movimento` (`varchar(32)`), e un `CREATE OR REPLACE VIEW … AS SELECT *` lo perderebbe in
  silenzio, senza poterlo più riprendere. La vista ricasta; il presidio della funzione pinna i tipi.
* ⚠️ **In sviluppo tutti i coefficienti valgono 1**, quindi la divisione dei kit non è
  esercitata dai dati reali: il test ne costruisce uno apposta con coefficienti 2 / 1 / 0.5.
* Test: `db/pgtap/vendite/test-vw-af-merce-per-riga-v1.sql` (il conto) e
  `test-fn-af-merce-per-riga-chiusura-v1.sql` (la lettura per chiave, i pin di forma).

---

{% include-markdown "signature-core.md" %}
