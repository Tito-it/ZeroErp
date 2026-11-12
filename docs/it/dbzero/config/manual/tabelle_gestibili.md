## 📘 Documentazione Concettuale – Tabella `config.tabelle_gestibili`

> **Ultimo aggiornamento**: 13 novembre 2026
>
> 👀 **Vedi anche**
>
> **Chi la usa:** [config.fn_pannello_scrivi](/dbzero/config/funzioni/fn_pannello_scrivi) — il verbo del pannello · il lookup generico delle tendine
>
> **L'area di un oggetto:** [script.fn_area_di_oggetto](/dbzero/script/funzioni/fn_area_di_oggetto) · [config.area_model_overrides](/dbzero/config/tabelle/area_model_overrides)

---

### 🎯 Scopo Principale
(scritta il 25-09-2026)

È l'elenco delle tabelle che l'applicazione gestisce **in modo generico**, senza
una schermata dedicata. Ogni riga dice due cose:

| Colonna | Domanda |
| --- | --- |
| `lookup` | la tabella fornisce i valori delle tendine? |
| `pannello` | la tabella si modifica dal pannello «Gestione tabelle»? |

Fino al 25-09-2026 questo elenco stava nel backend, in una costante. Adesso è un
dato del database, e il verbo del pannello lo legge per sapere cosa può scrivere.

---

### L'oggetto, non l'area

Ogni riga dice anche **a quale oggetto appartiene** la tabella (`app_label`,
`model_name`). Quando qualcuno salva dal pannello, il permesso si chiede su
quell'oggetto: le causali di magazzino chiedono il livello sul Magazzino, non
sulla Configurazione.

La chiave dell'oggetto segue la convenzione che esiste già: `(schema, nome
tabella)`, per esempio `('magazzino', 'causali')`. Se l'oggetto ha già una
chiave diversa nel catalogo si usa quella: `vendite.listini` è l'oggetto
`('vendite', 'listino')`.

L'**area** non è scritta qui: la ricava `script.fn_area_di_oggetto`. Se fosse una
colonna, la regola «a quale area appartiene un oggetto» avrebbe due sedi.

#### Un oggetto, più righe

Due righe possono nominare lo **stesso oggetto**. Una riga dice da dove si leggono
o si scrivono i valori. L'oggetto dice chi ne ha il permesso, e le due cose
possono stare in sedi diverse. Le causali onere ne sono l'esempio (13-11-2026):

| Riga | Serve a | Oggetto |
| --- | --- | --- |
| `catalogo.vw_causali_onere_assegnabili` | la tendina del drawer articolo, che offre solo le causali non ancora legate a un articolo | `('config', 'causali_onere')` |
| `config.causali_onere` | il pannello, dove una causale nuova si crea e si modifica | `('config', 'causali_onere')` |

Il permesso è uno solo: chi può modificare le causali dal pannello è chi le vede
nella tendina. Ogni lettura della lista cerca la riga per `codice_interno`,
quindi niente presuppone una riga sola per oggetto.

---

### Cosa non ci può stare

* ⛔ **Nel pannello, una tabella con la RLS.** Il verbo scrive con i privilegi
  del proprietario e non saprebbe rimettere il perimetro della tabella. Le
  quattro tabelle con RLS (`magazzini`, `ubicazioni`, `enti_incasso`,
  `listini`) restano nelle tendine ma non nel pannello.
* ⛔ **Una riga aggiunta dall'applicazione.** L'app la può solo leggere. Il
  verbo scrive su ogni tabella della lista: se l'app potesse aggiungerne una,
  potrebbe scrivere anche una tabella che le è chiusa. Le righe nascono nel CSV
  del seed.

* ⛔ **Nel pannello, una tabella che ha già una sua schermata con il suo
  cancello.** Il pannello diventerebbe una seconda strada per modificarla,
  che salta il cancello. Il caso più grave è `config.profili_accesso`: dal
  pannello, chi può modificare la Configurazione cambierebbe i profili di
  permesso, cioè si darebbe da solo più diritti, senza passare dalla gestione
  accessi riservata al SUPER_ADMIN. Per la stessa ragione restano fuori
  `ui.lista_definizione`, `config.email_account`, `vendite.famiglie_documento`,
  `anagrafiche.categorie_clienti` e `catalogo.uom_tipi`.
* ⛔ **Nel pannello, un vocabolario di sistema.** Sono le tabelle che il seed
  carica e il programma legge per codice (per esempio `config.nature_vendita`,
  `config.registri_giornale`, i tipi di `documenti`). Una modifica dal pannello
  cambierebbe un codice che il programma interpreta, o sparirebbe al
  caricamento successivo.
* ⛔ **Nel pannello, il catalogo delle aree** (`config.aree_funzionali`). È
  la base su cui si danno i permessi: cambiarne la chiave staccherebbe profili
  e permessi di un'area intera. La sua gestione va nell'amministrazione del
  software, riservata al SUPER_ADMIN (decisa il 27-09-2026, da costruire).
* ⛔ **Nel pannello, una tabella che non è nelle tendine.** Il pannello ne
  elenca le righe passando dal lookup: `pannello` senza `lookup` è impedito
  dalla tabella stessa (vincolo, 27-09-2026).

Le tabelle tenute fuori dal pannello restano nella lista con `lookup`: servono
alle tendine, ma non si modificano dal pannello (27-09-2026). Nel pannello ogni
tabella appartiene a un'area del catalogo, senza eccezioni.

Presidio: `db/pgtap/config/test-pannello-porta-v1.sql` (la lista risolve tabelle
vere, nessuna ha la RLS, ogni area è a catalogo, `config.profili_accesso` e
`config.aree_funzionali` sono fuori dal pannello, il vincolo c'è).

{% include-markdown "signature-core.md" %}
