## 📘 Documentazione Concettuale – Tabella `config.area_model_overrides`

> 👀 **Vedi anche**
>
Architettura di riferimento:
>
[Architettura Permessi e Autorizzazioni](/guide/architettura-permessi-e-autorizzazioni) — §4.3, il catalogo degli oggetti
>
Tabelle correlate:
>
[config.aree_funzionali](/dbzero/config/tabelle/aree_funzionali) ·
[config.user_override_oggetti](/dbzero/config/tabelle/user_override_oggetti)

---

La tabella **`config.area_model_overrides`** è il **catalogo degli oggetti**
che il sistema dei permessi conosce. Il nome è storico: nata per riassegnare
un model a un'area diversa dal suo schema, oggi è l'elenco di ciò che il
pannello dei permessi lascia personalizzare per operatore.

---

### 🎯 Cosa dice ogni riga

| Colonna | Scopo |
|---------|-------|
| `app_label`, `model_name` | L'oggetto, con la chiave che backend e frontend chiedono (es. `vendite`, `offerta_commerciale`) |
| `area_id` | L'area a cui l'oggetto appartiene: la legge `script.fn_area_di_oggetto`. Un oggetto non a catalogo vale come area = `app_label` |
| `riservato` | `true` = l'oggetto è a catalogo ma **non si personalizza**: il kernel dei permessi, dove un override aprirebbe un blocco ricorsivo |

---

### ⛔ La regola che la tabella regge

Un override in `config.user_override_oggetti` esiste **solo per un oggetto a
catalogo e non riservato**. Lo garantisce una FK composita
(`fk_user_override_oggetti_catalogo`, su `app_label`, `model_name` e
`riservato`), non il backend: vale per qualunque percorso di scrittura.

Conseguenze da sapere prima di toccare il catalogo:

* un oggetto che **diventa riservato**, o che **esce** dal catalogo, mentre ha
  override si ferma sulla FK. Gli override si tolgono prima;
* un oggetto **entra** a catalogo solo quando tutte le porte lo chiedono
  (rotte del backend, `READONLY_MODELS` del frontend, verbo del pannello di
  configurazione). La ragione è nella guida, §4.3.

---

### Dove si cambia

Nel CSV `db/changelog/migrations_v2/80_data/sql/config/area_model_overrides.csv`,
chiave naturale `(app_label, model_name)`. Il mirror non cancella: una riga tolta
dal CSV esce con un `DELETE` a parte, come è stato per `billing_account`
(brief `brief-db-be-fe-catalogo-oggetti-permessi`, D-5).
