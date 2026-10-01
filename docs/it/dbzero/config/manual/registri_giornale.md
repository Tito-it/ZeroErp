## 📘 Documentazione Concettuale – Tabella `config.registri_giornale`

> 👀 **Vedi anche**
>
Approfondimento viste:
> • [script.vw_giornale_entita](/dbzero/script/views/vw_giornale_entita) — la vista che cuce i registri
>
Approfondimento tabelle:
> • [config.tipi_entita](/dbzero/config/tabelle/tipi_entita) — il vocabolario gemello «di che cosa parla la riga»
> • [config.eventi_dominio](/dbzero/config/tabelle/eventi_dominio) — il vocabolario gemello «che cosa è successo»

---
### 🎯 Scopo Principale

(rev 2026-09-19 — nata con `20260919-08`, seminata da `20260919-09`)

**Da quale registro viene una riga del Giornale eventi.** Il Giornale mette in
fila cronologica ciò che quattro registri diversi raccontano di un lotto o di
una fattura, e ogni riga dice da quale dei quattro arriva. Questa tabella dà un
nome, una descrizione e un'etichetta a ciascuno:

| `codice_interno` | Che cosa contiene | Tabella letta |
|---|---|---|
| `EVENT_LOG` | gli eventi di dominio: i momenti della pipeline (avvio, passo, fine, errore) | `vendite.event_log` |
| `LOTTO_LOG` | le segnalazioni del lotto di fatturazione, fase per fase | `vendite.fatturazione_lotti_log` |
| `TASK_RUN` | i tentativi dei task di pipeline, con il loro esito | `vendite.fatturazione_lotti_task_runs` |
| `FATTURA_LOG` | le segnalazioni sulla singola fattura | `vendite.fatture_log` |

Fino al 19-09-2026 questo elenco viveva in **tre posti che non si conoscevano**
— dentro la vista, in una costante del backend, in un elenco del frontend — e
nessuno dei tre sapeva dire come si chiama un registro a video: la tendina
«Registro» mostrava `EVENT_LOG` così com'è. Ora la sede è **una**, e porta
l'etichetta.

---

### ⭐ Una riga è un ramo della vista — e un test lo pretende

La vista `script.vw_giornale_entita` è fatta di un pezzo per registro, e ogni
pezzo scrive il proprio nome come valore fisso. Questa tabella **non** viene
interrogata dalla vista: la **descrive**. Il legame fra le due lo tiene un test
(`db/pgtap/script/test-giornale-registri-catalogo-v1.sql`), nei due versi:

* ogni registro che la vista **emette** deve essere qui, e vivo;
* ogni riga **viva** di questa tabella deve avere il suo pezzo nella vista.

⇒ Un quinto registro entra con **due** cose nello stesso giro: il suo pezzo
nella vista e la sua riga nel CSV del seed. Con una sola delle due il test è
rosso. È ciò che rende questa tabella una sede e non una quarta copia.

Per lo stesso motivo **una riga non si aggiunge dall'applicazione**: nasce col
ramo, nel file `80_data/sql/config/registri_giornale.csv`.

---

### Regole principali

* Forma di tutti i vocabolari di `config`: `codice_interno` **immutabile** (il
  lock lo monta da solo il framework delle automazioni, per la sola presenza
  della colonna), `codice` e `descrizione` modificabili dall'operatore. La
  logica confronta **solo** `codice_interno`: è il valore che la vista emette
  nella colonna `registro` e che il backend accetta nel filtro.
  Regola generale: [linee guida SQL §6c](/linee-guida-sql).
* `etichetta_key` è l'indirizzo del testo a video, dichiarato dal database:
  `config.registri_giornale.<codice_interno minuscolo>`. Le traduzioni le
  porta il frontend nei propri file di lingua — ⚠️ il controllo automatico
  delle chiavi (`scripts/check_i18n_keys.py`) **non legge questa colonna**,
  quindi una chiave dimenticata non fa rosso da sola.
* `sorgente` è la tabella che il ramo legge, scritta come `schema.tabella`.
  È testo, non un riferimento di sistema, di proposito: un riferimento di
  sistema seguirebbe una rinomina in silenzio e mostrerebbe un numero se la
  tabella sparisse. Il test verifica che il nome si risolva **e** che la
  tabella sia davvero fra quelle che la vista legge.
* **Niente colonna `attivo`**, come in `tipi_entita` e `eventi_dominio`: un
  registro non si «assegna» a niente, e le righe vecchie del Giornale devono
  restare leggibili. Il ritiro di un ramo è `obsoleto_dal`: la riga resta per
  dare un nome al codice negli export e nei dati vecchi, e il lookup «per il
  nuovo» la esclude (`p_includi_obsoleti => false`).

---

### Chi la legge

* Il **frontend**, con il lookup generico
  (`GET /core/lookup/codici/?rel=config.registri_giornale`): la tendina
  «Registro» del Giornale eventi e l'etichetta della colonna.
* Il **backend**, per validare il filtro `registro` della lista del Giornale —
  dal cantiere BE che segue il brief, in sostituzione della costante
  `GIORNALE_REGISTRI`.

Brief: `brief-db-registri-giornale-catalogo`, sezione 4.

---
{% include-markdown "signature-core.md" %}
