## 📘 Documentazione Concettuale – Vista `dbops.vw_emittenti_regime_non_confermato`

> **Ultimo aggiornamento**: 4 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.emittenti_fiscali](/dbzero/anagrafiche/tabelle/emittenti_fiscali) — il regime e la sua conferma
> * [config.regimi_fiscali](/dbzero/config/tabelle/regimi_fiscali) — i regimi fiscali
> * [dbops.presidi](/dbzero/dbops/tabelle/presidi) — il catalogo che la iscrive
>
> Approfondimento funzioni:
>
> * [anagrafiche.trgfn_emittenti_fiscali_regime_conferma](/dbzero/anagrafiche/funzioni/trgfn_emittenti_fiscali_regime_conferma) — chi scrive la conferma
> * [anagrafiche.trgfn_emittenti_fiscali_guard_regime_conferma](/dbzero/anagrafiche/funzioni/trgfn_emittenti_fiscali_guard_regime_conferma) — la conferma non si scrive da fuori
>
> Guide:
>
> * [Presidi e registri del debito](/guide/presidi-e-registri-del-debito) — come si legge un presidio che deve restare vuoto

---

### 🎯 Scopo Principale

Gli emittenti fiscali attivi il cui regime fiscale **nessuno ha mai confermato**. Deve restare
vuota.

---

### ⛔ Un default non è una dichiarazione

Il regime fiscale di un emittente ha un default, il regime ordinario `RF01`. Un emittente in IVA
per cassa lasciato a `RF01` emette **tutte** le fatture a esigibilità immediata, e nessun
controllo lo dice: il guasto non assomiglia a un errore. Un default è un regime che nessuno ha
dichiarato, e questa vista lo rende visibile.

---

### Perché tutti i regimi e non solo `RF01`

Un emittente può nascere con un regime diverso dal default, e la creazione non conferma mai: un
regime non confermato è lo stesso fatto, qualunque codice abbia, «nessuno ha dichiarato questo
regime». Filtrare su `RF01` sarebbe un letterale di codice in un presidio, e un buco.

---

### ⭐ La conferma la scrive il database, e non si azzera

Ogni aggiornamento che **nomina** il regime, anche con lo stesso valore, è una dichiarazione: il
trigger `trgfn_emittenti_fiscali_regime_conferma` scrive data e autore della conferma. Un
aggiornamento che non nomina il regime non la tocca, e la conferma non si scrive a mano
(`trgfn_emittenti_fiscali_guard_regime_conferma`).

⇒ Una volta confermato, un emittente esce dalla vista e non ci rientra. La vista mostra solo i
regimi che nessuno ha mai dichiarato, e si svuota confermando il regime dal form dell'emittente.

---

### Chi la può vedere

`anagrafiche.emittenti_fiscali` non ha row level security, e la vista gira coi privilegi del
proprietario: perimetro `LIBERO`. Cadenza `SETTIMANALE`: è una condizione di prontezza, non un
incidente.

---

### Test

* `db/pgtap/vendite/test-esigibilita-iva-per-cassa-v1.sql` — un emittente col regime non
  confermato compare, e confermato esce.

---

### Note di migrazione

* 2026-10-01 — nasce con l'esigibilità dell'IVA per cassa dell'emittente
  (`brief-db-esigibilita-iva-per-cassa-emittente`, D-1 e D-11).
* 2026-10-02 — la conferma la deriva il database da ogni aggiornamento che nomina il regime
  (stesso brief, sezione 10). Prima un cambio di regime poteva lasciarla vuota.

---

{% include-markdown "signature-core.md" %}
