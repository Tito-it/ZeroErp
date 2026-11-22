## 📘 Documentazione Concettuale – Trigger function `anagrafiche.trgfn_dati_societari_guard_canale_fe`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.dati_societari](/dbzero/anagrafiche/tabelle/dati_societari) — il canale e i recapiti che il trigger controlla
>
> Approfondimento funzioni:
>
> * [anagrafiche.fn_scrivi_dati_societari](/dbzero/anagrafiche/funzioni/fn_scrivi_dati_societari) — la porta da cui arrivano le scritture

---

### 🎯 Scopo Principale

`anagrafiche.trgfn_dati_societari_guard_canale_fe` controlla che il canale della fattura elettronica abbia il
suo recapito, e che il codice SDI abbia la sua forma. Scatta quando si scrivono il canale, la PEC o il codice,
e non fa niente se nessuno dei tre cambia.

---

### Il canale pretende il suo recapito

Il canale (`destinatario_fe`) dice come arriva la fattura elettronica al soggetto:

* **`C`**, via codice SDI: il codice deve esserci.
* **`P`**, via PEC: la PEC deve esserci, e una PEC fatta di soli spazi non conta.
* **nessun canale**: un cliente estero, o uno di cui non si sa ancora. I due recapiti sono liberi, e se ci sono
  restano.

Un canale non pretende che l'altro recapito manchi: una riga con canale `C` può avere anche la PEC.

---

### Il codice SDI ha la sua forma, con qualunque canale

Un codice, quando c'è, è fatto di sei o sette caratteri, lettere maiuscole o cifre. Il controllo vale anche
senza canale: un codice malformato non si conserva per dopo. Un codice più lungo di sette caratteri non arriva
al trigger: lo ferma prima il tipo della colonna.

---

### Un codice per campo, e i CHECK sotto

Ogni rifiuto nomina il campo da compilare o da correggere, così l'applicazione lo porta sul campo giusto. Sotto
il trigger, tre CHECK dicono le stesse regole (`chk_dati_societari_destinatario_fe_canale`,
`chk_dati_societari_codice_sdi_forma`, `chk_dati_societari_canale_fe_coerente`) e fanno da rete. Un canale
fuori vocabolario lo rifiuta solo il CHECK, senza un codice del catalogo, perché arriva
da un chiamante rotto e non da un utente.

---

### ⚠️ Che cosa oggi non copre

* **La lunghezza del codice non dipende dal soggetto.** Sei caratteri sono il codice di una pubblica
  amministrazione, sette quello degli altri, ma il trigger accetta l'una o l'altra lunghezza per chiunque.

---

### Codici errore

* `E_DATI_SOCIETARI_CODICE_SDI_NON_VALIDO` — il codice SDI non ha sei o sette lettere maiuscole o cifre.
* `E_DATI_SOCIETARI_CODICE_SDI_MANCANTE` — il canale è `C` e il codice manca.
* `E_DATI_SOCIETARI_PEC_FATTURAZIONE_MANCANTE` — il canale è `P` e la PEC manca.

---

### Test

* `db/pgtap/anagrafiche/test-dati-societari-canale-fe-v1.sql` — il codice di sette e di sei caratteri, il
  codice in minuscolo, quello troppo lungo fermato dal tipo, i due canali senza recapito, il canale fuori
  vocabolario fermato dal CHECK, il canale tolto, lo stesso codice e la stessa PEC su due soggetti, i tre
  CHECK.

---

### Note di migrazione

* 2026-10-10 — nasce, insieme al canale `P` / `C` / nessuno e alla fine dell'unicità di codice SDI e PEC.

---

{% include-markdown "signature-core.md" %}
