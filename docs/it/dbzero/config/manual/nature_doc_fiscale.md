## 📘 Documentazione Concettuale – Tabella `config.nature_doc_fiscale`

> 👀 **Vedi anche**
>
> [config.tipi_doc_fiscale](/dbzero/config/tabelle/tipi_doc_fiscale) ·
> [vendite.fatture](/dbzero/vendite/tabelle/fatture) ·
> [vendite.tipi_doc_fiscale_registri](/dbzero/vendite/tabelle/tipi_doc_fiscale_registri) ·
> [config.fn_get_natura_doc_fiscale_id](fn_get_natura_doc_fiscale_id.md) ·
> [vendite.fn_get_registro_id](/dbzero/vendite/funzioni/fn_get_registro_id)
>
> Brief autorevole: `docs/it/dev/work-in-progress/brief-design-note-credito-resi.md`
> (decisione **D-NC-3**, §12.4-bis)

---

### 🎯 Scopo Principale

(rev 2026-08-18)

**Che cosa è, fiscalmente, questo documento**: una fattura, una nota di credito,
una nota di debito.

Sembra una domanda a cui il sistema sapesse già rispondere, e per anni si è
creduto di sì. Non era così.

---

### ⭐ L'asse non è nuovo: era nel disegno, ed era stato occupato da altro

`config.tipi_doc_fiscale` **è nata** per rispondere a questa domanda — la
documentazione di `vendite.fatture`, scritta a gennaio 2026, lo dice ancora:

> *«Tipo documento: `tipo_doc_fiscale_id` → `config.tipi_doc_fiscale`
> (es.: fattura, nota credito, parcella)»*

Il **seed**, però, contiene `FRONTOFFICE` e `BACKOFFICE`: i due **canali** di
fatturazione. E una decisione di dominio del 19 giugno 2026 ha registrato
quell'uso come definitivo — *«front/back office è solo un esempio d'uso, ogni
azienda può usare quel campo per scopi diversi; non inferire mai il valore da
logica cablata»*.

Non ci sono due verità in conflitto: **c'era una colonna sola per due assi**, e
chi ha scritto la doc a gennaio e chi ha deciso a giugno stavano guardando due
cose diverse con lo stesso nome.

> **Questa tabella non inventa un asse: ne separa due che erano fusi dal primo
> giorno**, e lascia a ciascuno ciò che davvero contiene.

| Asse | Dove vive | Chi lo decide |
|---|---|---|
| **canale** (front office, back office, area, brand, mandante…) | `config.tipi_doc_fiscale` | l'**azienda**: è configurabile, e nessuna logica deve inferirlo |
| **natura fiscale** (fattura, nota di credito, nota di debito) | `config.nature_doc_fiscale` | la **legge**: domani è il `TipoDocumento` della FatturaPA |

⚠️ **Perché non bastava aggiungere `NOTA_CREDITO` a `tipi_doc_fiscale`**: i due
assi sono ortogonali, e collassarli moltiplica. Due canali × due nature = quattro
valori e quattro registri; e un'azienda che usa il tipo documento per un asse
suo si troverebbe il **prodotto cartesiano** del proprio asse per due.

---

### Il vocabolario resta NEUTRO, per dichiarazione del modello

La documentazione di `vendite.fatture` mette fra i propri obiettivi:

> *«Tracciare stato e tipo fiscale **senza vincoli di specifico ordinamento
> nazionale** (modello neutro, estendibile).»*

Ne discende che i `codice_interno` sono `FATTURA`, `NOTA_CREDITO`,
`NOTA_DEBITO` — e che **il codice italiano non è una colonna**:

```jsonc
meta = {"sdi_tipo_documento": "TD04"}   // nota di credito
```

Vive in `meta` come **parametro di profilo nazionale**, sullo stesso criterio con
cui il progetto tiene i parametri locali a un handler. Se un domani servisse un
secondo profilo fiscale, diventerà una tabella di mapping — non prima.

⭐ **Il builder XML della FatturaPA legge di qui**, non da un `IF` cablato.

---

### Struttura

| Colonna | Ruolo |
|---|---|
| `codice_interno` | **chiave naturale stabile**, immutabile (lock automatico). È l'unica cosa su cui la logica si basa |
| `codice` | etichetta modificabile dall'utente. **Mai usata in logica** |
| `descrizione` | testo a video. Mono-lingua, come `causali_onere` e `tipi_reso` |
| `attivo`, `ordine` | selezionabilità e presentazione |
| `meta` | parametri di profilo nazionale. Chiave nota: `sdi_tipo_documento` |

**Niente `label_key`**: un vocabolario di tre voci non giustifica un namespace
i18n. È il precedente deciso nel brief porta oneri §4c.3.

---

### Dove la natura viene letta

```text
commesse_attivita.natura_doc_id     l'INTENTO      (una rettifica nasce NOTA_CREDITO)
        ↓  fn_emit_attivita_fatturabili_da_commessa
attivita_fatturabili.natura_doc_id  l'EMISSIONE
        ↓  fn_build_fattura_key  →  fn_get_or_create_fattura_header
fatture.natura_doc_id               il DOCUMENTO   ← è qui che la FatturaPA chiede
```

⭐ **Entra nella chiave del documento**, quindi due attività di natura diversa
finiscono su **due testate diverse**, con registro e numerazione diversi, senza
che nessuno debba separarle a mano. È il motivo per cui la nota di credito non ha
avuto bisogno di una seconda pipeline.

⚠️ **Da quel momento un lotto può contenere documenti di natura diversa**: chi
legge un lotto non deve più assumere «sono tutte fatture».

---

### Invarianti presidiati

| Invariante | Dove |
|---|---|
| un documento **non cambia natura** dopo | `trg_fatture_a10_lock_natura_doc_upd` (building block `script.trgfn_lock_columns`) |
| `natura = NOTA_CREDITO` ⟺ `totale_a_pagare ≤ 0` | condizione **7** del guard D-K in `fn_assign_numero_fattura`, verificata **prima** che il progressivo sia consumato |

⚠️ Il secondo non è cosmesi: senza, il segno del documento resterebbe una
**convenzione**. E il momento in cui verificarlo è quello — dopo la numerazione
*«un numero fiscale valido su un documento invalido si ripara solo con una nota
di variazione»*.

---

### ⚠️ Le tre righe esistono prima del mirror CSV

Sono inserite dal changeSet che **crea la tabella** (`20260818-24`), con
`ON CONFLICT DO NOTHING`, e ri-upsertate dal mirror `nature_doc_fiscale.csv` di
`80_data`.

Non è una doppia sorgente di verità, è il contrario: `80_data` gira **dopo**
tutto `00_schema`, e la colonna `natura_doc_id NOT NULL DEFAULT FATTURA` ha
bisogno della riga `FATTURA` **durante** l'`ALTER TABLE`. Senza il bootstrap
l'apply fallirebbe su ogni database che ha già delle fatture.

Il bootstrap **non aggiorna mai**: inserisce se manca e tace. **La sede dei
valori resta il CSV.** È il pattern già usato per `config.esiti_flussi_pratiche`.

---

### Query utili

```sql
-- Il TipoDocumento FatturaPA di una fattura, senza IF cablati
SELECT f.id, nd.codice_interno, nd.meta ->> 'sdi_tipo_documento' AS tipo_documento_sdi
  FROM vendite.fatture f
  JOIN config.nature_doc_fiscale nd ON nd.id = f.natura_doc_id
 WHERE f.id = :fattura_id;

-- L'invariante del segno, su tutto lo storico: deve tornare zero righe
SELECT f.id, nd.codice_interno, f.totale_a_pagare
  FROM vendite.fatture f
  JOIN config.nature_doc_fiscale nd ON nd.id = f.natura_doc_id
 WHERE (nd.codice_interno =  'NOTA_CREDITO' AND f.totale_a_pagare > 0)
    OR (nd.codice_interno <> 'NOTA_CREDITO' AND f.totale_a_pagare < 0);
```

---

### Importanza nel sistema

È il punto in cui il sistema ha smesso di sapere solo *da quale sportello* esce
un documento e ha cominciato a sapere *che cosa è*. Senza, la nota di credito
sarebbe stata una fattura con i numeri negativi — e la FatturaPA non avrebbe
avuto nulla da leggere per distinguere un TD01 da un TD04.

---

{% include-markdown "signature-core.md" %}
