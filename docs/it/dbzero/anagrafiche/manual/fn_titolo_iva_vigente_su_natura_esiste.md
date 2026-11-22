## 📘 Documentazione Concettuale – Funzione `anagrafiche.fn_titolo_iva_vigente_su_natura_esiste`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.soggetti_titoli_iva](/dbzero/anagrafiche/tabelle/soggetti_titoli_iva) — i titoli che cerca, di tutti gli emittenti
> * [config.tipi_titolo_iva_tipi_soggetto_dettaglio](/dbzero/config/tabelle/tipi_titolo_iva_tipi_soggetto_dettaglio) — la matrice di cui protegge le righe
>
> Approfondimento funzioni:
>
> * [config.trgfn_tipi_titolo_iva_tipi_soggetto_dettaglio_guard_ritiro](/dbzero/config/funzioni/trgfn_tipi_titolo_iva_tipi_soggetto_dettaglio_guard_ritiro) — il guard del ritiro, che la chiama

---

### 🎯 Scopo Principale

`anagrafiche.fn_titolo_iva_vigente_su_natura_esiste` dice se esiste un titolo IVA in vigore di un certo tipo su un
soggetto di una certa natura. Risponde solo sì o no, e gira sopra la RLS dei titoli.

---

### Perché la usa il ritiro di matrice

Una riga della matrice che smette di ammettere un tipo per una natura non si ritira finché ci sono titoli in vigore
che la usano: il guard del ritiro fa questa domanda. Una riga di configurazione vale per tutte le aziende, quindi
la risposta deve contare i titoli presentati a qualunque emittente, anche fuori dal perimetro di chi modifica la
matrice. La funzione gira coi privilegi del proprietario per questo, e non dice quale titolo né di chi.

---

{% include-markdown "it/dbzero/anagrafiche/_titolo-iva-per-natura.md" %}

---

{% include-markdown "signature-core.md" %}
