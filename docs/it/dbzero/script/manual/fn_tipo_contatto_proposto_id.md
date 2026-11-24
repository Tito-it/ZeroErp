## 📘 Documentazione Concettuale – Funzione `script.fn_tipo_contatto_proposto_id()`

> **Ultimo aggiornamento**: 24 novembre 2026
>
> 👀 **Vedi anche**
>
> * [config.tipi_contatti](/dbzero/config/manual/tipi_contatti) — il catalogo dei tipi
> * [script.fn_stato_proposto_id](/dbzero/script/manual/fn_stato_proposto_id) — il gemello, per lo stato
> * [script.fn_get_parameter_di_sessione](/dbzero/script/manual/fn_get_parameter_di_sessione) — la cascata degli override, col contesto della sessione

---

### 🎯 Scopo Principale

**Il tipo di contatto che si propone quando chi crea un soggetto non lo dice.** Ritorna l'id di
`config.tipi_contatti` indicato dal parametro `TIPO_CONTATTO_PROPOSTO`, che contiene il **codice
interno** del tipo (in dotazione `PRINCIPALE`).

È una **proposta**: il parametro passa per la cascata degli override, letta con
[`script.fn_get_parameter_di_sessione`](/dbzero/script/manual/fn_get_parameter_di_sessione).
Valgono gli override per utente, per gruppo, per azienda attiva, per sessione e per chi chiede
(`p_chi`, il nome della funzione che la chiama). Così un'azienda può proporre `REFERENTE` per i
soggetti che crea, o una sola porta può proporre un tipo diverso dalle altre.

---

### Chi la chiama

* `anagrafiche.fn_crea_soggetto_pf` e `fn_crea_soggetto_pg`, quando il chiamante non passa il tipo
  del contatto di default;
* `script.fn_crea_utente_tecnico`, per il contatto del soggetto dell'utente tecnico.

Ognuna passa il proprio nome come `p_chi`: un override «per funzione» vale solo per lei.

---

### Valida e non ripiega

| Caso | Esito |
| --- | --- |
| parametro assente o vuoto | `E_CONFIG_MANCANTE` |
| il codice non indica nessun tipo | `E_DEFAULT_ERRATO` |

Mai un ripiego sul «primo tipo per id» né su un codice scritto nel corpo. Il codice interno è
unico, quindi indica al più un tipo. Il registro `config.parameter_fk_surrogate` controlla già,
quando si scrive il parametro o un suo override, che il codice sia un tipo esistente
(`E_PARAMETER_DEFAULT_VALUE_INVALID`); qui il controllo resta come rete, per un tipo tolto dopo.

---

### Note di migrazione

Prende il posto di tre scelte diverse per la stessa cosa (decisione D-T5-6 b di Tid,
24-11-2026):

* il **primo tipo per id** del catalogo, nelle due porte di creazione del soggetto e nel builder
  pgTAP delle persone giuridiche: l'ordine di caricamento, non una scelta;
* `'PRINCIPALE'` **scritto nel corpo** della fabbrica degli utenti tecnici, senza controllo;
* `script.fn_get_tipo_contatto_id`, che cercava un tipo per codice ma non aveva chiamanti: è stata
  ritirata, e con lei il codice `E_DEFAULT_CONTATTO_MISSING`.

---

### Test

* `db/pgtap/anagrafiche/test-tipo-contatto-proposto-v1.sql` — le due porte senza tipo davanti a
  un tipo con id minore di tutti, gli override per funzione, la configurazione rotta che non
  ripiega;
* `db/pgtap/script/test-fn-crea-utente-tecnico.sql` (test 14) — l'utente tecnico segue l'override.

---

{% include-markdown "signature-core.md" %}
