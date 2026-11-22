## 📘 Documentazione Concettuale – Tabella `anagrafiche.soggetti`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [config.tipi_soggetto_dettaglio](/dbzero/config/tabelle/tipi_soggetto_dettaglio) — la natura, che decide le regole del soggetto
> * [anagrafiche.soggetti_ruoli](/dbzero/anagrafiche/tabelle/soggetti_ruoli) — i ruoli del soggetto: cliente, fornitore, operatore…
> * [anagrafiche.dati_societari](/dbzero/anagrafiche/tabelle/dati_societari) — i dati di registro di ditte, società ed enti
> * [anagrafiche.soggetti_titoli_iva](/dbzero/anagrafiche/tabelle/soggetti_titoli_iva) — i titoli IVA del soggetto
> * [anagrafiche.contatti](/dbzero/anagrafiche/tabelle/contatti) — i contatti, fra cui quello di default
> * [storico.soggetti](/dbzero/storico/tabelle/soggetti) — le versioni precedenti della riga
>
> Approfondimento funzioni:
>
> * [anagrafiche.fn_crea_soggetto_pf](/dbzero/anagrafiche/funzioni/fn_crea_soggetto_pf) — la nascita di una persona fisica
> * [anagrafiche.fn_crea_soggetto_pg](/dbzero/anagrafiche/funzioni/fn_crea_soggetto_pg) — la nascita di una società o di un ente
> * [anagrafiche.trgfn_soggetti_guard_id_fiscale_immutabile](/dbzero/anagrafiche/funzioni/trgfn_soggetti_guard_id_fiscale_immutabile) — CF e P.IVA scritti non si cambiano
> * [anagrafiche.trgfn_soggetti_guard_cf_piva_obbligatori](/dbzero/anagrafiche/funzioni/trgfn_soggetti_guard_cf_piva_obbligatori) — la presenza di CF e P.IVA
> * [anagrafiche.trgfn_soggetti_valida_cf_piva_dispatch](/dbzero/anagrafiche/funzioni/trgfn_soggetti_valida_cf_piva_dispatch) — il formato di CF e P.IVA
> * [anagrafiche.trgfn_soggetti_guard_sesso_policy](/dbzero/anagrafiche/funzioni/trgfn_soggetti_guard_sesso_policy) — quando serve il sesso
> * [anagrafiche.trgfn_soggetti_guard_regime_pa](/dbzero/anagrafiche/funzioni/trgfn_soggetti_guard_regime_pa) — chi può essere PA o in scissione dei pagamenti
> * [anagrafiche.trgfn_soggetti_guard_cambio_natura](/dbzero/anagrafiche/funzioni/trgfn_soggetti_guard_cambio_natura) — il cambio di natura
> * [anagrafiche.trgfn_soggetti_gen_codice](/dbzero/anagrafiche/funzioni/trgfn_soggetti_gen_codice) — il codice interno
> * [anagrafiche.trgfn_soggetti_normalize](/dbzero/anagrafiche/funzioni/trgfn_soggetti_normalize) — lo stato proposto
>
> Guide:
>
> * [Soggetti e ruoli anagrafici](/guide/soggetti-e-ruoli-anagrafici) — il modello del soggetto e dei suoi ruoli

---

### 🎯 Scopo Principale

`anagrafiche.soggetti` è l'anagrafica di ogni persona e di ogni organizzazione con cui l'ERP ha a che fare: una
riga per soggetto, qualunque ruolo abbia. Che sia cliente, fornitore, operatore o emittente lo dicono i suoi
ruoli in `anagrafiche.soggetti_ruoli`, non questa tabella.

---

### ⭐ La natura decide le regole

La natura di dettaglio (`tipo_soggetto_dettaglio_id`, verso `config.tipi_soggetto_dettaglio`) dice che cosa è il
soggetto: un privato o una ditta individuale (persone fisiche), una società di persone o di capitali, un ente.
Non c'è una regola scritta per natura nel codice: ogni regola legge un campo della natura.

| Che cosa | Lo decide nella natura | Chi lo fa valere |
| --- | --- | --- |
| CF e P.IVA obbligatori | `cf_obbligatorio`, `piva_obbligatoria` | `trgfn_soggetti_guard_cf_piva_obbligatori` |
| il formato di CF e P.IVA | `formato_cf`, `formato_piva` | `trgfn_soggetti_valida_cf_piva_dispatch` |
| il sesso | `sesso_policy` | `trgfn_soggetti_guard_sesso_policy` |
| cliente PA e scissione dei pagamenti | `cliente_pa_ammesso`, `split_payment_ammesso` | `trgfn_soggetti_guard_regime_pa` |
| i dati societari | `dati_societari_policy` | i guard di `anagrafiche.dati_societari` e quello differito del soggetto |

Anche gli indirizzi obbligatori, i titoli IVA e i ruoli ammessi dipendono dalla natura, nelle loro tabelle.

La natura **può mancare**. Un soggetto senza natura non ha una regola da leggere: i guard di CF e P.IVA, del
formato e del sesso tacciono. Il regime PA no: un flag a `S` senza natura è rifiutato, perché cambia la fattura.

---

### L'identificativo fiscale e il blocco

Lo stato e l'identificativo fiscale, ricavato da CF e P.IVA, sono la chiave d'unicità del soggetto; un valore
scritto non si cambia, salvo il SUPER_ADMIN. La regola è descritta qui sotto, nel blocco comune.

---

### Il sesso

Il sesso lo sceglie chi lo vede: la colonna non ha default. `M` e `F` sono il sesso della persona; `X` vuol
dire che serve ma non si può stabilire (dati storici, codice fiscale estero) e si scrive di proposito; NULL
vuol dire che per questo soggetto non serve. Il privato lo deve avere (`REQUIRED`), la ditta individuale può
(`OPTIONAL`), società ed enti non lo indicano (`NONE`): un vincolo della natura lega `NONE` alle nature che non
sono persone fisiche.

---

### 🧾 Il regime della controparte: cliente PA e scissione dei pagamenti

`cliente_pa` dice che la controparte è una Pubblica Amministrazione, `split_payment` che le operazioni verso di
lei sono in scissione dei pagamenti. Valgono `S` o `N`, e nascono a `N`: un soggetto di cui nessuno ha detto
nulla non è in scissione, e dichiararlo d'ufficio sbaglierebbe le fatture.

* ⭐ **Stanno sul soggetto perché discendono dalla partita IVA**: un ente è o non è una PA, per ogni fornitura.
* ⚠️ **Non sono un codice IVA.** La scissione non cambia l'aliquota, cambia chi versa l'imposta: in fattura è
  l'esigibilità. `split_payment` lo leggono `script.fn_esigibilita_iva_documento` e la risoluzione dell'IVA di
  riga; `cliente_pa` oggi non ha lettori fuori dalle regole della natura.
* **Li ammette la natura**: privato e ditta individuale nessuno dei due, le società la sola scissione, l'ente
  tutti e due. La persona fisica è esclusa per legge, e lo dice un vincolo del catalogo delle nature. La natura
  è una condizione necessaria: il flag lo accende l'operatore.

---

### Il nome, il codice e lo stato

* **Il nome**: una persona ha cognome e nome, una società o un ente la ragione sociale. La colonna generata
  `ragione_sociale_completa` vale la ragione sociale o, se manca, cognome e nome: è il nome su cui si cerca.
* **Il codice** interno (`SGT-` e sette cifre) lo genera `trgfn_soggetti_gen_codice` quando chi scrive non lo
  dà, in maiuscolo; una volta scritto non si cambia (`E_CODICE_NON_MODIFICABILE`).
* **Lo stato** (`stato_id`) è la nazionalità fiscale, e decide quale validatore di CF e P.IVA si applica. Chi
  non lo dice riceve lo stato proposto (`trgfn_soggetti_normalize`).

---

### ⭐ La completezza si controlla alla conferma

Un soggetto nasce in più scritture: la riga, il contatto di default, gli indirizzi, i dati societari. Cinque
trigger differiti controllano il risultato alla conferma dell'operazione, non riga per riga:

* almeno un contatto (`trgfn_soggetti_guard_soggetto_contatti`);
* gli indirizzi che la natura pretende (`trgfn_soggetti_guard_indirizzi_required`);
* i dati societari, se la natura li pretende (`trgfn_soggetti_guard_dati_societari_required`);
* dopo un cambio di natura, la forma giuridica ammessa dalla natura nuova
  (`trgfn_soggetti_guard_forma_giuridica_natura`) e gli indirizzi che ogni ruolo del soggetto pretende sulla
  natura nuova (`trgfn_soggetti_guard_obbligatori_ruoli`).

Per questo le porte di creazione restituiscono un soggetto che la stessa operazione deve ancora completare.

---

### Il cambio di natura, i dati societari, i titoli IVA

* **Il cambio di natura** resta dentro la stessa famiglia (persona fisica, società, ente) ed è rifiutato col
  primo dei motivi che lo impediscono, elencati da `anagrafiche.fn_check_cambio_natura_soggetto`. Il cambio non
  pulisce niente: chi cambia natura porta la riga in regola nella stessa scrittura, per esempio riportando a
  `N` un flag che la natura nuova non ammette. Le regole sono nella scheda del guard.
* **I dati societari** (forma giuridica, REA, capitale, canale della fattura elettronica) stanno in
  `anagrafiche.dati_societari`, una riga per soggetto, quando la natura li prevede.
* **I titoli IVA** (i documenti per cui un soggetto non paga l'IVA ordinaria, come una dichiarazione d'intento)
  stanno in `anagrafiche.soggetti_titoli_iva`, e la natura dice quali sono ammessi.

---

### Spegnere, cancellare, storicizzare

* **Un soggetto non si spegne** (`attivo` a falso) finché ha righe in una delle tabelle che lo usano (righe
  attive, dove la tabella ha `attivo`): contatti, dati societari, indirizzi, istanze, pratiche, risorse umane,
  conti bancari, ruoli, titoli IVA.
* **La cancellazione** porta con sé contatti, dati societari e ruoli; la fermano le istanze, gli indirizzi, i
  conti bancari, le pratiche, le risorse umane e i titoli IVA.
* **Lo storico**: ogni modifica e ogni cancellazione lasciano la versione precedente in `storico.soggetti`. La
  tabella tiene il flag `storicizza` acceso; lo salta solo una scrittura che lo porta a falso.
* La tabella non ha row security: ogni operatore vede ogni soggetto.

---

### ⚠️ Che cosa oggi non copre

* **Uno stato tolto in una modifica non è rifiutato**: una scrittura che porta `stato_id` a NULL riceve lo
  stato proposto, e il soggetto cambia nazionalità senza averlo chiesto.
* **`ragione_sociale_completa` resta vuota** su un soggetto senza ragione sociale a cui manca il nome o il
  cognome.
* **La presenza di CF e P.IVA guarda solo il NULL**: una stringa vuota la soddisfa (dettaglio nella scheda del
  guard).
* **Il formato di CF e P.IVA si controlla solo per l'Italia**, e si ricontrolla a ogni modifica della riga,
  anche quando i due campi non cambiano.
* **Tre trigger fuori dalle fasce dei nomi**: `trg_soggetti_normalize_ins_upd` e
  `trg_soggetti_valida_cf_piva_dispatch_ins_upd` non hanno la fascia, e `trg_soggetti_a10_guard_obbligatori_ruoli_upd`
  è differito ma porta la fascia dei guard immediati.

---

### Test

* `db/pgtap/anagrafiche/test-soggetti-id-fiscale-immutabile-v1.sql` — il blocco di CF e P.IVA, nel guard e nel form.
* `db/pgtap/anagrafiche/test-soggetti-guard-cf-piva-obbligatori.sql` — la presenza di CF e P.IVA per natura.
* `db/pgtap/anagrafiche/test-soggetti-sesso-policy-v1.sql` — il sesso per natura, senza default.
* `db/pgtap/anagrafiche/test-soggetti-regime-pa-v1.sql` e `test-soggetti-split-payment-cliente-pa.sql` — i due
  flag del regime: valori, default, nature che li ammettono.
* `db/pgtap/anagrafiche/test-cambio-natura-soggetto-v1.sql` — il cambio di natura e i suoi motivi di rifiuto.
* `db/pgtap/anagrafiche/test-soggetti-indirizzi-required.sql` — gli indirizzi obbligatori alla conferma.

---

### Note di migrazione

* 2025-07-14 — la colonna `tipo_soggetto` (F, G, X) lascia il posto alla natura di dettaglio
  `tipo_soggetto_dettaglio_id`, che porta le regole per paese e per natura.
* 2026-08-29 — `cliente_pa` e `split_payment` passano dai clienti al soggetto. Dove i clienti dello stesso
  soggetto dissentivano ha vinto `S`: omettere la scissione è un errore fiscale, applicarla in più è un errore
  visibile e correggibile.
* 2026-10-09 — il sesso perde il default `M` e il valore `S`; quando serve lo dice la natura.
* 2026-10-10 — i due flag del regime si accendono solo se la natura li ammette.
* 2026-11-09 — CF e P.IVA scritti non si cambiano anche nel database: prima la regola stava solo nel form.

---

{% include-markdown "it/dbzero/anagrafiche/_identificativo-fiscale.md" %}

---

{% include-markdown "signature-core.md" %}
