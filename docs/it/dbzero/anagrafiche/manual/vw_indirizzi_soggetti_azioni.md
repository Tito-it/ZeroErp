## 📘 Documentazione Concettuale – Vista `anagrafiche.vw_indirizzi_soggetti_azioni`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.indirizzi_soggetti](/dbzero/anagrafiche/tabelle/indirizzi_soggetti) — una riga della vista per ogni indirizzo
> * [config.azioni_riga](/dbzero/config/tabelle/azioni_riga) — il registro che la nomina superficie di `COPIA_INDIRIZZO_SOGGETTO`
>
> Approfondimento viste:
>
> * [anagrafiche.vw_indirizzi_resolved_soggetto](/dbzero/anagrafiche/views/vw_indirizzi_resolved_soggetto) — le colonne dell'indirizzo, che qui non ci sono
>
> Approfondimento funzioni:
>
> * [anagrafiche.fn_check_copia_indirizzo_soggetto](/dbzero/anagrafiche/funzioni/fn_check_copia_indirizzo_soggetto) — il motivo che la vista mostra
> * [anagrafiche.fn_copia_indirizzo_soggetto](/dbzero/anagrafiche/funzioni/fn_copia_indirizzo_soggetto) — il verbo che lo solleva
>
> Guide:
>
> * [Gestione degli indirizzi](/guide/gestione-degli-indirizzi) — la copia nel drawer

---

### 🎯 Scopo Principale

`anagrafiche.vw_indirizzi_soggetti_azioni` dice, per ogni indirizzo di un soggetto, se l'azione «Copia come…» è spenta
e perché. È la superficie dell'azione `COPIA_INDIRIZZO_SOGGETTO` nel registro `config.azioni_riga`.

---

### Due colonne per il pulsante

* `copia_blocco_reason` è il motivo, e `copia_blocco_reason_key` la sua chiave di traduzione: il primo motivo di
  `anagrafiche.fn_check_copia_indirizzo_soggetto`. Vuote, la copia si può proporre.
* L'unico motivo oggi è `NESSUN_TIPO_PROPONIBILE`: il soggetto ha già tutti i tipi che la sua natura ammette.

La vista porta solo la chiave della riga (l'indirizzo e il soggetto): le colonne dell'indirizzo stanno in
`anagrafiche.vw_indirizzi_resolved_soggetto`, dove l'indirizzo è `indirizzo_id`. Si filtra per soggetto o per indirizzo.

⭐ Il motivo non si calcola qui: la vista chiama la stessa check che il verbo solleva, e il registro delle azioni lega le
tre cose. Il pulsante spento e l'errore del verbo dicono la stessa frase.

---

### Dove si usa, e dove no

* **Nel drawer del soggetto**: le righe del soggetto si copiano sul soggetto, e il pulsante si spegne da qui.
* **Nel drawer del ruolo**: le righe del soggetto in cascata si copiano sul ruolo, con
  `anagrafiche.fn_copia_indirizzo_soggetto_su_ruolo`, e questa vista non conta. Lì la copia si spegne insieme ad
  «Aggiungi», dal picker della chiave aperta.

La vista gira coi permessi di chi legge: vede gli indirizzi che la sua sicurezza di riga gli mostra.

---

### Test

* `db/pgtap/anagrafiche/test-copia-indirizzo-v1.sql` — la copia proponibile finché manca un tipo, e il motivo
  `NESSUN_TIPO_PROPONIBILE` quando ci sono tutti.
* `db/pgtap/config/test-azioni-riga-registro-v1.sql` — il registro: la vista, le due colonne, la check e il verbo
  esistono, la vista dipende dalla check e il verbo la chiama.

---

### Note di migrazione

* 2026-11-15 — nasce, col verbo della copia e la sua check.

---

{% include-markdown "it/dbzero/anagrafiche/_copia-indirizzo.md" %}

---

{% include-markdown "signature-core.md" %}
