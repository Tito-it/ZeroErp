## 📘 Documentazione Concettuale – Funzione `dbops.fn_pgtap_crea_emittente`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.emittenti_fiscali](/dbzero/anagrafiche/tabelle/emittenti_fiscali) — la riga dell'azienda che nasce
>
> Approfondimento funzioni:
>
> * [anagrafiche.fn_crea_emittente_fiscale](/dbzero/anagrafiche/funzioni/fn_crea_emittente_fiscale) — il verbo di dominio che scrive l'emittente
> * [dbops.fn_pgtap_crea_soggetto_pg](/dbzero/dbops/funzioni/fn_pgtap_crea_soggetto_pg) — il soggetto persona giuridica
> * [dbops.fn_pgtap_crea_soggetto_ruolo](/dbzero/dbops/funzioni/fn_pgtap_crea_soggetto_ruolo) — il ruolo EF coi suoi indirizzi
> * [dbops.fn_pgtap_crea_emittente_operatore](/dbzero/dbops/funzioni/fn_pgtap_crea_emittente_operatore) — l'azienda insieme all'operatore che la vede
> * [vendite.fn_get_valuta_id](/dbzero/vendite/funzioni/fn_get_valuta_id) — la risoluzione della valuta per cui l'emittente nasce con la sua
> * [dbops.fn_pgtap_valuta](/dbzero/dbops/funzioni/fn_pgtap_valuta) — la valuta delle radici della catena, per le fixture
>
> Guide:
>
> * [Come si scrive un test pgTAP](/guide/pgtap-come-si-scrive-un-test) — le fixture dell'azienda

---

### 🎯 Scopo Principale

Un emittente fiscale nuovo per un test: il soggetto persona giuridica, il suo ruolo EF e la
riga dell'emittente, con una sigla libera e la valuta valorizzata. Torna l'id dell'emittente,
la sigla, il soggetto ruolo e il soggetto.

Da sola non basta a far lavorare un test sull'azienda: nessun operatore la ha nel perimetro.
Per quello c'è [fn_pgtap_crea_emittente_operatore](/dbzero/dbops/funzioni/fn_pgtap_crea_emittente_operatore).

---

### ⭐ L'emittente lo scrive il verbo, come l'applicazione

La riga la scrive
[anagrafiche.fn_crea_emittente_fiscale](/dbzero/anagrafiche/funzioni/fn_crea_emittente_fiscale),
che ritrova il ruolo EF già costruito dalla fixture. Nascendo dal verbo, l'emittente fa
nascere anche i propri registri di numerazione, come in produzione.

---

### ⚠️ Una sigla libera, nella forma che il vincolo ammette

La sigla è unica senza filtro sull'attivo: una sigla fissa farebbe collidere la seconda corsa
con il residuo della prima. Se il test non ne chiede una, la fixture prende la prima libera
fra `PGTR0001` e `PGTR9999`: solo maiuscole e cifre, fra 2 e 10 caratteri, come pretende il
vincolo di forma del codice. Una sigla chiesta dal test passa così com'è.

---

### ⚠️ La valuta non è un di più

La valuta di un documento si risolve lungo la catena «conto → emittente → gestore», e su un
database ricostruito nessuno dei tre la porta: il primo documento morirebbe su
`E_CONFIG_MANCANTE`. Il primo anello non basta, perché quando la risoluzione gira dentro un
trigger sull'inserimento del conto la riga del conto non è ancora visibile. Per questo
l'emittente nasce con la prima valuta a catalogo, per id, presa da
[dbops.fn_pgtap_valuta](/dbzero/dbops/funzioni/fn_pgtap_valuta): è una radice della catena, e
la valuta la dà agli altri.

---

### Codici errore

* I rifiuti del verbo di dominio, compresa la sigla già usata, che esce dal vincolo di
  unicità del codice.
* Nessuna sigla `PGTRnnnn` libera è un'eccezione senza codice, sollevata dalla fixture.

---

### Test

* `db/pgtap/anagrafiche/test-fn-crea-emittente-fiscale-v1.sql` — la fixture crea ancora
  l'emittente, con la valuta, e il suo corpo chiama il verbo invece di scrivere la tabella.

---

### Note di migrazione

* 2026-09-09 — l'emittente nasce con la valuta valorizzata.
* 2026-10-17 — la riga la scrive il verbo `anagrafiche.fn_crea_emittente_fiscale` (regola
  del 2, `brief-db-processi-accensione-per-ambiente`, 2b-1); firma e ritorno invariati.
* 2026-11-08 — la valuta la dà `dbops.fn_pgtap_valuta`, la sede comune delle fixture, invece di
  una copia della scelta.

---

{% include-markdown "it/dbzero/dbops/_fixture-pgtap.md" %}

---

{% include-markdown "signature-core.md" %}
