## 📘 Documentazione Concettuale – Funzione `anagrafiche.fn_crea_emittente_fiscale`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.emittenti_fiscali](/dbzero/anagrafiche/tabelle/emittenti_fiscali) — la riga che crea, con le regole della sigla e del regime
> * [anagrafiche.soggetti_ruoli](/dbzero/anagrafiche/tabelle/soggetti_ruoli) — il ruolo `EF` del soggetto
>
> Approfondimento funzioni:
>
> * [script.fn_get_or_create_soggetto_ruolo](/dbzero/script/funzioni/fn_get_or_create_soggetto_ruolo) — il ruolo, creato se manca
> * [script.fn_scrivi_riga_da_jsonb](/dbzero/script/funzioni/fn_scrivi_riga_da_jsonb) — la scrittura della riga dai campi
> * [vendite.trgfn_emittenti_fiscali_provision_registri](/dbzero/vendite/funzioni/trgfn_emittenti_fiscali_provision_registri) — i registri di numerazione che nascono con l'emittente
> * [anagrafiche.trgfn_emittenti_fiscali_default_bootstrap](/dbzero/anagrafiche/funzioni/trgfn_emittenti_fiscali_default_bootstrap) — il primo emittente diventa la predefinita

---

### 🎯 Scopo Principale

`anagrafiche.fn_crea_emittente_fiscale` fa di un soggetto un emittente fiscale in un'operazione sola: il ruolo
`EF` del soggetto, creato se manca, e la riga dell'emittente. Restituisce l'`id` dell'emittente e il suo ruolo.

---

### La sede unica della creazione

La usano il backend dalla pagina degli emittenti, il builder dei pgTAP (`dbops.fn_pgtap_crea_emittente`) e il
provisioning dei dati di sviluppo (`anagrafiche.fn_provisiona_dati_di_sviluppo`). Nascendo, l'emittente fa
nascere da sé, per trigger, i suoi registri di numerazione e, se è il primo, la riga dell'azienda predefinita.

---

### I campi

Oltre al soggetto e alla sigla, sono facoltativi `attivo`, `regime_fiscale_rf`, `bollo_auto`, `bollo_soglia`,
`rounding_policy` e `valuta_id`; quelli assenti prendono il default della colonna. Un campo diverso è rifiutato
col suo nome (`E_CAMPO_NON_AMMESSO`), comprese le due colonne della conferma del regime, che scrive il database.
Se i campi non sono un oggetto, la chiamata è rifiutata con `E_SCRIPT_CHIAMATA_NON_VALIDA`.

**Un regime indicato è un regime confermato.** Il default `RF01` e un `RF01` scelto sarebbero la stessa riga:
chi indica il regime lo dichiara, e la funzione lo conferma (data e autore). Senza regime l'emittente nasce con
`RF01` da confermare, e compare fra i regimi che nessuno ha dichiarato.

---

### Che cosa non controlla

* **La partita IVA del soggetto**: la controlla il backend prima di chiamare, e nessun guard sulla tabella la
  pretende.
* **Il permesso**: nel dominio anagrafiche lo decide il backend.
* **I duplicati e il regime fuori catalogo**: escono dai vincoli della tabella col loro nome (`uq:codice` per la
  sigla già usata, `uq_emittenti_fiscali_ruolo` per un secondo emittente sullo stesso soggetto, la FK sul
  catalogo dei regimi). La forma della sigla la giudica il suo guard.

---

### Codici errore

* `E_CAMPO_NON_AMMESSO` — un campo fuori elenco, col nome nel contesto.
* `E_SCRIPT_CHIAMATA_NON_VALIDA` — i campi non sono un oggetto.

---

### Test

* `db/pgtap/anagrafiche/test-fn-crea-emittente-fiscale-v1.sql` — la creazione col ruolo `EF`, i default e il
  regime non confermato, il regime dichiarato che si conferma, i registri, i rifiuti dei campi, i due duplicati,
  e il builder dei pgTAP che chiama la funzione invece di scrivere la tabella.

---

### Note di migrazione

* 2026-10-17 — nasce, e prende il posto della creazione in più passi del backend e degli inserimenti diretti
  delle fixture.

---

{% include-markdown "signature-core.md" %}
