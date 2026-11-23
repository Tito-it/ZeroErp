## 📘 Documentazione Concettuale – Funzione `magazzino.fn_modifica_documento_interno`

> **Ultimo aggiornamento**: 23 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [magazzino.inventari](/dbzero/magazzino/tabelle/inventari) — una delle tre testate
> * [magazzino.rettifiche](/dbzero/magazzino/tabelle/rettifiche) — una delle tre testate
> * [magazzino.trasferimenti](/dbzero/magazzino/tabelle/trasferimenti) — una delle tre testate
>
> Approfondimento funzioni:
>
> * [magazzino.fn_documento_interno_famiglia](/dbzero/magazzino/funzioni/fn_documento_interno_famiglia) — il registro da cui legge tabelle e colonne
> * [magazzino.fn_documento_interno_blocca](/dbzero/magazzino/funzioni/fn_documento_interno_blocca) — la testata presa nel perimetro
> * [magazzino.fn_documento_interno_transizioni](/dbzero/magazzino/funzioni/fn_documento_interno_transizioni) — la matrice degli stati
>
> Guide:
>
> * [Architettura dei permessi — il permesso nel verbo di scrittura](/guide/architettura-permessi-e-autorizzazioni#74-il-permesso-nel-verbo-di-scrittura) — il modello che questi verbi seguono

---

### 🎯 Scopo Principale

Il gesto «modifica la testata» di un documento interno, comune alle tre famiglie: la famiglia è il primo argomento, e tabelle e colonne il verbo le legge dal registro.

---

### Regole

Si manda il delta: la data, e per l'inventario la descrizione. Il documento deve essere in bozza: confermato, annullato o registrato, la testata non si modifica più.

Lo stato non è un campo: ha il suo verbo. Ritorna la testata con le colonne modificabili.

---

### ⭐ Perché lo dice il verbo

La regola «la testata si modifica solo in bozza» c'era già, ma la faceva rispettare il backend: nessun controllo della tabella la dice. Qui il verbo è l'unico scrittore, e la fa rispettare lui.

---

### Codici errore

* `E_PERMESSO_NEGATO` — l'operatore non ha il livello «tutto» sul documento, o la famiglia non esiste.
* `E_MAG_DOCUMENTO_NON_TROVATO` — il documento non esiste o è fuori dal perimetro.
* `E_MAG_DOCUMENTO_TESTATA_CONGELATA` — il documento non è in bozza.
* `E_CAMPO_NON_AMMESSO` — un campo fuori dalla lista «modifica»; il codice lo nomina.

---

### Test

`db/pgtap/magazzino/test-verbi-documenti-interni-v1.sql` (il permesso, il perimetro, i campi, gli stati e la variabile della registrazione accesa dall'applicazione); `db/pgtap/magazzino/test-documenti-interni-guard-v1.sql` (la matrice, le righe congelate e l'eliminazione, attraverso i verbi).

---

### Note di migrazione

* 2026-11-23 — nasce quando i documenti interni passano dai verbi: prima testate, righe e stati li scriveva il backend, direttamente sulle tabelle (`brief-db-magazzino-tutte-le-scritture-dal-verbo`).

---

{% include-markdown "it/dbzero/magazzino/_verbi-di-scrittura.md" %}

---

{% include-markdown "it/dbzero/magazzino/_documenti-interni.md" %}

---

{% include-markdown "signature-core.md" %}
