from flask import Flask, render_template, request, redirect, url_for, flash
from models import init_db, get_connection, create_crawl_run, update_crawl_run
from crawler import WebCrawler

app = Flask(__name__)
app.secret_key = "advanced-crawler-secret-key"

init_db()


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        seed_url = request.form.get("seed_url", "").strip()
        max_pages = request.form.get("max_pages", "10").strip()
        same_domain = request.form.get("same_domain") == "on"

        if not seed_url:
            flash("Please enter a seed URL.", "error")
            return redirect(url_for("index"))

        if not seed_url.startswith("http://") and not seed_url.startswith("https://"):
            seed_url = "https://" + seed_url

        try:
            max_pages = int(max_pages)
            if max_pages < 1 or max_pages > 100:
                raise ValueError
        except ValueError:
            flash("Max pages must be a number between 1 and 100.", "error")
            return redirect(url_for("index"))

        run_id = create_crawl_run(seed_url, max_pages, same_domain)
        crawler = WebCrawler(run_id=run_id, max_pages=max_pages, same_domain=same_domain)
        crawled_count = crawler.crawl(seed_url)
        update_crawl_run(run_id, crawled_count)

        flash(f"Crawl completed successfully. {crawled_count} pages processed.", "success")
        return redirect(url_for("dashboard", run_id=run_id))

    return render_template("index.html")


@app.route("/dashboard/<int:run_id>")
def dashboard(run_id):
    conn = get_connection()
    cur = conn.cursor()

    run = cur.execute("SELECT * FROM crawl_runs WHERE id = ?", (run_id,)).fetchone()
    if run is None:
        conn.close()
        flash("Run not found.", "error")
        return redirect(url_for("index"))

    page_count = cur.execute(
        "SELECT COUNT(*) AS total FROM pages WHERE run_id = ?",
        (run_id,),
    ).fetchone()["total"]

    link_count = cur.execute(
        "SELECT COUNT(*) AS total FROM links WHERE run_id = ?",
        (run_id,),
    ).fetchone()["total"]

    success_count = cur.execute(
        "SELECT COUNT(*) AS total FROM pages WHERE run_id = ? AND status_code BETWEEN 200 AND 399",
        (run_id,),
    ).fetchone()["total"]

    failed_count = cur.execute(
        "SELECT COUNT(*) AS total FROM pages WHERE run_id = ? AND status_code = 0",
        (run_id,),
    ).fetchone()["total"]

    recent_pages = cur.execute(
        "SELECT * FROM pages WHERE run_id = ? ORDER BY crawled_at DESC LIMIT 8",
        (run_id,),
    ).fetchall()

    conn.close()

    return render_template(
        "dashboard.html",
        run=run,
        page_count=page_count,
        link_count=link_count,
        success_count=success_count,
        failed_count=failed_count,
        recent_pages=recent_pages,
    )


@app.route("/pages")
def pages():
    q = request.args.get("q", "").strip()
    run_id = request.args.get("run_id", "").strip()

    conn = get_connection()
    cur = conn.cursor()

    query = "SELECT * FROM pages WHERE 1=1"
    params = []

    if run_id:
        query += " AND run_id = ?"
        params.append(run_id)

    if q:
        query += " AND (url LIKE ? OR title LIKE ? OR meta_description LIKE ?)"
        like_q = f"%{q}%"
        params.extend([like_q, like_q, like_q])

    query += " ORDER BY crawled_at DESC"
    all_pages = cur.execute(query, params).fetchall()

    runs = cur.execute("SELECT * FROM crawl_runs ORDER BY started_at DESC").fetchall()
    conn.close()

    return render_template("pages.html", pages=all_pages, q=q, run_id=run_id, runs=runs)


@app.route("/page/<int:page_id>")
def page_detail(page_id):
    conn = get_connection()
    cur = conn.cursor()

    page = cur.execute("SELECT * FROM pages WHERE id = ?", (page_id,)).fetchone()
    if page is None:
        conn.close()
        flash("Page not found.", "error")
        return redirect(url_for("pages"))

    outgoing_links = cur.execute(
        "SELECT * FROM links WHERE run_id = ? AND source_url = ? LIMIT 30",
        (page["run_id"], page["url"]),
    ).fetchall()

    conn.close()
    return render_template("page_detail.html", page=page, outgoing_links=outgoing_links)


@app.route("/history")
def history():
    conn = get_connection()
    cur = conn.cursor()
    runs = cur.execute("SELECT * FROM crawl_runs ORDER BY started_at DESC").fetchall()
    conn.close()
    return render_template("history.html", runs=runs)


if __name__ == "__main__":
    app.run(debug=True)