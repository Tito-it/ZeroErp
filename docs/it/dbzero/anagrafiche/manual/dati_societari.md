## 📘 Documentazione Concettuale – Tabella `anagrafiche.dati_societari`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.soggetti](/dbzero/anagrafiche/tabelle/soggetti) — il soggetto a cui la riga appartiene
> * [config.tipi_soggetto_dettaglio](/dbzero/config/tabelle/tipi_soggetto_dettaglio) — la natura, che dice se la riga c'è
> * [config.forme_giuridiche](/dbzero/config/tabelle/forme_giuridiche) — la forma, che dice se servono REA e capitale
> * [config.forme_giuridiche_tipi_soggetto_dettaglio](/dbzero/config/tabelle/forme_giuridiche_tipi_soggetto_dettaglio) — le forme ammesse da ogni natura
> * [config.province](/dbzero/config/tabelle/province) — la provincia d'iscrizione al REA
>
> Approfondimento viste:
>
> * [anagrafiche.vw_dati_societari](/dbzero/anagrafiche/views/vw_dati_societari) — la lettura con le decodifiche
>
> Approfondimento funzioni:
>
> * [anagrafiche.fn_scrivi_dati_societari](/dbzero/anagrafiche/funzioni/fn_scrivi_dati_societari) — la porta di scrittura
> * [anagrafiche.fn_elimina_dati_societari](/dbzero/anagrafiche/funzioni/fn_elimina_dati_societari) — la porta di eliminazione
> * [anagrafiche.fn_scrivi_dati_societari_alla_nascita](/dbzero/anagrafiche/funzioni/fn_scrivi_dati_societari_alla_nascita) — la scrittura alla nascita del soggetto
> * [anagrafiche.trgfn_dati_societari_guard_tipo_soggetto](/dbzero/anagrafiche/funzioni/trgfn_dati_societari_guard_tipo_soggetto) — la natura che ammette la riga
> * [anagrafiche.trgfn_dati_societari_guard_forma_giuridica](/dbzero/anagrafiche/funzioni/trgfn_dati_societari_guard_forma_giuridica) — la forma, il REA e il capitale
> * [anagrafiche.trgfn_dati_societari_guard_canale_fe](/dbzero/anagrafiche/funzioni/trgfn_dati_societari_guard_canale_fe) — il canale della fattura elettronica
> * [anagrafiche.trgfn_soggetti_guard_dati_societari_required](/dbzero/anagrafiche/funzioni/trgfn_soggetti_guard_dati_societari_required) — la riga pretesa dalla natura, al COMMIT
> * [anagrafiche.trgfn_soggetti_guard_forma_giuridica_natura](/dbzero/anagrafiche/funzioni/trgfn_soggetti_guard_forma_giuridica_natura) — la forma al cambio di natura, al COMMIT
> * [script.trgfn_storico_generic](/dbzero/script/funzioni/trgfn_storico_generic) — lo storico della riga
>
> Guide:
>
> * [Soggetti e ruoli anagrafici](/guide/soggetti-e-ruoli-anagrafici) — il soggetto nel suo insieme

---

### 🎯 Scopo Principale

`anagrafiche.dati_societari` tiene i dati societari di un soggetto: forma giuridica, iscrizione al REA,
capitale sociale, socio unico, liquidazione, canale e recapito della fattura elettronica, data di
costituzione. Un soggetto ha al più una riga (`uq_ds_soggetto`), e la riga se ne va col soggetto quando questo si
cancella.

Stanno a parte perché non tutte le nature li hanno: un privato no, una società di capitali sempre, una ditta
individuale o un ente a scelta.

---

### Il significato delle colonne che il nome non dice

* **`socio_unico`**: `SU` socio unico, `SM` più soci. **`liquidazione`**: `LN` non in liquidazione, `LS` in
  liquidazione. Sono obbligatorie; chi scrive col verbo e non le passa riceve il valore proposto dai parametri
  di sessione, non il default della colonna.
* **`id_prov_iscri_rea`** e **`iscrizione_rea`**: provincia e numero dell'iscrizione al REA. Vanno in coppia,
  o tutti e due o nessuno (`chk_dati_societari_rea_coppia`), e la coppia è unica (`uq_ds_prov_cea`): due
  soggetti non hanno lo stesso REA nella stessa provincia.
* **`destinatario_fe`**: il **canale** della fattura elettronica, `P` via PEC, `C` via codice SDI, vuoto
  nessun canale (un cliente estero, o uno di cui non si sa ancora). **`pec_fatturazione`** e **`codice_sdi`**
  sono i due recapiti. Il codice è quello che il Sistema di Interscambio assegna: sei caratteri per una
  pubblica amministrazione, sette per gli altri.
* **`capitale_sociale`**: in euro; un valore infinito non entra (`chk_dati_societari_capitale_sociale_finito`).

---

### ⭐ La riga la chiede la natura, il contenuto la forma

Nessuna colonna di contenuto è obbligatoria per tutti, salvo la forma: REA e capitale li pretende o li vieta
la forma giuridica, la riga stessa la pretende o la vieta la natura del soggetto. Il blocco in fondo alla
pagina racconta i tre livelli e chi li controlla.

---

### Lo storico conserva ogni versione

La tabella è nel registro dello storico: ogni modifica e ogni cancellazione lasciano la versione precedente
nello storico, e il flag `storicizza` non si spegne. Una riga eliminata col suo verbo si ritrova lì.

---

### ⚠️ Che cosa oggi non copre

* **Una società di capitali non si spegne.** Il soggetto non si disattiva finché ha la sua riga di dati
  societari (`trg_soggetti_a10_dati_societari_block_deact_upd`, `E_ATTIVO_BLOCK_CHILDREN_EXIST`), e la tabella
  non ha una colonna `attivo` da spegnere al suo posto. Per una natura che la riga la pretende, la riga non si
  elimina (`E_DATI_SOCIETARI_NON_ELIMINABILI`): la disattivazione del soggetto resta senza strada.
* **La cancellazione diretta non guarda la natura.** Il controllo «la natura la pretende» sta nel verbo di
  eliminazione e nel guard al COMMIT su `anagrafiche.soggetti`, che scatta quando si scrive il soggetto, non
  quando si cancella la riga. Chi cancella la riga senza il verbo (il proprietario: l'applicazione non ha
  `DELETE`) lascia una società senza dati societari, e il rifiuto arriva solo alla prossima scrittura del
  soggetto.

---

### Test

* `db/pgtap/anagrafiche/test-fn-scrivi-dati-societari-v1.sql` — la porta (l'applicazione legge e non scrive),
  le colonne nullable e la forma obbligatoria, la forma, REA e capitale, il cambio di natura.
* `db/pgtap/anagrafiche/test-dati-societari-policy.sql` — la natura che vieta, ammette o pretende la riga.
* `db/pgtap/anagrafiche/test-dati-societari-canale-fe-v1.sql` — il canale e i suoi recapiti.
* `db/pgtap/anagrafiche/test-fn-elimina-dati-societari-v1.sql` — l'eliminazione e lo storico sempre acceso.
* `db/pgtap/anagrafiche/test-dati-societari-alla-nascita-v1.sql` — la riga alla nascita del soggetto.

---

### Note di migrazione

* 2026-10-10 — il codice SDI e la PEC smettono di essere unici: un secondo cliente dello stesso intermediario
  veniva rifiutato. Il canale `destinatario_fe` diventa `P` / `C` / nessuno, col suo guard.
* 2026-10-10 — REA e capitale diventano nullable e li decide la forma: prima erano obbligatori per tutti, e un
  ente o una ditta con dati societari non si potevano scrivere. La forma diventa obbligatoria il giorno dopo.
* 2026-10-11 — l'applicazione perde la scrittura diretta: la porta è `anagrafiche.fn_scrivi_dati_societari`.
* 2026-11-14 — nasce `anagrafiche.fn_elimina_dati_societari`, per il cambio da una ditta a un privato.

---

{% include-markdown "it/dbzero/anagrafiche/_dati-societari.md" %}

---

{% include-markdown "signature-core.md" %}
