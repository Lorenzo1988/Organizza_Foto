"""
ReportGeneratorAgent — Fase 5, step 31
Genera un report HTML con le statistiche della pipeline.
"""
import logging
import os
from datetime import datetime

logger = logging.getLogger(__name__)


class ReportGeneratorAgent:
    """
    Genera un report HTML in {destination}/report_{timestamp}.html
    con statistiche sulla pipeline eseguita.
    """

    def generate(self, stats: dict, destination: str) -> str:
        """
        Genera il report HTML e lo salva nella cartella di destinazione.
        Ritorna il path del file generato.
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"report_{timestamp}.html"

        try:
            os.makedirs(destination, exist_ok=True)
            report_path = os.path.join(destination, filename)

            html = self._build_html(stats, timestamp)

            with open(report_path, 'w', encoding='utf-8') as f:
                f.write(html)

            logger.debug("Report generato: %s", report_path)
            return report_path

        except Exception as e:
            logger.error("ReportGenerator: errore generazione report: %s", e)
            return ''

    def _build_html(self, stats: dict, timestamp: str) -> str:
        total = stats.get('total', 0)
        moved = stats.get('moved', 0)
        duplicates = stats.get('duplicates', 0)
        errors = stats.get('errors', 0)
        highlights = stats.get('highlights', 0)
        yearly_best = stats.get('yearly_best', {})

        yearly_rows = ''
        for year, paths in sorted(yearly_best.items()):
            yearly_rows += f'<tr><td>{year}</td><td>{len(paths)}</td></tr>\n'

        if not yearly_rows:
            yearly_rows = '<tr><td colspan="2" style="color:#666">Nessuna raccolta annuale</td></tr>'

        return f"""<!DOCTYPE html>
<html lang="it">
<head>
<meta charset="UTF-8">
<title>Photo Organizer v2 — Report {timestamp}</title>
<style>
  body {{ font-family: 'Segoe UI', sans-serif; background: #0f1117; color: #fff;
         margin: 40px auto; max-width: 800px; padding: 0 20px; }}
  h1 {{ color: #f5a623; }}
  .card {{ background: #1a1d27; border-radius: 8px; padding: 20px; margin: 16px 0; }}
  .stats {{ display: flex; gap: 16px; flex-wrap: wrap; }}
  .stat {{ background: #252836; border-radius: 6px; padding: 16px 24px; text-align: center; }}
  .stat .num {{ font-size: 2em; font-weight: bold; }}
  .stat .label {{ color: #a0aec0; font-size: 0.9em; }}
  table {{ width: 100%; border-collapse: collapse; }}
  th, td {{ padding: 8px 12px; text-align: left; border-bottom: 1px solid #2d3748; }}
  th {{ color: #a0aec0; }}
  .green {{ color: #2ecc71; }}
  .gold {{ color: #f5a623; }}
  .red {{ color: #e74c3c; }}
  .blue {{ color: #4a9eff; }}
</style>
</head>
<body>
<h1>📸 Photo Organizer v2 — Report</h1>
<p style="color:#a0aec0">Generato: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}</p>

<div class="card">
  <h2>📊 Riepilogo</h2>
  <div class="stats">
    <div class="stat"><div class="num blue">{total}</div><div class="label">Totale foto</div></div>
    <div class="stat"><div class="num green">{moved}</div><div class="label">Organizzate</div></div>
    <div class="stat"><div class="num gold">{highlights}</div><div class="label">Highlights</div></div>
    <div class="stat"><div class="num blue">{duplicates}</div><div class="label">Duplicati saltati</div></div>
    <div class="stat"><div class="num red">{errors}</div><div class="label">Errori</div></div>
  </div>
</div>

<div class="card">
  <h2>📅 Raccolte Annuali (MIGLIORI_ANNO)</h2>
  <table>
    <tr><th>Anno</th><th>Foto copiate</th></tr>
    {yearly_rows}
  </table>
</div>

</body>
</html>"""
