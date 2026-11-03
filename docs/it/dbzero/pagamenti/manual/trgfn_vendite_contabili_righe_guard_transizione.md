## 📘 Documentazione Concettuale – Trigger function `pagamenti.trgfn_vendite_contabili_righe_guard_transizione`

> **Ultimo aggiornamento**: 3 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [pagamenti.transizioni_stati_contabile_riga](/dbzero/pagamenti/tabelle/transizioni_stati_contabile_riga) — la matrice che il guard legge
> * [pagamenti.vendite_contabili_righe](/dbzero/pagamenti/tabelle/vendite_contabili_righe) — la tabella che custodisce
>
> Approfondimento funzioni:
>
> * [pagamenti.trgfn_vendite_contabili_guard_transizione](/dbzero/pagamenti/funzioni/trgfn_vendite_contabili_guard_transizione) — il gemello sulla distinta
> * [pagamenti.trgfn_vendite_contabili_righe_guard_stato_dati](/dbzero/pagamenti/funzioni/trgfn_vendite_contabili_righe_guard_stato_dati) — la metà «bagaglio» della stessa regola
> * [vendite.fn_sync_contabili_fondo_fattura](/dbzero/vendite/funzioni/fn_sync_contabili_fondo_fattura) — il giro che riscriveva una riga già registrata
> * [pagamenti.trgfn_vendite_contabili_righe_marca_fondo_eseguito](/dbzero/pagamenti/funzioni/trgfn_vendite_contabili_righe_marca_fondo_eseguito) — la difesa lato fondi
>
> Guide:
>
> * [Linee guida trigger](/linee-guida-trigger) — l'ordine alfabetico dei `BEFORE ROW`

---

### 🎯 Scopo Principale

Fa rispettare nel database il grafo degli stati della **riga contabile**, letto da
[transizioni_stati_contabile_riga](/dbzero/pagamenti/tabelle/transizioni_stati_contabile_riga):
un cambio di stato passa solo se la coppia esiste ed è attiva in matrice. È il gemello del guard
sulla distinta.

---

### Guarda solo i cambi di stato

* Scatta solo quando cambia lo stato, e se lo stato non cambia davvero non fa niente.
* ⚠️ Mai sull'inserimento: il giro dei fondi crea le sue righe direttamente in `ABBINATA`, che
  non è raggiungibile per transizione.
* Una coppia seminata spenta (`attivo = false`) vale come assente: è così che
  `ABBINATA → DA_ABBINARE` è rifiutata.

---

### ⭐ `POSTATA` è terminale, e chiude un difetto

`POSTATA` è l'unico stato dopo il quale esiste un fatto: il movimento contabile. Non avere
uscite da lì non è un dettaglio.

🔴 Il giro dei fondi fattura
([vendite.fn_sync_contabili_fondo_fattura](/dbzero/vendite/funzioni/fn_sync_contabili_fondo_fattura))
cerca la propria riga contabile e, trovandola, la riporta ad `ABBINATA`. Su una riga già
registrata questo faceva **contare lo stesso denaro due volte**, nel saldo contabile *e* nel
saldo movimenti, su una fattura che nessuno stava guardando. Ed è su percorso vivo: il ricalcolo
dei totali della fattura chiama quel giro **sempre**. Il database **rifiuta** quel passaggio.

⚠️ Non è l'unica difesa, e non deve esserlo, perché su percorso vivo un errore è una pipeline
che cade. Le difese sono tre, dalla più a monte:

1. l'atto di fondo esce dal ciclo con lo stato `ESEGUITO`
   ([marca_fondo_eseguito](/dbzero/pagamenti/funzioni/trgfn_vendite_contabili_righe_marca_fondo_eseguito)),
   e il giro **non arriva più** a quella riga;
2. se ci arriva lo stesso, il giro chiede **alla stessa matrice** se dallo stato della riga si
   torna ad `ABBINATA`, e se no scrive un avviso nel diario della fattura e salta l'atto, senza
   sollevare;
3. questo guard, che resta l'ultimo presidio per chiunque altro scriva lo stato.

---

### ⚠️ Parla per ultimo fra i guard di riga

I `BEFORE ROW` scattano in ordine **alfabetico**. Su `vendite_contabili_righe` questo guard
viene dopo il guard del contenuto, quello della distinta finale, quelli del perimetro, quello
della rata e quello sui dati. È l'ordine giusto: se la distinta è chiusa non ha senso discutere
del bagaglio della riga, né del suo percorso.

---

### Codici errore

* `E_RIGA_CONTABILE_TRANSIZIONE_NON_AMMESSA` — il passaggio da uno stato all'altro non c'è in
  matrice, o c'è spento.

---

### Test

`db/pgtap/pagamenti/test-transizioni-stati-contabili.sql` — `POSTATA` terminale (test 9),
l'inserimento non vincolato dalla matrice (10), `ABBINATA → DA_ABBINARE` seminata ma spenta
(11).

---

### Note di migrazione

* 2026-08-21 — nasce con la matrice della riga, con `POSTATA` già terminale.

---

{% include-markdown "signature-core.md" %}
