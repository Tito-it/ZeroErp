## 📘 Documentazione Concettuale – Funzione `anagrafiche.fn_crea_indirizzi_ruolo()`

> 👀 **Vedi anche**
>
> [anagrafiche.indirizzi](/dbzero/anagrafiche/manual/indirizzi) ·
> [anagrafiche.fn_crea_indirizzo_soggetto](/dbzero/anagrafiche/manual/fn_crea_indirizzo_soggetto) ·
> [anagrafiche.fn_indirizzo_elemento](/dbzero/anagrafiche/manual/fn_indirizzo_elemento) ·
> [anagrafiche.trgfn_indirizzi_guard_forma_libera](/dbzero/anagrafiche/manual/trgfn_indirizzi_guard_forma_libera)

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
| libero | `indirizzo_libero` con lo stato e, secondo lo stato, comune e CAP del catalogo oppure la località (`locality`, con `postal_code` facoltativo) |
| dettaglio già risolto | `indirizzo_dettaglio_id` |
| via da risolvere | `stradario_id`, oppure una via nuova (tipo strada, nome, comune, CAP), più il civico: la risolve `fn_create_indirizzo` |

Il tipo si indica per id o per codice interno. Un campo che non appartiene a un
indirizzo è rifiutato col suo nome (`E_CAMPO_NON_AMMESSO`), un tipo
inesistente con `E_TIPO_INDIRIZZO_NON_TROVATO`.

⭐ Dal 18-10-2026 la lettura dell'elemento (le chiavi ammesse, il tipo) e la
risoluzione della via stanno nei building block
[`fn_indirizzo_elemento`](/dbzero/anagrafiche/manual/fn_indirizzo_elemento) e
`fn_indirizzo_elemento_dettaglio`, che usa anche la madre del soggetto: una
grammatica sola per i due livelli.

⚠️ Due indirizzi diversi restano diversi: ognuno si risolve da sé. Fino al
16-10-2026 il backend riusava il primo dettaglio per tutti quelli che venivano
dopo.

### Che cosa non controlla

* I campi di una via nuova (tipo strada, nome, comune, CAP): li controlla il
  backend prima di chiamare, come per `fn_create_indirizzo`.
* Il permesso: nel dominio anagrafiche lo decide il backend.
* Il tipo ammesso per il ruolo e la forma dell'indirizzo libero: li dicono i
  guard della tabella (`trgfn_indirizzi_guard_forma_libera` per la forma, con
  codice e campo).

### 🔄 rev 19-10-2026 — la riga la scrive la singolare

(R-BE-6, decisione D-16a di Tid, `brief-db-processi-accensione-per-ambiente` §6.16)

* ogni riga la scrive la singolare [`fn_crea_indirizzo_ruolo`](/dbzero/anagrafiche/manual/fn_crea_indirizzo_ruolo), che ammette anche l'istanza; la plurale non conosce le istanze (un elemento con `istanza_utility_id` è rifiutato);
* la copia degli obbligatori è il BB `fn_indirizzi_con_obbligatori`, comune alla plurale del soggetto;
* il salto dei tipi che il ruolo ha già guarda solo gli indirizzi **senza istanza**: prima un indirizzo di un'istanza dello stesso tipo faceva saltare quello del ruolo, che poi non nasceva.

---

### Test

`db/pgtap/anagrafiche/test-fn-crea-indirizzi-ruolo-v1.sql`.

---

{% include-markdown "signature-core.md" %}
