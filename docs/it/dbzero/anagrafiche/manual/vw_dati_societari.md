## 📘 Documentazione Concettuale – Vista `anagrafiche.vw_dati_societari`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.dati_societari](/dbzero/anagrafiche/tabelle/dati_societari) — la riga che la vista espone
> * [anagrafiche.soggetti](/dbzero/anagrafiche/tabelle/soggetti) — la ragione sociale e l'identificativo fiscale
> * [config.forme_giuridiche](/dbzero/config/tabelle/forme_giuridiche) — codice e descrizione della forma
> * [config.province](/dbzero/config/tabelle/province) — sigla e descrizione della provincia del REA
>
> Approfondimento funzioni:
>
> * [anagrafiche.fn_scrivi_dati_societari](/dbzero/anagrafiche/funzioni/fn_scrivi_dati_societari) — la porta di scrittura
> * [anagrafiche.fn_elimina_dati_societari](/dbzero/anagrafiche/funzioni/fn_elimina_dati_societari) — la porta di eliminazione

---

### 🎯 Scopo Principale

`anagrafiche.vw_dati_societari` è la lettura dei dati societari con le decodifiche: per ogni riga, la ragione
sociale e l'identificativo fiscale del soggetto, il codice e la descrizione della forma, la sigla e la
descrizione della provincia del REA. Tiene anche gli id delle tabelle di origine e le colonne di audit.

---

### Una riga per soggetto con dati societari

La vista parte da `anagrafiche.dati_societari`: un soggetto senza dati societari non compare, e uno che li ha
compare una volta. Forma e provincia si aggiungono senza togliere righe: una riga senza REA esce con la
provincia vuota.

---

### Si legge, non si scrive

La vista è una lettura. I dati societari si scrivono con `anagrafiche.fn_scrivi_dati_societari` e si
eliminano con `anagrafiche.fn_elimina_dati_societari`; l'applicazione sulla tabella ha solo la lettura.

La vista legge coi privilegi del proprietario; le tabelle sotto non hanno RLS, e chi la interroga vede tutti
i soggetti.

---

### ⚠️ Che cosa oggi non copre

* **L'applicazione ha i diritti di scrittura sulla vista.** `zeroerp_app` ha `INSERT`, `UPDATE` e `DELETE`
  oltre a `SELECT`. La vista unisce più tabelle e non ha trigger `INSTEAD OF`: una scrittura è comunque
  rifiutata da PostgreSQL, ma il permesso dice il contrario della regola.

---

{% include-markdown "signature-core.md" %}
