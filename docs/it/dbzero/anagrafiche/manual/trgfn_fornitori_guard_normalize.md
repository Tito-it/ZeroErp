## 📘 Documentazione Concettuale – Trigger function `anagrafiche.trgfn_fornitori_guard_normalize`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.fornitori](/dbzero/anagrafiche/tabelle/fornitori) — la tabella su cui è agganciata

---

### 🎯 Scopo Principale

`anagrafiche.trgfn_fornitori_guard_normalize` tiene coerente la ritenuta d'acconto del fornitore a ogni
salvataggio: con la ritenuta serve un'aliquota, senza ritenuta l'aliquota non c'è.

---

### La ritenuta e la sua aliquota

* Con la ritenuta (`ritenuta_acconto` vero) l'aliquota dev'essere maggiore di zero: altrimenti il salvataggio è
  rifiutato con `E_FORNITORI_RITENUTA_ALIQUOTA_OBBLIGATORIA`, sul campo `ritenuta_aliquota`.
* Senza la ritenuta (falsa o non indicata) l'aliquota si svuota: un valore rimasto da prima non resta appeso.

Il tetto dell'aliquota (fino a 100) è un vincolo della tabella, non di questo trigger.

---

### Scatta a ogni scrittura

Il trigger scatta prima di ogni inserimento e di ogni modifica, qualunque colonna cambi. Il codice del fornitore lo
genera un altro trigger, `anagrafiche.trgfn_fornitori_gen_codice`.

---

### Codici errore

* `E_FORNITORI_RITENUTA_ALIQUOTA_OBBLIGATORIA` — la ritenuta senza un'aliquota maggiore di zero.

---

### Note di migrazione

* 2026-11-21 — smette di normalizzare il canale della fatturazione elettronica e la PEC del fornitore, usciti dalla
  tabella: l'instradamento è del soggetto, in `anagrafiche.dati_societari`.

---

{% include-markdown "signature-core.md" %}
