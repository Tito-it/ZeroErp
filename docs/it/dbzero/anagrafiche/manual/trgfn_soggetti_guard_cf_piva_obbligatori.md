## 📘 Documentazione Concettuale – Trigger function `anagrafiche.trgfn_soggetti_guard_cf_piva_obbligatori`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.soggetti](/dbzero/anagrafiche/tabelle/soggetti) — la tabella che il guard presidia
> * [config.tipi_soggetto_dettaglio](/dbzero/config/tabelle/tipi_soggetto_dettaglio) — la natura, coi due obblighi
>
> Approfondimento funzioni:
>
> * [anagrafiche.trgfn_soggetti_valida_cf_piva_dispatch](/dbzero/anagrafiche/funzioni/trgfn_soggetti_valida_cf_piva_dispatch) — il formato di CF e P.IVA
> * [anagrafiche.trgfn_soggetti_guard_id_fiscale_immutabile](/dbzero/anagrafiche/funzioni/trgfn_soggetti_guard_id_fiscale_immutabile) — il cambio di un valore già scritto

---

### 🎯 Scopo Principale

`anagrafiche.trgfn_soggetti_guard_cf_piva_obbligatori` rifiuta un soggetto senza il codice fiscale o senza la
partita IVA quando la sua natura li pretende.

---

### L'obbligo lo dice la natura

Gli obblighi stanno sulla natura di dettaglio (`cf_obbligatorio`, `piva_obbligatoria`), non sul ruolo: un
soggetto è tenuto ad avere la partita IVA per quello che è, non per quello che fa. Il codice fiscale lo
pretendono tutte le nature; la partita IVA tutte salvo il privato. Il catalogo delle nature non ammette un
obbligo su un campo che la natura dichiara non applicabile.

Il guard scatta alla nascita e quando cambiano la natura, il CF o la P.IVA: un cambio di natura verso una che
pretende la P.IVA deve portarla nella stessa scrittura.

---

### Tre guard, tre domande

| Domanda | Chi risponde |
| --- | --- |
| c'è? | questo guard |
| è scritto bene? | `anagrafiche.trgfn_soggetti_valida_cf_piva_dispatch` |
| è cambiato un valore già scritto? | `anagrafiche.trgfn_soggetti_guard_id_fiscale_immutabile` |

Chi svuota un CF o una P.IVA obbligatori è fermato da questo guard; il guard sull'immutabilità ferma anche lo
svuotamento di un campo facoltativo.

---

### ⚠️ Che cosa oggi non copre

* **Guarda solo il NULL.** Una stringa vuota, o di soli spazi, conta come presente. Per un soggetto italiano la
  ferma poi il controllo del formato, che non la riconosce come un codice valido; fuori dall'Italia passa, e
  diventa un valore scritto che il guard sull'immutabilità blocca.
* **Senza natura tace**: non c'è un obbligo da leggere. Tace anche con una natura che non esiste, e il rifiuto
  arriva da chi parla dopo: per un soggetto italiano un errore tecnico del controllo del formato, altrimenti la
  chiave esterna.

---

### Codici errore

* `E_PIVA_OBBLIGATORIA` — la natura pretende la partita IVA e manca. Il campo dell'errore è `partita_iva`.
* `E_CF_OBBLIGATORIO` — la natura pretende il codice fiscale e manca. Il campo dell'errore è `codice_fiscale`.

---

### Test

* `db/pgtap/anagrafiche/test-soggetti-guard-cf-piva-obbligatori.sql` — il privato senza CF, la ditta
  individuale senza P.IVA o senza CF, la società di persone senza P.IVA, i casi completi che passano, il soggetto
  senza natura che passa.

---

### Note di migrazione

* 2026-02-28 — nasce con i due obblighi sulla natura di dettaglio.

---

{% include-markdown "signature-core.md" %}
