## 📘 Documentazione Trigger Function – `pratiche.trgfn_template_flussi_figli_guard_immutabile`

> 👀 **Vedi anche**
>
Funzioni collegate:
>
[pratiche.fn_check_definizione_congelata](fn_check_definizione_congelata.md)
> [pratiche.trgfn_template_flussi_guard_immutabile](trgfn_template_flussi_guard_immutabile.md)
> [pratiche.fn_copia_definizione](fn_copia_definizione.md)
>
Tabelle:
>
[pratiche.template_flussi](template_flussi.md)

---
### 🎯 Scopo Principale

**Immutabilità strutturale «Leggera»** dei **figli di configurazione** del template
su un'edizione forkata pubblicata (congelata). Un'unica trigger function
**generica** presidia i 6 figli del set di copia (contratto C6): blocca
**INSERT / UPDATE / DELETE** se il template referenziato appartiene a un'edizione
congelata → `TEMPLATE_DEFINIZIONE_CONGELATA` (514).

A differenza dei template (dove `descrizione` resta correggibile a caldo), i figli
**non hanno campo display**: su fork pubblicato **ogni** scrittura è vietata (il lock
strutturale include l'intero grafo — C4).

---

### Trigger associati

Un solo function, sei trigger (uno per figlio); la colonna FK verso `template_flussi`
arriva come **argomento** (`TG_ARGV[0]`):

| Trigger | Tabella | FK usata (`TG_ARGV[0]`) |
|---|---|---|
| `trg_template_flussi_canali_a10_guard_immutabile_iud` | `template_flussi_canali` | `template_flusso_id` |
| `trg_template_flussi_handler_eventi_a10_guard_immutabile_iud` | `template_flussi_handler_eventi` | `template_flusso_id` |
| `trg_competenze_flussi_a10_guard_immutabile_iud` | `competenze_flussi` | `template_flusso_id` |
| `trg_template_flussi_prerequisiti_a10_guard_immutabile_iud` | `template_flussi_prerequisiti` | `template_flusso_id` |
| `trg_formule_tempo_a10_guard_immutabile_iud` | `formule_tempo` | `template_flusso_da_id` |
| `trg_regole_generazione_a10_guard_immutabile_iud` | `regole_generazione` | `template_flusso_origine_id` |

Tutti `BEFORE INSERT OR UPDATE OR DELETE ... FOR EACH ROW`.

---

### Regole

* Per i figli con **due** FK verso `template_flussi` si usa il lato **proprietario**
  della riga: `template_flusso_id` (prerequisiti), `template_flusso_da_id` (formule),
  `template_flusso_origine_id` (regole). L'altro lato appartiene alla stessa
  definizione (prereq/formula) oppure è la **destinazione cross-definizione** (regole),
  che **non deve** governare il congelamento della regola.
* Estrazione FK **data-driven**: `to_jsonb(riga) ->> TG_ARGV[0]`. FK non risolvibile
  (riga incoerente) → il guard non decide: lasciano decidere le FK / gli altri guard.
* La verità "congelata" è
  [fn_check_definizione_congelata](fn_check_definizione_congelata.md) (regola unica,
  non ripetuta qui).

---

### Note operative

* **Set di copia = perimetro del lock** (C6): l'elenco dei 6 figli è **allineato a
  [fn_copia_definizione](fn_copia_definizione.md)**. Aggiungere un figlio al set di
  copia = aggiungere qui un `CREATE TRIGGER`, nient'altro.
* Durante `fn_fork_definizione` / `fn_nuova_versione_definizione` i figli sono inseriti
  nella nuova **BOZZA** (non congelata) → il guard è trasparente. Si attiva solo quando
  si tenta di scrivere su un fork **già pubblicato**.
* **Teardown**: un fork pubblicato va **ritirato** (`PUBBLICATA→RITIRATA`) prima di
  poterne cancellare i figli. Vale per manutenzione e cleanup pgTAP.
* Introdotto con `20260703-12` (Parte 2 / Fase 2b, D2-9).
* Test: `db/pgtap/pratiche/test-workflow-definizioni-fase2b.sql` (casi 9–11).

---
{% include-markdown "signature-core.md" %}
