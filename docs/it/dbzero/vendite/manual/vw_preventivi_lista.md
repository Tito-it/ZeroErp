## 📘 Documentazione Concettuale – Vista `vendite.vw_preventivi_lista`

> 👀 **Vedi anche**
>
> Approfondimento tabelle/viste:
>
> [vendite.vw_preventivi](/dbzero/vendite/views/vw_preventivi)
> [vendite.preventivi](/dbzero/vendite/tabelle/preventivi)
> [config.stati_doc_preventivi](/dbzero/config/tabelle/stati_doc_preventivi)
> [anagrafiche.istanze_utilities](/dbzero/anagrafiche/tabelle/istanze_utilities)
> [anagrafiche.billing_account](/dbzero/anagrafiche/tabelle/billing_account)
> [anagrafiche.soggetti](/dbzero/anagrafiche/tabelle/soggetti)
> [anagrafiche.emittenti_fiscali](/dbzero/anagrafiche/tabelle/emittenti_fiscali)
> [config.utilities](/dbzero/config/tabelle/utilities)
> [config.valute](/dbzero/config/tabelle/valute)
>
> Guida correlata:
> [Configurazione, personalizzazione e responsività delle liste](/guide/configurazione-liste)

---

### 🎯 Scopo Principale

(rev 2026-06-03 — rev1)

`vendite.vw_preventivi_lista` è la vista **canonica** che alimenta la **lista
preventivi configurabile** (`ui.lista_definizione` codice `vendite.preventivi`,
sistema liste DEF-8). È pura **denormalizzazione**: nessuno scope, filtro o
paginazione — scope emittente, filtri e `LIMIT/OFFSET` restano nel repository
backend consumer.

Nasce dal refactor che porta la lista preventivi nel motore di personalizzazione
liste (ritiro dinamico colonne, preset, preferenze utente, export CSV/XLSX),
gemella di `vw_contratti_lista` e `vw_offerte_commerciali_lista`.

#### Differenza chiave vs `vw_preventivi_list` (deprecata)

Espone i **nomi canonici** del catalogo liste (lezione DEF-8), così che ogni
`campo_sorgente` del catalogo combaci 1:1 con una colonna della vista (validato
dal trigger `trgfn_ui_lista_colonna_a10_valida_campo_sorgente`):

| `vw_preventivi_list` (vecchia) | `vw_preventivi_lista` (canonica) |
| --- | --- |
| `cliente_denominazione` | **`ragione_sociale_completa`** |
| `id_fiscale` | **`id_fiscale_univoco_cf_piva`** |
| `billing_account_codice` | **`ba_codice`** |
| — | **`emittente_fiscale_codice`** (nuovo, JOIN `emittenti_fiscali`) |

In più la vista è `WITH (security_invoker = on)` (standard liste DEF-8,
RLS-ready) e **non** espone `termine_pagamento_*` (non serve alla lista).

> La vista precedente `vw_preventivi_list` è stata **rimossa** (DROP changeset
> `20260603-09`) dopo la commutazione del backend (`list_preventivi`,
> `list_revisioni`) sulla vista canonica.

---

### Sorgente: `vendite.vw_preventivi` (non la tabella)

La vista legge **`FROM vendite.vw_preventivi p`**, non dalla tabella
`vendite.preventivi`. Motivo: la colonna fisica `is_revision_attiva` è stata
**droppata** e `is_attiva` è ora **derivata** in `vw_preventivi` (`TRUE` se non
esiste una revisione successiva non-abortita). Leggendo dalla vista base si
riusa quella derivazione senza duplicare logica — stesso pattern adottato dalla
precedente `vw_preventivi_list` (ora rimossa).

---

### JOIN principali

| Tabella/vista | Dati esposti | Note |
| --- | --- | --- |
| `config.stati_doc_preventivi` | `stato_codice_interno`, `stato_descrizione` | INNER JOIN |
| `anagrafiche.istanze_utilities` → `anagrafiche.soggetti` | `soggetto_id`, `ragione_sociale_completa`, `id_fiscale_univoco_cf_piva` | LEFT (in pratica sempre match: `istanza_utility_id` NOT NULL) |
| `anagrafiche.billing_account` | `ba_codice` | LEFT: `billing_account_id` opzionale per prospect (NULL ammesso) |
| `anagrafiche.emittenti_fiscali` | `emittente_fiscale_codice` | LEFT |
| `config.utilities` | `utility_codice`, `utility_descrizione` | LEFT |
| `config.valute` | `valuta_codice` | LEFT |

---

### 📑 Campi chiave esposti

* **Identificatori**: `id`, `uid`, `numero`, `rev`, **`is_attiva`**, `data`
* **Stato**: `stato_doc_preventivo_id`, **`stato_codice_interno`** (severity Tag FE), `stato_descrizione`
* **Cliente (via istanza)**: `billing_account_id`, **`ba_codice`**, `soggetto_id`, **`ragione_sociale_completa`**, **`id_fiscale_univoco_cf_piva`**
* **Permessi / emittente**: `emittente_fiscale_id` (scope), **`emittente_fiscale_codice`**
* **Utility e istanza**: `utility_id`, **`utility_codice`**, `utility_descrizione`, `istanza_utility_id`, **`istanza_utility_codice`**
* **Importi**: `totale_imponibile`, `totale_iva`, **`totale_documento`**
* **Validità**: `validita_dal`, **`validita_al`**, `competenza_mese`
* **Valuta**: `valuta_id`, `valuta_codice`
* **Audit**: `data_insert`

**Filtro storico revisioni**: il toggle UI «mostra storico revisioni» si traduce
nel predicato `is_attiva` (mostra solo la revisione viva quando ON), gestito dal
repository — non è una colonna della lista.

---

### Mappatura catalogo lista (`vendite.preventivi`, lista_id=5)

Le 12 colonne visibili di default nel preset di sistema `preventivi_default`
riproducono 1:1 la lista attuale (numero, rev, data, cliente, cd. account,
id. fiscale, utility, cod. istanza, totale, validità, stato, azioni). La colonna
tecnica `stato_codice_interno` è nel preset ma nascosta (serve al Tag severity
FE). Le restanti colonne (`utility_descrizione`, `validita_dal`,
`totale_imponibile`, `totale_iva`, `valuta`, `emittente_fiscale_codice`,
`competenza_mese`, `data_insert`) sono nel catalogo come **extra opt-in**
(`visibile=false`), attivabili dall'operatore.

L'attributo **`priorita`** di ogni colonna governa il ritiro dinamico (packing a
somma): più alto = la colonna resiste più a lungo. Si ritirano per prime `data`
(25) e `ba_codice` (40); resistono `cliente` (95), `stato` (90), `totale` (80);
`numero` e `azioni` non si ritirano mai.

---

### Esempio d'uso

```sql
-- Lista preventivi per un emittente, filtro stato, con dati cliente canonici
SELECT id, numero, rev, data,
       stato_codice_interno, ragione_sociale_completa, id_fiscale_univoco_cf_piva,
       ba_codice, utility_codice, istanza_utility_codice,
       totale_documento, validita_al
  FROM vendite.vw_preventivi_lista
 WHERE emittente_fiscale_id = 1
   AND stato_codice_interno = 'EMESSO'
 ORDER BY data DESC, numero DESC, id;
```

```sql
-- Solo la revisione viva (toggle storico OFF)
SELECT id, numero, rev, ragione_sociale_completa, totale_documento
  FROM vendite.vw_preventivi_lista
 WHERE is_attiva = TRUE
 ORDER BY data DESC;
```

---

### Note operative

* **Prospect senza BA**: anche con `billing_account_id IS NULL`, la riga ha
  `ragione_sociale_completa` e `id_fiscale_univoco_cf_piva` valorizzati grazie al
  lookup via istanza; solo `ba_codice` resta NULL (informazione corretta).
* **`security_invoker=on`**: la vista gira col contesto del chiamante, pronta per
  un'eventuale RLS sulla tabella base senza diventare «RLS cosmetica»
  (linee-guida-sql §10.1). Nota: la sorgente intermedia `vw_preventivi` non è
  invoker, quindi rispetto allo status quo nulla cambia sul fronte RLS finché non
  verrà propagato anche lì.
* **Performance**: lookup su PK indicizzata (`pk_istanze_utilities`,
  `pk_soggetti`, `pk_billing_account`, `pk_utilities`, ecc.), zero scansioni full.

---

{% include-markdown "signature-core.md" %}
