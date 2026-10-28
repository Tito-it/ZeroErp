## 📘 Documentazione Concettuale – Tabella `config.stati_doc_offerte`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
• [vendite.offerte_commerciali](/dbzero/vendite/tabelle/offerte_commerciali)
> • [config.esiti_flussi_pratiche](/dbzero/config/tabelle/esiti_flussi_pratiche)
>
### 🎯 Scopo Principale
(latest review 2026-10-26)
`config.stati_doc_offerte` definisce gli **stati documento** del ciclo di vita
delle offerte commerciali, dalla bozza fino all'accettazione, al rifiuto o al
superamento.

---

### Campi chiave (semantica)

* **Identita` stato**: `id`, `codice`, `codice_interno`.
* **Ordine**: `ordine` per la progressione logica degli stati.
* **Governance**: `attivo`, `meta`.
* **Audit**: `data_insert`, `user_insert`, `data_update`, `user_update`.
* **Proiezione stato di dominio** (D1, brief `brief-db-proiezione-stato-dominio`):
  `fase`, `esito`, `terminale` — la **mappa dichiarata dal dominio** che normalizza il
  ciclo di vita per il motore pratiche (consumata via
  `vendite.vw_stato_sorgente_offerta` → `script.vw_stato_sorgente`).
* **Assi di chiusura, ortogonali fra loro**: `is_abortito` e `is_superato` — vedi
  sotto. Sono due *domande diverse*, e tenerle separate è il motivo per cui
  esistono come colonne invece che come letterali dentro una vista.

---

### I due assi di chiusura: `is_abortito` e `is_superato`

Un'offerta può smettere di essere quella «buona» per due ragioni che **non hanno
niente a che vedere l'una con l'altra**:

| Colonna | Stato marcato | Domanda a cui risponde | Chi la scrive |
| --- | --- | --- | --- |
| `is_abortito` | `ANNULLATA` | «è stata **annullata**?» | l'operatore, con l'azione di annullamento |
| `is_superato` | `SUPERATA` | «è stata **rimpiazzata** da una revisione successiva?» | la proiezione `vendite.fn_offerta_proietta_stato_revisione`, sul padre, all'inserimento della revisione successiva — e lo **toglie** la stessa proiezione quando l'ultima revisione viva viene annullata (la chiamano i trigger `vendite.trgfn_offerte_commerciali_revisione` e `vendite.trgfn_offerte_commerciali_rientro_padre`, dal 2026-10-26) |

⚠️ **`SUPERATA` non è più uno stato senza uscite** (dal 2026-08-28): ha la sola
transizione `SUPERATA -> EMESSA`, seedata con `manuale: false` perché è un
**rientro automatico**, non un gesto offerto all'operatore. Serve a sostenere il
flusso «ho sbagliato a revisionare, annullo e torno a operare sul predecessore»,
che prima lasciava l'intero lineage senza nessuna offerta attiva. La porta è
chiusa da una regola in `trgfn_offerte_commerciali_guard_transizione` — si esce
dal superamento **solo** se non esiste più una revisione figlia viva, altrimenti
`E_OFFERTA_RIENTRO_CON_REVISIONE_VIVA` — perché una transizione ammessa vale per
chiunque scriva, non solo per il trigger che l'ha resa necessaria.

Un'offerta è **attiva** quando nessuno dei due è vero:

```sql
NOT is_superato AND NOT is_abortito   -- = vw_offerte_commerciali_lista.is_attiva
```

⭐ **Perché due colonne e non un flag solo.** Fino al 2026-08-28
`vw_offerte_commerciali_lista` scriveva quel predicato come
`codice_interno NOT IN ('SUPERATA','ANNULLATA')`: un flag che rispondeva a
entrambe le domande, in AND, e quindi **non più separabile da chi legge**. Chi
voleva «solo l'ultima revisione» si portava dietro «e non annullata», e non
poteva farne a meno — con la conseguenza che la lista, filtrando `is_attiva` di
default, non poteva offrire un filtro di stato «Annullata» che restituisse
qualcosa. Con le due colonne la domanda si fa da sola:

```sql
WHERE is_superata IS FALSE     -- «solo l'ultima revisione», senza altro
```

⚠️ **E non è solo comodità di lettura**: finché quella coppia di letterali viveva
dentro la vista, la vista era l'unico posto dove stava scritto *che cosa*
significa `SUPERATA`. Uno stato nuovo che volesse dire la stessa cosa non sarebbe
entrato nel predicato, e nessun errore l'avrebbe detto.

⚠️ `is_superato` esiste **solo qui**, non su `config.stati_doc_preventivi`: nei
preventivi il superamento non è uno stato ma una **relazione** fra righe
(`numero`, `rev`), e `vendite.vw_preventivi` lo deriva. Meccanismi diversi,
stessa coppia di colonne esposta a valle.

Brief: `brief-db-revisione-attiva-due-domande`.

---

### Proiezione stato di dominio (mappa dichiarata)

| `codice_interno` | `fase` | `esito` | `terminale` |
|------------------|--------|---------|-------------|
| `BOZZA` | `APERTO` | — | no |
| `EMESSA` | `IN_ATTESA` | — | no |
| `ACCETTATA` | `IN_CORSO` | `POSITIVO` | no |
| `RIFIUTATA` | `CHIUSO` | `NEGATIVO` | sì |
| `SUPERATA` | `CHIUSO` | `NEGATIVO` | sì |
| `ANNULLATA` | `CHIUSO` | `NEGATIVO` | sì |

⚠️ La proiezione **non basta** a distinguere i due assi: `RIFIUTATA`, `SUPERATA` e
`ANNULLATA` hanno tutte e tre `fase=CHIUSO` + `esito=NEGATIVO` + `terminale=sì`.
Servono `is_abortito` e `is_superato` (sezione «I due assi di chiusura», qui sopra).

* `fase` e` NOT NULL con CHECK sui 4 valori del vocabolario di motore: **ogni nuovo
  stato deve dichiarare la propria fase** (niente default silenziosi).
* `esito` referenzia `config.esiti_flussi_pratiche.codice_interno` (FK) e deve essere un
  **verdetto** (`is_verdetto=true`, guard
  `trg_stati_doc_offerte_a10_guard_esito_verdetto_ins_upd`); NULL = nessun verdetto.
* `terminale` implica `fase='CHIUSO'` (CHECK `chk_stati_doc_offerte_terminale_chiuso`).

---

### Regole operative

* Lo stato e` usato da `vendite.offerte_commerciali.stato_doc_offerta_id`.
* `codice` e `codice_interno` devono restare **stabili** per workflow, query e integrazioni.
* La disattivazione di uno stato gia` in uso su offerte esistenti e` bloccata a livello DB.

---

{% include-markdown "signature-core.md" %}
