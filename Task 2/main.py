from flask import Flask, render_template
from google.cloud import bigquery

app = Flask(__name__)

PROJECT_ID = os.environ["GOOGLE_CLOUD_PROJECT"]
DATASET = os.environ.get("BIGQUERY_DATASET", "assessment1_group3")

client = bigquery.Client(project=PROJECT_ID)


def run_query(sql):
    query_job = client.query(sql)
    results = query_job.result()
    return [dict(row) for row in results]


@app.route("/")
def index():
    query1 = f"""
        SELECT
            time_ref,
            SUM(value) AS trade_value
        FROM `{PROJECT_ID}.{DATASET}.trade`
        GROUP BY time_ref
        ORDER BY trade_value DESC
        LIMIT 10;
    """

    query2 = f"""
        SELECT
            c.country_label,
            t.product_type,
            SUM(
                CASE
                    WHEN t.account = 'Imports' THEN t.value
                    WHEN t.account = 'Exports' THEN -t.value
                    ELSE 0
                END
            ) AS trade_deficit_value,
            t.status
        FROM `{PROJECT_ID}.{DATASET}.trade` AS t
        JOIN `{PROJECT_ID}.{DATASET}.countries` AS c
            ON t.country_code = c.country_code
        WHERE t.time_ref BETWEEN 201301 AND 201512
          AND t.product_type = 'Goods'
          AND t.status = 'F'
        GROUP BY
            c.country_label,
            t.product_type,
            t.status
        ORDER BY trade_deficit_value DESC
        LIMIT 40;
    """

    query3 = f"""
        WITH top_time_slots AS (
            SELECT
                time_ref,
                SUM(value) AS trade_value
            FROM `{PROJECT_ID}.{DATASET}.trade`
            GROUP BY time_ref
            ORDER BY trade_value DESC
            LIMIT 10
        ),

        top_deficit_countries AS (
            SELECT
                country_code,
                SUM(
                    CASE
                        WHEN account = 'Imports' THEN value
                        WHEN account = 'Exports' THEN -value
                        ELSE 0
                    END
                ) AS trade_deficit_value
            FROM `{PROJECT_ID}.{DATASET}.trade`
            WHERE time_ref BETWEEN 201301 AND 201512
              AND product_type = 'Goods'
              AND status = 'F'
            GROUP BY country_code
            ORDER BY trade_deficit_value DESC
            LIMIT 40
        )

        SELECT
            s.service_label,
            SUM(
                CASE
                    WHEN t.account = 'Exports' THEN t.value
                    WHEN t.account = 'Imports' THEN -t.value
                    ELSE 0
                END
            ) AS trade_surplus_value
        FROM `{PROJECT_ID}.{DATASET}.trade` AS t
        JOIN top_time_slots AS ts
            ON t.time_ref = ts.time_ref
        JOIN top_deficit_countries AS tc
            ON t.country_code = tc.country_code
        JOIN `{PROJECT_ID}.{DATASET}.services` AS s
            ON CAST(t.code AS STRING) = CAST(s.code AS STRING)
        WHERE t.product_type = 'Services'
        GROUP BY
            s.service_label
        ORDER BY trade_surplus_value DESC
        LIMIT 25;
    """

    try:
        result1 = run_query(query1)
        result2 = run_query(query2)
        result3 = run_query(query3)

        return render_template(
            "index.html",
            result1=result1,
            result2=result2,
            result3=result3,
        )

    except Exception:
        app.logger.exception("BigQuery query failed")
        return "Unable to load BigQuery data.", 500


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8080, debug=True)

