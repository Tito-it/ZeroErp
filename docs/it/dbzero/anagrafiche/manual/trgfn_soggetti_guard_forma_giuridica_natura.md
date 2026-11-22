## 📘 Documentazione Concettuale – Trigger function `anagrafiche.trgfn_soggetti_guard_forma_giuridica_natura`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.soggetti](/dbzero/anagrafiche/tabelle/soggetti) — la tabella su cui è montato
> * [anagrafiche.dati_societari](/dbzero/anagrafiche/tabelle/dati_societari) — la forma giuridica del soggetto
> * [config.forme_giuridiche_tipi_soggetto_dettaglio](/dbzero/config/tabelle/forme_giuridiche_tipi_soggetto_dettaglio) — quali forme ammette ogni natura
>
> Approfondimento funzioni:
>
> * [anagrafiche.fn_forma_giuridica_ammessa](/dbzero/anagrafiche/funzioni/fn_forma_giuridica_ammessa) — la domanda «la natura ammette la forma?»
> * [anagrafiche.trgfn_dati_societari_guard_forma_giuridica](/dbzero/anagrafiche/funzioni/trgfn_dati_societari_guard_forma_giuridica) — lo stesso controllo quando si scrive la forma
> * [anagrafiche.fn_scrivi_dati_societari](/dbzero/anagrafiche/funzioni/fn_scrivi_dati_societari) — il verbo che scrive i dati societari

---

### 🎯 Scopo Principale

`anagrafiche.trgfn_soggetti_guard_forma_giuridica_natura` controlla, alla conferma della transazione, che la
natura del soggetto ammetta la forma giuridica dei suoi dati societari. È il lato «cambia la natura» di una
regola che ha anche il lato «cambia la forma».

---

### Una regola, due guard

Che una natura ammetta una forma lo dice una sola funzione, `anagrafiche.fn_forma_giuridica_ammessa`, sulla
matrice delle forme per natura, nel giorno operativo. La chiamano due guard, uno per ciascuna delle due cose
che possono cambiare:

* quando si scrivono i dati societari, il guard della forma (`anagrafiche.trgfn_dati_societari_guard_forma_giuridica`),
  **immediato**, confronta la forma con la natura salvata del soggetto;
* quando cambia la natura del soggetto, questo guard, **al COMMIT**.

---

### ⭐ Prima la natura, poi la forma

Natura e forma si cambiano insieme: una società di capitali che diventa società di persone deve lasciare la
forma di una società di capitali. Il guard è differito apposta: dentro la transazione si cambia prima la
natura, poi la forma, e alla conferma si giudica lo stato finale. L'ordine inverso non passa: la forma
scritta per prima si confronta, subito, con la natura che il soggetto ha ancora.

Alla conferma il guard rilegge le due tabelle, non la riga del trigger: vede la forma scritta dopo il cambio.

Tace quando il soggetto non ha dati societari, o non ha natura. Una natura nuova che non ha dati societari
non arriva qui con la riga ancora presente: la regola del cambio di natura la ferma prima.

---

{% include-markdown "it/dbzero/anagrafiche/_cambio-di-natura.md" %}

---

### Codici errore

* `E_TIPO_SOGGETTO_FORMA_GIURIDICA_NON_AMMESSA` — la natura del soggetto non ammette la forma dei suoi dati
  societari; la frase nomina la natura e la forma, e il campo evidenziato è la forma.

---

### Test

* `db/pgtap/anagrafiche/test-fn-scrivi-dati-societari-v1.sql` — da società di capitali a società di persone:
  senza cambiare la forma il rifiuto arriva alla conferma, cambiando la forma nella stessa transazione passa,
  e nell'ordine inverso (prima la forma) il rifiuto è immediato.

---

### Note di migrazione

* 2026-10-10 — nasce con la forma giuridica come riferimento al catalogo delle forme ammesse per natura
  (`brief-db-dati-fiscali-e-societari-del-soggetto`).
* 2026-11-14 — il cambio fra macro-tipologie (una società che diventa ente), che il test del guard usava come
  caso, è rifiutato prima dalla regola del cambio di natura: il caso diventa il passaggio fra due nature di
  società.

---

{% include-markdown "signature-core.md" %}
