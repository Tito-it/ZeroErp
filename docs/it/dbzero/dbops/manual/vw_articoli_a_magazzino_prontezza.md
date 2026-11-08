## 📘 Documentazione Concettuale – Vista `dbops.vw_articoli_a_magazzino_prontezza`

> **Ultimo aggiornamento**: 4 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [catalogo.articoli](/dbzero/catalogo/tabelle/articoli) — il flag `gestito_a_magazzino` che la vista guarda
> * [dbops.presidi](/dbzero/dbops/tabelle/presidi) — il catalogo che la iscrive, con lo stato atteso
>
> Approfondimento funzioni:
>
> * [dbops.fn_conta_presidio](/dbzero/dbops/funzioni/fn_conta_presidio) — il conteggio che fa suonare lo zero
>
> Guide:
>
> * [Presidi e registri del debito](/guide/presidi-e-registri-del-debito) — le nature dei presidi e la colonna di stato

---

### 🎯 Scopo Principale

**Il magazzino è pronto?** Una riga sola: `MARCATI` se almeno un articolo attivo è gestito a
magazzino, altrimenti `NESSUNO_MARCATO`, con il numero degli articoli marcati.

---

### ⭐ Perché esiste: un magazzino vuoto non dà errori

Al rilascio **nessun articolo** è gestito a magazzino: il flag nasce spento, per sicurezza, e si
accende col primo carico, non prima. Senza una spia il magazzino resterebbe un mobile vuoto senza
che nessun rosso lo dica: le bolle partono, nessuna merce si muove, e nessuno se ne accorge.

---

### ⭐ L'invariante non è la vista vuota: è una riga col valore giusto

A catalogo la vista ha natura `ZERO`, colonna di stato `stato` e stato atteso `MARCATI`: il
conteggio del presidio conta le righe **diverse** dall'atteso. Lo zero degli articoli suona, il
pieno tace. Non serve una natura nuova per un caso solo.

Cadenza `SETTIMANALE`: è una condizione di prontezza, non un incidente, e un allarme quotidiano su
una cosa già saputa si spegne.

---

### Chi la può vedere

`catalogo.articoli` non ha row level security, e la vista gira coi privilegi del proprietario:
perimetro `LIBERO`, il numero è lo stesso per chiunque lo chieda.

---

### Test

* `db/pgtap/dbops/test-articoli-a-magazzino-prontezza-v1.sql` — una riga sola, lo stato nei due
  versi, gli articoli spenti che non contano, la riga a catalogo con lo stato atteso.

---

### Note di migrazione

* 2026-09-14 — Tid decide che il flag si scrive col primo carico, non prima
  (`brief-db-modifiche-certe-ciclo-vendita-e-articolo` §7).
* 2026-09-18 — nasce con il Lotto 2 del magazzino (`brief-db-magazzino-lotto-2-motore` §4.8).

---

{% include-markdown "signature-core.md" %}
