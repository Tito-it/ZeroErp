## 📘 Documentazione Concettuale – Tabella `anagrafiche.emittenti_fiscali`

> **Ultimo aggiornamento**: 26 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.soggetti_ruoli](/dbzero/anagrafiche/tabelle/soggetti_ruoli) — il ruolo `EF` che l'emittente è
> * [anagrafiche.emittenti_fiscali_billing_account](/dbzero/anagrafiche/tabelle/emittenti_fiscali_billing_account) — per quale azienda fattura ciascun billing account, e la predefinita
> * [anagrafiche.emittenti_fiscali_utilities](/dbzero/anagrafiche/tabelle/emittenti_fiscali_utilities) — i parametri d'importo dell'azienda per una utility
> * [config.regimi_fiscali](/dbzero/config/tabelle/regimi_fiscali) — il catalogo dei regimi fiscali
> * [dbops.automazione_attivo_eccezioni](/dbzero/dbops/tabelle/automazione_attivo_eccezioni) — le tabelle figlie che non fermano lo spegnimento, con il motivo
>
> Approfondimento funzioni:
>
> * [anagrafiche.fn_crea_emittente_fiscale](/dbzero/anagrafiche/funzioni/fn_crea_emittente_fiscale) — la porta di creazione
> * [anagrafiche.trgfn_emittenti_fiscali_guard_codice_forma](/dbzero/anagrafiche/funzioni/trgfn_emittenti_fiscali_guard_codice_forma) — la forma della sigla
> * [anagrafiche.trgfn_emittenti_fiscali_regime_conferma](/dbzero/anagrafiche/funzioni/trgfn_emittenti_fiscali_regime_conferma) — chi dichiara il regime, e quando
> * [dbops.trgfn_prevent_deactivate_if_children](/dbzero/dbops/funzioni/trgfn_prevent_deactivate_if_children) — i trigger che vietano lo spegnimento
>
> Guide:
>
> * [Soggetti e ruoli anagrafici](/guide/soggetti-e-ruoli-anagrafici) — il soggetto e i suoi ruoli
> * [Gli emittenti fiscali](/guide/emittenti-fiscali) — come nasce un emittente, gli operatori assegnati, l'emittente di lavoro

---

### 🎯 Scopo Principale

`anagrafiche.emittenti_fiscali` è l'elenco delle aziende per cui l'installazione emette documenti: ogni riga è
il ruolo di emittente fiscale (`EF`) di un soggetto, con la sigla, il regime fiscale e le impostazioni generali
dell'emissione.

La tabella non dice per quale azienda fattura un cliente: lo dice
`anagrafiche.emittenti_fiscali_billing_account`, che tiene anche l'azienda predefinita.

---

### L'emittente è il ruolo di un soggetto

`soggetto_ruolo_id` è l'identità dell'emittente: un emittente per ruolo (`uq_emittenti_fiscali_ruolo`) e un ruolo
che deve essere di tipo `EF`, che verifica `anagrafiche.trgfn_emittenti_fiscali_guard_ruolo_emi_fis`. La colonna
non cambia dopo la nascita: la blocca il lock di colonna, con `E_EMITTENTE_SOGGETTO_IMMUTABILE`, e riscrivere lo
stesso valore è ammesso. Il ruolo, a sua volta, non cambia soggetto (`E_SOGGETTO_RUOLO_SOGGETTO_IMMUTABILE` su
`anagrafiche.soggetti_ruoli`): l'intera catena emittente → ruolo → soggetto è fissa. Un emittente creato sul
soggetto sbagliato si ritira e se ne crea un altro.

Molte tabelle di vendita e di pagamento nominano l'azienda col ruolo (`emittente_soggetto_ruolo_id`, con la FK
su `soggetti_ruoli`), le altre con `id` di questa tabella (`emittente_fiscale_id`). Le due chiavi dicono la
stessa azienda.

Un emittente non si cancella: lo ferma `script.trgfn_delete_block_by_guc` con `E_DELETE_NOT_ALLOWED`, salvo in
manutenzione con la GUC `zeroerp.maintenance_ruoli_delete`. Si spegne.

---

### ⭐ La sigla sta dentro i codici dei documenti

`codice` è la sigla dell'azienda: unica (`uq:codice`), da 2 a 10 caratteri fra maiuscole e cifre, e immutabile.

* **Perché ha una forma.** La sigla entra nei codici che il motore dei registri compone: la commessa è
  `CMM-<sigla>-<anno>-<progressivo>` (`vendite.fn_get_or_create_commessa`), la distinta d'incasso
  `DIS-<sigla>-<anno>-<progressivo>` (`pagamenti.trgfn_vendite_contabili_gen_codice`). Quei codici si leggono
  separando sul trattino: una sigla con un trattino li renderebbe illeggibili senza che niente lo segnali, perché
  l'unicità reggerebbe lo stesso.
* **Chi la controlla.** `anagrafiche.trgfn_emittenti_fiscali_guard_codice_forma` porta la sigla al maiuscolo e
  rifiuta il resto con `E_EMITTENTE_CODICE_FORMA_NON_VALIDA`; il CHECK `chk_emittenti_fiscali_codice_forma` è la
  rete per le strade che il trigger non percorre.
* **Perché non cambia.** Un codice già composto porta la sigla di quel momento: cambiarla lascerebbe i documenti
  emessi con una sigla che non è più di nessuno. Il lock di colonna la blocca con `E_CODICE_NON_MODIFICABILE`;
  il form la mostra non modificabile perché la colonna compare in `dbops.vw_non_editable_fields`.

---

### Il regime fiscale decide l'esigibilità IVA

`regime_fiscale_rf` è il codice `RegimeFiscale` del tracciato della fattura elettronica, con la FK su
`config.regimi_fiscali`. Non è un'etichetta: decide l'esigibilità IVA delle righe (un emittente `RF17` emette a
esigibilità differita, salvo le esclusioni di `script.fn_esigibilita_iva`).

* **Chi lo ha dichiarato.** La colonna ha il default `RF01`, e un `RF01` scelto e uno messo dal default sarebbero
  la stessa riga. Per questo `regime_fiscale_confermato_il` e `regime_fiscale_confermato_da` dicono quando e chi
  lo ha dichiarato: le scrive il database a ogni `UPDATE` che nomina il regime, anche con lo stesso valore
  (`anagrafiche.trgfn_emittenti_fiscali_regime_conferma`); la creazione non conferma mai, e da fuori le due
  colonne non si scrivono (`anagrafiche.trgfn_emittenti_fiscali_guard_regime_conferma`). Un emittente acceso col
  regime mai dichiarato compare in `dbops.vw_emittenti_regime_non_confermato`.
* **Un regime spento.** Non si assegna a un emittente acceso (`E_ATTIVO_PADRE_NON_ATTIVO`, al COMMIT); un regime
  che un emittente acceso usa non si spegne. Un emittente spento tiene il suo regime anche se il regime si spegne,
  ma per riaccenderlo gli serve un regime acceso. La regola completa sta nella scheda di `config.regimi_fiscali`.

---

### Le impostazioni dell'emissione

* `bollo_auto` e `bollo_soglia`: se il bollo si applica da sé, e da quale importo (non negativo).
* `rounding_policy`: il metodo di arrotondamento generale dell'azienda (`UP`, `DOWN`, `HALF_UP`, `HALF_DOWN`).
  Vale quando la riga dell'azienda per una utility non c'è o non è accesa; i parametri per utility stanno in
  `anagrafiche.emittenti_fiscali_utilities`, e quelli effettivi li dice `anagrafiche.fn_parametri_importo_utility`.
* `valuta_id`: la valuta dell'azienda, quando ne ha una propria.
* `brand_meta`: i dati d'impaginazione dei documenti (logo, contatti, note).

I dati societari e fiscali del soggetto (partita IVA, sede, forma giuridica) restano sul soggetto.

---

### ⛔ Un emittente in uso non si spegne

Spegnere un emittente è respinto finché una tabella figlia ha righe collegate. Ogni tabella con una FK verso
questa ha il suo trigger `BEFORE UPDATE OF attivo`, generato dall'automazione ATTIVO e scritto da
`dbops.trgfn_prevent_deactivate_if_children`; il codice dice il rimedio:

* `E_ATTIVO_BLOCK_CHILDREN_ACTIVE` quando la figlia ha la colonna `attivo`: le righe collegate vanno spente;
* `E_ATTIVO_BLOCK_CHILDREN_EXIST` quando non ce l'ha: le righe vanno tolte.

Le figlie sono i collegamenti dei billing account e i parametri per utility; i documenti che nominano l'azienda
per `id` (contratti, offerte, preventivi, ordini, DDT, resi); il magazzino (magazzini, lotti, asset); i titoli
IVA; i modelli di stampa e i loro asset; le pratiche e le definizioni dei workflow; i parametri di
configurazione per azienda, le aziende assegnate agli utenti e l'azienda attiva di ciascuno; il registro e la
coda delle email. Il messaggio non nomina tabelle: la figlia che blocca sta nel contesto del registro errori.

⚠️ La regola vive in trigger generati dalle FK: se una FK sparisse o cambiasse bersaglio, l'automazione
toglierebbe il suo trigger e il divieto se ne andrebbe senza rumore. Per i collegamenti dei billing account lo
presidia il test 7 di `db/pgtap/vendite/test-registri-per-emittente-v1.sql`, che verifica che il trigger ci sia.

Alcune figlie sono escluse di proposito, e il motivo sta in `dbops.automazione_attivo_eccezioni`: i preset di
lista e di dashboard (il preset di un'azienda spenta non si applica) e le stampe generate (sono storia, non figli
vivi).

Il verso opposto: una riga che nasce o passa a un emittente spento è respinta al COMMIT dai trigger
`dbops.trgfn_child_requires_active_parent` delle figlie (`E_ATTIVO_PADRE_NON_ATTIVO`).

---

### ⚠️ Che cosa oggi non copre

* **I documenti che nominano l'azienda col ruolo non fermano lo spegnimento.** Fatture, commesse, registri di
  numerazione, listini, lotti di fatturazione, distinte d'incasso e sistemazioni hanno la FK su
  `soggetti_ruoli`, non su questa tabella, e l'automazione ATTIVO non li vede: un emittente con fatture o
  commesse aperte si spegne, uno con un ordine no. Lo stesso per `dbops.coda_lavori`, che punta all'`id` ma sta
  fuori dal perimetro dell'automazione.
* **La fattura non segue l'azienda del billing account.** Ordini, DDT, commesse, resi, contratti, offerte,
  preventivi e asset hanno `script.trgfn_doc_guard_emittente_ba`; `vendite.fatture` no: una fattura in bozza
  resta all'azienda di prima quando il billing account cambia azienda.
* **`valuta_id` non ha la FK** su `config.valute`: la colonna accetta un id che non è una valuta.
* **I commenti del catalogo sono stantii**: quello della tabella parla di «preferenze di numerazione, IBAN
  predefinito», colonne che la tabella non ha.

---

### Test

* `db/pgtap/anagrafiche/test-emittenti-fiscali.sql` — il primo emittente fa nascere la predefinita, l'azienda di
  un billing account con e senza collegamento, lo spegnimento respinto con un collegamento.
* `db/pgtap/anagrafiche/test-emittenti-fiscali-codice-forma.sql` — la forma della sigla.
* `db/pgtap/anagrafiche/test-emittente-soggetto-immutabile-v1.sql` — il ruolo dell'emittente non cambia.
* `db/pgtap/vendite/test-registri-per-emittente-v1.sql` — i registri per emittente e il trigger generato sui
  collegamenti dei billing account (test 6 e 7).

---

### Note di migrazione

* 2026-08-20 — lo spegnimento bloccato dai collegamenti dei billing account passa al trigger generato
  dall'automazione ATTIVO, che è nato quando la tabella dei collegamenti ha avuto la FK verso questa. Il guard
  dedicato `trgfn_emittenti_fiscali_guard_attivo` è tolto (era un doppione che non veniva più raggiunto: i
  trigger della stessa fascia scattano in ordine alfabetico) e il suo codice `E_EMITTENTE_DISATTIVAZIONE_BLOCCATA`
  è ritirato.
* 2026-08-31 — la sigla entra nel codice commessa, e da allora ha una forma.
* 2026-10-01 — `regime_fiscale_rf` diventa una FK sul catalogo dei regimi, `NOT NULL` col default `RF01`; dal
  giorno dopo la conferma la scrive il database. Dal 2026-11-21 un regime spento non si assegna a un emittente
  acceso.

---

{% include-markdown "signature-core.md" %}
