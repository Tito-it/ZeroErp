## 📘 Documentazione Concettuale – Trigger function `anagrafiche.trgfn_gestori_guard_ruolo_gestore`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.gestori](/dbzero/anagrafiche/tabelle/gestori) — la specializzazione che presidia
> * [anagrafiche.soggetti_ruoli](/dbzero/anagrafiche/tabelle/soggetti_ruoli) — il ruolo nominato dalla riga
> * [config.tipi_ruoli](/dbzero/config/tabelle/tipi_ruoli) — il ruolo `GE`
>
> Approfondimento funzioni:
>
> * [script.fn_guard_soggetto_ruolo](/dbzero/script/funzioni/fn_guard_soggetto_ruolo) — il controllo, a cui delega per intero
> * [anagrafiche.trgfn_gestori_guard](/dbzero/anagrafiche/funzioni/trgfn_gestori_guard) — il guard di dominio, che scatta prima

---

### 🎯 Scopo Principale

`anagrafiche.trgfn_gestori_guard_ruolo_gestore` è il guard di ruolo del gestore: la riga di `anagrafiche.gestori`
punta solo a un ruolo `GE`.

---

### Che cosa ha di proprio il gestore

Sulla stessa riga scatta prima `anagrafiche.trgfn_gestori_guard`, che controlla già che il ruolo esista: un ruolo
mancante o inesistente risponde con `E_GESTORE_SOGGETTO_RUOLO_MANCANTE`, e a questo guard arriva solo un ruolo che
esiste, per dire se è del tipo giusto.

Il commento nel corpo parla di una riga «nuova o esistente» di `soggetti_ruoli`: il guard non crea niente e non
scrive niente, il ruolo `GE` va creato prima.

---

{% include-markdown "it/dbzero/anagrafiche/_guard-di-ruolo.md" %}

---

{% include-markdown "signature-core.md" %}
