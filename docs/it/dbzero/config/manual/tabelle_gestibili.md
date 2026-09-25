## 📘 Documentazione Concettuale – Tabella `config.tabelle_gestibili`

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

`ui.lista_definizione` sta nel pannello, ma la sua area (`ui`) non è a
catalogo: la può modificare solo un SUPER_ADMIN, come dai suoi endpoint. È
voluto, e il pgTAP lo dichiara.

Presidio: `db/pgtap/config/test-pannello-porta-v1.sql` (la lista risolve tabelle
vere, nessuna ha la RLS, ogni area è a catalogo tranne quella dichiarata).

{% include-markdown "signature-core.md" %}
