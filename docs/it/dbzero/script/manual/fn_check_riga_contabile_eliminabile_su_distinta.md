## 📘 Documentazione Concettuale – Funzione `script.fn_check_riga_contabile_eliminabile_su_distinta()`

> 👀 **Vedi anche**
>
> **Chi la chiama:**
>
> • [script.fn_check_riga_contabile_eliminabile](/dbzero/script/funzioni/fn_check_riga_contabile_eliminabile) — la firma per id: legge riga e testata, poi delega qui
> • il backend, in `LATERAL` sulle liste delle righe contabili, con l'alias della testata
>
> **Approfondimento tabelle:**
>
> • [pagamenti.vendite_contabili](/dbzero/pagamenti/tabelle/vendite_contabili)
> • [pagamenti.vendite_contabili_stati](/dbzero/pagamenti/tabelle/vendite_contabili_stati)
>
> **La regola:** [linee-guida-sql §13.2](/linee-guida-sql) · **Il precedente:** [script.fn_check_articolo_riga_su_contesto](/dbzero/script/funzioni/fn_check_articolo_riga_su_contesto)

---

### 🎯 Scopo Principale
(scritta il 21-10-2026)

Dice se una riga contabile si può **eliminare**, guardando la sua **distinta**.
Risponde `[]` quando si può (distinta `MANUALE` in `BOZZA`), altrimenti
l'elenco ordinato dei motivi. Le regole e i codici sono quelli di
[`fn_check_riga_contabile_eliminabile`](/dbzero/script/manual/fn_check_riga_contabile_eliminabile):
qui c'è la stessa risposta, data su una distinta **già letta**.

---

### ⭐ Perché esiste: il perimetro una volta per lista

Il database decide che cosa vede ogni utente (il suo **perimetro**) e lo
calcola **una volta per istruzione**
([§10.3](/linee-guida-sql)). La firma per id legge riga e testata sotto la row
security: chiamata per ogni riga di una lista, ogni chiamata è un'istruzione a sé,
e il perimetro si ricalcola **per riga**. Eppure la lista quelle righe le ha già
lette, sotto la sua policy.

Questa metà **non legge niente sotto perimetro**: riceve la distinta e la
giudica. Legge solo il catalogo degli stati, che non ha row security, perché le
bandiere `is_final` e `righe_lavorabili` sono sue.

| Chi chiama | Che cosa usa | Perché |
| --- | --- | --- |
| una **lista** di righe | questa metà, con la testata della riga (`…_su_distinta(c)`) | la lista ha già letto la testata, una volta per istruzione |
| il **guard** del contenuto, il **dettaglio** di una riga | la firma per id | serve la lettura sotto RLS e il 404 no-leak |

Le regole stanno **qui**, una volta sola: la firma per id legge e delega.
Tooltip del cestino e rifiuto del guard non possono divergere.

---

### Il parametro: la riga della testata

`p_contabile` è una riga di `pagamenti.vendite_contabili`: il tipo **è** la
tabella. Il chiamante passa l'alias della testata, e il giorno in cui un motivo
chiede un'altra colonna della distinta la chiamata non cambia.

⚠️ **Nessun 404 qui, ed è giusto.** La funzione giudica un valore ricevuto, non
cerca niente: non c'è niente da nascondere. Il no-leak è della firma per id.
Una distinta passata a mano riceve la risposta su ciò che è stato passato. Il
guard resta l'autorità, perché chiama la firma per id.

---

### Codici errore

I motivi e i loro codici sono quelli della firma per id
([tabella](/dbzero/script/manual/fn_check_riga_contabile_eliminabile)). In più:

| Codice | Classe | Quando |
| --- | --- | --- |
| `E_PAGAMENTI_CHIAMATA_NON_VALIDA` | `TECNICO` | la distinta non ha id: un `LEFT JOIN` che non ha trovato la testata, cioè un chiamante rotto |

---

Presidio: `db/pgtap/pagamenti/test-righe-contabili-eliminazione-v1.sql` (31-35):
stessa risposta per le due strade, nessuna rilettura, i codici ereditati dal
guard. ChangeSet: `20261021-62`.

{% include-markdown "signature-core.md" %}
