## 📘 Documentazione Concettuale – Vista `vendite.vw_dash_competenza_attivita`

> 👀 **Vedi anche**
>
Approfondimento tabelle e funzioni:
>
[vendite.commesse_attivita](/dbzero/vendite/tabelle/commesse_attivita)
> [vendite.attivita_fatturabili](/dbzero/vendite/tabelle/attivita_fatturabili)
> [vendite.fatture_righe](/dbzero/vendite/tabelle/fatture_righe)
> [vendite.fn_emit_attivita_fatturabili_da_commessa](/dbzero/vendite/funzioni/fn_emit_attivita_fatturabili_da_commessa)
>
Famiglia due lenti:
>
[vw_dash_competenza_mensile](vw_dash_competenza_mensile.md)
> [vw_dash_competenza_errori](vw_dash_competenza_errori.md)
> [vw_dash_backlog_documenti](vw_dash_backlog_documenti.md)

---
### 🎯 Scopo Principale
(latest review 06-07-2026)
Vista di dettaglio della **Lente 1 Competenza** (cruscotti fatturazione a due
lenti, brief `brief-db-fatturazione-due-lenti` §4): una riga per **attività di
commessa computabile**, con la sua posizione nel funnel a valle
(commessa → attività fatturabile → riga fattura → stato fiscale) e la
dimensione dei **recuperi tardivi**. L'asse è la competenza **vera**
(`commesse_attivita.competenza_mese`, NOT NULL) — nessun proxy.

---

### Semantica

| Aspetto | Regola |
|---------|--------|
| **`stadio`** | `DA_APPROVARE` (BOZZA, non emessa) · `DA_EMETTERE` (approvata, non emessa) · `EMESSA_NON_FATTURATA` (riga AF con `fattura_riga_id` NULL) · `FATTURATA` (agganciata a riga fattura, con `stato_fattura_codice_interno` per il breakdown) |
| **Misura (DB-6)** | `valore = prezzo_snapshot × quantita` su **tutti** gli stadi (stessa misura del resolver commesse: funnel omogeneo); `valore_fatturato = fatture_righe.imponibile_riga` è la **riconciliazione** col fatturato reale |
| **`data_emissione` (DL-5)** | = `attivita_fatturabili.data_insert`. Validata 2026-07-06: la riga AF nasce una volta sola all'emissione, mai DELETE in produzione, il reset lotto fa solo UPDATE (la data non si sposta), nessuna re-emissione possibile |
| **`emessa_in_ritardo`** | `mese(data_emissione) > competenza_mese` — competenza M lavorata dopo M. NULL per attività non ancora emesse |
| **Perimetro (computabile)** | Esclude commesse `ANNULLATE` (testata) e attività void (predicato `20260703-61`: `stato_emissione <> 'ANNULLATA' AND (stato_approvazione <> 'RIFIUTATA' OR stato_emissione = 'EMESSA')`) |
| **Scope emittente** | In-vista via `script.fn_get_emittenti_scope_sr_ids(app.current_user_id)` da GUC: `NULL`=tutto · `'{}'`=niente · array=whitelist. `security_invoker = on` |
| `cliente_display` | Intestatario BA (`billing_account → soggetto_ruolo → soggetti`) |

---

### Esempio d'uso

```sql
-- Il mese M e' completo? Cosa manca, e cosa e' stato recuperato in ritardo.
SELECT stadio, count(*), sum(valore),
       count(*) FILTER (WHERE emessa_in_ritardo) AS recuperi_tardivi
FROM vendite.vw_dash_competenza_attivita
WHERE competenza_mese = DATE '2026-05-01'
GROUP BY stadio;
```

---

### Note operative

* **Il BE aggrega da `vw_dash_competenza_mensile`** e usa questa vista per il
  drill-down (layering come la famiglia `vw_dash_fatturazione_*`).
* ⚠️ **Caveat C1 (`data_insert`)**: il ramo UPDATE di idempotenza di
  `fn_emit_attivita_fatturabili_da_commessa` cerca la riga AF per
  `(sorgente_tipo_id, sorgente_uid)` **senza** filtrare per commessa: una
  collisione di `segment_key` fra attività diverse farebbe ereditare un
  `data_insert` **più vecchio**. Nessun percorso di produzione lo genera oggi;
  direzione benigna (il flag ritardo può solo **sotto-stimare**, mai falso
  positivo). Sentinella pgTAP sul reset in `test-vw-dash-competenza-v1.sql`.
* ⚠️ **Fail-closed dello scope**: senza GUC operatore (`app.current_user_id`)
  la vista restituisce **0 righe** (vale per superuser/psql/batch ad-hoc, il
  filtro-in-vista non è aggirato da `BYPASSRLS`). Per interrogare a mano:
  impostare la GUC. Il pgTAP la imposta esplicitamente.
* Un'attività `EMESSA` senza riga AF (solo manutenzioni fuori flusso) cade in
  `EMESSA_NON_FATTURATA` con `data_emissione` NULL: classificazione corretta,
  ritardo non calcolabile.
* Test: `db/pgtap/vendite/test-vw-dash-competenza-v1.sql`.

---

---

### Colonne di gruppo fatturabile (rev 2026-07-27)

Aggiunte **in coda** quattro colonne: `sorgente_tipo_id`, `sorgente_uid`,
`tipo_movimento`, `gruppo_key`.

`gruppo_key` viene da
[`fn_build_gruppo_fatturabile_key`](/dbzero/vendite/funzioni/fn_build_gruppo_fatturabile_key),
la **stessa** funzione usata dai filtri `p_gruppi` dell'emissione: le chiavi
mostrate sono esattamente quelle che l'emissione accetta.

Questa vista è la base di
[`vw_dash_competenza_gruppi`](/dbzero/vendite/views/vw_dash_competenza_gruppi),
che da qui eredita **scope emittente** e **coerenza dei conteggi con la card**.

⚠️ **Due vincoli su ogni futura modifica**:

1. `CREATE OR REPLACE VIEW` ammette solo l'**aggiunta di colonne in fondo**: non
   si possono rinominare, riordinare o eliminare quelle esistenti. L'ordine
   attuale è di fatto immutabile;
2. `WITH (security_invoker=on)` va **ri-specificato ogni volta**: la reloption
   non compare in `pg_get_viewdef` e PostgreSQL la azzera in silenzio,
   trasformando la vista in `security_definer` di fatto e aprendo un buco nello
   scope emittente su tutte le dashboard di competenza.

**Fail-closed senza GUC**: `script.fn_get_emittenti_scope_sr_ids(NULL)`
restituisce l'array **vuoto**, non `NULL`, quindi senza `app.current_user_id`
nessuna riga passa. Da tenere presente scrivendo test.

---

### 🆕 `commessa_stato_descrizione` (2026-08-15)

Aggiunta con `20260815-24` su richiesta del backend
([brief-db-emittibilita-visibile-e-sbloccabile](/dev/work-done/brief-db-emittibilita-visibile-e-sbloccabile)
§8.3), e propagata sui gruppi dal `20260815-25`.

La vista esponeva `commessa_stato_codice_interno` e nient'altro. A video va però
la **descrizione**: la convenzione del progetto è che le liste ricevano i campi
di display già decodificati dal DB, mai risolti lato client, e un codice interno
dentro un'interfaccia inglese — *«The job order is in state BOZZA»* — è il
sintomo che quella convenzione è stata aggirata.

Il backend si era messo un `LEFT JOIN` sul repository per cavarsela. Funzionava,
ed è la ragione per cui la richiesta era arancione e non rossa: ma quel JOIN **la
vista lo faceva già** — è da lì che arrivano `emittibile` e `codice_interno` — e
una seconda risoluzione della stessa cosa è la duplicazione che il §7.1 di quel
brief aveva già dovuto estrarre una volta, sul guard di transizione.

ℹ️ `COALESCE(descrizione, codice)` e non `descrizione` nuda: la colonna è
nullable a catalogo (il seed la valorizza su tutte e sei le righe, ma il DDL non
lo impone), e un campo di **display** che torna `NULL` produce una cella vuota,
che l'operatore legge come «non lo so» invece che come «manca il dato di
catalogo». `codice` è `NOT NULL` ed è la forma leggibile del mutabile: è il
ripiego giusto.


---

### 🆕 `emittente_ragione_sociale` *(R-4, 18-08-2026)*

Il nome dell'emittente **della commessa** arriva in coda alla proiezione.

⭐ **Il drill-down commesse può metterla nel `GROUP BY` in sicurezza**, e non è
una misura sui dati: nella vista quella colonna è `co.emittente_soggetto_ruolo_id`
dove `co` è `vendite.commesse`, e `commessa_id` è la sua **chiave primaria**.
L'emittente è un campo *della commessa*: una commessa ne ha uno solo per lo
stesso motivo per cui ha un solo codice, e non può avere attività di emittenti
diversi perché l'emittente non sta sull'attività. Non è una proprietà dei dati
che possa cambiare domani.

⚠️ **La colonna nel `GROUP BY` serve comunque.** PostgreSQL deduce da sé la
dipendenza funzionale quando si raggruppa per la chiave primaria di una
*tabella*, ma qui si raggruppa su una colonna di **vista**: la deduzione non
scatta. È innocua, non superflua.

⚠️ **Due catene distinte sulle stesse tabelle**: `sr`/`s` sono il **cliente**
(via billing account), `sr_ef`/`s_ef` l'**emittente**. Scambiarle non darebbe
nessun errore — solo un nome sbagliato a video.

⚠️ **Il flag `multi_emittente` della lista NON si accende insieme alla colonna.**
Si guadagna dopo, quando la colonna mostra un nome su dati veri (brief
perimetro-emittente §7, decisione 3). Il controllo automatico
`dbops.vw_liste_multi_emittente_non_certificate` deve restare a zero righe.

* Test: `db/pgtap/vendite/test-viste-dash-emittente-v1.sql`.

---

{% include-markdown "signature-core.md" %}
