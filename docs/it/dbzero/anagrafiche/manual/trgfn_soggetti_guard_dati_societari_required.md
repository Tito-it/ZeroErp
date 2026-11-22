## 📘 Documentazione Concettuale – Trigger function `anagrafiche.trgfn_soggetti_guard_dati_societari_required`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.soggetti](/dbzero/anagrafiche/tabelle/soggetti) — il soggetto che il trigger guarda
> * [anagrafiche.dati_societari](/dbzero/anagrafiche/tabelle/dati_societari) — la riga che deve esserci
> * [config.tipi_soggetto_dettaglio](/dbzero/config/tabelle/tipi_soggetto_dettaglio) — la natura e la sua policy dei dati societari
>
> Approfondimento funzioni:
>
> * [anagrafiche.trgfn_dati_societari_guard_tipo_soggetto](/dbzero/anagrafiche/funzioni/trgfn_dati_societari_guard_tipo_soggetto) — l'altra metà: la riga non ammessa, subito
> * [anagrafiche.fn_check_elimina_dati_societari](/dbzero/anagrafiche/funzioni/fn_check_elimina_dati_societari) — la stessa pretesa, quando si chiede di eliminare la riga

---

### 🎯 Scopo Principale

`anagrafiche.trgfn_soggetti_guard_dati_societari_required` pretende che un soggetto la cui natura chiede i
dati societari (la società di capitali) li abbia: senza la riga in `anagrafiche.dati_societari`, il soggetto
è rifiutato. Il controllo avviene al COMMIT.

---

### ⭐ Perché al COMMIT

Il soggetto e i suoi dati societari si scrivono in due istruzioni, e la riga dei dati societari ha bisogno del
soggetto già scritto. Il trigger è un constraint trigger **differito**, montato dopo ogni nascita e ogni
modifica del soggetto: nella stessa operazione si scrive il soggetto, poi la riga, e alla conferma si giudica
il risultato. È per questo che una società di capitali nasce dalla sua porta di creazione in una chiamata sola.

Gli altri guard dei dati societari sono immediati: la riga non ammessa, la forma, il canale si rifiutano
sull'istruzione che li scrive.

---

### Quando tace, quando parla

* **Soggetto senza natura**: nessuna pretesa.
* **Natura `NONE` o `OPTIONAL`**: nessuna pretesa.
* **Natura senza policy**: `E_DATI_SOCIETARI_TIPO_DETTAGLIO_NON_CONFIGURATO`, perché non si sa che cosa
  pretendere.
* **Natura `REQUIRED` senza la riga**: `E_DATI_SOCIETARI_REQUIRED_MANCANTI`.

Il controllo si rifà a ogni scrittura del soggetto, non solo al cambio di natura: anche un soggetto che passa a
una natura che li pretende (una società di persone che diventa di capitali) deve avere la riga alla conferma.

---

### ⚠️ Che cosa oggi non copre

* **La cancellazione della riga non lo fa scattare.** Il trigger sta su `anagrafiche.soggetti`, e una riga
  cancellata dalla sua tabella non riscrive il soggetto. La pretesa la tiene il verbo di eliminazione, che
  rifiuta; chi cancella la riga direttamente (il proprietario: l'applicazione non ha `DELETE`) lascia la
  società senza dati societari fino alla prossima scrittura del soggetto, che allora è rifiutata.

---

### Codici errore

* `E_DATI_SOCIETARI_TIPO_DETTAGLIO_NON_CONFIGURATO` — la natura del soggetto non ha una policy.
* `E_DATI_SOCIETARI_REQUIRED_MANCANTI` — la natura pretende i dati societari e la riga manca.

---

### Test

* `db/pgtap/anagrafiche/test-dati-societari-policy.sql` — la società di capitali senza riga rifiutata, con la
  riga ammessa.

---

{% include-markdown "it/dbzero/anagrafiche/_dati-societari.md" %}

---

{% include-markdown "signature-core.md" %}
