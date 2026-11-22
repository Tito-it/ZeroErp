## 📘 Documentazione Concettuale – Funzione `anagrafiche.fn_check_copia_indirizzo_soggetto`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.indirizzi_soggetti](/dbzero/anagrafiche/tabelle/indirizzi_soggetti) — l'indirizzo giudicato
> * [config.azioni_riga](/dbzero/config/tabelle/azioni_riga) — l'azione `COPIA_INDIRIZZO_SOGGETTO`, che nomina questa check
>
> Approfondimento viste:
>
> * [anagrafiche.vw_indirizzi_soggetti_azioni](/dbzero/anagrafiche/views/vw_indirizzi_soggetti_azioni) — la vista di riga che ne mostra il motivo
>
> Approfondimento funzioni:
>
> * [anagrafiche.fn_copia_indirizzo_soggetto](/dbzero/anagrafiche/funzioni/fn_copia_indirizzo_soggetto) — il verbo che ne solleva il motivo
> * [anagrafiche.fn_tipi_indirizzo_proponibili_soggetto](/dbzero/anagrafiche/funzioni/fn_tipi_indirizzo_proponibili_soggetto) — il picker da cui legge
>
> Guide:
>
> * [Gestione degli indirizzi](/guide/gestione-degli-indirizzi) — la copia nel drawer

---

### 🎯 Scopo Principale

`anagrafiche.fn_check_copia_indirizzo_soggetto` dice perché un indirizzo del soggetto non si può copiare in nessun
tipo: un elenco ordinato di motivi, vuoto se la copia si può proporre. È il motivo di riga dell'azione «Copia come…»
nel drawer del soggetto.

---

### Un motivo solo: nessun tipo in cui copiarlo

L'indirizzo non si può copiare quando il picker del soggetto, `anagrafiche.fn_tipi_indirizzo_proponibili_soggetto`, non
ha nessun tipo ammesso: il soggetto ha già tutti i tipi che la sua natura ammette. Il motivo è `NESSUN_TIPO_PROPONIBILE`,
col codice `E_INDIRIZZO_COPIA_NESSUN_TIPO` e la chiave `anagrafiche.indirizzi.copia_blocco.nessun_tipo_proponibile`,
senza valori.

⭐ La check non ripete la regola del tipo: la legge dal picker, che a sua volta legge la check della madre singolare.
Ciò che il pulsante spento dice, ciò che la dialog propone e ciò che la singolare rifiuta sono la stessa regola.

Il motivo dipende dal soggetto, non dalla riga: tutti gli indirizzi dello stesso soggetto hanno lo stesso esito. Resta
di riga perché il pulsante sta sulla card di ogni indirizzo, e la vista è la superficie che il registro delle azioni
prevede.

---

### Chi la legge

* **Il verbo** `anagrafiche.fn_copia_indirizzo_soggetto`, che ne solleva il primo motivo prima di scrivere.
* **La vista di riga** `anagrafiche.vw_indirizzi_soggetti_azioni`, che ne mostra il primo motivo sul pulsante.

Il tooltip e l'errore non possono dire due cose diverse: la check è una, e il registro `config.azioni_riga` la lega
alla vista e al verbo.

---

### Codici errore

* `E_SCRIPT_CHIAMATA_NON_VALIDA` — manca l'indirizzo.
* `E_INDIRIZZO_SOGGETTO_NON_TROVATO` — l'indirizzo non esiste.
* `E_INDIRIZZO_COPIA_NESSUN_TIPO` — il motivo che la check restituisce, e che il verbo solleva.

---

### Test

* `db/pgtap/anagrafiche/test-copia-indirizzo-v1.sql` — la copia proponibile finché manca un tipo, il pulsante spento
  col motivo `NESSUN_TIPO_PROPONIBILE` quando ci sono tutti.
* `db/pgtap/script/test-rubinetto-primo-motivo-v1.sql` — il verbo che ne solleva il primo motivo.

---

### Note di migrazione

* 2026-11-15 — nasce, col verbo e la vista di riga.

---

{% include-markdown "it/dbzero/anagrafiche/_copia-indirizzo.md" %}

---

{% include-markdown "signature-core.md" %}
