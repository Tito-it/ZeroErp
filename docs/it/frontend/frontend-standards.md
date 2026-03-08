# ZeroERP — Standard Frontend

> Questo documento definisce le regole di progettazione e sviluppo dell'interfaccia utente di ZeroERP.  
> È vincolante per qualsiasi contributo al frontend. Le deroghe devono essere documentate e motivate.

---

## Stack tecnologico

| Componente | Versione | Ruolo                   |
| ---------- | -------- | ----------------------- |
| Vue.js     | 3.5.x    | Framework UI            |
| Vite       | 7.x      | Build tool e dev server |
| PrimeVue   | 4.5.x    | Libreria componenti     |
| PrimeIcons | latest   | Iconografia             |
| Pinia      | 3.x      | Gestione stato          |
| Vue Router | 4.x      | Navigazione             |
| Node.js    | 24 LTS   | Runtime di sviluppo     |

---

## Struttura del progetto

La struttura delle cartelle rispecchia i domini del database. Chi conosce il backend riconosce immediatamente il frontend.

```
src/
  core/               ← client API, error handling, composables base, utilities
  config/             ← dominio config
  anagrafiche/        ← dominio anagrafiche
  catalogo/           ← dominio catalogo
  pratiche/           ← dominio pratiche
  vendite/            ← dominio vendite
  acquisti/           ← dominio acquisti
  magazzino/          ← dominio magazzino
  pagamenti/          ← dominio pagamenti
  contabilita/        ← dominio contabilità
  router/             ← definizione rotte
  stores/             ← store Pinia globali
  assets/             ← immagini, font, stili globali
```

Ogni cartella di dominio contiene:

```
anagrafiche/
  views/              ← pagine intere (lista, dettaglio)
  components/         ← componenti specifici del dominio
```

`core/` è l'equivalente frontend di `dbops` e `scripts`: nessun dominio lo chiama esplicitamente, ma tutti dipendono da lui.

---

## Layout generale

L'interfaccia è suddivisa in tre aree fisse:

```
┌─────────────────────────────────────────────────┐
│                   TOPBAR                         │
├──────────┬──────────────────────────────────────┤
│          │                                      │
│ SIDEBAR  │           AREA CONTENUTO             │
│          │                                      │
│          │                                      │
└──────────┴──────────────────────────────────────┘
```

### Sidebar sinistra (fissa)
- Sempre visibile, non collassabile
- Contiene la navigazione tra i domini (le "stanze")
- Ogni voce ha un'icona PrimeIcons e un'etichetta
- La voce attiva è evidenziata visivamente
- Logo e nome applicazione in cima
- Informazioni utente connesso e logout in fondo

### Topbar
- Sempre visibile
- Mostra il percorso corrente (breadcrumb): `Dominio > Sezione`
- Contiene il pulsante **Nuovo** quando applicabile
- Contiene eventuali filtri rapidi globali della schermata

### Area contenuto
- Occupa tutto lo spazio rimanente
- Contiene la schermata attiva (lista o altra vista)

---

## Login

La schermata di login è l'unica pagina senza sidebar e topbar.

- Centrata verticalmente e orizzontalmente
- Logo ZeroERP in cima
- Form con campi: **Username** e **Password**
- Pulsante **Accedi** (larghezza piena del form)
- Messaggio di errore inline in caso di credenziali errate (non toast)
- Nessun link "Registrati" — accesso solo su invito

---

## Schermata di benvenuto (default dopo login)

La prima schermata dopo l'autenticazione mostra:

- Saluto personalizzato con nome utente
- Accessi rapidi ai domini autorizzati (card cliccabili con icona e nome)
- Sezione "Attività recenti" con le ultime pratiche modificate dall'utente
- Nessun KPI o dato aggregato in questa fase — evolverà in una dashboard completa in seguito

---

## Pattern lista

Ogni schermata di elenco segue questo schema fisso:

```
┌─ TOPBAR: [Breadcrumb]                  [Nuovo] ─┐
├─────────────────────────────────────────────────┤
│ [Filtro 1] [Filtro 2] [Cerca...]                │
├─────────────────────────────────────────────────┤
│ Colonna A │ Colonna B │ Colonna C │   Azioni    │
│───────────┼───────────┼───────────┼─────────────│
│ dato      │ dato      │ dato      │ 🖊 👁 🗑    │
│ dato      │ dato      │ dato      │ 🖊 👁 🗑    │
├─────────────────────────────────────────────────┤
│                  [Paginazione]                   │
└─────────────────────────────────────────────────┘
```

### Tabella
- Componente `DataTable` di PrimeVue
- Paginazione server-side (mai caricare tutti i record)
- Ordinamento per colonna abilitato di default sulle colonne principali
- Righe con altezza confortevole, padding verticale sufficiente
- Nessuna riga espandibile — i dettagli si aprono nel drawer

### Filtri
- Posizionati sopra la tabella, sotto la topbar
- Campo di ricerca testuale sempre presente
- Filtri specifici del dominio accanto al campo di ricerca
- I filtri agiscono in tempo reale o con pulsante Cerca (deciso dominio per dominio)

### Colonna Azioni
- Sempre l'ultima colonna della tabella
- Larghezza fissa, non ridimensionabile
- Contiene icone cliccabili, una per azione disponibile
- Ogni icona ha un **tooltip** con la descrizione dell'azione (appare al passaggio del mouse)
- Le azioni tipiche sono: **Modifica** (`pi-pencil`), **Visualizza** (`pi-eye`), **Elimina** (`pi-trash`)
- Le azioni variano per dominio — non tutte le righe hanno le stesse azioni
- Icone con colori semantici: modifica neutro, elimina rosso

---

## Drawer (nuovo e modifica)

**Regola unica: qualsiasi form di inserimento o modifica si apre sempre in un drawer laterale destro.**  
Non esistono dialog di compilazione né pagine intere per i form. Il drawer è l'unico pattern.

### Comportamento
- Si apre da destra con animazione slide
- La lista rimane visibile e invariata sullo sfondo
- Si chiude con: tasto `ESC`, clic fuori dal drawer, pulsante Annulla, o salvataggio riuscito
- Non è possibile aprire due drawer contemporaneamente

### Larghezze standard
| Tipo di form                              | Larghezza |
| ----------------------------------------- | --------- |
| Form semplice (tabelle di lookup, config) | 480px     |
| Form standard (anagrafiche, catalogo)     | 640px     |
| Form complesso (pratiche, contratti)      | 800px     |

La larghezza è definita a livello di dominio, non lasciata alla discrezione del developer.

### Struttura interna del drawer
```
┌─────────────────────────────────┐
│ Titolo ("Nuovo soggetto" /      │
│ "Modifica soggetto")            │
├─────────────────────────────────┤
│                                 │
│   Contenuto del form            │
│   (scrollabile se necessario)   │
│                                 │
├─────────────────────────────────┤
│ [Annulla]          [Salva]      │  ← fissi in fondo, non scrollano
└─────────────────────────────────┘
```

- Il titolo indica sempre l'operazione e l'entità: "Nuovo soggetto" / "Modifica soggetto"
- I pulsanti **Annulla** e **Salva** sono sempre in fondo, fissi, non scrollano con il contenuto
- **Salva** è il pulsante primario (colorato), **Annulla** è secondario (outline o testo)
- La validazione è inline sui campi — gli errori appaiono sotto il campo interessato
- Il pulsante Salva rimane disabilitato finché il form non è valido

---

## Conferma azioni distruttive

Qualsiasi azione irreversibile (eliminazione, annullamento, reset) richiede una conferma esplicita.

- Si apre un **dialog di conferma** centrato nella pagina (non un drawer)
- Il dialog mostra: titolo dell'azione + nome dell'elemento coinvolto
- Esempio: *"Sei sicuro di voler eliminare il soggetto **Mario Rossi**? L'operazione non può essere annullata."*
- Due pulsanti: **Annulla** (secondario) e **Conferma** (primario, colore rosso per azioni distruttive)
- Il dialog si chiude solo tramite uno dei due pulsanti — non con ESC o clic fuori

---

## Notifiche

| Tipo                  | Componente       | Posizione      | Durata                           |
| --------------------- | ---------------- | -------------- | -------------------------------- |
| Successo              | Toast            | Alto a destra  | 3 secondi                        |
| Errore operativo      | Toast            | Alto a destra  | 5 secondi (con chiusura manuale) |
| Errore di validazione | Inline sul campo | Sotto il campo | Fino a correzione                |
| Errore di sistema     | Toast            | Alto a destra  | Persistente con chiusura manuale |

I toast di successo hanno icona e colore verde. I toast di errore hanno icona e colore rosso.  
Il testo è sempre in italiano, chiaro e specifico — mai messaggi generici come "Errore" o "OK".

---

## Regole di stile generali

- **Tema**: Aura (PrimeVue) — dark mode seguendo le preferenze di sistema
- **Lingua interfaccia**: italiano
- **Iconografia**: esclusivamente PrimeIcons — nessuna libreria aggiuntiva
- **Font**: default del tema Aura — non personalizzare senza motivazione documentata
- **Densità**: interfaccia densa, adatta all'uso intensivo da desktop — no spaziature consumer/marketing
- **Responsive**: ottimizzato per desktop (≥ 1280px) — il mobile non è un obiettivo in questa fase

---

## Multilingua

ZeroERP è progettato per supportare più lingue fin dall'inizio. La libreria utilizzata è **vue-i18n v10**.

### Regola fondamentale
**Nessun testo visibile all'utente viene scritto direttamente nei componenti.** Ogni stringa usa la funzione di traduzione `$t()`:

```html
<!-- ❌ SBAGLIATO -->
<Button label="Salva" />

<!-- ✅ CORRETTO -->
<Button :label="$t('common.save')" />
```

### Struttura dei file di traduzione
```
src/
  locales/
    it.json    ← italiano (lingua di default)
    en.json    ← inglese (lingua di fallback)
```

Le chiavi sono organizzate per area funzionale: `common`, `nav`, `auth`, `notifications`, `confirm`, e una sezione per ogni dominio.

### Regole operative
- La lingua di default è **italiano** (`locale: 'it'`)
- La lingua di fallback è **inglese** (`fallbackLocale: 'en'`) — se una chiave manca in italiano, viene usata quella inglese
- Quando si aggiunge una nuova stringa, va aggiunta **in entrambi i file** contemporaneamente
- I nomi delle chiavi sono in inglese, il contenuto nella lingua del file
- Le chiavi specifiche di dominio vanno nella sezione del dominio corrispondente (es. `anagrafiche.new_subject`)

---

## Regole per il developer

- Ogni componente è autonomo — nessuna logica di business fuori dai composables di `core/`
- Le chiamate API passano sempre attraverso `core/api.js` — mai `fetch` o `axios` diretti nei componenti
- I testi visibili all'utente sono sempre in italiano
- Nessun `console.log` in produzione
- I componenti di dominio non importano da altri domini — solo da `core/`
- Le larghezze dei drawer sono costanti definite in `core/constants.js`

---

*ZeroERP Frontend Standards — revisione iniziale*  
*Sviluppo Concentrico — anello esterno, radici nell'infrastruttura*