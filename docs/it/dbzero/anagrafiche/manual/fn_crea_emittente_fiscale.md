## 📘 Documentazione Concettuale – Funzione `anagrafiche.fn_crea_emittente_fiscale()`

> 👀 **Vedi anche**
>
> [anagrafiche.emittenti_fiscali](/dbzero/anagrafiche/manual/emittenti_fiscali) ·
> [script.fn_scrivi_riga_da_jsonb](/dbzero/script/manual/fn_scrivi_riga_da_jsonb)

### 🎯 Scopo
(17-10-2026 — brief `brief-db-processi-accensione-per-ambiente`, 2b-1)

**Fare di un soggetto un emittente fiscale**, in un'operazione sola: il ruolo
EF del soggetto (creato se manca) e la riga dell'emittente. Nascendo,
l'emittente fa nascere da sé i suoi registri di numerazione e, se è il primo,
il mapping di default.

È la sede unica della creazione: la usano il backend (dalla pagina degli
emittenti), i builder pgTAP e il provisioning dei dati di sviluppo.

### I campi

Oltre a soggetto e codice, facoltativi: `attivo`, `regime_fiscale_rf`,
`bollo_auto`, `bollo_soglia`, `rounding_policy`, `valuta_id`. Quelli assenti
prendono il default. Un campo diverso è rifiutato col suo nome
(`E_CAMPO_NON_AMMESSO`).

**Un regime indicato è un regime confermato**: il default `RF01` e un `RF01`
scelto sono indistinguibili sulla riga, quindi chi lo indica lo conferma (data
e autore). Senza regime l'emittente nasce con `RF01` da confermare, e finisce
nel presidio dei regimi da confermare.

### Che cosa non controlla

* **La partita IVA del soggetto**: oggi la controlla il backend prima di
  chiamare. È una regola di dominio senza un guard sulla tabella (debito
  dichiarato nel brief).
* **Il permesso**: nel dominio anagrafiche lo decide il backend.
* I **duplicati** (stesso codice, secondo emittente sullo stesso soggetto) e
  il regime fuori catalogo escono dai vincoli della tabella, col loro nome.

### Test

`db/pgtap/anagrafiche/test-fn-crea-emittente-fiscale-v1.sql`.

---

{% include-markdown "signature-core.md" %}
