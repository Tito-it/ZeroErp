## 📘 Documentazione Concettuale – Trigger function `anagrafiche.trgfn_soggetti_titoli_iva_guard_coerenza`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.soggetti_titoli_iva](/dbzero/anagrafiche/tabelle/soggetti_titoli_iva) — i titoli su cui è montata
> * [config.tipi_titolo_iva](/dbzero/config/tabelle/tipi_titolo_iva) — il tipo, che dice se il titolo ha un tetto
> * [anagrafiche.soggetti_titoli_iva_ambiti](/dbzero/anagrafiche/tabelle/soggetti_titoli_iva_ambiti) — le righe di ambito che conta
>
> Approfondimento funzioni:
>
> * [anagrafiche.fn_check_titolo_iva_ambito](/dbzero/anagrafiche/funzioni/fn_check_titolo_iva_ambito) — le regole dell'ambito, comprese le righe su un titolo totale

---

### 🎯 Scopo Principale

`anagrafiche.trgfn_soggetti_titoli_iva_guard_coerenza` tiene le due regole del titolo IVA che un controllo di
colonna non può scrivere, perché guardano fuori dalla riga: il plafond c'è se e solo se il tipo ne prevede uno, e
un titolo che vale per tutto non ha righe di ambito.

---

### ⭐ Il plafond vale sui due versi

Il tipo dice se il titolo ha un tetto che si consuma (`config.tipi_titolo_iva.ha_plafond`), la riga porta il
valore. Il guard rifiuta i due errori:

* **tipo con tetto, plafond assente** (`E_TITOLO_IVA_PLAFOND_MANCANTE`): la funzione di consumo non avrebbe una
  capienza con cui confrontarsi;
* **tipo senza tetto, plafond presente** (`E_TITOLO_IVA_PLAFOND_NON_AMMESSO`): un numero che nessuno consuma, e che
  chi lo legge scambia per un limite. È il verso che si dimentica.

Scatta alla nascita del titolo e quando cambiano il tipo, il plafond o l'ambito. Se il tipo non esiste tace: lo
dice la chiave esterna, che ha la sua voce.

---

### Un titolo riportato a «tutto» con le righe di ambito

Il caso «vale per tutto e ha un elenco di voci» si crea in due modi. Aggiungere una riga di ambito a un titolo
totale lo ferma il guard sulle righe. Riportare a `TUTTO` un titolo che le righe le ha già lo ferma questo, in
aggiornamento, con `E_TITOLO_IVA_AMBITO_NON_AMMESSO`: le righe esistono già, e nessuno le tocca.

Conta le righe coi permessi di chi scrive, ed è sufficiente: le righe di ambito sono visibili alle stesse
condizioni del loro titolo, quindi chi scrive il titolo le vede tutte.

---

### Parla per primo, perché è prima della scrittura

Il guard gira prima che la riga sia scritta. Le chiavi esterne e i controlli dei padri attivi (il tipo, il codice
IVA, il soggetto, l'emittente) girano dopo, e quelli dei padri attivi solo alla conferma dell'operazione: su una
riga che sbaglia in tutti e due i modi, il messaggio che l'operatore legge è questo, quello di dominio. Lo decide il
momento in cui scattano, non l'ordine dei nomi, che conta solo fra trigger dello stesso momento.

---

### ⚠️ Che cosa oggi non copre

* **La regola «tutto non ha righe di ambito» è scritta due volte.** Questo guard la conta da sé; la stessa regola è
  il primo motivo di `anagrafiche.fn_check_titolo_iva_ambito`, che il guard sul titolo chiama dopo la scrittura
  quando cambia l'ambito. Sul cambio di ambito parla sempre questo, che viene prima; ma le due copie possono
  divergere senza che nessun test se ne accorga.

---

### Codici errore

* `E_TITOLO_IVA_PLAFOND_MANCANTE` — tipo con tetto, plafond assente.
* `E_TITOLO_IVA_PLAFOND_NON_AMMESSO` — tipo senza tetto, plafond presente.
* `E_TITOLO_IVA_AMBITO_NON_AMMESSO` — titolo riportato a «tutto» con righe di ambito.

---

### Test

* `db/pgtap/anagrafiche/test-soggetti-titoli-iva.sql` — il plafond mancante, quello di troppo, il titolo ben formato
  che si registra.

---

{% include-markdown "signature-core.md" %}
