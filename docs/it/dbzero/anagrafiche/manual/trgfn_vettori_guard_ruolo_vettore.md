## 📘 Documentazione Concettuale – Trigger function `anagrafiche.trgfn_vettori_guard_ruolo_vettore`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.vettori](/dbzero/anagrafiche/tabelle/vettori) — la specializzazione che il guard presidia
> * [anagrafiche.soggetti_ruoli](/dbzero/anagrafiche/tabelle/soggetti_ruoli) — il ruolo a cui la riga punta
> * [config.tipi_ruoli](/dbzero/config/tabelle/tipi_ruoli) — dove il codice `VT` diventa un tipo di ruolo
>
> Approfondimento funzioni:
>
> * [script.fn_guard_soggetto_ruolo](/dbzero/script/funzioni/fn_guard_soggetto_ruolo) — il controllo, a cui il guard delega
>
> Guide:
>
> * [Soggetti e ruoli anagrafici](/guide/soggetti-e-ruoli-anagrafici) — il soggetto, i ruoli e le loro specializzazioni

---

### 🎯 Scopo Principale

`anagrafiche.trgfn_vettori_guard_ruolo_vettore` impedisce che una riga di `anagrafiche.vettori` punti a un ruolo che
non è un vettore (`VT`). Senza, nulla vieterebbe di agganciarla al ruolo cliente o fornitore dello stesso soggetto.

---

### L'assegnazione non risolve niente

Il guard scrive in `soggetto_ruolo_id` il valore che la funzione delegata restituisce, ma quel valore è quello
passato: il guard o lascia passare la riga com'è, o la rifiuta. Non ricava il ruolo `VT` dal soggetto, e chi scrive
un vettore deve passare il ruolo giusto. Il commento nel corpo, che parla di «sostituire con l'id vero», descrive
più di quello che succede.

---

{% include-markdown "it/dbzero/anagrafiche/_guard-di-ruolo.md" %}

---

### Codici errore

* `E_SOGGETTI_RUOLI` — il ruolo manca, non esiste o non è `VT`.
* `E_COD_INT_RUOLO` — il codice `VT` non è in `config.tipi_ruoli`.

Li solleva `script.fn_guard_soggetto_ruolo`, passando dal registro degli errori.

---

### Test

Nessun pgTAP prova il rifiuto di un ruolo di altro tipo sui vettori.

---

{% include-markdown "signature-core.md" %}
