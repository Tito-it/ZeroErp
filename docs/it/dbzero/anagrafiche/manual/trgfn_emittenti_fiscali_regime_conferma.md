## 📘 Documentazione Concettuale – Trigger function `anagrafiche.trgfn_emittenti_fiscali_regime_conferma`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.emittenti_fiscali](/dbzero/anagrafiche/tabelle/emittenti_fiscali) — il regime e le due colonne della conferma
>
> Approfondimento viste:
>
> * [dbops.vw_emittenti_regime_non_confermato](/dbzero/dbops/views/vw_emittenti_regime_non_confermato) — gli emittenti accesi col regime che nessuno ha dichiarato
>
> Approfondimento funzioni:
>
> * [anagrafiche.trgfn_emittenti_fiscali_guard_regime_conferma](/dbzero/anagrafiche/funzioni/trgfn_emittenti_fiscali_guard_regime_conferma) — il guard che impedisce di scrivere la conferma da fuori

---

### 🎯 Scopo Principale

`anagrafiche.trgfn_emittenti_fiscali_regime_conferma` scrive quando e da chi è stato dichiarato il regime fiscale
di un emittente: chi scrive il regime lo dichiara, e data e autore della conferma li scrive il database.

---

### ⭐ Scrivere il regime è dichiararlo

Scatta prima di ogni `UPDATE` che nomina `regime_fiscale_rf`, **anche con lo stesso valore**: è così che si
conferma un `RF01` che nessuno aveva dichiarato. Scrive `regime_fiscale_confermato_il` con l'istante e
`regime_fiscale_confermato_da` con l'utente dell'applicazione (la GUC `app.jwt_user`), o col ruolo del database
quando la GUC manca.

La regola sta nel database perché ogni scrittore del regime (il form, un import, un batch) la segue senza
doverla ricordare: il chiamante scrive il fatto, il trigger ne deriva data e autore.

---

### Che cosa non è una dichiarazione

* **Un `UPDATE` che non nomina il regime** non fa scattare il trigger: la conferma resta com'era.
* **La creazione.** Un `RF01` scelto e un `RF01` di default sono la stessa riga nuova, quindi la `INSERT` non
  conferma mai. Un regime dichiarato alla creazione si conferma con un `UPDATE` del regime nella stessa
  transazione: è quello che fa `anagrafiche.fn_crea_emittente_fiscale`.
* **Riempire un regime vuoto.** È il default `RF01` applicato dopo, non una scelta di qualcuno: la conferma
  resta vuota. Oggi la colonna è `NOT NULL`, e il ramo serve solo a un database ricostruito da zero, dove il
  riempimento dei regimi gira dopo questa funzione.

Il trigger non solleva. Chi scrive le due colonne da fuori lo ferma prima il guard
`anagrafiche.trgfn_emittenti_fiscali_guard_regime_conferma`, che per fascia vede i valori del chiamante prima che
questa funzione li riscriva. Con un regime che cambia sempre insieme alla sua conferma, il presidio mostra solo
i regimi che nessuno ha mai dichiarato.

---

### Test

* `db/pgtap/vendite/test-esigibilita-iva-per-cassa-v1.sql` (casi 22-33) — la conferma a ogni dichiarazione,
  anche con lo stesso valore, la creazione che non conferma, l'`UPDATE` che non nomina il regime.

Il ramo del regime vuoto non è nel pgTAP: per costruire la riga bisogna togliere il `NOT NULL` e spegnere i
trigger, cosa che il runner come applicazione non può fare.

---

### Note di migrazione

* 2026-10-01 — nasce la conferma: la scriveva il form insieme al regime, e la funzione la azzerava se il regime
  cambiava senza. Lo stesso cantiere riempie i regimi vuoti col default `RF01` e poi mette il `NOT NULL` con la
  FK sul catalogo.
* 2026-10-02 — la conferma la scrive il database, a ogni dichiarazione.

---

{% include-markdown "signature-core.md" %}
