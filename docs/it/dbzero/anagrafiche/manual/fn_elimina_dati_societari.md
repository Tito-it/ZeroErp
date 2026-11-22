## 📘 Documentazione Concettuale – Funzione `anagrafiche.fn_elimina_dati_societari`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.dati_societari](/dbzero/anagrafiche/tabelle/dati_societari) — la riga che la funzione elimina
>
> Approfondimento funzioni:
>
> * [anagrafiche.fn_check_elimina_dati_societari](/dbzero/anagrafiche/funzioni/fn_check_elimina_dati_societari) — i motivi per cui non si può
> * [anagrafiche.fn_scrivi_dati_societari](/dbzero/anagrafiche/funzioni/fn_scrivi_dati_societari) — la porta gemella, per la scrittura
> * [anagrafiche.fn_check_cambio_natura_soggetto](/dbzero/anagrafiche/funzioni/fn_check_cambio_natura_soggetto) — il cambio di natura, che chiede la riga eliminata prima
> * [script.fn_raise_primo_motivo_se_presente](/dbzero/script/funzioni/fn_raise_primo_motivo_se_presente) — il rifiuto col primo motivo

---

### 🎯 Scopo Principale

`anagrafiche.fn_elimina_dati_societari` è la porta di eliminazione dei dati societari di un soggetto: cancella
la sua riga, se la natura non la pretende. Restituisce vero se ha cancellato, falso se non c'era niente da
cancellare, e il falso non è un errore.

---

### ⭐ Un'azione a sé, prima del cambio di natura

Il cambio di natura non elimina i dati societari da solo: verso una natura che non li ammette (una ditta
individuale che diventa privato) il cambio è rifiutato finché la riga c'è (`E_CAMBIO_NATURA_CON_DATI_SOCIETARI`).
Chi cambia la natura elimina prima la riga con questa funzione, poi cambia il soggetto. Così la perdita dei
dati è un gesto esplicito di chi lavora, non un effetto del cambio.

---

### Come decide

* La riga del soggetto si **blocca** prima della decisione: un cambio di natura concorrente aspetta, e la
  natura che si giudica è quella che resta.
* La decisione è di `anagrafiche.fn_check_elimina_dati_societari`, e la funzione solleva il suo primo motivo.
  Oggi il motivo è uno: la natura del soggetto pretende la riga.
* La riga cancellata resta nello storico.

La funzione gira coi privilegi del proprietario, perché l'applicazione sulla tabella ha solo la lettura. Il
permesso lo decide l'applicazione.

---

### Codici errore

* `E_PARAMETRO_INVALIDO` — il soggetto non è passato.
* `E_DATI_SOCIETARI_SOGGETTO_NON_TROVATO` — il soggetto passato non esiste.
* `E_DATI_SOCIETARI_NON_ELIMINABILI` — la natura del soggetto pretende i dati societari.

---

### Test

* `db/pgtap/anagrafiche/test-fn-elimina-dati-societari-v1.sql` — la porta (eseguibile dall'applicazione, non
  da tutti; la tabella senza `DELETE` per l'applicazione), il rifiuto per una società di capitali con la riga
  che resta, l'eliminazione per una ditta individuale con lo storico che la conserva, la seconda chiamata che
  restituisce falso, il cambio verso il privato che dopo non ha più il motivo dei dati societari.

---

### Note di migrazione

* 2026-11-14 — nasce col cambio di natura del soggetto, come azione separata da quel cambio.

---

{% include-markdown "it/dbzero/anagrafiche/_dati-societari.md" %}

---

{% include-markdown "signature-core.md" %}
