## 📘 Documentazione Concettuale – Tabella `dbops.installazione`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
• [dbops.processi](/dbzero/dbops/manual/processi)
> • [dbops.processi_accensione](/dbzero/dbops/manual/processi_accensione)
>
**Approfondimento funzioni e viste:**
>
• [script.fn_ambiente_installazione](/dbzero/script/manual/fn_ambiente_installazione)
> • [dbops.vw_ambiente_non_dichiarato](/dbzero/dbops/manual/vw_ambiente_non_dichiarato)
>

### 🎯 Scopo Principale
(16-10-2026 — brief `brief-db-processi-accensione-per-ambiente`)

**Questo database è di sviluppo o di produzione?** Una riga sola, con il
valore `SVILUPPO` o `PRODUZIONE`.

Prima il modello non lo sapeva. Lo smoke notturno, che scrive dati di prova,
era «solo sviluppo» per due accorgimenti messi a mano; nessuna regola lo
diceva. Ora l'ambiente è un dato, e chiunque ne abbia bisogno lo chiede: oggi
la sveglia dei processi automatici, domani il provisioning dei dati di prova.

---

### ⭐ Si sceglie all'installazione, e non cambia più

| Momento | Che cosa succede |
| --- | --- |
| il changeSet crea la tabella | **vuota**: nessun valore di default |
| la fase `post` di `scripts/sql/provision_zeroerp.sql` | scrive l'ambiente col parametro `-v ambiente=SVILUPPO` oppure `-v ambiente=PRODUZIONE`; se manca la prima volta, si ferma e chiede di scegliere |
| dopo | il valore **non cambia**: `UPDATE`, `DELETE` e `TRUNCATE` sono rifiutati (`E_AMBIENTE_IMMUTABILE`) |

**Perché nessun default.** Un valore scritto da un changeSet troverebbe
database già esistenti e li dichiarerebbe al posto di chi li conosce: dbdev,
nato prima di questa tabella, sarebbe diventato produzione per sempre.

**Perché immutabile, in tutte e due le direzioni.**

* Da sviluppo a produzione no: un database di sviluppo contiene dati nati
  fuori da ogni regola (gli smoke scrivono dalle API normali), e nessun
  controllo può certificarlo pulito. Una produzione nasce dal provisioning,
  vuota.
* Da produzione a sviluppo no: protegge dall'errore di chi lavora sul database
  sbagliato. Una copia della produzione per fare prove **resta produzione**: lì
  smoke e dati di prova non partono, ed è giusto, perché contiene dati veri.

| Database | Ambiente | Chi lo dichiara |
| --- | --- | --- |
| dbdev | `SVILUPPO` | a mano, una volta, con la fase `post` |
| scratch `zeroerp_ruoli` | `SVILUPPO` | `scripts/ci-local.sh` |
| CI di GitHub | `SVILUPPO` | il workflow, nel bootstrap |
| installazione nuova | scelto da chi installa | la guida d'installazione |

---

### ⛔ L'applicazione legge, non scrive

Se l'applicazione potesse cambiare l'ambiente, un amministratore potrebbe
metterlo a sviluppo, lanciare un comando riservato allo sviluppo, e rimetterlo
a posto. Per questo `zeroerp_app` ha **solo `SELECT`**, dichiarato in tre sedi
(il changeSet `90_end/20261016-32`, il loop dei grant `20260205-41`, il blocco
«postura» della fase `post` del provisioning). Lo verifica
`dbops/test-installazione-ambiente-v1`.

Contro un DBA malintenzionato nessuna regola del database regge: quella difesa
sono i ruoli.

---

### Come si legge

| Chi | Funzione | Se manca l'ambiente |
| --- | --- | --- |
| chi **decide** in base all'ambiente | `script.fn_ambiente_installazione()` | errore `E_CONFIG_MANCANTE`, nessun ripiego |
| chi **descrive** (panorami, presidi) | `script.fn_ambiente_dichiarato()` | `NULL` |

Il presidio [vw_ambiente_non_dichiarato](/dbzero/dbops/manual/vw_ambiente_non_dichiarato)
ha una riga finché l'ambiente non è dichiarato.

---

{% include-markdown "signature-core.md" %}
