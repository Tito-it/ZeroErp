## 📘 Documentazione Concettuale – Funzione `vendite.fn_listini_attivi_uom_non_convertibili`

> **Ultimo aggiornamento**: 10 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento funzioni:
>
> * [catalogo.trgfn_uom_guard_listini_attivi](/dbzero/catalogo/funzioni/trgfn_uom_guard_listini_attivi) — il guard che la legge
> * [catalogo.fn_uom_primo_giorno_non_convertibile](/dbzero/catalogo/funzioni/fn_uom_primo_giorno_non_convertibile) — la regola del periodo

---

### 🎯 Scopo Principale

Elenca i prezzi delle versioni di listino ATTIVE in un'unità che, con le conversioni di adesso, in
un giorno del periodo non si converte per l'articolo: quelli che una chiusura nel catalogo lascia
scoperti. Per la mappatura si filtra su articolo e unità; per la conversione generale su una delle
due unità, per gli articoli la cui base è l'altra.

---

### Il perimetro

`SECURITY DEFINER`: il catalogo è comune, i listini sono per azienda. Una riga fuori dal perimetro di
chi chiama esce col solo primo giorno scoperto e `nel_perimetro = false`; gli identificativi
restano vuoti. La regola del perimetro è quella della policy delle righe di listino.

---

### Test

* `db/pgtap/vendite/test-listino-uom-periodo-v1.sql` — una riga nel perimetro, una di un'altra azienda.

---

### Note di migrazione

* 2026-11-10 — nasce (brief-db-revisione-catalogo, giro 2-bis).

---

{% include-markdown "signature-core.md" %}
