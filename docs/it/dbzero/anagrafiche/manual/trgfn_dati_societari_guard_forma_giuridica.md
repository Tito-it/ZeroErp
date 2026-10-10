## 📘 Documentazione Concettuale – Funzione `anagrafiche.trgfn_dati_societari_guard_forma_giuridica()`

> 👀 **Vedi anche**
>
> [anagrafiche.dati_societari](/dbzero/anagrafiche/manual/dati_societari) ·
> [config.forme_giuridiche](/dbzero/config/tabelle/forme_giuridiche) ·
> [config.forme_giuridiche_tipi_soggetto_dettaglio](/dbzero/config/tabelle/forme_giuridiche_tipi_soggetto_dettaglio)

---

### 🎯 Scopo

La forma giuridica dei dati societari deve reggere quattro domande. Le controlla in quest'ordine,
e risponde la prima che non regge:

| # | Domanda | Rifiuto | Campo |
| --- | --- | --- | --- |
| 1 | La forma è dello stesso Stato del soggetto? | `E_FORMA_GIURIDICA_PAESE` | `forma_giuridica_id` |
| 2 | La natura del soggetto ammette la forma? | `E_FORMA_GIURIDICA_NON_AMMESSA_PER_TIPO_SOGGETTO` | `forma_giuridica_id` |
| 3 | Il REA c'è se la forma lo pretende, e manca se lo vieta? | `E_REA_OBBLIGATORIO` / `E_REA_NON_AMMESSO` | `iscrizione_rea` |
| 4 | Il capitale c'è se la forma lo pretende, e manca se lo vieta? | `E_CAPITALE_SOCIALE_OBBLIGATORIO` / `E_CAPITALE_SOCIALE_NON_AMMESSO` | `capitale_sociale` |

* La domanda 2 ha una sede sola, `anagrafiche.fn_forma_giuridica_ammessa`: una riga **attiva e
  valida oggi** della matrice delle forme per natura. Nessuna riga vuol dire «non ammessa».
* Le domande 3 e 4 leggono `rea_policy` e `capitale_sociale_policy` della forma: `REQUIRED` =
  presente, `NONE` = assente, `OPTIONAL` = libero. Che provincia e numero REA vadano in coppia lo
  dice il `CHECK chk_dati_societari_rea_coppia`.

### Quando tace

* Forma assente: dal 2026-10-11 la colonna è `NOT NULL`, e parla lei.
* Soggetto o forma inesistenti: parlano le chiavi esterne.
* Soggetto senza natura, solo per la domanda 2: lo rifiuta già `trgfn_dati_societari_guard_tipo_soggetto`.

### Il cambio di natura

Se cambia la **natura del soggetto**, non scatta questo guard: scatta
`trgfn_soggetti_guard_forma_giuridica_natura`, **al COMMIT**. Natura e forma si cambiano insieme,
nella stessa transazione: **prima la natura, poi la forma**. Con due controlli immediati non si
potrebbe cambiare nessuna delle due.

### Aggancio

`BEFORE INSERT OR UPDATE OF forma_giuridica_id, soggetto_id, id_prov_iscri_rea, iscrizione_rea,
capitale_sociale`.
