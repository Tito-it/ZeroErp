## 📘 Documentazione Concettuale – Trigger function `anagrafiche.trgfn_dati_societari_guard_forma_giuridica`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.dati_societari](/dbzero/anagrafiche/tabelle/dati_societari) — la forma, il REA e il capitale che il trigger controlla
> * [config.forme_giuridiche](/dbzero/config/tabelle/forme_giuridiche) — lo Stato della forma e le sue due policy
> * [config.forme_giuridiche_tipi_soggetto_dettaglio](/dbzero/config/tabelle/forme_giuridiche_tipi_soggetto_dettaglio) — le forme ammesse da ogni natura
>
> Approfondimento funzioni:
>
> * [anagrafiche.fn_forma_giuridica_ammessa](/dbzero/anagrafiche/funzioni/fn_forma_giuridica_ammessa) — la domanda «la natura ammette la forma?»
> * [anagrafiche.trgfn_soggetti_guard_forma_giuridica_natura](/dbzero/anagrafiche/funzioni/trgfn_soggetti_guard_forma_giuridica_natura) — la stessa domanda quando cambia la natura, al COMMIT

---

### 🎯 Scopo Principale

`anagrafiche.trgfn_dati_societari_guard_forma_giuridica` controlla la forma giuridica dei dati societari e ciò
che la forma chiede: lo Stato, la natura che la ammette, il REA e il capitale. Scatta subito, quando si
scrivono la forma, il soggetto, il REA o il capitale.

---

### Quattro domande, in quest'ordine

Risponde la prima che non regge:

| # | Domanda | Rifiuto | Campo |
| --- | --- | --- | --- |
| 1 | La forma è dello stesso Stato del soggetto? | `E_FORMA_GIURIDICA_PAESE` | `forma_giuridica_id` |
| 2 | La natura del soggetto ammette la forma? | `E_FORMA_GIURIDICA_NON_AMMESSA_PER_TIPO_SOGGETTO` | `forma_giuridica_id` |
| 3 | Il REA c'è se la forma lo pretende, e manca se lo vieta? | `E_REA_OBBLIGATORIO` / `E_REA_NON_AMMESSO` | `iscrizione_rea` |
| 4 | Il capitale c'è se la forma lo pretende, e manca se lo vieta? | `E_CAPITALE_SOCIALE_OBBLIGATORIO` / `E_CAPITALE_SOCIALE_NON_AMMESSO` | `capitale_sociale` |

* La domanda 2 ha una sede sola, `anagrafiche.fn_forma_giuridica_ammessa`, sul giorno operativo: una riga
  attiva e valida quel giorno della matrice. Nessuna riga vuol dire «non ammessa».
* Le domande 3 e 4 leggono le due policy della forma (`rea_policy`, `capitale_sociale_policy`): `REQUIRED`
  presente, `NONE` assente, `OPTIONAL` libero. Basta il numero REA: che provincia e numero vadano in coppia lo
  dice `chk_dati_societari_rea_coppia`.

---

### Quando tace

* **Forma assente**: la colonna è obbligatoria, e il rifiuto è il suo `NOT NULL`.
* **Soggetto o forma inesistenti**: parlano le chiavi esterne.
* **Soggetto senza natura**, solo per la domanda 2: la riga la rifiuta
  `anagrafiche.trgfn_dati_societari_guard_tipo_soggetto`.

Questo guard parla prima di quello della natura: per un privato con una forma il rifiuto che arriva è di
solito la domanda 2, non «questa natura non ha dati societari».

---

### Il cambio di natura

Se cambia la **natura del soggetto**, questo guard non scatta: la forma la rilegge
`anagrafiche.trgfn_soggetti_guard_forma_giuridica_natura`, **al COMMIT**
(`E_TIPO_SOGGETTO_FORMA_GIURIDICA_NON_AMMESSA`). Natura e forma si cambiano nella stessa operazione, **prima
la natura, poi la forma**: la forma nuova, scritta dopo, si giudica qui sulla natura nuova. Nell'ordine
inverso la forma nuova è rifiutata subito, perché la natura è ancora la vecchia. Con due controlli immediati
non si potrebbe cambiare nessuna delle due.

---

### ⚠️ Che cosa oggi non copre

* **Un cambio dello Stato del soggetto non rilegge la forma.** La domanda 1 si fa solo quando si scrive la
  riga dei dati societari, e nessun guard su `anagrafiche.soggetti` la rifà quando cambia lo Stato: un
  soggetto può restare con una forma di un altro Paese.
* **Un cambio delle policy della forma non rilegge le righe.** Una forma che passa a pretendere il REA lascia
  com'erano le righe già scritte senza; il rifiuto arriva alla loro prossima scrittura.

---

### Codici errore

Quelli della tabella sopra: `E_FORMA_GIURIDICA_PAESE`, `E_FORMA_GIURIDICA_NON_AMMESSA_PER_TIPO_SOGGETTO`,
`E_REA_OBBLIGATORIO`, `E_REA_NON_AMMESSO`, `E_CAPITALE_SOCIALE_OBBLIGATORIO`, `E_CAPITALE_SOCIALE_NON_AMMESSO`.
Ognuno nomina il campo da correggere.

---

### Test

* `db/pgtap/anagrafiche/test-fn-scrivi-dati-societari-v1.sql` — un ente con la forma SRL, col campo della forma;
  il capitale su un'associazione; una SRL senza capitale e senza REA; la provincia REA senza numero; la forma
  assente; il cambio di natura senza cambiare la forma, con la forma nuova, e nell'ordine inverso.

---

### Note di migrazione

* 2026-10-10 — nasce con le policy di REA e capitale sulla forma; prima REA e capitale erano obbligatori per
  tutti.
* 2026-10-11 — la forma diventa obbligatoria: il guard smette di doverne gestire l'assenza.

---

{% include-markdown "signature-core.md" %}
