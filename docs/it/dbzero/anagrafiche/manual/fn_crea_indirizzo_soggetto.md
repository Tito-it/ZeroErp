## 📘 Documentazione Concettuale – Funzione `anagrafiche.fn_crea_indirizzo_soggetto()`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
[anagrafiche.indirizzi_soggetti](/dbzero/anagrafiche/tabelle/indirizzi_soggetti)
> [anagrafiche.indirizzi_dettaglio](/dbzero/anagrafiche/tabelle/indirizzi_dettaglio)
> [config.tipi_soggetto_dettaglio_tipi_indirizzo](/dbzero/config/tabelle/tipi_soggetto_dettaglio_tipi_indirizzo)
>
**Approfondimento funzioni:**
>
[anagrafiche.fn_crea_indirizzi_ruolo](/dbzero/anagrafiche/manual/fn_crea_indirizzi_ruolo) — la gemella sul livello del ruolo
> [anagrafiche.fn_indirizzo_elemento](/dbzero/anagrafiche/manual/fn_indirizzo_elemento) — la grammatica comune
> [anagrafiche.trgfn_indirizzi_guard_forma_libera](/dbzero/anagrafiche/manual/trgfn_indirizzi_guard_forma_libera) — le due forme dell'indirizzo libero
>
**Guide:**
>
[Gestione degli indirizzi](/guide/gestione-degli-indirizzi)

---
### 🎯 Scopo Principale
(latest review 18-10-2026)

**Scrivere un indirizzo di un soggetto** (`anagrafiche.indirizzi_soggetti`). Riceve il
soggetto e un oggetto jsonb con il tipo e l'indirizzo, e ritorna l'id della riga.

Parla la stessa lingua della gemella del ruolo, `fn_crea_indirizzi_ruolo`: le due madri
leggono l'indirizzo con gli stessi building block, quindi accettano le stesse chiavi e le
stesse forme.

---

### L'indirizzo, in una di tre forme

| Forma | Che cosa si indica |
| --- | --- |
| **libero** | `indirizzo_libero`, lo stato e, secondo lo stato, comune e CAP del catalogo (`comune_id`, `codice_postale_id`) oppure la località (`locality`) con codice postale, regione e sotto-località facoltativi |
| **dettaglio già risolto** | `indirizzo_dettaglio_id` |
| **via da risolvere** | `stradario_id`, oppure una via nuova (`toponomastica_id`, `descrizione_via`, `comune_id`, `codice_postale_id`), più il civico |

Il tipo si indica con `tipo_indirizzo_id` o con `tipo_indirizzo_codice` (codice interno,
per esempio `RES`, `DOMFISC`, `SEDELEG`).

---

### Chi dice che cosa

| Regola | Chi la dice | Codice |
| --- | --- | --- |
| manca il soggetto | la madre | `E_SCRIPT_CHIAMATA_NON_VALIDA` |
| l'indirizzo non è un oggetto | `fn_indirizzo_elemento` | `E_SCRIPT_CHIAMATA_NON_VALIDA` |
| una chiave che un indirizzo non ha | `fn_indirizzo_elemento` | `E_CAMPO_NON_AMMESSO` (col nome del campo) |
| un tipo che non esiste | `fn_indirizzo_elemento` | `E_TIPO_INDIRIZZO_NON_TROVATO` |
| la forma dell'indirizzo libero (campi mancanti, campi dell'altra forma, comune e CAP coerenti) | il guard della tabella, [`trgfn_indirizzi_guard_forma_libera`](/dbzero/anagrafiche/manual/trgfn_indirizzi_guard_forma_libera) | `E_INDIRIZZO_LIBERO_INCOMPLETO`, `E_INDIRIZZO_CAMPO_ALTRA_FORMA`, `E_INDIRIZZO_COMUNE_ALTRO_STATO`, `E_INDIRIZZO_CAP_ALTRO_COMUNE` |
| il tipo ammesso per il tipo di soggetto | `trgfn_indirizzi_soggetti_guard_tipo_indirizzo` | — |
| un tipo che il soggetto ha già | `uq_indirizzi_soggetti_soggetto_tipo` | — |

⭐ La completezza ha **una sede sola**, il guard della tabella: la madre non la ripete.
Se si indicano insieme `indirizzo_dettaglio_id` e `indirizzo_libero` vale il dettaglio
(il normalize svuota i campi liberi), come nella gemella del ruolo.

---

### Chi la chiama

* il backend, per l'indirizzo di un soggetto (`SoggettiRepository`);
* `anagrafiche.fn_crea_operatore_v2` (residenza e domicilio fiscale);
* `anagrafiche.fn_provisiona_dati_di_sviluppo` (i soggetti di prova).

---

### Test

`db/pgtap/anagrafiche/test-fn-crea-indirizzo-soggetto.sql` (il contratto della madre) e
`db/pgtap/anagrafiche/test-indirizzo-libero-due-forme-v1.sql` (le due forme, anche passando
dalla madre).

---

### Note di migrazione

Fino al 18-10-2026 la firma era posizionale: sette parametri (soggetto, codice del tipo,
dettaglio, testo, stato, comune, CAP). Mancavano i campi della forma estera, e la madre
pretendeva comune e CAP per ogni indirizzo libero: un indirizzo estero, che la tabella
ammette, non passava. I suoi rifiuti erano tutti `E_ADMIN_VALIDAZIONE` col solo nome del
parametro. La firma vecchia è stata tolta (non è rimasta accanto alla nuova). Richiesta
del backend in `brief-db-processi-accensione-per-ambiente` §6.11, decisione D-4 di Tid.

---

{% include-markdown "signature-core.md" %}
