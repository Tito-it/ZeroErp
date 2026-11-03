## 📘 Documentazione Concettuale – Vista `dbops.vw_sorgenti_orfane`

> **Ultimo aggiornamento**: 4 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [config.sorgenti](/dbzero/config/tabelle/sorgenti) — il catalogo dei bersagli
> * [dbops.presidi](/dbzero/dbops/tabelle/presidi) — dove la vista è iscritta
>
> Approfondimento funzioni:
>
> * [dbops.fn_sorgenti_orfane](/dbzero/dbops/funzioni/fn_sorgenti_orfane) — chi la calcola
> * [dbops.fn_sorgenti_orfane_perimetro](/dbzero/dbops/funzioni/fn_sorgenti_orfane_perimetro) — su quali tabelle
>
> Guide:
>
> * [Sorgente polimorfa](/guide/sorgente-polimorfa) — il modello del collegamento tipo + chiave
> * [Presidi e registri del debito](/guide/presidi-e-registri-del-debito) — come si legge un presidio che deve restare vuoto

---

### 🎯 Scopo Principale

Le righe la cui sorgente punta a un record che non c'è più. **Deve restare vuota.** Ogni riga dice
la tabella, l'identificativo della riga, il tipo e la chiave di sorgente, e il bersaglio cercato.

---

### Che cosa vuol dire una riga

Un movimento di magazzino (o un atteso, una testata) dice da quale riga di documento nasce, con un
tipo a catalogo e una chiave. Il collegamento non è una chiave esterna e non può esserlo, perché il
bersaglio cambia con il tipo. Il guard tipizzato impedisce di **inserire** un collegamento verso un
bersaglio inesistente; questa vista trova quelli rimasti orfani **dopo**, quando qualcuno ha
cancellato il bersaglio.

⛔ Il rimedio non è cancellare la riga orfana: è capire chi ha cancellato il bersaglio. Di norma è
una cancellazione fuori dalle porte, perché i documenti registrati non si eliminano.

---

### Il presidio

Nel catalogo dei presidi è di natura `ZERO`, guardata ogni settimana, con perimetro `DEFINER`: la
funzione che la calcola gira coi privilegi del proprietario e attraversa la row level security,
perché un orfano in una tabella protetta va visto comunque. Il perimetro delle tabelle esaminate si
legge da `dbops.fn_sorgenti_orfane_perimetro`.

---

### Test

* `db/pgtap/dbops/test-sorgenti-orfane-v1.sql` — un bersaglio cancellato produce una riga, il
  conteggio del presidio la vede, e la riga di catalogo dei presidi ha natura, perimetro e cadenza
  attesi.

---

### Note di migrazione

* 2026-09-18 — nasce con il secondo lotto del magazzino (`brief-db-magazzino-lotto-2-motore`).

---

{% include-markdown "signature-core.md" %}
