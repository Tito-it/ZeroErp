# Template contratto iniziale

## Scopo

Template HTML iniziale per la generazione PDF di un contratto commerciale
tramite context builder `CONTRATTO`.

## Contesto

Il template usa solo il document context preparato dal backend. Non esegue
query, chiamate esterne o logica business. Le righe esposte in `righe` sono:

- preview listino + override per contratti in modalita' A/B;
- righe `vendite.contratti_righe` per contratti in modalita' C.

## Template HTML

```html
<!doctype html>
<html lang="it">
<head>
  <meta charset="utf-8">
  <title>Contratto {{ contratto.numero or contratto.id }}</title>
  <style>
    @page {
      size: A4;
      margin: 18mm 16mm 18mm 16mm;

      @bottom-left {
        content: "Zero ERP - Template demo contratto";
        color: #6b7280;
        font-size: 8pt;
      }

      @bottom-right {
        content: "Pagina " counter(page) " di " counter(pages);
        color: #6b7280;
        font-size: 8pt;
      }
    }

    * { box-sizing: border-box; }

    body {
      margin: 0;
      color: #1f2937;
      font-family: "DejaVu Sans", Arial, sans-serif;
      font-size: 10pt;
      line-height: 1.45;
    }

    .document { width: 100%; }

    .header {
      display: table;
      width: 100%;
      padding-bottom: 14px;
      border-bottom: 2px solid #111827;
    }

    .brand,
    .doc-title {
      display: table-cell;
      vertical-align: top;
    }

    .brand { width: 52%; }

    .brand-mark {
      display: inline-block;
      min-width: 36px;
      min-height: 36px;
      padding: 8px 10px;
      background: #111827;
      color: #ffffff;
      font-size: 15pt;
      font-weight: 700;
      letter-spacing: 0;
      text-align: center;
    }

    .brand-name {
      margin-top: 8px;
      font-size: 12pt;
      font-weight: 700;
    }

    .brand-meta {
      margin-top: 2px;
      color: #6b7280;
      font-size: 8.5pt;
    }

    .doc-title {
      width: 48%;
      text-align: right;
    }

    h1 {
      margin: 0;
      color: #111827;
      font-size: 24pt;
      font-weight: 700;
      letter-spacing: 0;
    }

    .doc-number {
      margin-top: 6px;
      font-size: 11pt;
      font-weight: 700;
    }

    .status-pill {
      display: inline-block;
      margin-top: 8px;
      padding: 3px 8px;
      border: 1px solid #9ca3af;
      border-radius: 999px;
      color: #374151;
      font-size: 8pt;
      text-transform: uppercase;
    }

    .section { margin-top: 18px; }

    .two-columns {
      display: table;
      width: 100%;
      table-layout: fixed;
    }

    .column {
      display: table-cell;
      width: 50%;
      vertical-align: top;
    }

    .column + .column { padding-left: 18px; }

    .label {
      margin-bottom: 4px;
      color: #6b7280;
      font-size: 8pt;
      font-weight: 700;
      text-transform: uppercase;
    }

    .box {
      min-height: 62px;
      padding: 10px 12px;
      border: 1px solid #d1d5db;
      border-radius: 4px;
      background: #ffffff;
    }

    .box-strong {
      font-size: 11pt;
      font-weight: 700;
    }

    .muted { color: #6b7280; }

    .facts {
      width: 100%;
      border-collapse: collapse;
    }

    .facts th,
    .facts td {
      padding: 5px 0;
      border-bottom: 1px solid #e5e7eb;
      text-align: left;
      vertical-align: top;
    }

    .facts th {
      width: 42%;
      color: #6b7280;
      font-size: 8.5pt;
      font-weight: 700;
    }

    .facts td { text-align: right; }

    .table-title {
      margin: 22px 0 8px;
      color: #111827;
      font-size: 11pt;
      font-weight: 700;
    }

    table.lines {
      width: 100%;
      border-collapse: collapse;
      page-break-inside: auto;
    }

    table.lines thead { display: table-header-group; }

    table.lines tr {
      page-break-inside: avoid;
      page-break-after: auto;
    }

    table.lines th,
    table.lines td {
      padding: 7px 6px;
      border-bottom: 1px solid #e5e7eb;
      vertical-align: top;
    }

    table.lines th {
      background: #f3f4f6;
      color: #374151;
      font-size: 8pt;
      font-weight: 700;
      text-align: left;
      text-transform: uppercase;
    }

    .num {
      text-align: right;
      white-space: nowrap;
    }

    .row-description { font-weight: 700; }

    .row-note {
      margin-top: 2px;
      color: #6b7280;
      font-size: 8.5pt;
    }

    .conditions {
      margin-top: 24px;
      padding-top: 12px;
      border-top: 1px solid #d1d5db;
      color: #4b5563;
      font-size: 8.5pt;
    }
  </style>
</head>
<body>
  <main class="document">
    <header class="header">
      <div class="brand">
        <div class="brand-mark">ZE</div>
        <div class="brand-name">Emittente fiscale demo</div>
        <div class="brand-meta">Dati emittente/asset da collegare nelle prossime iterazioni</div>
      </div>

      <div class="doc-title">
        <h1>CONTRATTO</h1>
        <div class="doc-number">N. {{ contratto.numero or ("ID " ~ contratto.id) }}</div>
        <div class="status-pill">{{ contratto.stato.descrizione or contratto.stato.codice or "stato non indicato" }}</div>
      </div>
    </header>

    <section class="section two-columns">
      <div class="column">
        <div class="label">Cliente</div>
        <div class="box">
          <div class="box-strong">{{ cliente.denominazione or "Cliente non indicato" }}</div>
          {% if cliente.billing_account_codice %}
            <div class="muted">Billing account: {{ cliente.billing_account_codice }}</div>
          {% elif cliente.billing_account_id %}
            <div class="muted">Billing account ID: {{ cliente.billing_account_id }}</div>
          {% endif %}
        </div>
      </div>

      <div class="column">
        <div class="label">Dati contratto</div>
        <div class="box">
          <table class="facts">
            <tbody>
              <tr>
                <th>Data</th>
                <td>{{ contratto.data or "-" }}</td>
              </tr>
              <tr>
                <th>Validita</th>
                <td>{{ contratto.valido_dal or "-" }} - {{ contratto.valido_al or "aperto" }}</td>
              </tr>
              <tr>
                <th>Utility</th>
                <td>{{ contratto.utility.descrizione or "-" }}</td>
              </tr>
              <tr>
                <th>Ambito</th>
                <td>{{ contratto.ambito or "-" }}</td>
              </tr>
              <tr>
                <th>Modalita pricing</th>
                <td>{{ contratto.pricing.modalita or "-" }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </section>

    <section class="section two-columns">
      <div class="column">
        <div class="label">Listino e condizioni</div>
        <div class="box">
          <table class="facts">
            <tbody>
              <tr>
                <th>Listino</th>
                <td>{{ contratto.listino.codice or contratto.listino.descrizione or "-" }}</td>
              </tr>
              <tr>
                <th>Variazione</th>
                <td>
                  {% if contratto.pricing.tipo_variazione_globale %}
                    {{ contratto.pricing.tipo_variazione_globale }} {{ contratto.pricing.valore_variazione_globale or "" }}
                  {% else %}
                    -
                  {% endif %}
                </td>
              </tr>
              <tr>
                <th>Categoria</th>
                <td>{{ contratto.categoria_cliente_snapshot.descrizione or contratto.categoria_cliente_snapshot.codice or "-" }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <div class="column">
        <div class="label">Dati utility</div>
        <div class="box">
          {% if utility %}
            <table class="facts">
              <tbody>
                <tr>
                  <th>Tipo utenza</th>
                  <td>{{ utility.get("tipo_utenza_descrizione") or utility.get("tipo_utenza_codice") or "-" }}</td>
                </tr>
                <tr>
                  <th>Classe utenza</th>
                  <td>{{ utility.get("classe_utenza_descrizione") or utility.get("classe_utenza_codice") or "-" }}</td>
                </tr>
                <tr>
                  <th>Parametro</th>
                  <td>{{ utility.get("param_1_num") or utility.get("param_2_txt") or "-" }}</td>
                </tr>
              </tbody>
            </table>
          {% else %}
            <span class="muted">Nessun dettaglio utility disponibile.</span>
          {% endif %}
        </div>
      </div>
    </section>

    <section class="section">
      <div class="table-title">Condizioni economiche</div>
      <table class="lines">
        <thead>
          <tr>
            <th style="width: 6%;">#</th>
            <th>Descrizione</th>
            <th class="num" style="width: 14%;">UoM</th>
            <th class="num" style="width: 18%;">Prezzo</th>
            <th class="num" style="width: 16%;">Origine</th>
          </tr>
        </thead>
        <tbody>
          {% for r in righe %}
            <tr>
              <td>{{ r.get("ordine") or loop.index }}</td>
              <td>
                <div class="row-description">
                  {{ r.get("articolo_descrizione") or r.get("descrizione") or "Riga contratto" }}
                </div>
                {% if r.get("periodicita") or r.get("tipo_erogazione") %}
                  <div class="row-note">
                    {{ r.get("tipo_erogazione") or "" }}
                    {% if r.get("periodicita") %} - {{ r.get("periodicita") }}{% endif %}
                  </div>
                {% endif %}
              </td>
              <td class="num">{{ r.get("uom_codice") or "-" }}</td>
              <td class="num">{{ r.get("prezzo_finale") or r.get("prezzo_unitario") or r.get("override_prezzo") or "-" }}</td>
              <td class="num">{{ r.get("origine") or _meta.righe_source or "-" }}</td>
            </tr>
          {% else %}
            <tr>
              <td colspan="5" class="muted">Nessuna riga disponibile nel context.</td>
            </tr>
          {% endfor %}
        </tbody>
      </table>
    </section>

    <section class="conditions">
      <strong>Note demo.</strong>
      Template HTML di prova per stampa contratto. Il contenuto usa solo il
      document context CONTRATTO e non esegue query o chiamate esterne.
    </section>
  </main>
</body>
</html>
```

## Dipendenze DB

- `vendite.contratti`
- `vendite.contratti_righe`
- `vendite.contratti_utilities`
- `documenti.template_documenti`
- `documenti.template_documenti_versioni`

## Note

Il `file_name_pattern` consigliato per il template documento e':

```text
contratto-{contratto[numero]}.pdf
```
