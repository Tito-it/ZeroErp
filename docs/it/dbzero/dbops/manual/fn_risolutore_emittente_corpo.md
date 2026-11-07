## 📘 Documentazione Concettuale – Funzione `dbops.fn_risolutore_emittente_corpo`

> **Ultimo aggiornamento**: 7 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [dbops.emittente_modi](/dbzero/dbops/tabelle/emittente_modi) — il registro da cui scrive
>
> Approfondimento funzioni:
>
> * [dbops.fn_genera_risolutori_emittente](/dbzero/dbops/funzioni/fn_genera_risolutori_emittente) — chi usa il testo per riscrivere i risolutori
> * [script.fn_resolve_emittente_fiscale_id](/dbzero/script/funzioni/fn_resolve_emittente_fiscale_id) — il risolutore fiscale, il cui corpo è questo testo
> * [script.fn_resolve_emittente_sr_id](/dbzero/script/funzioni/fn_resolve_emittente_sr_id) — il gemello in convenzione soggetto-ruolo

---

### 🎯 Scopo Principale

Scrive il **corpo** di uno dei due risolutori dell'emittente dal registro `dbops.emittente_modi`:
con `false` quello del risolutore fiscale, con `true` quello del gemello in convenzione
soggetto-ruolo. Restituisce il testo e basta: a creare la funzione ci pensa
`dbops.fn_genera_risolutori_emittente`.

---

### Che cosa scrive

* Un ramo per modo, in ordine di nome. Ogni ramo cerca la riga nella tabella del modo, aggiunge un
  collegamento per ogni salto verso la testata, e legge l'emittente dalla radice.
* Il risolutore fiscale risponde con l'id dell'emittente fiscale: per una radice in convenzione
  soggetto-ruolo passa dall'anagrafica degli emittenti fiscali.
* Il gemello risponde con il soggetto-ruolo dell'emittente: per una radice in convenzione fiscale fa
  lo stesso passaggio al contrario.
* Il ramo finale solleva `E_PARAMETRO_INVALIDO` per un modo sconosciuto, e il messaggio elenca i modi
  del registro.

Le strade sono lette per chiave: lo stesso codice che i rami avevano quando si scrivevano a mano.

---

### Prima di scrivere, controlla

Per ogni modo controlla che la tabella esista e abbia la colonna chiave e la colonna, e che la
catena dei salti arrivi a una radice in al più dieci passi. Raccoglie tutti i problemi e li dice
insieme con `E_EMITTENTE_MODI_INVALIDO`, invece di scrivere un risolutore che si romperebbe alla prima
chiamata di quel modo. Anche un registro vuoto è un problema.

Senza l'argomento (`NULL`) risponde `E_DBOPS_CHIAMATA_NON_VALIDA`.

---

### Test

`dbops/test-emittente-modi-registro-v1`: il testo coincide col corpo vivo dei due risolutori; su un
registro costruito risolve salti, radici e convenzioni; con una colonna che non c'è risponde
`E_EMITTENTE_MODI_INVALIDO` nominando il modo.

---

{% include-markdown "signature-core.md" %}
