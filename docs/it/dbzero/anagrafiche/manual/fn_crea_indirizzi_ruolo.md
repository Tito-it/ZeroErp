## 📘 Documentazione Concettuale – Funzione `anagrafiche.fn_crea_indirizzi_ruolo()`

> 👀 **Vedi anche**
>
> [anagrafiche.indirizzi](/dbzero/anagrafiche/manual/indirizzi) ·
> [anagrafiche.fn_crea_indirizzo_soggetto](/dbzero/anagrafiche/manual/fn_crea_indirizzo_soggetto)

### 🎯 Scopo
(17-10-2026 — brief `brief-db-processi-accensione-per-ambiente`, 2b-1 lotto 2)

**Scrivere gli indirizzi di un ruolo** (cliente, fornitore, ...) in
un'operazione sola. È il gemello, sul livello del ruolo, di
`fn_crea_indirizzo_soggetto`, e la sede unica della regola: la usano la
creazione di fornitori e clienti, i builder pgTAP e il provisioning dei dati di
sviluppo.

### La regola dell'auto-clone

Ogni ruolo ha i suoi indirizzi **obbligatori**: per il fornitore fatturazione e
sede legale, per il cliente la fatturazione (la matrice è
`config.tipi_ruolo_tipi_indirizzo`). Se chi crea il ruolo ne indica uno solo,
gli altri obbligatori si **copiano dal primo**: stesso indirizzo, tipo diverso.

* Un tipo che il ruolo ha già si salta: niente doppioni.
* Un elenco vuoto non scrive niente, nemmeno i cloni.

### Le tre forme di un indirizzo

| Forma | Che cosa si indica |
| --- | --- |
| libero | `indirizzo_libero`, con stato, comune, CAP (o località) |
| dettaglio già risolto | `indirizzo_dettaglio_id` |
| via da risolvere | `stradario_id`, oppure una via nuova (tipo strada, nome, comune, CAP), più il civico: la risolve `fn_create_indirizzo` |

Il tipo si indica per id o per codice interno. Un campo che non appartiene a un
indirizzo è rifiutato col suo nome (`E_CAMPO_NON_AMMESSO`), un tipo
inesistente con `E_TIPO_INDIRIZZO_NON_TROVATO`.

⚠️ Due indirizzi diversi restano diversi: ognuno si risolve da sé. Fino al
16-10-2026 il backend riusava il primo dettaglio per tutti quelli che venivano
dopo.

### Che cosa non controlla

* I campi di una via nuova (tipo strada, nome, comune, CAP): li controlla il
  backend prima di chiamare, come per `fn_create_indirizzo`.
* Il permesso: nel dominio anagrafiche lo decide il backend.
* Il tipo ammesso per il ruolo e la completezza: li dicono i guard della
  tabella, come sempre.

### Test

`db/pgtap/anagrafiche/test-fn-crea-indirizzi-ruolo-v1.sql`.

---

{% include-markdown "signature-core.md" %}
