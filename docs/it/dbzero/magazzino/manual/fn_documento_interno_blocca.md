## 📘 Documentazione Concettuale – Funzione `magazzino.fn_documento_interno_blocca`

> **Ultimo aggiornamento**: 23 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento funzioni:
>
> * [magazzino.fn_documento_interno_famiglia](/dbzero/magazzino/funzioni/fn_documento_interno_famiglia) — il registro da cui legge nomi e variabile
> * [script.fn_scope_ef_whitelist_via_magazzino](/dbzero/script/funzioni/fn_scope_ef_whitelist_via_magazzino) — il predicato della policy, il perimetro

---

### 🎯 Scopo Principale

Il guard che **prende la testata** di un documento interno per un verbo: la trova nel perimetro dell'operatore, la blocca per la durata della transazione e ritorna il registro della famiglia con lo stato letto sotto il blocco.

---

### Inesistente e fuori perimetro rispondono uguale

Il verbo gira come il proprietario delle tabelle, e lì la sicurezza per riga non filtra: il guard applica lo stesso predicato della policy sul magazzino del documento (per il trasferimento, quello di partenza). Un documento di un'altra azienda è «non trovato», come uno che non esiste.

---

### ⚠️ Spegne la variabile della registrazione

Prima di ritornare spegne la variabile con cui la registrazione apre le porte della sua famiglia. Il verbo che lo chiama scrive come il proprietario: una variabile accesa dall'applicazione prima della chiamata aprirebbe ai controlli della tabella il passaggio a «registrato» e le righe fuori dalla bozza, senza che niente venga registrato.

---

### Che cosa non fa

Non controlla il permesso (lo ha già fatto il verbo) e non guarda lo stato: lo stato lo fanno rispettare i controlli della tabella e, per la testata, il verbo di modifica.

---

### Codici errore

* `E_MAG_DOCUMENTO_NON_TROVATO` — il documento non esiste o è fuori dal perimetro, senza dire quale dei due.
* `E_MAG_CHIAMATA_NON_VALIDA` — una famiglia che il registro non conosce.

---

### Test

`db/pgtap/magazzino/test-verbi-documenti-interni-v1.sql` (il perimetro e la variabile accesa dall'applicazione).

---

### Note di migrazione

* 2026-11-23 — nasce con i verbi comuni dei documenti interni; lo stesso giorno impara a spegnere la variabile della registrazione, dopo il controesempio di un'applicazione che la accendeva davanti al verbo (`brief-db-magazzino-tutte-le-scritture-dal-verbo`).

---

{% include-markdown "it/dbzero/magazzino/_documenti-interni.md" %}

---

{% include-markdown "signature-core.md" %}
