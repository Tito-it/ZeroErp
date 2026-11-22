## 📘 Documentazione Concettuale – Funzione `anagrafiche.fn_copia_indirizzo_soggetto`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.indirizzi_soggetti](/dbzero/anagrafiche/tabelle/indirizzi_soggetti) — la sorgente e le righe nuove
> * [config.azioni_riga](/dbzero/config/tabelle/azioni_riga) — l'azione `COPIA_INDIRIZZO_SOGGETTO`, con la sua vista e la sua check
>
> Approfondimento viste:
>
> * [anagrafiche.vw_indirizzi_soggetti_azioni](/dbzero/anagrafiche/views/vw_indirizzi_soggetti_azioni) — il pulsante spento, col motivo
>
> Approfondimento funzioni:
>
> * [anagrafiche.fn_check_copia_indirizzo_soggetto](/dbzero/anagrafiche/funzioni/fn_check_copia_indirizzo_soggetto) — il motivo di riga, che il verbo solleva
> * [anagrafiche.fn_indirizzo_elemento_da_riga](/dbzero/anagrafiche/funzioni/fn_indirizzo_elemento_da_riga) — l'indirizzo della sorgente
> * [anagrafiche.fn_crea_indirizzo_soggetto](/dbzero/anagrafiche/funzioni/fn_crea_indirizzo_soggetto) — la singolare, che scrive ogni riga
> * [anagrafiche.fn_tipi_indirizzo_proponibili_soggetto](/dbzero/anagrafiche/funzioni/fn_tipi_indirizzo_proponibili_soggetto) — i tipi che la dialog propone
> * [anagrafiche.fn_copia_indirizzo_soggetto_su_ruolo](/dbzero/anagrafiche/funzioni/fn_copia_indirizzo_soggetto_su_ruolo) — la copia di una riga del soggetto sul ruolo
>
> Guide:
>
> * [Gestione degli indirizzi](/guide/gestione-degli-indirizzi) — la copia nel drawer

---

### 🎯 Scopo Principale

`anagrafiche.fn_copia_indirizzo_soggetto` copia un indirizzo del soggetto in uno o più altri tipi dello stesso
soggetto, tutto o niente, e restituisce gli id delle righe nuove nell'ordine dei tipi. È il verbo di «Copia come…» sul
drawer aperto su un soggetto.

Che cosa vuol dire copiare un indirizzo, verso quale chiave e con quali rifiuti, lo dice la sezione «La copia di un
indirizzo» in fondo alla pagina.

---

### Che cosa fa questo verbo

1. **La sorgente** dev'essere un indirizzo di quel soggetto.
2. **Il motivo di riga**: solleva il primo motivo di `anagrafiche.fn_check_copia_indirizzo_soggetto`, lo stesso che la
   vista di riga mostra sul pulsante spento. Un indirizzo che non si può copiare in nessun tipo si rifiuta prima di
   guardare i tipi chiesti.
3. **Una riga per tipo**, nell'ordine dato: l'elemento della sorgente più il codice del tipo, scritto dalla singolare
   del soggetto, che ne giudica il tipo.

I tipi si indicano per codice interno.

---

### Codici errore

* `E_SCRIPT_CHIAMATA_NON_VALIDA` — manca il soggetto, l'indirizzo, o l'elenco dei tipi è vuoto.
* `E_INDIRIZZO_SOGGETTO_NON_TROVATO` — l'indirizzo non è di quel soggetto.
* `E_INDIRIZZO_COPIA_NESSUN_TIPO` — l'indirizzo non si può copiare in nessun tipo.
* Dalla singolare: `E_TIPO_INDIRIZZO_NON_TROVATO`, `E_INDIRIZZO_SOGGETTO_TIPO_GIA_PRESENTE` (anche per un tipo ripetuto
  nell'elenco), `E_TIPO_INDIRIZZO_TIPO_SOGGETTO_NON_PERMESSO`, e i guard della tabella.

---

### Test

* `db/pgtap/anagrafiche/test-copia-indirizzo-v1.sql` — la copia di un dettaglio e di un indirizzo libero, nazionale ed
  estero, con tutte le colonne della forma; il secondo tipo già presente, che non lascia scritto il primo; il tipo
  ripetuto; la sorgente di un altro soggetto; il tipo inesistente; l'elenco vuoto; gli id nell'ordine dei tipi; il verbo
  che non scrive la tabella da sé.
* `db/pgtap/script/test-rubinetto-primo-motivo-v1.sql` — il verbo fra i chiamanti del sollevamento del primo motivo.

---

### Note di migrazione

* 2026-11-15 — nasce, con la check e la vista di riga.

---

{% include-markdown "it/dbzero/anagrafiche/_copia-indirizzo.md" %}

---

{% include-markdown "signature-core.md" %}
