## 📘 Documentazione Concettuale – Funzione `anagrafiche.fn_crea_fornitore`

> **Ultimo aggiornamento**: 23 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.fornitori](/dbzero/anagrafiche/tabelle/fornitori) — la scheda che la funzione scrive
> * [anagrafiche.soggetti_ruoli](/dbzero/anagrafiche/tabelle/soggetti_ruoli) — il ruolo `FO`, creato se manca
> * [config.stati_fornitore](/dbzero/config/tabelle/stati_fornitore) — lo stato iniziale «in verifica»
>
> Approfondimento funzioni:
>
> * [script.fn_guard_campi_ammessi](/dbzero/script/funzioni/fn_guard_campi_ammessi) — il guard che rifiuta la chiave fuori elenco (`E_CAMPO_NON_AMMESSO`)
> * [script.fn_get_or_create_soggetto_ruolo](/dbzero/script/funzioni/fn_get_or_create_soggetto_ruolo) — il ruolo del soggetto, nuovo o esistente
> * [anagrafiche.fn_crea_contatto](/dbzero/anagrafiche/funzioni/fn_crea_contatto) — il contatto del ruolo
> * [anagrafiche.fn_crea_indirizzi_ruolo](/dbzero/anagrafiche/funzioni/fn_crea_indirizzi_ruolo) — gli indirizzi del ruolo, coi tipi obbligatori copiati
>
> Guide:
>
> * [Soggetti e ruoli anagrafici](/guide/soggetti-e-ruoli-anagrafici) — il soggetto, i ruoli e le loro specializzazioni

---

### 🎯 Scopo Principale

`anagrafiche.fn_crea_fornitore` fa di un soggetto un fornitore in un'operazione sola: il ruolo fornitore (creato se
manca), la scheda del fornitore, il suo contatto e i suoi indirizzi. Restituisce il fornitore e il suo ruolo.

È la sede unica della creazione: la usano l'applicazione, i pgTAP e il provisioning dei dati di sviluppo.

---

### I campi della scheda

* **Facoltativi**: il codice, valuta, modalità e termine di pagamento, ritenuta d'acconto e aliquota, regime fiscale
  (`regime_fiscale_rf`, un codice del catalogo dei regimi), rating, scadenza della qualifica, note. Un campo assente
  o a null prende il default della colonna; senza codice lo genera il trigger della tabella.
* **Un campo fuori elenco è rifiutato** col suo nome (`E_CAMPO_NON_AMMESSO`). Lo sono anche lo split payment e
  l'instradamento della fatturazione elettronica, che sono del soggetto, e le condizioni di pagamento (giorni, fine
  mese), che sono del termine.
* **Lo stato non è un campo**: un fornitore nasce sempre **in verifica** (`VE`). Qualificarlo è un passaggio di stato
  successivo.

---

### Il ruolo, il contatto, gli indirizzi

* **Il ruolo**: se il soggetto ha già il ruolo fornitore, lo riusa; altrimenti lo crea.
* **Il contatto**: facoltativo. Se c'è, valgono le regole del contatto (nominativo e tipo obbligatori).
* **Gli indirizzi**: un elenco, anche vuoto. Basta il primo: gli altri tipi obbligatori per un fornitore si copiano
  da lui. La sede legale sul ruolo è facoltativa: l'indirizzo fiscale sta sul soggetto, e un privato fornitore non ne
  ha una. Se il ruolo esisteva già, i tipi che ha non si riscrivono.

---

### Quando si controlla la completezza

Un fornitore senza gli indirizzi obbligatori è rifiutato **alla conferma**, non subito: il ruolo e i suoi indirizzi
nascono nella stessa transazione.

---

### Che cosa non controlla

* **Il permesso**: nel dominio anagrafiche lo decide l'applicazione. La funzione gira coi permessi di chi la chiama.
* **I doppioni e i riferimenti**: un secondo fornitore sullo stesso soggetto (`uq_fornitori_soggetto_ruolo_id`), un
  codice già usato (`uq_fornitori_codice`) e un regime fuori catalogo (`fk_fornitori_regimi_fiscali`) escono dai
  vincoli della tabella, col loro nome.

---

### Codici errore

* `E_SCRIPT_CHIAMATA_NON_VALIDA` — il soggetto non è passato, o i campi non sono un oggetto.
* `E_CAMPO_NON_AMMESSO` — un campo fuori elenco, col suo nome.

Contatto e indirizzi rifiutano coi codici delle loro funzioni.

---

### Test

* `db/pgtap/anagrafiche/test-fn-crea-fornitore-v1.sql` — il caso felice (ruolo nuovo, contatto, un indirizzo, i
  tipi obbligatori copiati e la completezza al commit), il ruolo riusato, il codice generato anche con la chiave a
  null; i rifiuti: lo stato fra i campi, il soggetto mancante, il contatto incompleto, il secondo fornitore sullo
  stesso soggetto, le chiavi dei doppioni ritirati.

---

### Note di migrazione

* 2026-10-18 — nasce come sede unica della creazione del fornitore.
* 2026-11-21 — escono dai campi ammessi lo split payment e l'instradamento della fatturazione elettronica, passati
  al soggetto, e il regime fiscale prende il nome `regime_fiscale_rf`.

---

{% include-markdown "signature-core.md" %}
